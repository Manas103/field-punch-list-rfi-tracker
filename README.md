# Field Punch List and RFI Tracker with Verified Closeout

A FastAPI backend and a React/TypeScript console that open punch items and
contractor RFIs against a level, room and drawing sheet, route each one to a
responsible discipline, age RFIs on a clock that escalates unanswered
questions, close a punch item only against a piece of inspection evidence
that names it, and refuse to turn over a room while anything in it is still
open, naming the exact item. Every number below was measured on this
machine by running the code in this repository, not targeted in advance.

## Why this exists

Turnover is the moment a room, or a job, actually ends, and it is exactly
where "I think we're done" has to become "here is the evidence that we are
done." A Project Engineer's punch list and RFI log are the two registers
that decide whether that claim is true. This project builds the smallest
honest version of both: real opened-against-a-location items, a real
routing step, a real aging clock, and a real refusal that names names
instead of saying a room "isn't ready."

## What this is and is not

- **The dataset is synthetic and says so.** 2,600 punch items and 420 RFIs
  are generated from a fixed vocabulary of realistic descriptions across
  500 rooms; no claim on this page implies a student walked a real jobsite.
- **Status is never a mutable column.** `PunchItem` and `Rfi` carry no
  `status` field at all. Status is always derived by folding an append-only
  event log (`punch_item_events`, `rfi_events`); nothing in this codebase
  runs an `UPDATE` or `DELETE` against either table, and a test asserts
  that by inspecting the raw tables, not by trusting the code
  (`test_the_event_log_and_evidence_tables_are_never_updated_or_deleted`).
- **Routing is a keyword table, not a classifier.** Discipline assignment
  is a fixed, ordered set of MEP and structural keywords, checked in
  priority order, with architectural as the catch-all. It is disclosed as a
  simplification: a real routing step lets a superintendent override a bad
  guess, this one only proposes one.
- **The turnover gate checks resolution, not correctness.** A closed punch
  item or an answered RFI clears the gate regardless of whether the
  underlying work is actually good; that judgment belongs to the inspector
  who records the evidence, not to this tool.
- **PostgreSQL is the intended backend, SQLite is what every test actually
  runs against.** PostgreSQL is not installed as a service on the build
  machine; the PostgreSQL-backed test skips cleanly when
  `TRACKER_DATABASE_URL` is unset or unreachable rather than failing the
  suite.
- **Machine and toolchain.** 8 physical / 16 logical cores, Windows 11
  Home, Python 3.12.10, FastAPI 0.115.6, SQLAlchemy 2.0.36, Node.js 22.17.1,
  React 18.3, TypeScript 5.7, Vite 6, Vitest 2.1.

## Architecture

```
backend/
  app/
    models.py       PunchItem, Rfi (no status column) + append-only PunchItemEvent, RfiEvent, InspectionEvidence
    db.py            SQLite (StaticPool, see Findings) by default, PostgreSQL via TRACKER_DATABASE_URL
    routing.py        ordered keyword table: description/question -> architectural | structural | mep
    punch_items.py    open_punch_item, record_inspection_evidence, close_punch_item (refuses, names the item), punch_item_status
    rfi.py             open_rfi, answer_rfi, rfi_status (open | escalated | answered), ESCALATION_SLA_DAYS
    turnover.py        attempt_room_turnover: blocked while any punch item or RFI in the room is unresolved, names each one
    generator.py        synthetic dataset builder: >=2,500 punch items, >=400 RFIs, one vocabulary per kind
    api.py               FastAPI routes, one per lifecycle action, no business logic beyond what the modules above already have
  scripts/
    run_demo.py          end-to-end: open -> close 2 of 3 -> refused -> close the 3rd -> allowed
    run_benchmarks.py     reproduces the measured numbers in this README
  tests/
    test_closeout.py            verified closeout, refusal naming the item, append-only assertion on the raw tables
    test_turnover_gate.py        30/30 seeded premature closeouts refused naming the item; 0 false holds/40 clean rooms
    test_rfi_aging.py             escalation clock
    test_routing.py                keyword table
    test_generator_scale.py       >=2,500 punch items, >=400 RFIs
    test_api.py                     FastAPI TestClient over the full lifecycle
    test_postgres_store.py         real PostgreSQL path, skips cleanly when unreachable
frontend/
  src/
    api/client.ts, api/types.ts    typed fetch wrapper, one function per backend route
    components/TurnoverPanel.tsx    looks up a room, shows the refusal naming every blocking item, or "allowed"
    components/OpenPunchItemForm.tsx opens an item, shows the routed discipline
  src/__tests__/                    Vitest + Testing Library, fetch mocked
docs/
  test_output.txt, benchmark_output.txt, demo_output.txt, frontend_test_output.txt, frontend_build_output.txt
```

### Why status is derived, not stored

