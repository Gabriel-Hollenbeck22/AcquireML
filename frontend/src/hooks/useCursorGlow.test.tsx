import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useCursorGlow } from "./useCursorGlow";

function TestTarget() {
  const { onMouseMove } = useCursorGlow();
  return (
    <div
      data-testid="target"
      onMouseMove={onMouseMove}
      style={{ position: "absolute", width: 200, height: 100 }}
    />
  );
}

describe("useCursorGlow", () => {
  it("sets --gx and --gy custom properties relative to the element on mousemove", () => {
    const { getByTestId } = render(<TestTarget />);
    const el = getByTestId("target");
    // jsdom's getBoundingClientRect returns all-zero by default, so
    // clientX/clientY map directly to --gx/--gy here.
    fireEvent.mouseMove(el, { clientX: 42, clientY: 17 });
    expect(el.style.getPropertyValue("--gx")).toBe("42px");
    expect(el.style.getPropertyValue("--gy")).toBe("17px");
  });
});
