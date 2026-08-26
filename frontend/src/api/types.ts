export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type Discipline = "architectural" | "structural" | "mep";
export type PunchItemStatus = "open" | "closed";
export type RfiStatus = "open" | "escalated" | "answered";

export interface PunchItem {
  id: number;
  level: string;
  room: string;
  drawing_sheet: string;
  discipline: Discipline;
  description: string;
  status: PunchItemStatus;
}

export interface Rfi {
  id: number;
  level: string;
  room: string;
  drawing_sheet: string;
  discipline: Discipline;
  question: string;
  status: RfiStatus;
}

export interface BlockingPunchItem {
  id: number;
  description: string;
}

export interface BlockingRfi {
  id: number;
  question: string;
}

export interface TurnoverResult {
  level: string;
  room: string;
  allowed: boolean;
  blocking_punch_items: BlockingPunchItem[];
  blocking_rfis: BlockingRfi[];
  message: string;
}

export interface OpenPunchItemRequest {
  level: string;
  room: string;
  drawing_sheet: string;
  description: string;
}

export interface OpenRfiRequest {
  level: string;
  room: string;
  drawing_sheet: string;
  question: string;
}
