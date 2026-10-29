import { useEffect, useState } from "react";
import { api, getNickname, getToken, setNickname } from "../api";

interface Props {
  onOpen: (gameId: string) => void;
}

function readRecent(): string[] {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem("checkers-games") ?? "[]");
    return Array.isArray(raw) ? (raw as string[]) : [];
  } catch {
    return [];
  }
}

export function Lobby({ onOpen }: Props) {
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

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const { game_id } = await api.createGame();
      remember(game_id);
      onOpen(game_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create game");
    } finally {
      setBusy(false);
    }
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

          <button
            onClick={() => void create()}
            disabled={busy}
            className="btn-primary mt-4 w-full disabled:opacity-50"
          >
            {busy ? "Working…" : "Create game"}
          </button>

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

          {error && (
            <p className="pop-in mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
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

          <p className="mt-4 break-all text-[10px] text-slate-600">
            session token {getToken().slice(0, 8)}…
          </p>
        </section>
      </main>
    </div>
  );
}
