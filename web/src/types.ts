export type Color = "WHITE" | "BLACK";
export type Kind = "MAN" | "KING";

export interface Piece {
  player: Color;
  kind: Kind;
}

export interface Move {
  from_sq: number;
  to_sq: number;
  captures: number[];
  dies: boolean;
}

export interface MoveRecord extends Move {
  player: Color | null;
}

export interface LobbyInvite {
  invite_id: string;
  from_token: string;
  from_name: string | null;
}

export type LobbyState = "idle" | "waiting" | "invited" | "matched";

export interface LobbyStatus {
  state: LobbyState;
  game_id: string | null;
  invites: LobbyInvite[];
}

export interface GameState {
  game_id: string;
  version: number;
  board: {
    squares: (Piece | null)[];
    turn: Color;
    poisoned: Record<Color, boolean>;
  };
  legal_moves: Move[];
  freeze: Record<string, boolean>;
  winner: Color | null;
  is_draw: boolean;
  seats: Record<Color, boolean>;
  your_color: Color | null;
  names: Record<Color, string | null>;
  history: MoveRecord[];
  move_count: number;
  game_over: boolean;
  rematch: Record<Color, boolean>;
  left: Record<Color, boolean>;
}
