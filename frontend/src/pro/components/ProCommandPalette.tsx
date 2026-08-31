import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getStatus, listSessions } from "../../api/client";
import { filterCommands, type Command } from "../../components/commandFilter";
import styles from "./ProCommandPalette.module.css";

interface ProCommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export default function ProCommandPalette({ open, onClose }: ProCommandPaletteProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [sessionNames, setSessionNames] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [currentSessionCostTracked, setCurrentSessionCostTracked] = useState(false);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelectedIndex(0);
    listSessions()
      .then((sessions) => setSessionNames(sessions.map((s) => s.name)))
      .catch(() => setSessionNames([]));
  }, [open]);

  const currentSessionName = useMemo(() => {
    const match = location.pathname.match(/^\/pro\/sessions\/([^/]+)/);
    return match ? match[1] : null;
  }, [location.pathname]);

  useEffect(() => {
    if (!open || !currentSessionName) {
      setCurrentSessionCostTracked(false);
      return;
    }
    getStatus(currentSessionName)
      .then((status) => {
        setCurrentSessionCostTracked(
          status?.cost_per_sample !== null && status?.cost_per_sample !== undefined
        );
      })
      .catch(() => setCurrentSessionCostTracked(false));
  }, [open, currentSessionName]);

  const commands = useMemo<Command[]>(() => {
    const go = (path: string) => () => {
      navigate(path);
      onClose();
    };
    const list: Command[] = [
      { id: "new-session", label: "New session", action: go("/pro/new") },
      ...sessionNames.map((name) => ({
        id: `go-${name}`,
        label: `Go to session: ${name}`,
        action: go(`/pro/sessions/${name}`),
      })),
    ];
    if (currentSessionName) {
      list.push(
        { id: "cur-dashboard", label: "Dashboard", action: go(`/pro/sessions/${currentSessionName}`) },
        { id: "cur-recommend", label: "Recommendations", action: go(`/pro/sessions/${currentSessionName}/recommend`) },
        { id: "cur-history", label: "History", action: go(`/pro/sessions/${currentSessionName}/history`) },
        { id: "cur-settings", label: "Settings", action: go(`/pro/sessions/${currentSessionName}/settings`) }
      );
      if (currentSessionCostTracked) {
        list.push({ id: "cur-budget", label: "Budget", action: go(`/pro/sessions/${currentSessionName}/budget`) });
      }
    }
    return list;
  }, [sessionNames, currentSessionName, currentSessionCostTracked, navigate, onClose]);

  const filtered = filterCommands(commands, query);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        filtered[selectedIndex]?.action();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, filtered, selectedIndex, onClose]);

  if (!open) return null;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.palette} onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          className={styles.input}
          placeholder="Jump to a session or page…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <ul className={styles.list}>
          {filtered.map((cmd, i) => (
            <li
              key={cmd.id}
              className={i === selectedIndex ? styles.selected : undefined}
              onMouseEnter={() => setSelectedIndex(i)}
              onClick={cmd.action}
            >
              {cmd.label}
            </li>
          ))}
          {filtered.length === 0 && <li className={styles.noResults}>No matches</li>}
        </ul>
      </div>
    </div>
  );
}
