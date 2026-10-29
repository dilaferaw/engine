import { useMemo } from "react";
import type { Color, Move, Piece } from "../types";

interface Props {
  squares: (Piece | null)[];
  legalMoves: Move[];
  frozen: Record<string, boolean>;
  yourColor: Color | null;
  turn: Color;
  selected: number | null;
  lastMove: Move | null;
  onSquareClick: (sq: number) => void;
}

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];

// White pieces start on ranks 5-7 and Black on ranks 0-2, so the side to
// move is drawn from the rank containing its own back row upward.
function orderFor(color: Color | null): number[] {
  const out: number[] = [];
  if (color === "BLACK") {
    for (let r = 7; r >= 0; r--) for (let f = 7; f >= 0; f--) out.push(r * 8 + f);
  } else {
    for (let r = 0; r < 8; r++) for (let f = 0; f < 8; f++) out.push(r * 8 + f);
  }
  return out;
}

function PieceGlyph({ piece }: { piece: Piece }) {
  const white = piece.player === "WHITE";
  const base = white ? "#f4f6f8" : "#262c33";
  const edge = white ? "#9aa4ad" : "#0a0e12";
  const crown = white ? "#c2812b" : "#f0b429";
  return (
    <div
      className="piece relative flex h-[84%] w-[84%] items-center justify-center rounded-full"
      style={{
        background: `radial-gradient(circle at 34% 26%, #ffffffcc 0%, transparent 32%), radial-gradient(circle at 50% 58%, ${base}, ${edge})`,
        boxShadow:
          "0 1px 1px rgba(255,255,255,0.55) inset, 0 -3px 5px rgba(0,0,0,0.35) inset, 0 3px 4px rgba(0,0,0,0.45), 0 1px 0 rgba(0,0,0,0.5)",
      }}
    >
      <span
        className="pointer-events-none absolute inset-[14%] rounded-full border"
        style={{ borderColor: white ? "#00000014" : "#ffffff1f" }}
      />
      {piece.kind === "KING" && (
        <svg
          viewBox="0 0 24 24"
          className="h-[52%] w-[52%] drop-shadow"
          fill="none"
          stroke={crown}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M3 8l4 3 5-6 5 6 4-3-2 10H5L3 8z" />
          <path d="M6 21h12" />
        </svg>
      )}
    </div>
  );
}

export function Board({
  squares,
  legalMoves,
  frozen,
  yourColor,
  turn,
  selected,
  lastMove,
  onSquareClick,
}: Props) {
  const order = useMemo(() => orderFor(yourColor), [yourColor]);

  const destinations = useMemo(() => {
    if (selected === null) return new Map<number, Move>();
    const m = new Map<number, Move>();
    for (const mv of legalMoves) {
      if (mv.from_sq === selected && !m.has(mv.to_sq)) m.set(mv.to_sq, mv);
    }
    return m;
  }, [selected, legalMoves]);

  const movable = useMemo(
    () => new Set(legalMoves.map((m) => m.from_sq)),
    [legalMoves],
  );

  return (
    <div className="board-grid relative w-full select-none">
      {order.map((sq) => {
        const f = sq % 8;
        const r = Math.floor(sq / 8);
        const dark = (f + r) % 2 === 0;
        const piece = squares[sq];
        const isSelected = selected === sq;
        const isDest = destinations.has(sq);
        const isLast = lastMove && (lastMove.from_sq === sq || lastMove.to_sq === sq);
        const canPick = piece !== null && movable.has(sq) && piece.player === turn;
        const isFrozen = frozen[String(sq)] === true;
        const showFile = yourColor === "BLACK" ? r === 0 : r === 7;
        const showRank = yourColor === "BLACK" ? f === 7 : f === 0;
        return (
          <button
            key={sq}
            type="button"
            aria-label={`${FILES[f]}${r + 1}${piece ? ` ${piece.player} ${piece.kind}` : ""}`}
            onClick={() => onSquareClick(sq)}
            className="relative flex items-center justify-center"
            style={{ background: dark ? "#769656" : "#eeeed2" }}
          >
            {isLast && <span className="absolute inset-0 bg-yellow-300/30" />}
            {lastMove?.captures.includes(sq) && (
              <span className="absolute inset-0 bg-rose-500/35 ring-2 ring-inset ring-rose-400/50" />
            )}
            {isSelected && (
              <span className="absolute inset-0 ring-4 ring-inset ring-amber-400/90" />
            )}
            {canPick && !isSelected && (
              <span className="absolute inset-0 ring-2 ring-inset ring-white/10" />
            )}
            {isFrozen && piece && (
              <span className="absolute inset-0 bg-sky-400/25" />
            )}
            {piece && <PieceGlyph piece={piece} />}
            {isDest && !piece && (
              <span className="pulse-ring h-[28%] w-[28%] rounded-full bg-emerald-900/40 shadow-[0_0_0_2px_rgba(255,255,255,0.25)]" />
            )}
            {isDest && piece && (
              <span className="absolute inset-1 rounded-full ring-4 ring-rose-500/85" />
            )}
            {showFile && (
              <span
                className="absolute bottom-0.5 left-1 text-[min(2.2vw,0.65rem)] font-semibold"
                style={{ color: dark ? "#eeeed2" : "#769656" }}
              >
                {FILES[f]}
              </span>
            )}
            {showRank && (
              <span
                className="absolute right-1 top-0.5 text-[min(2.2vw,0.65rem)] font-semibold"
                style={{ color: dark ? "#eeeed2" : "#769656" }}
              >
                {r + 1}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
