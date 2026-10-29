import type { GameState, Move } from "./types";

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

export function forceNewToken(): string {
  const token = randomToken();
  sessionStorage.setItem(TOKEN_KEY, token);
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

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    field.remove();
    return ok;
  }
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
};
