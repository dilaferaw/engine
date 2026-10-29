import type { ReactNode } from "react";
import type { Color, Kind } from "./types";

export type PieceSetId = "classic" | "flat" | "outline" | "stone";

export interface PieceArtProps {
  color: Color;
  kind: Kind;
  set: PieceSetId;
}

function Classic({ color, kind }: { color: Color; kind: Kind }) {
  const white = color === "WHITE";
  const gid = white ? "pc-w" : "pc-b";
  const ring = white ? "#00000018" : "#ffffff1f";
  const crown = white ? "#b7781f" : "#f0b429";
  return (
    <svg viewBox="0 0 100 100" aria-hidden>
      <defs>
        <radialGradient id={gid} cx="38%" cy="30%" r="75%">
          <stop offset="0%" stopColor={white ? "#ffffff" : "#4a5560"} />
          <stop offset="55%" stopColor={white ? "#e7ebef" : "#232a31"} />
          <stop offset="100%" stopColor={white ? "#9aa4ad" : "#0b0f13"} />
        </radialGradient>
      </defs>
      <circle cx="50" cy="52" r="42" fill="#000" opacity="0.28" />
      <circle cx="50" cy="49" r="42" fill={`url(#${gid})`} stroke={white ? "#8d99a3" : "#05080b"} strokeWidth="1.5" />
      <circle cx="50" cy="49" r="30" fill="none" stroke={ring} strokeWidth="2.5" />
      {kind === "KING" && (
        <path
          d="M32 40l9 7 9-13 9 13 9-7-4 22H36l-4-22z"
          fill={crown}
          stroke={white ? "#7a4f12" : "#8a6212"}
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

function Flat({ color, kind }: { color: Color; kind: Kind }) {
  const white = color === "WHITE";
  return (
    <svg viewBox="0 0 100 100" aria-hidden>
      <circle cx="50" cy="52" r="40" fill="#000" opacity="0.22" />
      <circle
        cx="50" cy="49" r="40"
        fill={white ? "#f3f5f7" : "#2b323a"}
        stroke={white ? "#b3bcc4" : "#0a0d10"}
        strokeWidth="2"
      />
      {kind === "KING" && (
        <>
          <circle cx="50" cy="49" r="25" fill="none" stroke={white ? "#c8912f" : "#f0b429"} strokeWidth="5" />
          <circle cx="50" cy="49" r="9" fill={white ? "#c8912f" : "#f0b429"} />
        </>
      )}
    </svg>
  );
}

function Outline({ color, kind }: { color: Color; kind: Kind }) {
  const white = color === "WHITE";
  const ink = white ? "#f7f9fb" : "#0d1116";
  const halo = white ? "#11161b" : "#e8edf2";
  return (
    <svg viewBox="0 0 100 100" aria-hidden>
      <circle cx="50" cy="52" r="38" fill="#000" opacity="0.18" />
      <circle cx="50" cy="49" r="38" fill="none" stroke={halo} strokeWidth="9" />
      <circle cx="50" cy="49" r="38" fill="none" stroke={ink} strokeWidth="5" />
      {kind === "KING" && (
        <circle cx="50" cy="49" r="20" fill="none" stroke={ink} strokeWidth="5" />
      )}
    </svg>
  );
}

function Stone({ color, kind }: { color: Color; kind: Kind }) {
  const white = color === "WHITE";
  const body = white ? "#f6f7f8" : "#22282e";
  const line = white ? "#9aa4ad" : "#05080b";
  const stoneAt = (y: number, k: string) => (
    <g key={k} transform={`translate(0 ${y})`}>
      <path
        d="M -32,0 L -32,10 A 32,14 0 0 0 32,10 L 32,0 Z"
        fill={body}
        stroke={line}
        strokeWidth="2"
      />
      <ellipse cx="0" cy="0" rx="32" ry="14" fill={body} stroke={line} strokeWidth="2" />
    </g>
  );
  return (
    <svg viewBox="0 0 100 100" aria-hidden>
      <ellipse cx="50" cy="78" rx="34" ry="10" fill="#000" opacity="0.25" />
      <g transform="translate(50 40)">
        {kind === "KING" ? (
          <>
            {stoneAt(16, "a")}
            {stoneAt(0, "b")}
          </>
        ) : (
          stoneAt(8, "a")
        )}
      </g>
    </svg>
  );
}

const SETS: Record<PieceSetId, (p: { color: Color; kind: Kind }) => ReactNode> = {
  classic: Classic,
  flat: Flat,
  outline: Outline,
  stone: Stone,
};

export function PieceArt({ color, kind, set }: PieceArtProps) {
  const Art = SETS[set];
  return <>{Art({ color, kind })}</>;
}
