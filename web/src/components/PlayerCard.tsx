import type { Color } from "../types";

interface Props {
  name: string;
  color: Color | null;
  active: boolean;
  online: boolean;
  time: string;
  you?: boolean;
}

export function PlayerCard({ name, color, active, online, time, you = false }: Props) {
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
