# Matchmaking and the Redis broker — a short course

This document explains how "Create game" finds you an opponent, and what
Redis is actually doing. It assumes you know what an HTTP API is and nothing
about brokers.

## The problem

The game itself is a dumb key-value store: `POST /games` makes a game and
returns its id, and anyone with the id can join. That is fine when a player
shares a link. It is useless when the player just wants to click *Create game*
and be matched with whoever else is around — the server has no idea who is
around, and no way to tell an idle player that a game is waiting for them.

Matchmaking is the missing layer: a live list of who is *here and free*, plus
a way to deliver an offer to them.

## Three pieces

1. **State** — presence, a waiting queue, pending invites and "your game is
   ready" outcomes. This lives in `engine/matchmaking/store.py`.
2. **Policy** — every rule (when to invite, what accept means, who gets which
   colour) lives in `engine/matchmaking/service.py` and nowhere else.
3. **Transport** — `engine/api/lobby_routes.py` exposes policy over HTTP.

`LobbyStore` is a `Protocol`. Two implementations satisfy it:
`MemoryLobbyStore` (a dict, for tests and for `uvicorn` with one worker) and
`RedisLobbyStore` (shared between processes). The service never knows which
one it got.

## What the store keys mean

With the default prefix `lobby:`:

| Key | Redis type | Purpose | Expires |
| --- | --- | --- | --- |
| `lobby:presence:<token>` | hash `{name, busy}` | "this tab is alive"; `busy=1` means inside a game | ~20 s, refreshed by heartbeat |
| `lobby:queue` | list of tokens | players waiting for an opponent, FIFO | membership only, no TTL |
| `lobby:invite:<token>` | hash `invite_id -> JSON` | offers addressed to that player | ~35 s, refreshed when a new offer arrives |
| `lobby:outcome:<token>` | string `{game_id}` | the game a match put you in | ~65 s, consumed on read |

Presence has a TTL on purpose. A player who closes their tab stops sending
heartbeats, the key expires, and from then on they are invisible: never
invited, and silently dropped from the queue. That is how "the game knows
someone is no longer playing" without any disconnect event.

## The flow, end to end

Every browser tab sends `POST /lobby/heartbeat?busy=…` every 5 seconds. An
open lobby is `busy=false`; a tab sitting on a board is `busy=true`.

**One player clicks Create.** `POST /lobby/create`.

- The service refreshes presence, clears the caller's own inbox, and asks the
  store to atomically take the oldest queued player that is not the caller.
- *Nobody there* → the caller is appended to `lobby:queue` and every fresh,
  non-busy player gets an invite entry in `lobby:invite:<their token>`. The
  response is `{"state": "waiting"}`.
- *Somebody there* → both players are matched immediately (see below).

**A second player clicks Create.** Same call. `claim_other` finds the first
player in the queue, so instead of queueing, the second click *consumes* the
waiting entry. That is the "two people click Create at the same time" case:
whichever request reaches the store second is the one that pairs them. No
special case needed.

**Someone accepts an invite.** `POST /lobby/invites/<id>/accept`.

1. The invite is removed from the accepter's inbox (one-shot; a double click
   cannot seat you twice).
2. The sender is re-checked against the queue. If they cancelled, timed out or
   were already matched, the request fails with `410 Gone`.
3. `LobbyService._match` creates the game, seats the creator on White and the
   accepter on Black, removes both from the queue and their inboxes, marks both
   `busy`, and writes the same `game_id` into `lobby:outcome:<token>` for each.
4. The accepter's response is already `{"state": "matched", "game_id": …}`.
   The creator finds out on their next `GET /lobby/status`, which pops the
   outcome. Both tabs then set `location.hash = #/game/<id>`.

**Decline** deletes one invite; the sender keeps waiting and can be invited by
someone else. **Cancel** leaves the queue. **Entering or leaving a game**
(`busy=true`, or `POST /lobby/leave`) removes presence, queue slot, inbox and
outcome, so you are never pestered mid-game.

## So what is a message broker?

A message broker (RabbitMQ, Kafka, NATS, Redis Streams/pub-sub) is a process
that lets one service *send* and another *receive* without sharing memory or
calling each other directly. Producers write messages into a channel; consumers
read them, often later, often on another machine. The broker owns delivery,
ordering and retention. Typical uses: background jobs, fan-out events, keeping
microservices loosely coupled.

This project does **not** need one yet. What it needs is a small piece of
*shared, concurrently-edited state* that several API workers can see, plus
leases that expire by themselves when a browser disappears. Redis is the right
tool for that, and it is what we use. It is acting as a **cache with TTLs and a
coordination point**, not as a broker. If you later want server-push instead of
polling, the natural next step is Redis pub/sub or Streams — that would make it
a broker as well. Until then, say "Redis cache and coordination store".

Why Redis and not something else:

- **TTL per key.** Presence and invites need to vanish on their own. Redis does
  that natively; a SQL table needs a sweeper job.
- **Atomic primitives.** `LPUSH`/`LREM` and Lua scripts are single-threaded per
  key, so `claim_other` cannot hand the same partner to two creators. That is a
  compare-and-swap over a list.
- **Cheap, local-first.** `redis-server` is one binary; for development and a
  single worker you can skip it entirely, because `MemoryLobbyStore` implements
  the same contract.

## Running it

```sh
# single process, no Redis
uv run uvicorn engine.api:app --port 8000

# shared state across workers
docker run --rm -p 6379:6379 redis:7
REDIS_URL=redis://localhost:6379/0 uv run --extra redis uvicorn engine.api:app --workers 4
```

`create_app(lobby_store=…)` also accepts an explicit store, which is how the
tests inject `MemoryLobbyStore`. Only `engine/matchmaking/redis_store.py`
imports the `redis` package, and only inside methods, so a plain install still
runs.

## Extending it

- New rule (ranking, rematch queue, invite expiry tuning) → `service.py`.
- New state → a method on `LobbyStore` plus both implementations. Keep the
  Redis version atomic: if a rule reads and then writes the same key, put the
  whole sequence in one Lua script.
- New endpoint → `engine/api/lobby_routes.py`, keep it a one-liner over the
  service, and add any new exception to `STATUS_FOR` in `engine/api/errors.py`.
- The client side is `web/src/hooks/useLobby.ts` (heartbeat + poll) and the
  invite cards in `web/src/components/Lobby.tsx`.
