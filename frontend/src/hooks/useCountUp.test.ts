import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useCountUp } from "./useCountUp";

describe("useCountUp", () => {
  it("animates from 0 up to the target value", async () => {
    const { result } = renderHook(() => useCountUp(50, 50));

    expect(result.current).toBeGreaterThanOrEqual(0);

    await waitFor(
      () => {
        expect(result.current).toBe(50);
      },
      { timeout: 1000 }
    );
  });

  it("starts a fresh animation when the target changes", async () => {
    const { result, rerender } = renderHook(({ target }) => useCountUp(target, 50), {
      initialProps: { target: 10 },
    });

    await waitFor(() => expect(result.current).toBe(10), { timeout: 1000 });

    rerender({ target: 25 });

    await waitFor(() => expect(result.current).toBe(25), { timeout: 1000 });
  });
});
