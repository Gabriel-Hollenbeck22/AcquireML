import type { ReactNode } from "react";
import { useCursorGlow } from "../hooks/useCursorGlow";
import styles from "./AppShell.module.css";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { onMouseMove } = useCursorGlow();

  return (
    <div className={styles.shell} onMouseMove={onMouseMove}>
      <div className={styles.scan} />
      <div className={styles.content}>{children}</div>
    </div>
  );
}
