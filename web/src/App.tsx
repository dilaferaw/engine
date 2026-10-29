import { useCallback, useEffect, useState } from "react";
import { GameScreen } from "./components/GameScreen";
import { Lobby } from "./components/Lobby";

function gameIdFromHash(): string | null {
  const hash = window.location.hash.replace(/^#\/?/, "");
  if (hash.startsWith("game/")) return hash.slice(5);
  return null;
}

export default function App() {
  const [gameId, setGameId] = useState<string | null>(() => gameIdFromHash());

  useEffect(() => {
    const onHash = () => setGameId(gameIdFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const open = useCallback((id: string) => {
    window.location.hash = `#/game/${id}`;
    setGameId(id);
  }, []);

  const leave = useCallback(() => {
    window.location.hash = "";
    setGameId(null);
  }, []);

  return gameId ? (
    <GameScreen key={gameId} gameId={gameId} onLeave={leave} />
  ) : (
    <Lobby onOpen={open} />
  );
}
