import type { Color } from "../types";

export const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];

/** White starts on ranks 5-7 and Black on 0-2, so each side is drawn with
 * its own back row at the bottom of the screen. */
export function orderFor(color: Color | null): number[] {
  const out: number[] = [];
  if (color === "BLACK") {
    for (let r = 7; r >= 0; r--) for (let f = 7; f >= 0; f--) out.push(r * 8 + f);
  } else {
    for (let r = 0; r < 8; r++) for (let f = 0; f < 8; f++) out.push(r * 8 + f);
  }
  return out;
}

export function squareName(sq: number): string {
  return `${FILES[sq % 8]}${Math.floor(sq / 8) + 1}`;
}