A mutable `status` column can be set wrong by a bug and there is no way to
tell, after the fact, that it ever held a different value. An append-only
event log makes "this item was opened, then closed" a fact recoverable from
history rather than a snapshot trusted at face value, which is the same
reason a real Issues Resolution Log is a log and not a spreadsheet cell.
`punch_item_status` and `rfi_status` always read the latest event; nothing
in this repository writes to a status field, because there isn't one.

### Why the seeded turnover scenarios build three items per room, not one

A room with exactly one punch item and nothing else would make "refused,
naming the item still open" trivially true. Each of the 30 seeded rooms
opens 3 punch items and 1 RFI, closes all but one item, and answers the RFI,
so the refusal has to correctly identify the *one* item among several that
is still open, not just report that the room has any open item at all.

## Validation

```
cd backend && pytest tests -v
cd frontend && npm run test && npm run build
```

Backend: 21 passed, 1 skipped (PostgreSQL not running). Frontend: 4 passed,
clean `tsc -b && vite build`. Full output in `docs/test_output.txt` and
`docs/frontend_test_output.txt` / `docs/frontend_build_output.txt`.

Three layers specific to the closeout and turnover claims:

1. **Refusal naming.** Every refusal (`CloseoutRefused`, a blocked
   `TurnoverResult`) carries the specific item id and description or
   question, and the tests assert on that text, not just on a boolean
   (`test_closeout.py`, `test_turnover_gate.py`).
2. **Append-only, checked from outside the ORM.** `test_the_event_log_and_evidence_tables_are_never_updated_or_deleted`
   runs raw SQL (`select count(*) from ...`) after each operation and
   asserts the count only grows.
3. **Scale.** The generator is run at 2,600 items / 420 RFIs inside the
   test suite itself (`test_generator_scale.py`), not just in a
   demonstration script, so "over 2,500" and "over 400" are asserted, not
   just printed.

## Findings

**An in-memory SQLite database is private to the connection that opened
it.** The first version of the FastAPI app created one module-level engine
with `sqlite:///:memory:` and the default connection pool, on the
assumption that "in-memory" meant "one shared database for the process."
The first manual test against the running server opened a punch item, then
immediately queried its turnover status, and got "room does not exist,"
even though the open had just succeeded. The discriminating fact:
SQLAlchemy's default pool hands out a fresh DB-API connection per checkout,
and for SQLite, `:memory:` databases are private per connection, so every
request was silently getting its own empty database. The fix was
`poolclass=StaticPool` (plus `check_same_thread=False`) for the in-memory
URL specifically, which keeps one connection alive for the engine's whole
lifetime; a file-backed SQLite URL or a real PostgreSQL URL never had this
problem, because a file or a server is shared across connections by
construction. This is disclosed in `db.py`, not just fixed silently,
because it is exactly the kind of bug that looks like a data-loss bug in
production and is actually a pooling default.

**A naive seeded-scenario builder can pass by construction, not by
correctness.** An early version of `test_turnover_gate.py` left only one
punch item open per room and asserted the room was blocked, which is true
even if the turnover check ignored every other item in the room and just
checked the single one. Rebuilding each seeded room with 3 punch items and
1 answered RFI, and asserting the refusal names the *specific* still-open
item among the group, is what actually exercises the "which one" logic
instead of the "any at all" logic.

## Measured results

Machine: 8 physical / 16 logical cores, Windows 11 Home, Python 3.12.10,
Node.js 22.17.1.

| Claim | Measured | Meets claim |
|---|---|---|
| 30 of 30 seeded premature closeouts refused, naming the item still open | **30 / 30** | yes |
| 0 false holds across 40 clean rooms | **0** | yes |
| Over 2,500 synthetic punch items and 400 RFIs | **2,600** punch items, **420** RFIs, every one routed and located | yes |

Raw output: `docs/benchmark_output.txt` (reproduce with
`python scripts/run_benchmarks.py`), `docs/test_output.txt` (`pytest -v`).

The one number that matters is the first row: 30 rooms, each with 3 punch
items and 1 answered RFI, 2 of the 3 items closed with real inspection
evidence and 1 left open, and the turnover gate correctly names the one
that is still open in all 30, never the wrong one and never none.

## Building and running

```
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
pytest tests -v
python scripts/run_benchmarks.py
python scripts/run_demo.py
python -m app.main               # serves the API on :8000

cd ../frontend
npm install
npm run test
npm run build
npm run dev                       # serves the console on :5174, proxies /api to :8000
```

To exercise the real PostgreSQL path instead of the SQLite default:

```
set TRACKER_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/tracker
pytest tests/test_postgres_store.py -v
```

## Limitations

- Routing is a fixed keyword table with no human override.
- The turnover gate checks resolution (closed, answered), not the quality
  of the underlying work; that judgment is the inspector's, recorded as
  evidence, not the tool's.
- The escalation clock is a single fixed SLA (10 calendar days) for every
  RFI regardless of discipline or drawing complexity.
- The console covers opening a punch item and checking room turnover; it
  does not yet expose recording evidence, closing an item, or answering an
  RFI from the UI (all three exist as backend routes and are exercised by
  `test_api.py`).
