import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { CopyButton } from "./CopyButton";
import type { Color, GameState, Move } from "../types";
import { Board } from "./Board";

interface Props {
  gameId: string;
  onLeave: () => void;
}

const COLOR_LABEL: Record<Color, string> = { WHITE: "White", BLACK: "Black" };

function timeText(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

let audioCtx: AudioContext | null = null;
function cue(kind: "move" | "capture" | "end"): void {
  try {
    audioCtx ??= new AudioContext();
    const ctx = audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const now = ctx.currentTime;
    osc.type = "triangle";
    osc.frequency.setValueAtTime(
      kind === "capture" ? 196 : kind === "end" ? 523 : 392,
      now,
    );
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.07, now + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.2);
  } catch {
    /* audio unavailable */
  }
}

export function GameScreen({ gameId, onLeave }: Props) {
  const [state, setState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [lastMove, setLastMove] = useState<Move | null>(null);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  const prevCount = useRef<number | null>(null);
  const autoJoined = useRef(false);
  const stateRef = useRef<GameState | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    const tick = async () => {
      if (document.hidden) return;
      try {
        const next = await api.getGame(gameId, ctrl.signal);
        if (cancelled) return;
        const prev = prevCount.current;
        if (prev === next.move_count && stateRef.current) {
          setState((cur) =>
            cur && cur.your_color === next.your_color &&
            cur.seats.WHITE === next.seats.WHITE &&
            cur.seats.BLACK === next.seats.BLACK
              ? cur
              : next,
          );
          return;
        }
        prevCount.current = next.move_count;
        if (prev !== null && next.move_count > prev) {
          if (next.winner || next.is_draw) cue("end");
          else if (next.your_color && next.board.turn === next.your_color)
            cue(next.history.at(-1)?.captures.length ? "capture" : "move");
        }
        setState(next);
        setError(null);
      } catch (e) {
        if (cancelled || (e instanceof DOMException && e.name === "AbortError"))
          return;
        setError(e instanceof Error ? e.message : "Failed to load game");
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 600);
    document.addEventListener("visibilitychange", tick);
    return () => {
      cancelled = true;
      ctrl.abort();
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [gameId]);

  useEffect(() => {
    if (!state || autoJoined.current || state.your_color !== null) return;
    const free = [state.seats.WHITE, state.seats.BLACK].filter((s) => !s);
    if (free.length !== 1) return;
    autoJoined.current = true;
    api
      .joinGame(gameId)
      .then(setState)
      .catch((e: unknown) =>
        setError(e instanceof ApiError ? e.message : "Could not join"),
      );
  }, [state, gameId]);

  useEffect(() => {
    const id = window.setInterval(
      () => setElapsed(Date.now() - startRef.current),
      1000,
    );
    return () => window.clearInterval(id);
  }, []);

  const yourColor = state?.your_color ?? null;
  const myTurn = state !== null && yourColor !== null && state.board.turn === yourColor;

  const onSquareClick = async (sq: number) => {
    if (!state || busy) return;
    const piece = state.board.squares[sq];
    if (selected !== null) {
      const move = state.legal_moves.find(
        (m) => m.from_sq === selected && m.to_sq === sq,
      );
      if (move) {
        setBusy(true);
        setError(null);
        try {
          const next = await api.playMove(gameId, move);
          setState(next);
          setLastMove(move);
          setSelected(null);
        } catch (e) {
          setError(e instanceof ApiError ? e.message : "Move failed");
        } finally {
          setBusy(false);
        }
        return;
      }
    }
    if (piece && piece.player === yourColor && myTurn) {
      setSelected(sq === selected ? null : sq);
    } else {
      setSelected(null);
    }
  };

  const undo = async () => {
    setBusy(true);
    try {
      setState(await api.undo(gameId));
      setLastMove(null);
      setSelected(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Undo failed");
    } finally {
      setBusy(false);
    }
  };

  const requestRematch = async () => {
    setBusy(true);
    setError(null);
    try {
      setState(await api.rematch(gameId));
      setSelected(null);
      setLastMove(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Rematch failed");
    } finally {
      setBusy(false);
    }
  };

  const declineRematch = async () => {
    setBusy(true);
    try {
      await api.declineRematch(gameId);
    } catch {
      /* leaving regardless */
    } finally {
      setBusy(false);
      onLeave();
    }
  };

  const join = async () => {
    try {
      setState(await api.joinGame(gameId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not join");
    }
  };

  if (!state) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Loading game…
      </div>
    );
  }

  const opponent: Color = yourColor === "BLACK" ? "WHITE" : "BLACK";
  const board = state.board;

  const status = state.winner
    ? state.winner === yourColor
      ? "You won"
      : "You lost"
    : state.is_draw
      ? "Draw"
      : yourColor === null
        ? "Spectating"
        : !state.seats[opponent]
          ? "Waiting for opponent"
          : myTurn
            ? "Your move"
            : "Opponent's move";

  const opponentName = state.names[opponent] ?? COLOR_LABEL[opponent];
  const yourName =
    state.names[yourColor ?? "WHITE"] ??
    (yourColor ? `${COLOR_LABEL[yourColor]} player` : "Guest");
  const turnLabel = state.winner
    ? `${COLOR_LABEL[state.winner]} wins`
    : state.is_draw
      ? "Draw"
      : `${COLOR_LABEL[board.turn]} to move`;
  const inviteUrl = `${window.location.origin}${window.location.pathname}#/game/${gameId}`;
  const seatsFull = state.seats.WHITE && state.seats.BLACK;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-white/5 bg-slate-950/70 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 lg:px-6">
          <button
            onClick={onLeave}
            className="flex items-center gap-2 text-sm font-semibold text-slate-100 transition hover:text-emerald-300"
          >
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-emerald-500 text-emerald-950">♟</span>
            Checkers
          </button>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="hidden rounded-md bg-white/5 px-2 py-1 font-mono sm:block">
              #{gameId.slice(0, 8)}
            </span>
            {!seatsFull && (
              <CopyButton
                text={inviteUrl}
                idleLabel="Invite friend"
                className="rounded-md border border-white/10 px-2.5 py-1 font-medium text-slate-200 transition hover:bg-white/10"
              />
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-5 px-3 py-4 lg:grid-cols-[minmax(0,1fr)_300px] lg:px-6 lg:py-6">
        <div className="flex flex-col gap-2">
          <PlayerCard
            name={opponentName}
            color={opponent}
            active={board.turn === opponent}
            online={state.seats[opponent]}
            time={timeText(elapsed)}
          />
          <div className="board-wrap">
            <Board
              squares={board.squares}
              legalMoves={state.legal_moves}
              frozen={state.freeze}
              yourColor={yourColor}
              turn={board.turn}
              selected={selected}
              lastMove={lastMove}
              onSquareClick={(sq) => void onSquareClick(sq)}
            />
          </div>
          <PlayerCard
            name={yourName}
            color={yourColor}
            active={yourColor !== null && board.turn === yourColor}
            online={yourColor !== null}
            time={timeText(elapsed)}
            you
          />
        </div>

        <aside className="flex min-w-0 flex-col gap-3">
          <section className="card p-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                {status}
              </span>
              <span
                className={`h-2 w-2 rounded-full ${state.winner || state.is_draw ? "bg-amber-400" : myTurn ? "bg-emerald-400 animate-pulse" : "bg-slate-600"}`}
              />
            </div>
            <h1 className="mt-1 text-lg font-semibold text-slate-50">{turnLabel}</h1>
            <p className="mt-0.5 text-xs text-slate-500">
              {yourColor
                ? `You play ${COLOR_LABEL[yourColor]} · your pieces at the bottom`
                : "Spectating"}
            </p>
          </section>

          {error && (
            <div className="pop-in rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          )}

          <section className="card flex min-h-0 flex-col">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                Moves
              </span>
              <span className="text-[11px] text-slate-500 tabular-nums">
                {state.move_count}
              </span>
            </div>
            <MoveList history={state.history} yourColor={yourColor} />
          </section>

          <div className="flex flex-col gap-2">
            {yourColor === null && (
              <button onClick={() => void join()} className="btn-primary">
                Join game
              </button>
            )}
            {!seatsFull && (
              <CopyButton
                text={inviteUrl}
                idleLabel="Copy invite link"
                className="btn-ghost"
              />
            )}
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => void undo()}
                disabled={busy || state.move_count === 0}
                className="btn-subtle"
              >
                Undo
              </button>
              <button onClick={onLeave} className="btn-subtle">
                Leave
              </button>
            </div>
          </div>

          <section className="card p-4 text-xs leading-relaxed text-slate-400">
            <p className="mb-1 font-semibold text-slate-300">Variant rules</p>
            <p>Captures are forced and longest-capture wins the choice.</p>
            <p className="mt-1">A piece whose only capture is length-1 is frozen (blue).</p>
            <p className="mt-1">Promotion poisons the opponent's home row.</p>
          </section>
        </aside>
      </div>

      {state.game_over && (
        <GameOverCard
          state={state}
          yourColor={yourColor}
          yourName={yourName}
          opponentName={opponentName}
          busy={busy}
          onRematch={() => void requestRematch()}
          onDecline={() => void declineRematch()}
        />
      )}
    </div>
  );
}

function GameOverCard({
  state,
  yourColor,
  yourName,
  opponentName,
  busy,
  onRematch,
  onDecline,
}: {
  state: GameState;
  yourColor: Color | null;
  yourName: string;
  opponentName: string;
  busy: boolean;
  onRematch: () => void;
  onDecline: () => void;
}) {
  const draw = state.is_draw;
  const won = !draw && state.winner === yourColor;
  const headline = draw ? "Draw" : yourColor === null ? `${COLOR_LABEL[state.winner!]} wins` : won ? "You won" : "You lost";
  const tone = draw
    ? "from-slate-500/30 to-slate-700/30 text-slate-100"
    : won
      ? "from-emerald-400/30 to-emerald-600/20 text-emerald-100"
      : "from-rose-500/25 to-rose-700/20 text-rose-100";
  const waiting = yourColor !== null && state.rematch[yourColor];
  const opponentAsked = yourColor !== null && state.rematch[yourColor === "WHITE" ? "BLACK" : "WHITE"];

  return (
    <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="game-over-title"
        className="pop-in w-full max-w-sm overflow-hidden rounded-2xl border border-white/10 bg-slate-900 shadow-2xl"
      >
        <div className={`bg-gradient-to-br px-5 py-6 text-center ${tone}`}>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] opacity-70">
            Game over
          </p>
          <h2 id="game-over-title" className="mt-1 text-3xl font-extrabold tracking-tight">
            {headline}
          </h2>
          <p className="mt-1 text-xs opacity-80">
            {draw
              ? "Neither side could force a win."
              : yourColor === null
                ? "The game has been decided."
                : won
                  ? `You beat ${opponentName} in ${state.move_count} moves.`
                  : `${opponentName} won in ${state.move_count} moves.`}
          </p>
        </div>

        <div className="flex flex-col gap-2 p-4">
          {yourColor !== null && (
            <>
              <button
                onClick={onRematch}
                disabled={busy || waiting}
                className="btn-primary w-full disabled:opacity-50"
              >
                {waiting
                  ? opponentAsked
                    ? "Starting rematch…"
                    : "Waiting for opponent…"
                  : opponentAsked
                    ? "Accept rematch"
                    : "Rematch"}
              </button>
              <button onClick={onDecline} disabled={busy} className="btn-subtle w-full">
                Back to lobby
              </button>
            </>
          )}
          {yourColor === null && (
            <button onClick={onDecline} className="btn-ghost w-full">
              Back to lobby
            </button>
          )}
          {yourColor !== null && opponentAsked && !waiting && (
            <p className="text-center text-[11px] text-emerald-300">
              {opponentName} wants another game.
            </p>
          )}
          <p className="text-center text-[11px] text-slate-500">
            {yourName} · {state.move_count} moves played
          </p>
        </div>
      </div>
    </div>
  );
}

function MoveList({
  history,
  yourColor,
}: {
  history: GameState["history"];
  yourColor: Color | null;
}) {
  if (history.length === 0) {
    return (
      <p className="px-4 py-6 text-center text-xs text-slate-500">
        No moves yet. {yourColor ? "Make the first move." : ""}
      </p>
    );
  }
  return (
    <ol className="max-h-64 min-h-0 overflow-y-auto px-2 py-2 text-sm lg:max-h-[40vh]">
      {history.map((m, i) => (
        <li
          key={`${i}-${m.from_sq}-${m.to_sq}`}
          className="flex items-center gap-2 rounded-md px-2 py-1 odd:bg-white/[0.03]"
        >
          <span className="w-5 text-right font-mono text-[11px] text-slate-500 tabular-nums">
            {i + 1}
          </span>
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${m.player === "WHITE" ? "bg-slate-100" : "bg-slate-700 ring-1 ring-white/25"}`}
          />
          <span className="font-mono text-xs text-slate-300">
            {squareName(m.from_sq)}–{squareName(m.to_sq)}
          </span>
          {m.captures.length > 0 && (
            <span className="ml-auto rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-300">
              ×{m.captures.length}
            </span>
          )}
          {m.dies && (
            <span className="ml-auto rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
              dies
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

function squareName(sq: number): string {
  return `${String.fromCharCode(97 + (sq % 8))}${Math.floor(sq / 8) + 1}`;
}

function PlayerCard({
  name,
  color,
  active,
  online,
  time,
  you = false,
}: {
  name: string;
  color: Color | null;
  active: boolean;
  online: boolean;
  time: string;
  you?: boolean;
}) {
  const isWhite = color === "WHITE";
  return (
    <div
      className={`flex items-center justify-between rounded-xl border px-2.5 py-2 transition ${
        active
          ? "border-emerald-400/40 bg-emerald-400/[0.06]"
          : "border-white/5 bg-slate-900/50"
      }`}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <span
          className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-sm ${isWhite ? "bg-slate-100 text-slate-900" : "bg-slate-800 text-slate-100 ring-1 ring-white/15"}`}
        >
          {isWhite ? "○" : "●"}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-100">
            {name}
            {you && <span className="ml-1 text-xs font-normal text-slate-500">(you)</span>}
          </p>
          <p className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span
              className={`h-1.5 w-1.5 rounded-full ${online ? "bg-emerald-400" : "bg-slate-600"}`}
            />
            {online ? "connected" : "waiting"}
          </p>
        </div>
      </div>
      <span
        className={`rounded-md px-2 py-1 font-mono text-sm tabular-nums ${active ? "bg-emerald-400 text-emerald-950" : "bg-slate-950/80 text-slate-400"}`}
      >
        {time}
      </span>
    </div>
  );
}
