import { useEffect, useState } from "react";
import { api, getNickname, getToken, setNickname } from "../api";
import type { Lobby as LobbyState } from "../hooks/useLobby";
import { CopyButton } from "./CopyButton";
import {
  BOARD_THEMES,
  PIECE_SETS,
  PieceArt,
  useTheme,
  type BoardThemeId,
  type PieceSetId,
} from "../theme";

interface Props {
  onOpen: (gameId: string) => void;
  lobby: LobbyState;
}

function readRecent(): string[] {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem("checkers-games") ?? "[]");
    return Array.isArray(raw) ? (raw as string[]) : [];
  } catch {
    return [];
  }
}

export function Lobby({ onOpen, lobby }: Props) {
  const [joinId, setJoinId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNick] = useState(getNickname);
  const [recent, setRecent] = useState<string[]>(readRecent);

  useEffect(() => {
    setNickname(nickname);
  }, [nickname]);

  const remember = (id: string) => {
    const next = [id, ...recent.filter((g) => g !== id)].slice(0, 6);
    setRecent(next);
    localStorage.setItem("checkers-games", JSON.stringify(next));
  };

  const join = async () => {
    const id = joinId.trim().split(/[?#/]/).filter(Boolean).pop() ?? "";
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      await api.joinGame(id);
      remember(id);
      onOpen(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not join game");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/5 bg-slate-950/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-emerald-500 text-emerald-950">♟</span>
            Checkers
          </div>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-slate-300">
            Local · no sign-up
          </span>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-5 py-10 lg:grid-cols-2 lg:py-20">
        <section>
          <p className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-medium text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Play a friend in two tabs
          </p>
          <h1 className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight text-slate-50 sm:text-6xl">
            Checkers,
            <br />
            from both sides.
          </h1>
          <p className="mt-4 max-w-lg text-slate-400">
            Create a game and share the link. Each player sees the board from
            their own color, with forced captures, frozen pieces, and a poisoned
            home row. Minimal, fast, and local-first.
          </p>
          <dl className="mt-8 grid max-w-md grid-cols-3 gap-3 text-center">
            {[
              ["Forced captures", "longest wins"],
              ["Frozen pieces", "cannot move"],
              ["Poisoned rows", "instant death"],
            ].map(([title, sub]) => (
              <div key={title} className="card px-2 py-3">
                <dt className="text-[11px] font-semibold text-slate-200">{title}</dt>
                <dd className="mt-0.5 text-[10px] text-slate-500">{sub}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="card w-full max-w-md justify-self-center p-5 shadow-2xl lg:justify-self-end">
          <h2 className="text-base font-semibold text-slate-100">Play now</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Your name is shown to your opponent.
          </p>

          <label
            htmlFor="nickname"
            className="mt-4 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500"
          >
            Display name
          </label>
          <input
            id="nickname"
            value={nickname}
            onChange={(e) => setNick(e.target.value.slice(0, 24))}
            placeholder="Player"
            autoComplete="nickname"
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950/60 px-3 py-2.5 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-emerald-400/60 focus:ring-2 focus:ring-emerald-400/20"
          />

          {lobby.status.state === "waiting" ? (
            <div className="mt-4 rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-3 text-sm text-emerald-100">
              <p className="font-medium">Looking for an opponent…</p>
              <p className="mt-0.5 text-xs text-emerald-200/70">
                Available players are being asked to join you.
              </p>
              <button
                onClick={lobby.cancel}
                className="btn-ghost mt-2 w-full text-xs"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={lobby.create}
              disabled={busy || lobby.busy}
              className="btn-primary mt-4 w-full disabled:opacity-50"
            >
              {busy || lobby.busy ? "Working…" : "Create game"}
            </button>
          )}

          <Appearance />

          <div className="my-5 flex items-center gap-3 text-[11px] text-slate-600">
            <span className="h-px flex-1 bg-white/10" />
            or join with a link
            <span className="h-px flex-1 bg-white/10" />
          </div>

          <div className="flex gap-2">
            <input
              value={joinId}
              onChange={(e) => setJoinId(e.target.value)}
              placeholder="Paste invite link or game id"
              className="min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-950/60 px-3 py-2.5 font-mono text-xs text-slate-100 outline-none transition placeholder:font-sans placeholder:text-slate-600 focus:border-emerald-400/60"
            />
            <button
              onClick={() => void join()}
              disabled={busy || !joinId.trim()}
              className="btn-ghost px-4 disabled:opacity-40"
            >
              Join
            </button>
          </div>

          {(error ?? lobby.error) && (
            <p className="pop-in mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error ?? lobby.error}
            </p>
          )}

          {lobby.status.invites.length > 0 && (
            <div className="pop-in mt-4 rounded-lg border border-sky-400/30 bg-sky-400/10 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-200/80">
                Game invites
              </p>
              <ul className="mt-2 flex flex-col gap-2">
                {lobby.status.invites.map((invite) => (
                  <li
                    key={invite.invite_id}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="truncate text-sm text-slate-100">
                      {invite.from_name ?? "A player"} wants to play
                    </span>
                    <span className="flex shrink-0 gap-1">
                      <button
                        onClick={() => lobby.accept(invite.invite_id)}
                        className="btn-primary px-3 py-1 text-xs"
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => lobby.decline(invite.invite_id)}
                        className="btn-ghost px-3 py-1 text-xs"
                      >
                        Decline
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recent.length > 0 && (
            <div className="mt-5 border-t border-white/5 pt-3">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Recent games
              </p>
              <div className="flex flex-col gap-1">
                {recent.map((id) => (
                  <button
                    key={id}
                    onClick={() => onOpen(id)}
                    className="flex items-center justify-between rounded-md px-2 py-1.5 text-left font-mono text-xs text-slate-400 transition hover:bg-white/5 hover:text-slate-200"
                  >
                    {id.slice(0, 12)}
                    <span className="text-slate-600">→</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between gap-2 border-t border-white/5 pt-3">
            <span className="truncate text-[10px] text-slate-600">
              token {getToken().slice(0, 8)}…
            </span>
            <CopyButton
              text={getToken()}
              idleLabel="Copy player code"
              className="shrink-0 rounded-md border border-white/10 px-2 py-1 text-[10px] font-medium text-slate-400 transition hover:bg-white/5 hover:text-slate-200"
            />
          </div>
        </section>
      </main>
    </div>
  );
}

const PIECE_SET_IDS = Object.keys(PIECE_SETS) as PieceSetId[];
const BOARD_THEME_IDS = Object.keys(BOARD_THEMES) as BoardThemeId[];

function Appearance() {
  const { pieceSet, board, setPieceSet, setBoardTheme } = useTheme();
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-4 border-t border-white/5 pt-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-lg px-1 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400 transition hover:text-slate-200"
      >
        Appearance
        <span className="text-slate-600">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="pop-in mt-3 flex flex-col gap-4">
          <div>
            <p className="mb-2 text-[11px] font-medium text-slate-500">Board</p>
            <div className="grid grid-cols-4 gap-2">
              {BOARD_THEME_IDS.map((id) => {
                const t = BOARD_THEMES[id];
                const active = board.id === id;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setBoardTheme(id)}
                    aria-pressed={active}
                    aria-label={`${t.label} board`}
                    className={`overflow-hidden rounded-lg border p-1 transition ${
                      active
                        ? "border-emerald-400/70 ring-2 ring-emerald-400/25"
                        : "border-white/10 hover:border-white/25"
                    }`}
                  >
                    <span className="grid aspect-square w-full grid-cols-4 overflow-hidden rounded-[3px]">
                      {Array.from({ length: 16 }, (_, i) => {
                        const file = i % 4;
                        const rank = Math.floor(i / 4);
                        return (
                          <span
                            key={i}
                            style={{
                              background:
                                (file + rank) % 2 === 0 ? t.dark : t.light,
                            }}
                          />
                        );
                      })}
                    </span>
                    <span className="mt-1 block text-[10px] text-slate-400">
                      {t.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <p className="mb-2 text-[11px] font-medium text-slate-500">Pieces</p>
            <div className="grid grid-cols-4 gap-2">
              {PIECE_SET_IDS.map((id) => {
                const active = pieceSet === id;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setPieceSet(id)}
                    aria-pressed={active}
                    className={`flex flex-col items-center rounded-lg border px-1 py-1.5 transition ${
                      active
                        ? "border-emerald-400/70 ring-2 ring-emerald-400/25"
                        : "border-white/10 hover:border-white/25"
                    }`}
                  >
                    <span className="flex aspect-square w-full items-center justify-center gap-0.5 rounded-[3px] bg-slate-800/70 p-0.5">
                      <span className="block h-full w-1/2">
                        <PieceArt color="WHITE" kind="MAN" set={id} />
                      </span>
                      <span className="block h-full w-1/2">
                        <PieceArt color="BLACK" kind="KING" set={id} />
                      </span>
                    </span>
                    <span className="mt-1 text-[10px] text-slate-400">
                      {PIECE_SETS[id].label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
