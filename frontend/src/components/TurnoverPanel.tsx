import { useState } from "react";
import { fetchTurnover } from "../api/client";
import type { TurnoverResult } from "../api/types";

/** Looks up a room's turnover status and names exactly which punch items
 * and RFIs are still blocking it, if any. Never says a room merely "isn't
 * ready"; it says which item is still open. */
export function TurnoverPanel() {
  const [level, setLevel] = useState("L01");
  const [room, setRoom] = useState("R001");
  const [result, setResult] = useState<TurnoverResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function checkTurnover() {
    setError(null);
    try {
      const outcome = await fetchTurnover(level, room);
      setResult(outcome);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setResult(null);
    }
  }

  return (
    <section aria-label="Room turnover">
      <h2>Room turnover</h2>
      <label>
        Level
        <input value={level} onChange={(e) => setLevel(e.target.value)} />
      </label>
      <label>
        Room
        <input value={room} onChange={(e) => setRoom(e.target.value)} />
      </label>
      <button onClick={checkTurnover}>Check turnover</button>

      {error && <p role="alert">{error}</p>}

      {result && (
        <div data-testid="turnover-result">
          {result.allowed ? (
            <p data-testid="turnover-allowed">Turnover allowed for level {result.level} room {result.room}.</p>
          ) : (
            <div data-testid="turnover-blocked">
              <p>Turnover refused for level {result.level} room {result.room}. Still open:</p>
              <ul>
                {result.blocking_punch_items.map((item) => (
                  <li key={`punch-${item.id}`}>Punch item {item.id}: {item.description}</li>
                ))}
                {result.blocking_rfis.map((rfi) => (
                  <li key={`rfi-${rfi.id}`}>RFI {rfi.id}: {rfi.question}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
