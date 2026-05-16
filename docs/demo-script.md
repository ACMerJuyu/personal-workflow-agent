# Demo Script

This script is a short interview walkthrough for the Personal Workflow Agent.

## 1. Open The Dashboard

Start the API:

```bash
python -m uvicorn api:app --reload --port 8010
```

Open:

```text
http://127.0.0.1:8010/dashboard
```

Point out:

- FastAPI serves the dashboard and JSON endpoints.
- SQLite stores emails, calendar events, todos, agent runs, tool calls, and pending actions.
- The dashboard is intentionally lightweight so the agent architecture is easy to inspect.

## 2. Show A Read-Only Agent Run

Run:

```text
Do I have calendar conflicts today?
```

Explain:

- The router classifies the request as `calendar_conflicts`.
- The planner loads memory to get today's date.
- The tool layer calls `detect_calendar_conflicts`.
- The ReAct Timeline shows Thought, Action, Observation, and Final.

## 3. Show A Write Action In Dry-Run Mode

Run:

```text
Move event-001 to 16:00-17:00
```

Explain:

- The agent proposes a calendar change.
- Dry-run mode prevents immediate mutation.
- A pending action is created instead.
- This separates planning from side effects.

## 4. Approve The Action

Click `Approve` in Pending Actions.

Explain:

- Approval executes the same tool in commit mode.
- The calendar data changes only after explicit approval.
- This is the safety pattern real agents need before modifying user data.

## 5. Show Planner Modes

Use the Planner select:

```text
Auto
Rule-based
OpenAI
```

Explain:

- Rule-based planner is deterministic and testable.
- OpenAI planner is optional and uses tool calling when configured.
- Auto mode falls back safely when no API key is available.

## 6. Show Evals

Run:

```bash
python scripts/run_evals.py
```

Explain:

- Evals verify expected intent, title, tool calls, and pending action behavior.
- The project is not just manually tested; agent decisions are checked systematically.

## Closing Pitch

This project demonstrates a practical agent system:

```text
natural language
  -> planner
  -> tools
  -> ReAct trace
  -> SQLite persistence
  -> approval workflow
  -> dashboard
```

The current data sources are mocked, but the architecture is ready for Gmail, Google Calendar, and real LLM planner integrations.
