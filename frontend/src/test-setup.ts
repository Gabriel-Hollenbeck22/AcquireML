import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== "undefined" && !window.ResizeObserver) {
  window.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

// Mock CSS modules to return identity mappings during tests
vi.mock("./components/SessionLayout.module.css", () => ({
  default: new Proxy(
    {},
    {
      get: (_target, prop) => {
        if (typeof prop === "symbol") return undefined;
        return String(prop);
      },
    }
  ),
}));
