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

/** Read `GET /games/{id}/events` until the stream ends or `signal` aborts. */
async function streamGame(
  id: string,
  onState: (state: GameState) => void,
  signal: AbortSignal,
): Promise<void> {
  const name = getNickname();
  const res = await fetch(`/games/${id}/events`, {
    signal,
    headers: {
      Accept: "text/event-stream",
      "X-Player-Token": getToken(),
      ...(name ? { "X-Player-Name": name } : {}),
    },
  });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  if (!res.body) throw new ApiError(res.status, "streaming unsupported");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    let split = buffer.indexOf("\n\n");
    while (split >= 0) {
      const frame = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      for (const line of frame.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        onState(JSON.parse(line.slice(6)) as GameState);
      }
      split = buffer.indexOf("\n\n");
    }
  }
}

export const api = {
  streamGame,
  createGame: (): Promise<{ game_id: string }> =>
    request("/games", { method: "POST" }),
  joinGame: (id: string, signal?: AbortSignal): Promise<GameState> =>
    request(`/games/${id}/join`, { method: "POST", signal }),
  // Returns null when the game has not changed since `version`, so an idle
  // poll is a tiny response instead of a full 2 KB board.
  getGame: (
    id: string,
    version: number | null = null,
    signal?: AbortSignal,
  ): Promise<GameState | null> => {
    const query = version === null ? "" : `?after=${version}`;
    return request<GameState | { changed: false; version: number }>(
      `/games/${id}${query}`,
      { signal },
    ).then((body) => ("changed" in body && !body.changed ? null : (body as GameState)));
  },
  playMove: (id: string, move: Move): Promise<GameState> =>
    request(`/games/${id}/moves`, { method: "POST", body: JSON.stringify(move) }),
  undo: (id: string): Promise<GameState> =>
    request(`/games/${id}/undo`, { method: "POST" }),
  rematch: (id: string): Promise<GameState> =>
    request(`/games/${id}/rematch`, { method: "POST" }),
  declineRematch: (id: string): Promise<GameState> =>
    request(`/games/${id}/rematch/decline`, { method: "POST" }),
  leaveGame: (id: string): Promise<GameState> =>
    request(`/games/${id}/leave`, { method: "POST" }),
  // Leaving must not depend on the page staying alive.
  leaveGameBeacon: (id: string): void => {
    const name = getNickname();
    const headers: Record<string, string> = { "X-Player-Token": getToken() };
    if (name) headers["X-Player-Name"] = name;
    void fetch(`/games/${id}/leave`, { method: "POST", headers, keepalive: true });
  },
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
