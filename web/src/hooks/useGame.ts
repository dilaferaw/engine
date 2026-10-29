import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { cue } from "../lib/sound";
import type { GameState, Move } from "../types";

function message(e: unknown, fallback: string): string {
  return e instanceof ApiError ? e.message : fallback;
}

interface Game {
  state: GameState | null;
  error: string | null;
  busy: boolean;
  selected: number | null;
  lastMove: Move | null;
  elapsed: number;
  yourColor: GameState["your_color"];
  myTurn: boolean;
  select: (sq: number) => void;
  undo: () => void;
  join: () => void;
  rematch: () => void;
  declineRematch: () => void;
}

/** Owns all game state, polling, and player actions for one game id. */
export function useGame(gameId: string, onLeave: () => void): Game {
  const [state, setState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [lastMove, setLastMove] = useState<Move | null>(null);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  const prevCount = useRef<number | null>(null);
  const autoJoined = useRef(false);
  const stateRef = useRef<GameState | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    const tick = async () => {
      if (document.hidden) return;
      try {
        const next = await api.getGame(gameId, ctrl.signal);
        if (cancelled) return;
        const prev = prevCount.current;
        if (prev === next.move_count && stateRef.current) {
          setState((cur) =>
            cur &&
            cur.your_color === next.your_color &&
            cur.seats.WHITE === next.seats.WHITE &&
            cur.seats.BLACK === next.seats.BLACK &&
            cur.rematch.WHITE === next.rematch.WHITE &&
            cur.rematch.BLACK === next.rematch.BLACK
              ? cur
              : next,
          );
          return;
        }
        prevCount.current = next.move_count;
        if (prev !== null && next.move_count > prev) {
          if (next.winner || next.is_draw) cue("end");
          else if (next.your_color && next.board.turn === next.your_color)
            cue(next.history.at(-1)?.captures.length ? "capture" : "move");
        }
        setState(next);
        setError(null);
      } catch (e) {
        if (cancelled || (e instanceof DOMException && e.name === "AbortError"))
          return;
        setError(e instanceof Error ? e.message : "Failed to load game");
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 600);
    document.addEventListener("visibilitychange", tick);
    return () => {
      cancelled = true;
      ctrl.abort();
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [gameId]);

  useEffect(() => {
    if (!state || autoJoined.current || state.your_color !== null) return;
    const free = [state.seats.WHITE, state.seats.BLACK].filter((s) => !s);
    if (free.length !== 1) return;
    autoJoined.current = true;
    api
      .joinGame(gameId)
      .then(setState)
      .catch((e: unknown) => setError(message(e, "Could not join")));
  }, [state, gameId]);

  useEffect(() => {
    const id = window.setInterval(
      () => setElapsed(Date.now() - startRef.current),
      1000,
    );
    return () => window.clearInterval(id);
  }, []);

  const yourColor = state?.your_color ?? null;
  const myTurn = state !== null && yourColor !== null && state.board.turn === yourColor;

  const act = async (fn: () => Promise<GameState>, failure: string) => {
    setBusy(true);
    setError(null);
    try {
      setState(await fn());
    } catch (e) {
      setError(message(e, failure));
    } finally {
      setBusy(false);
    }
  };

  const select = (sq: number) => {
    if (!state || busy) return;
    const piece = state.board.squares[sq];
    if (selected !== null) {
      const move = state.legal_moves.find(
        (m) => m.from_sq === selected && m.to_sq === sq,
      );
      if (move) {
        setBusy(true);
        setError(null);
        api
          .playMove(gameId, move)
          .then((next) => {
            setState(next);
            setLastMove(move);
            setSelected(null);
          })
          .catch((e: unknown) => setError(message(e, "Move failed")))
          .finally(() => setBusy(false));
        return;
      }
    }
    if (piece && piece.player === yourColor && myTurn) {
      setSelected(sq === selected ? null : sq);
    } else {
      setSelected(null);
    }
  };

  return {
    state,
    error,
    busy,
    selected,
    lastMove,
    elapsed,
    yourColor,
    myTurn,
    select,
    undo: () => {
      setSelected(null);
      setLastMove(null);
      void act(() => api.undo(gameId), "Undo failed");
    },
    join: () => void act(() => api.joinGame(gameId), "Could not join"),
    rematch: () => {
      setSelected(null);
      setLastMove(null);
      void act(() => api.rematch(gameId), "Rematch failed");
    },
    declineRematch: () => {
      setBusy(true);
      api
        .declineRematch(gameId)
        .catch(() => undefined)
        .finally(() => {
          setBusy(false);
          onLeave();
        });
    },
  };
}
