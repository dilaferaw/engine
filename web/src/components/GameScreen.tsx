import { useGame } from "../hooks/useGame";
import { timeText } from "../lib/format";
import type { Color } from "../types";
import { Board } from "./Board";
import { CopyButton } from "./CopyButton";
import { GameOverCard } from "./GameOverCard";
import { MoveList } from "./MoveList";
import { PlayerCard } from "./PlayerCard";

interface Props {
  gameId: string;
  onLeave: () => void;
}

const COLOR_LABEL: Record<Color, string> = { WHITE: "White", BLACK: "Black" };

export function GameScreen({ gameId, onLeave }: Props) {
  const {
    state,
    error,
    busy,
    selected,
    lastMove,
    elapsed,
    yourColor,
    myTurn,
    select,
    undo,
    join,
    rematch,
    declineRematch,
  } = useGame(gameId, onLeave);

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
              onSquareClick={select}
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
          onRematch={rematch}
          onDecline={declineRematch}
        />
      )}
    </div>
  );
}

