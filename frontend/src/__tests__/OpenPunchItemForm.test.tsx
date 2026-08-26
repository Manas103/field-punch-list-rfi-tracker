import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { OpenPunchItemForm } from "../components/OpenPunchItemForm";

describe("OpenPunchItemForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("submits the form and shows the routed discipline for the opened item", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 7,
          level: "L01",
          room: "R001",
          drawing_sheet: "A-101",
          discipline: "mep",
          description: "duct hanger missing insulation clamp",
          status: "open",
        }),
      }),
    );

    const onOpened = vi.fn();
    render(<OpenPunchItemForm onOpened={onOpened} />);

    fireEvent.change(screen.getByLabelText("Level"), { target: { value: "L01" } });
    fireEvent.change(screen.getByLabelText("Room"), { target: { value: "R001" } });
    fireEvent.change(screen.getByLabelText("Drawing sheet"), { target: { value: "A-101" } });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "duct hanger missing insulation clamp" },
    });
    fireEvent.click(screen.getByText("Open item"));

    await waitFor(() => expect(screen.getByTestId("opened-item-summary")).toBeInTheDocument());
    expect(screen.getByText(/routed to mep/)).toBeInTheDocument();
    expect(onOpened).toHaveBeenCalledWith(expect.objectContaining({ id: 7, discipline: "mep" }));
  });
});
