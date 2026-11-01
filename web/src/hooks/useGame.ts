import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { cue } from "../lib/sound";
import type { GameState, Move } from "../types";

// Reconnect backoff for the event stream: 0.3s, 0.6s, 1.2s ... capped at 5s.
const FIRST_RETRY_MS = 300;
const MAX_RETRY_MS = 5000;

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
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  const prevCount = useRef<number | null>(null);
  const autoJoined = useRef(false);
  const stateRef = useRef<GameState | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const apply = (next: GameState) => {
    const prev = prevCount.current;
    prevCount.current = next.move_count;
    if (prev !== null && next.move_count > prev) {
      if (next.winner || next.is_draw) cue("end");
      else if (next.your_color && next.board.turn === next.your_color)
        cue(next.history.at(-1)?.captures.length ? "capture" : "move");
    }
    setState(next);
    setError(null);
  };

  // One event stream per open game: the server pushes the state on every
  // change, so an idle board costs one TCP connection and a keepalive frame.
  useEffect(() => {
    let cancelled = false;
    let retry = FIRST_RETRY_MS;
    let timer = 0;
    let ctrl = new AbortController();

    const connect = () => {
      ctrl = new AbortController();
      api
        .streamGame(gameId, apply, ctrl.signal)
        .then(() => {
          retry = FIRST_RETRY_MS;
        })
        .catch((e: unknown) => {
          if (cancelled || (e instanceof DOMException && e.name === "AbortError"))
            return;
          retry = Math.min(retry * 2, MAX_RETRY_MS);
          setError(e instanceof Error ? e.message : "Lost connection");
        })
        .finally(() => {
          if (!cancelled) timer = window.setTimeout(connect, retry);
        });
    };

    // A hidden tab cannot paint anyway; close the stream so the server does
    // not hold a socket for nobody, and reconnect when it comes back.
    const onVisibility = () => {
      if (document.hidden) {
        ctrl.abort();
      } else {
        window.clearTimeout(timer);
        connect();
      }
    };

    connect();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelled = true;
      ctrl.abort();
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [gameId]);

  // A declined rematch ends the game screen for both players: the one who
  // clicked decline, and the one whose request was refused.
  useEffect(() => {
    if (state?.rematch_declined) onLeave();
  }, [state?.rematch_declined, onLeave]);

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

  // Tell the server this seat is gone when the component unmounts (back to
  // lobby, or the tab closed); the opponent then gets a forfeit instead of
  // waiting forever. `keepalive` lets the request outlive the page.
  useEffect(() => {
    return () => api.leaveGameBeacon(gameId);
  }, [gameId]);

  const yourColor = state?.your_color ?? null;
  const myTurn = state !== null && yourColor !== null && state.board.turn === yourColor;

  // Highlight the opponent's latest move; your own move is already obvious
  // from the piece you just touched.
  const opponentColor =
    yourColor === "BLACK" ? "WHITE" : yourColor === "WHITE" ? "BLACK" : null;
  const lastMove =
    state && opponentColor
      ? ([...state.history].reverse().find((m) => m.player === opponentColor) ??
        null)
      : null;

  const act = async (fn: () => Promise<GameState>, failure: string) => {
    setBusy(true);
    setError(null);
    try {
      const next = await fn();
      prevCount.current = next.move_count;
      setState(next);
    } catch (e) {
      setError(message(e, failure));
    } finally {
      setBusy(false);
    }
  };

  const select = (sq: number) => {
    if (!state || busy || state.game_over) return;
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
      void act(() => api.undo(gameId), "Undo failed");
    },
    join: () => void act(() => api.joinGame(gameId), "Could not join"),
    rematch: () => {
      setSelected(null);
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
