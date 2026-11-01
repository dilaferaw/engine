import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { LobbyStatus } from "../types";

const HEARTBEAT_MS = 5000;
const POLL_MS = 1500;
const IDLE: LobbyStatus = { state: "idle", game_id: null, invites: [] };

export interface Lobby {
  status: LobbyStatus;
  busy: boolean;
  error: string | null;
  create: () => void;
  cancel: () => void;
  accept: (inviteId: string) => void;
  decline: (inviteId: string) => void;
}

/**
 * Matchmaking presence for this tab. Heartbeats keep the player visible to
 * others; while idle it polls for invites and for the game a match placed us
 * in. Inside a game (`busy`) it only heartbeats as busy, so nobody invites a
 * player who is already playing.
 */
export function useLobby(busy: boolean, onMatch: (gameId: string) => void): Lobby {
  const [status, setStatus] = useState<LobbyStatus>(IDLE);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const beat = () => void api.heartbeat(busy).catch(() => undefined);
    beat();
    const id = window.setInterval(beat, HEARTBEAT_MS);
    return () => window.clearInterval(id);
  }, [busy]);

  useEffect(() => {
    if (busy) {
      void api.leaveLobby().catch(() => undefined);
      setStatus(IDLE);
      return;
    }
    let cancelled = false;
    const ctrl = new AbortController();
    const tick = async () => {
      if (document.hidden) return;
      try {
        const next = await api.lobbyStatus(ctrl.signal);
        if (cancelled) return;
        setError(null);
        if (next.state === "matched" && next.game_id) {
          onMatch(next.game_id);
          return;
        }
        setStatus(next);
      } catch {
        /* the next tick retries */
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      ctrl.abort();
      window.clearInterval(id);
    };
  }, [busy, onMatch]);

  const act = useCallback(async (fn: () => Promise<LobbyStatus>, failure: string) => {
    setPending(true);
    setError(null);
    try {
      const next = await fn();
      if (next.state === "matched" && next.game_id) onMatch(next.game_id);
      else setStatus(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : failure);
    } finally {
      setPending(false);
    }
  }, [onMatch]);

  return {
    status,
    busy: pending || status.state === "waiting",
    error,
    create: () => void act(() => api.createGameMatch(), "Could not create game"),
    cancel: () => void act(() => api.cancelLobby(), "Could not cancel"),
    accept: (inviteId) =>
      void act(() => api.acceptInvite(inviteId), "Could not accept invite"),
    decline: (inviteId) => {
      void api.declineInvite(inviteId).catch(() => undefined);
      setStatus((cur) => ({
        ...cur,
        invites: cur.invites.filter((i) => i.invite_id !== inviteId),
        state: cur.invites.length > 1 ? cur.state : "idle",
      }));
    },
  };
}
