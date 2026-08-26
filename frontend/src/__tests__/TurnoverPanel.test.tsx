import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { TurnoverPanel } from "../components/TurnoverPanel";

describe("TurnoverPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the refusal, naming the blocking item, when turnover is blocked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          level: "L01",
          room: "R001",
          allowed: false,
          blocking_punch_items: [{ id: 42, description: "wall paint touch-up needed" }],
          blocking_rfis: [],
          message: "level L01 room R001: turnover refused, still open: punch item 42 (wall paint touch-up needed)",
        }),
      }),
    );

    render(<TurnoverPanel />);
    fireEvent.click(screen.getByText("Check turnover"));

    await waitFor(() => expect(screen.getByTestId("turnover-blocked")).toBeInTheDocument());
    expect(screen.getByText(/Punch item 42: wall paint touch-up needed/)).toBeInTheDocument();
  });

  it("shows turnover allowed when nothing blocks it", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          level: "L01",
          room: "R002",
          allowed: true,
          blocking_punch_items: [],
          blocking_rfis: [],
          message: "level L01 room R002: turnover allowed",
        }),
      }),
    );

    render(<TurnoverPanel />);
    fireEvent.click(screen.getByText("Check turnover"));

    await waitFor(() => expect(screen.getByTestId("turnover-allowed")).toBeInTheDocument());
  });

  it("shows an error message when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: "Internal Server Error", text: async () => "boom" }));

    render(<TurnoverPanel />);
    fireEvent.click(screen.getByText("Check turnover"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
