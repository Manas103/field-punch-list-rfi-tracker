/** Thin fetch wrapper over the FastAPI backend. Every function here maps
 * one to one to an endpoint in backend/app/api.py. No caching, no retry
 * logic: the tracker's state lives on the backend, so a plain request per
 * call keeps the client honest about what is live. */

import type { OpenPunchItemRequest, OpenRfiRequest, PunchItem, Rfi, TurnoverResult } from "./types";
import { ApiError } from "./types";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, detail || res.statusText);
  }
  return (await res.json()) as T;
}

export function fetchTurnover(level: string, room: string): Promise<TurnoverResult> {
  return request<TurnoverResult>(`/rooms/${encodeURIComponent(level)}/${encodeURIComponent(room)}/turnover`);
}

export function openPunchItem(body: OpenPunchItemRequest): Promise<PunchItem> {
  return request<PunchItem>("/punch-items", { method: "POST", body: JSON.stringify(body) });
}

export function recordEvidence(punchItemId: number, inspector: string, note: string): Promise<{ id: number }> {
  return request<{ id: number }>("/inspection-evidence", {
    method: "POST",
    body: JSON.stringify({ punch_item_id: punchItemId, inspector, note }),
  });
}

export function closePunchItem(punchItemId: number, evidenceId: number): Promise<PunchItem> {
  return request<PunchItem>("/punch-items/close", {
    method: "POST",
    body: JSON.stringify({ punch_item_id: punchItemId, evidence_id: evidenceId }),
  });
}

export function openRfi(body: OpenRfiRequest): Promise<Rfi> {
  return request<Rfi>("/rfis", { method: "POST", body: JSON.stringify(body) });
}

export function answerRfi(rfiId: number, answerText: string): Promise<Rfi> {
  return request<Rfi>("/rfis/answer", { method: "POST", body: JSON.stringify({ rfi_id: rfiId, answer_text: answerText }) });
}
