import { useEffect, useState, type ReactNode } from "react";
import "../styles/tokens.css";
import ProCommandPalette from "./ProCommandPalette";
import styles from "./ProAppShell.module.css";

interface ProAppShellProps {
  children: ReactNode;
}

export default function ProAppShell({ children }: ProAppShellProps) {
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
    <div className={`pro-root ${styles.shell}`}>
      {children}
      <button
        type="button"
        className={styles.paletteHint}
        onClick={() => setPaletteOpen(true)}
        aria-label="Open command palette"
      >
        ⌘K
      </button>
      <ProCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
