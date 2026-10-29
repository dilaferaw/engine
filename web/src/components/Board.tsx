import { useMemo } from "react";
import { PieceArt, useTheme } from "../theme";
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

// Fixed square slot: keeps every piece, men and kings alike, the same size.
function PieceGlyph({ piece }: { piece: Piece }) {
  const { pieceSet } = useTheme();
  return (
    <span className="piece-slot">
      <span className="piece block h-full w-full">
        <PieceArt color={piece.player} kind={piece.kind} set={pieceSet} />
      </span>
    </span>
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
  const { board: theme } = useTheme();
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
            style={{ background: dark ? theme.dark : theme.light }}
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
