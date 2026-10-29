import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { PieceSetId } from "./pieceArt";

export type { PieceSetId } from "./pieceArt";
export { PieceArt } from "./pieceArt";

export type BoardThemeId = "green" | "brown" | "blue" | "slate";

export interface BoardTheme {
  id: BoardThemeId;
  label: string;
  light: string;
  dark: string;
}

export const BOARD_THEMES: Record<BoardThemeId, BoardTheme> = {
  green: { id: "green", label: "Green", light: "#eeeed2", dark: "#769656" },
  brown: { id: "brown", label: "Wood", light: "#f0d9b5", dark: "#b58863" },
  blue: { id: "blue", label: "Ocean", light: "#dee3e6", dark: "#8ca2ad" },
  slate: { id: "slate", label: "Slate", light: "#cfd4dc", dark: "#6b7686" },
};

export const PIECE_SETS: Record<PieceSetId, { id: PieceSetId; label: string }> = {
  classic: { id: "classic", label: "Classic" },
  flat: { id: "flat", label: "Flat" },
  outline: { id: "outline", label: "Outline" },
  stone: { id: "stone", label: "Stone" },
};

const PIECE_KEY = "checkers-piece-set";
const BOARD_KEY = "checkers-board-theme";

function read<T extends string>(
  key: string,
  allowed: Record<T, unknown>,
  fallback: T,
): T {
  const raw = localStorage.getItem(key);
  return raw && raw in allowed ? (raw as T) : fallback;
}

interface ThemeValue {
  pieceSet: PieceSetId;
  board: BoardTheme;
  setPieceSet: (id: PieceSetId) => void;
  setBoardTheme: (id: BoardThemeId) => void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [pieceSet, setPieceSetState] = useState<PieceSetId>(() =>
    read(PIECE_KEY, PIECE_SETS, "classic"),
  );
  const [boardId, setBoardId] = useState<BoardThemeId>(() =>
    read(BOARD_KEY, BOARD_THEMES, "green"),
  );

  useEffect(() => {
    localStorage.setItem(PIECE_KEY, pieceSet);
  }, [pieceSet]);
  useEffect(() => {
    localStorage.setItem(BOARD_KEY, boardId);
  }, [boardId]);

  const setPieceSet = useCallback((id: PieceSetId) => setPieceSetState(id), []);
  const setBoardTheme = useCallback((id: BoardThemeId) => setBoardId(id), []);

  const value = useMemo<ThemeValue>(
    () => ({ pieceSet, board: BOARD_THEMES[boardId], setPieceSet, setBoardTheme }),
    [pieceSet, boardId, setPieceSet, setBoardTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}

