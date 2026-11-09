import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { PieceArt, useTheme } from "../theme";
import type { Color, Kind } from "../types";
import { orderFor } from "../lib/board";

// Engine square indices: a1 = 0, h8 = 63.
const WHITE_PROMO = 0; // a1
const BLACK_PROMO = 63; // h8
const WHITE_DEATH = [2, 4, 6]; // c1, e1, g1
const BLACK_DEATH = [57, 59, 61]; // b8, d8, f8

interface MiniPiece {
  sq: number;
  color: Color;
  kind?: Kind;
  frozen?: boolean;
  ghost?: boolean;
}

interface Scene {
  pieces?: MiniPiece[];
  /** Gold: this square promotes (once). */
  promo?: number[];
  /** Red: landing here kills the piece. */
  death?: number[];
  /** Red ring: a poisoned home row. */
  poison?: number[];
  /** Green dot: a square this piece may move to. */
  targets?: number[];
  /** Red ring around a piece that is about to be captured. */
  captured?: number[];
  /** Small badge on a square (order numbers, "×", ...). */
  labels?: Record<number, string>;
  caption: string;
}

function MiniPieceView({
  color,
  kind,
  frozen,
  ghost,
  captured,
}: Omit<MiniPiece, "sq"> & { captured?: boolean }) {
  const { pieceSet } = useTheme();
  // `PieceArt` is a bare <svg> with no intrinsic size; `.piece-slot` and
  // `.piece` (index.css) supply it. Tint goes under the artwork so the
  // piece keeps its own colour.
  return (
    <>
      {frozen && (
        <span className="pointer-events-none absolute inset-0 bg-teal-400/35" />
      )}
      <span className={`piece-slot ${ghost ? "opacity-40" : ""}`}>
        <span
          className={`piece block h-full w-full ${captured ? "opacity-45" : ""}`}
        >
          <PieceArt color={color} kind={kind ?? "MAN"} set={pieceSet} />
        </span>
      </span>
      {frozen && (
        <span className="pointer-events-none absolute inset-[6%] rounded-full ring-2 ring-teal-300/90" />
      )}
      {captured && (
        <span className="pointer-events-none absolute inset-[4%] rounded-full ring-2 ring-red-400/90" />
      )}
    </>
  );
}

function MiniBoard({ scene }: { scene: Scene }) {
  const { board } = useTheme();
  const promo = new Set(scene.promo ?? []);
  const death = new Set(scene.death ?? []);
  const poison = new Set(scene.poison ?? []);
  const targets = new Set(scene.targets ?? []);
  const captured = new Set(scene.captured ?? []);
  const labels = scene.labels ?? {};

  const bySq = new Map<number, MiniPiece[]>();
  for (const p of scene.pieces ?? []) {
    const list = bySq.get(p.sq) ?? [];
    list.push(p);
    bySq.set(p.sq, list);
  }

  return (
    <div className="w-full">
      <div className="grid grid-cols-8 overflow-hidden rounded-lg ring-1 ring-white/10">
        {orderFor(null).map((sq) => {
          // Same ordering as the real board (`Board.tsx`), so rank 1 is at the
          // top-left and a1 is a dark square in both views. Flipping only the
          // rank here would mirror the grid and invert every square colour.
          const r = Math.floor(sq / 8);
          const f = sq % 8;
          const dark = (f + r) % 2 === 0;
          const isPromo = promo.has(sq);
          const isDeath = death.has(sq);
          const isPoison = poison.has(sq);
          const isTarget = targets.has(sq);
          const isCaptured = captured.has(sq);
          const label =
            labels[sq] ?? (isPromo ? "P" : isDeath || isPoison ? "D" : null);
          return (
            <span
              key={sq}
              className="relative aspect-square"
              style={{ background: dark ? board.dark : board.light }}
            >
              {isPromo ? (
                <span className="absolute inset-0 bg-amber-300/45 ring-2 ring-inset ring-amber-400" />
              ) : isDeath ? (
                <span className="absolute inset-0 bg-red-500/45 ring-2 ring-inset ring-red-500" />
              ) : isPoison ? (
                <span className="absolute inset-0 bg-red-500/25 ring-2 ring-inset ring-red-500/80" />
              ) : null}
              {isTarget && (
                <span className="absolute inset-0 grid place-items-center">
                  <span className="h-1/3 w-1/3 rounded-full bg-emerald-500/80" />
                </span>
              )}
              {(bySq.get(sq) ?? []).map((p, idx) => (
                <MiniPieceView key={idx} {...p} captured={isCaptured} />
              ))}
              {label && (
                <span
                  className={`absolute right-px top-px z-10 grid h-[13px] min-w-[13px] place-items-center rounded-full px-0.5 text-[8px] font-bold leading-none shadow ${
                    isPromo
                      ? "bg-amber-400 text-amber-950"
                      : isDeath || isPoison
                        ? "bg-red-500 text-white"
                        : "bg-slate-900/90 text-slate-100 ring-1 ring-white/25"
                  }`}
                >
                  {label}
                </span>
              )}
            </span>
          );
        })}
      </div>

      <p className="mt-2 min-h-[2.75em] text-center text-[11px] leading-relaxed text-slate-400">
        {scene.caption}
      </p>
      <div className="mt-1 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[10px] text-slate-500">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-amber-400" /> promotion
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-red-500" /> death
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-teal-400" /> frozen
        </span>
      </div>
    </div>
  );
}

