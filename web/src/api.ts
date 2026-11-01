import type { GameState, LobbyStatus, Move } from "./types";

const TOKEN_KEY = "checkers-token";
const NAME_KEY = "checkers-nickname";

function randomToken(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function getToken(): string {
  let token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) {
    token = randomToken();
    sessionStorage.setItem(TOKEN_KEY, token);
  }
  return token;
}

// The nickname is per-tab: two tabs in the same browser are two players, so
// neither should inherit the other's name.
export function getNickname(): string {
  const scoped = sessionStorage.getItem(NAME_KEY)?.trim();
  if (scoped) return scoped;
  const legacy = localStorage.getItem(NAME_KEY)?.trim() ?? "";
  if (legacy) {
    sessionStorage.setItem(NAME_KEY, legacy);
    localStorage.removeItem(NAME_KEY);
  }
  return legacy;
}

export function setNickname(name: string): void {
  sessionStorage.setItem(NAME_KEY, name.slice(0, 24));
}


export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const name = getNickname();
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Player-Token": getToken(),
      ...(name ? { "X-Player-Name": name } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  createGame: (): Promise<{ game_id: string }> =>
    request("/games", { method: "POST" }),
  joinGame: (id: string, signal?: AbortSignal): Promise<GameState> =>
    request(`/games/${id}/join`, { method: "POST", signal }),
  getGame: (id: string, signal?: AbortSignal): Promise<GameState> =>
    request(`/games/${id}`, { signal }),
  playMove: (id: string, move: Move): Promise<GameState> =>
    request(`/games/${id}/moves`, { method: "POST", body: JSON.stringify(move) }),
  undo: (id: string): Promise<GameState> =>
    request(`/games/${id}/undo`, { method: "POST" }),
  rematch: (id: string): Promise<GameState> =>
    request(`/games/${id}/rematch`, { method: "POST" }),
  declineRematch: (id: string): Promise<GameState> =>
    request(`/games/${id}/rematch/decline`, { method: "POST" }),
  heartbeat: (busy: boolean): Promise<void> =>
    request(`/lobby/heartbeat?busy=${busy}`, { method: "POST" }),
  lobbyStatus: (signal?: AbortSignal): Promise<LobbyStatus> =>
    request("/lobby/status", { signal }),
  createGameMatch: (): Promise<LobbyStatus> =>
    request("/lobby/create", { method: "POST" }),
  acceptInvite: (inviteId: string): Promise<LobbyStatus> =>
    request(`/lobby/invites/${inviteId}/accept`, { method: "POST" }),
  declineInvite: (inviteId: string): Promise<void> =>
    request(`/lobby/invites/${inviteId}/decline`, { method: "POST" }),
  cancelLobby: (): Promise<LobbyStatus> =>
    request("/lobby/cancel", { method: "POST" }),
  leaveLobby: (): Promise<void> =>
    request("/lobby/leave", { method: "POST" }),
};
