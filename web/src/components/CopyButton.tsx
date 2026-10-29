import { useEffect, useRef, useState } from "react";
import { copyText } from "../api";

interface Props {
  text: string;
  idleLabel: string;
  className?: string;
}

type Status = "idle" | "copied" | "failed";

export function CopyButton({ text, idleLabel, className = "" }: Props) {
  const [status, setStatus] = useState<Status>("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const onClick = async () => {
    const ok = await copyText(text);
    setStatus(ok ? "copied" : "failed");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setStatus("idle"), 2000);
  };

  const label =
    status === "copied" ? "Copied!" : status === "failed" ? "Copy failed" : idleLabel;

  return (
    <button
      type="button"
      onClick={() => void onClick()}
      aria-live="polite"
      className={[
        className,
        status === "copied"
          ? "text-emerald-300"
          : status === "failed"
            ? "text-rose-300"
            : "",
      ].join(" ")}
    >
      {status === "copied" ? "✓ " : ""}
      {label}
    </button>
  );
}