function Bullets({ items }: { items: ReactNode[] }) {
  return (
    <ul className="flex flex-col gap-1.5 text-sm leading-relaxed text-slate-300">
      {items.map((t, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-emerald-400/70" />
          <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

function CheatRow({
  label,
  tone,
  items,
}: {
  label: string;
  tone: string;
  items: string[];
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className={`text-[11px] font-semibold uppercase tracking-[0.18em] ${tone}`}>
        {label}
      </p>
      <ul className="flex flex-col gap-1 text-sm leading-relaxed text-slate-300">
        {items.map((t) => (
          <li key={t} className="flex gap-2">
            <span className="text-slate-600">·</span>
            <span>{t}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface Section {
  id: string;
  title: string;
  body: ReactNode;
  scene: Scene;
}

const SECTIONS: Section[] = [
  {
    id: "goal",
    title: "The goal",
    body: (
      <Bullets
        items={[
          "You win by being the last player with pieces on the board.",
          "Pieces leave the board two ways: the opponent captures them, or they land on a death square and are killed.",
          "Death is neutral — the opponent gets no credit for it. The winner is simply whoever still has pieces.",
          "If it is your turn and you have no legal move at all, you lose.",
        ]}
      />
    ),
    scene: {
      pieces: [
        { sq: 36, color: "WHITE" },
        { sq: 20, color: "WHITE" },
        { sq: 27, color: "BLACK" },
        { sq: 2, color: "WHITE", ghost: true },
      ],
      death: [2],
      labels: { 2: "×" },
      caption:
        "A White man died on c1 — and Black got no capture credit for it. The last side with pieces wins.",
    },
  },
  {
    id: "board",
    title: "The board",
    body: (
      <Bullets
        items={[
          "8×8 board, only the dark squares are used — 32 in total. Each side starts with 12 men on three rows.",
          "White starts at the bottom and moves up the board. Black starts at the top and moves down. White moves first.",
          "The far row — the opponent's back row — is special. It holds one promotion square and three death squares.",
          "White promotes on a1 and dies on c1, e1 and g1. Black promotes on h8 and dies on b8, d8 and f8.",
          "The two promotion squares sit at opposite ends of the long dark diagonal.",
        ]}
      />
    ),
    scene: {
      pieces: [
        // White: ranks 8, 7, 6 (bottom three).
        ...[57, 59, 61, 63, 48, 50, 52, 54, 41, 43, 45, 47].map(
          (sq) => ({ sq, color: "WHITE" as const }),
        ),
        // Black: ranks 1, 2, 3 (top three).
        ...[0, 2, 4, 6, 9, 11, 13, 15, 16, 18, 20, 22].map((sq) => ({
          sq,
          color: "BLACK" as const,
        })),
      ],
      promo: [WHITE_PROMO, BLACK_PROMO],
      death: [...WHITE_DEATH, ...BLACK_DEATH],
      caption:
        "White at the bottom, Black at the top. Each far row holds one promotion square (gold) and three death squares (red).",
    },
  },
  {
    id: "pieces",
    title: "Pieces and movement",
    body: (
      <Bullets
        items={[
          "A man moves one square forward diagonally. Forward is toward the opponent's back row.",
          "A man never moves backward as a quiet move — but it does capture backward.",
          "A king slides any distance along a diagonal, and captures by flying: jump the first enemy piece on the diagonal and land on any empty square beyond it.",
          "A man becomes a king only on its own promotion square, not on any other square of the back row.",
          "No piece may jump over a friend, or over more than one enemy at a time.",
        ]}
      />
    ),
    scene: {
      pieces: [
        { sq: 41, color: "WHITE" },
        { sq: 54, color: "WHITE", kind: "KING" },
      ],
      // The king on g7 (54) sits on both the a1-h8 diagonal and the
      // f8/h6 anti-diagonal; dots run to the board edge to show it is
      // not limited to a short hop.
      targets: [32, 34, 0, 9, 18, 27, 36, 45, 63, 61, 47],
      caption:
        "A man steps one square forward (green dots); a king slides as far as the edge, in every diagonal direction.",
    },
  },
  {
    id: "captures",
    title: "Captures — the big change",
    body: (
      <Bullets
        items={[
          "Capturing exactly one piece is illegal. Only captures of two or more pieces count as a move.",
          "Captures are forced: if you have one, you must take it — you may not play a quiet move instead.",
          "You must take the longest capture available. If several are tied for longest, you choose between them.",
          "Men capture forward and backward, just like in standard checkers.",
          "Captured pieces are removed immediately, so you can never jump the same piece twice.",
        ]}
      />
    ),
    scene: {
      pieces: [
        { sq: 45, color: "WHITE" },
        { sq: 36, color: "BLACK" },
        { sq: 18, color: "BLACK" },
      ],
      captured: [36, 18],
      labels: { 27: "1", 9: "2" },
      caption:
        "One capture is never enough: chain two or more, in order, and take the longest chain available.",
    },
  },
  {
    id: "death",
    title: "Death squares",
    body: (
      <Bullets
        items={[
          "Landing on a death square kills the piece — any piece, either colour, men and kings alike.",
          "It applies whether you land there with a quiet move or at the end of a capture.",
          "Death is neutral: the opponent gets no capture credit for a piece that dies this way.",
          "Voluntary death: a piece that is not frozen may deliberately step onto a death square as its move. It is a legal way to pass.",
          "If a capture sequence lands on a death square, it stops there. Only the pieces captured before the landing count.",
        ]}
      />
    ),
    scene: {
      pieces: [
        { sq: 9, color: "WHITE" },
        { sq: 2, color: "WHITE", ghost: true },
      ],
      death: WHITE_DEATH,
      labels: { 2: "×" },
      caption:
        "A White man stepped onto c1 and was removed — even on purpose. The opponent got no credit for it.",
    },
  },
  {
    id: "freezing",
    title: "Freezing",
    body: (
      <Bullets
        items={[
          "A piece whose only possible capture would be a single capture is frozen. Since single captures are illegal, it has no capture at all — so it is stuck.",
          "A frozen piece cannot make a quiet move, cannot capture, and cannot even die voluntarily.",
          "Kings freeze too: a king whose only capture along its diagonals is a single one is frozen exactly like a man.",
          "Two pieces facing each other can freeze each other at the same time — as in the picture, where both pieces are frozen.",
          "A frozen piece still blocks the board, and it can still be captured like any other piece.",
          "Freezing can change from move to move — a piece that was stuck may free up, and vice versa. If all your remaining pieces are frozen, you have no legal move, which is a loss.",
        ]}
      />
    ),
    scene: {
      pieces: [
        { sq: 34, color: "WHITE", frozen: true },
        { sq: 25, color: "BLACK", frozen: true },
        { sq: 50, color: "WHITE" },
      ],
      caption:
        "The two teal men on c5 and b4 each have only a single capture, so they freeze each other. The White man on c7 has no capture at all, so it is free to move.",
    },
  },
  {
    id: "promotion",
    title: "Promotion and poisoning",
    body: (
      <Bullets
        items={[
          "A man that reaches its promotion square becomes a king immediately.",
          "Promoting also poisons the opponent's entire home row: all four dark squares of that row become death squares for the rest of the game, for both players.",
          "White promoting at a1 poisons rank 1. Black promoting at h8 poisons rank 8. Each side's poison is independent of the other's.",
          "The king that just promoted is safe where it stands, because death only happens on landing. But it can never return to that square once it leaves.",
          "Each side's promotion square can only ever be used once: after the first promotion, that whole row is death.",
        ]}
      />
    ),
    scene: {
      pieces: [{ sq: WHITE_PROMO, color: "WHITE", kind: "KING" }],
      promo: [WHITE_PROMO],
      poison: [WHITE_PROMO, ...WHITE_DEATH],
      caption:
        "White promoted at a1: the new king stands there safely, while Black's whole home row (rank 1) is now death for everyone.",
    },
  },
  {
    id: "cheat",
    title: "Cheat sheet: what changed from standard checkers",
    body: (
      <div className="flex flex-col gap-4">
        <CheatRow
          label="Same as standard"
          tone="text-slate-400"
          items={[
            "8×8 board, 12 pieces each, three rows of setup.",
            "Men move one square forward diagonally and capture forward and backward.",
            "Kings slide and capture by flying along the diagonals.",
            "Captures are compulsory, and you may not jump a friend or more than one enemy at a time.",
          ]}
        />
        <CheatRow
          label="Changed from standard"
          tone="text-sky-300/90"
          items={[
            "Only one square per side promotes — a1 for White, h8 for Black — not the whole back row.",
            "You must take the longest capture. In standard checkers any capture would do.",
            "Single captures are illegal, so a piece that can only single-capture is frozen instead.",
          ]}
        />
        <CheatRow
          label="Brand new"
          tone="text-amber-300/90"
          items={[
            "Death squares: landing on one kills the piece, with no capture credit to anyone.",
            "Voluntary death: stepping onto a death square is a legal, pass-like move.",
            "Mid-sequence death: a capture chain that lands on a death square ends there.",
            "Freezing: a piece with only a single capture available cannot move at all.",
            "Promotion poisoning: promoting turns the opponent's whole home row into death squares.",
            "Grandfathering: the newly promoted king is safe on its poisoned square, but can never return to it.",
          ]}
        />
      </div>
    ),
    scene: {
      pieces: [
        { sq: 34, color: "WHITE", frozen: true },
        { sq: 25, color: "BLACK" },
      ],
      promo: [WHITE_PROMO],
      death: WHITE_DEATH,
      caption:
        "Gold promotes once. Red kills on landing. Teal cannot move at all.",
    },
  },
];

export function RulesPanel({
  onClose,
  closeLabel = "Got it",
}: {
  onClose?: () => void;
  closeLabel?: string;
}) {
  const [activeId, setActiveId] = useState<string>(SECTIONS[0].id);
  const active = SECTIONS.find((s) => s.id === activeId) ?? SECTIONS[0];
  const activeRef = useRef<HTMLElement | null>(null);
  const firstRender = useRef(true);

  // Bring the freshly opened section to the middle of the viewport so the
  // whole explanation is readable without hunting for it.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    activeRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeId]);

  return (
    <div className="mx-auto grid w-full max-w-5xl grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
      <div className="flex min-w-0 flex-col gap-2">
        {SECTIONS.map((s) => {
          const isOpen = s.id === activeId;
          return (
            <section
              key={s.id}
              ref={isOpen ? activeRef : undefined}
              className="card overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setActiveId(s.id)}
                aria-expanded={isOpen}
                className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition ${
                  isOpen ? "bg-white/[0.04]" : "hover:bg-white/5"
                }`}
              >
                <span
                  className={`text-sm font-semibold ${
                    isOpen ? "text-slate-50" : "text-slate-200"
                  }`}
                >
                  {s.title}
                </span>
                <span className={`shrink-0 ${isOpen ? "text-emerald-300" : "text-slate-500"}`}>
                  {isOpen ? "−" : "+"}
                </span>
              </button>
              {isOpen && (
                <div className="pop-in border-t border-white/5 px-4 py-3">
                  {s.body}
                  <div className="mt-3 lg:hidden">
                    <MiniBoard scene={s.scene} />
                  </div>
                </div>
              )}
            </section>
          );
        })}

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="btn-primary mt-1 self-start px-4 py-2 text-sm"
          >
            {closeLabel}
          </button>
        )}
      </div>

      <aside className="hidden lg:sticky lg:top-4 lg:block lg:self-start">
        <div className="card p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {active.title}
          </p>
          <MiniBoard scene={active.scene} />
        </div>
      </aside>
    </div>
  );
}
