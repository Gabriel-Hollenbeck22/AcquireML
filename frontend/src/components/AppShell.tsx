import { useEffect, useState, type ReactNode } from "react";
import { useCursorGlow } from "../hooks/useCursorGlow";
import CommandPalette from "./CommandPalette";
import styles from "./AppShell.module.css";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { onMouseMove } = useCursorGlow();
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className={styles.shell} onMouseMove={onMouseMove}>
      <div className={styles.scan} />
      <div className={styles.content}>{children}</div>
      <button
        type="button"
        className={styles.paletteHint}
        onClick={() => setPaletteOpen(true)}
        aria-label="Open command palette"
      >
        ⌘K
      </button>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
