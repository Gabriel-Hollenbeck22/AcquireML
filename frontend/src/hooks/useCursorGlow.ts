import type { MouseEvent } from "react";

export function useCursorGlow() {
  function onMouseMove(event: MouseEvent<HTMLElement>) {
    const el = event.currentTarget;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--gx", `${event.clientX - rect.left}px`);
    el.style.setProperty("--gy", `${event.clientY - rect.top}px`);
  }

  return { onMouseMove };
}
