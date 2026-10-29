export type Cue = "move" | "capture" | "end";

let ctx: AudioContext | null = null;

const FREQ: Record<Cue, number> = { move: 392, capture: 196, end: 523 };

/** Short synthesised blip; silently does nothing when audio is unavailable. */
export function cue(kind: Cue): void {
  try {
    ctx ??= new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const now = ctx.currentTime;
    osc.type = "triangle";
    osc.frequency.setValueAtTime(FREQ[kind], now);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.07, now + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.2);
  } catch {
    /* audio unavailable */
  }
}
