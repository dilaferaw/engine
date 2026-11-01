import type { Color, GameState } from "../types";

const COLOR_LABEL: Record<Color, string> = { WHITE: "White", BLACK: "Black" };

interface Props {
  state: GameState;
  yourColor: Color | null;
  yourName: string;
  opponentName: string;
  busy: boolean;
  onRematch: () => void;
  onDecline: () => void;
}

export function GameOverCard({
  state,
  yourColor,
  yourName,
  opponentName,
  busy,
  onRematch,
  onDecline,
}: Props) {
  const draw = state.is_draw;
  const won = !draw && state.winner === yourColor;
  const headline = draw
    ? "Draw"
    : yourColor === null
      ? `${COLOR_LABEL[state.winner!]} wins`
      : won
        ? "You won"
        : "You lost";
  const tone = draw
    ? "from-slate-500/30 to-slate-700/30 text-slate-100"
    : won
      ? "from-emerald-400/30 to-emerald-600/20 text-emerald-100"
      : "from-rose-500/25 to-rose-700/20 text-rose-100";
  const opponent: Color = yourColor === "BLACK" ? "WHITE" : "BLACK";
  const opponentLeft = yourColor !== null && state.left[opponent];
  const waiting = yourColor !== null && state.rematch[yourColor];
  const opponentAsked =
    yourColor !== null && state.rematch[opponent];

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
            {opponentLeft
              ? `${opponentName} left the game.`
              : draw
                ? "Neither side had a piece left."
                : yourColor === null
                  ? "The game has been decided."
                  : won
                    ? `You beat ${opponentName} in ${state.move_count} moves.`
                    : `${opponentName} won in ${state.move_count} moves.`}
          </p>
        </div>

        <div className="flex flex-col gap-2 p-4">
          {yourColor !== null && opponentLeft && (
            <button onClick={onDecline} disabled={busy} className="btn-primary w-full">
              Back to lobby
            </button>
          )}
          {yourColor !== null && !opponentLeft && (
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
          {yourColor !== null && !opponentLeft && opponentAsked && !waiting && (
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
