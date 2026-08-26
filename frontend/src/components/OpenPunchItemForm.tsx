import { useState } from "react";
import { openPunchItem } from "../api/client";
import type { PunchItem } from "../api/types";

export function OpenPunchItemForm({ onOpened }: { onOpened?: (item: PunchItem) => void }) {
  const [level, setLevel] = useState("");
  const [room, setRoom] = useState("");
  const [sheet, setSheet] = useState("");
  const [description, setDescription] = useState("");
  const [lastOpened, setLastOpened] = useState<PunchItem | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const item = await openPunchItem({ level, room, drawing_sheet: sheet, description });
    setLastOpened(item);
    onOpened?.(item);
  }

  return (
    <form aria-label="Open punch item" onSubmit={submit}>
      <h2>Open punch item</h2>
      <label>
        Level
        <input value={level} onChange={(e) => setLevel(e.target.value)} required />
      </label>
      <label>
        Room
        <input value={room} onChange={(e) => setRoom(e.target.value)} required />
      </label>
      <label>
        Drawing sheet
        <input value={sheet} onChange={(e) => setSheet(e.target.value)} required />
      </label>
      <label>
        Description
        <input value={description} onChange={(e) => setDescription(e.target.value)} required />
      </label>
      <button type="submit">Open item</button>

      {lastOpened && (
        <p data-testid="opened-item-summary">
          Opened item {lastOpened.id}, routed to {lastOpened.discipline}, status {lastOpened.status}.
        </p>
      )}
    </form>
  );
}
