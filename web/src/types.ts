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

export interface GameState {
  game_id: string;
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
}
