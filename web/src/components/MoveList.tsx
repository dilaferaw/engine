import { squareName } from "../lib/board";
import type { Color, GameState } from "../types";

export function MoveList({
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
