import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import SessionLayout from "./SessionLayout";
import styles from "./SessionLayout.module.css";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<div>dashboard content</div>} />
          <Route path="recommend" element={<div>recommend content</div>} />
          <Route path="history" element={<div>history content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("SessionLayout", () => {
  it("shows the session name as a mono SESSION:// label", () => {
    renderAt("/sessions/azm-project");
    expect(screen.getByText("SESSION://azm-project")).toBeInTheDocument();
  });

  it("marks only the Dashboard link active on the index route", () => {
    renderAt("/sessions/azm-project");
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "Recommendations" })).not.toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "History" })).not.toHaveClass(styles.active);
  });

  it("marks only the Recommendations link active on the recommend route", () => {
    renderAt("/sessions/azm-project/recommend");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "Recommendations" })).toHaveClass(styles.active);
  });
});
