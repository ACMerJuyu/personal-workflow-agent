# Personal Workflow Agent

A lightweight personal AI assistant prototype for coordinating email, calendar, todos, and daily work communication.

This project is a portfolio-ready mini version of a next-generation personal assistant. It reads daily work context, calls tools, detects conflicts, drafts replies, produces a daily brief, and persists agent runs with tool traces.

## Why This Project

Modern personal assistants should not only chat. They should coordinate across tools:

- Email
- Calendar
- Todos
- Chat-style instructions
- User preferences and memory

This repository demonstrates an agent loop with tool calling, structured outputs, dry-run safety, SQLite persistence, and deterministic tests.

## Features

- Reads mock email inbox
- Reads mock calendar events
- Reads and writes todos
- Detects urgent emails
- Detects calendar conflicts
- Creates todos
- Drafts email replies
- Produces tool-call traces
- Supports dry-run and commit modes
- Persists agent runs and tool calls in SQLite
- Exposes a FastAPI backend service

## Project Structure

```text
personal-workflow-agent/
  api.py
  app.py
  requirements.txt
  agent/
    __init__.py
    memory.py
    models.py
    parser.py
    planner.py
    router.py
    storage.py
    tools.py
  data/
    calendar.json
    emails.json
    memory.json
    todos.json
  docs/
    interview-and-architecture-notes.md
  scripts/
    init_db.py
  tests/
    test_agent.py
    test_api.py
    test_chat_agent.py
    test_router.py
    test_storage.py
    test_tools.py
```

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Initialize SQLite:

```bash
python scripts/init_db.py
```

Run CLI examples:

```bash
python app.py brief
python app.py emails
python app.py calendar
python app.py todos
python app.py plan "Help me prepare for today's important work"
python app.py chat "Any important emails?"
python app.py chat "Do I have calendar conflicts today?"
python app.py chat "Show my open todos"
python app.py chat "Complete todo 1"
python app.py chat "Move event-001 to 16:00-17:00"
python app.py --commit chat "Complete todo 1"
python app.py history
python app.py history 1
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Agent Design

The agent follows a simple loop:

```text
message -> intent -> parameter extraction -> tool call -> observation -> response
```

Core components:

- `router.py`: classifies user intent
- `parser.py`: extracts ids and time ranges
- `tools.py`: executes email, calendar, todo, and reply tools
- `planner.py`: orchestrates tool calls and returns `AgentResult`
- `storage.py`: persists product data, agent runs, and tool calls
- `models.py`: defines result and trace structures

The current implementation is deterministic and rule-based. This makes it easy to test. A future version can replace the router/planner with an LLM tool-calling planner while keeping the same tools and storage layer.

## Conversational Router

Supported intents:

| Intent | Example |
| --- | --- |
| `morning_brief` | `Give me a morning brief` |
| `important_emails` | `Any important emails?` |
| `today_calendar` | `What is on my calendar today?` |
| `open_todos` | `Show my open todos` |
| `calendar_conflicts` | `Do I have calendar conflicts today?` |
| `complete_todo` | `Complete todo 1` |
| `reschedule_event` | `Move event-001 to 16:00-17:00` |

## Execution Safety

The agent runs in `dry-run` mode by default.

In dry-run mode, write tools simulate actions without changing state:

```bash
python app.py chat "Give me a morning brief"
python app.py chat "Move event-001 to 16:00-17:00"
```

Example wording:

```text
Todo would be created: Review A1 product proposal due 15:00.
Event would be moved: Deep Work to 16:00-17:00.
```

To persist write actions, explicitly use `--commit`:

```bash
python app.py --commit chat "Complete todo 1"
python app.py --commit chat "Move event-001 to 16:00-17:00"
```

This mirrors a real agent safety pattern:

```text
plan action -> show proposed change -> require confirmation -> commit side effect
```

## SQLite Persistence

The CLI and API use a local SQLite database:

```text
data/workflow.db
```

The database is seeded from the JSON files in `data/`:

```bash
python scripts/init_db.py
```

You can also reset the database before a run:

```bash
python app.py --reset-db chat "Any important emails?"
```

SQLite stores both product data and agent execution history:

```text
emails
calendar_events
todos
user_memory
agent_runs
tool_calls
```

Each CLI/API run is persisted as an `agent_run`, and every tool call is saved under `tool_calls`.

View recent runs:

```bash
python app.py history
```

Inspect one run:

```bash
python app.py history 1
```

This persistence layer makes the agent debuggable and auditable:

```text
user message -> intent -> mode -> final result -> tool call trace
```

## FastAPI Service

Start the API server:

```bash
python -m uvicorn api:app --reload --port 8010
```

Open interactive API docs:

```text
http://127.0.0.1:8010/docs
```

FastAPI turns the existing agent functions into web endpoints. This moves the project from a CLI demo toward a backend service that a web dashboard can call.

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/agent/chat` | Run conversational agent |
| `POST` | `/agent/brief` | Generate morning brief |
| `GET` | `/agent/runs` | List saved agent runs |
| `GET` | `/agent/runs/{run_id}` | Inspect one saved run and tool trace |
| `GET` | `/emails` | Query emails |
| `GET` | `/calendar` | Query calendar events |
| `GET` | `/todos` | Query todos |

Example request:

```bash
curl -X POST http://127.0.0.1:8010/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Do I have calendar conflicts today?\",\"commit\":false,\"reset_db\":true}"
```

Example response shape:

```json
{
  "run_id": 1,
  "title": "Calendar Conflicts",
  "bullets": ["Deep Work overlaps with Proposal Review."],
  "trace": [
    {
      "name": "load_memory",
      "arguments": {},
      "result": {}
    }
  ],
  "mode": "dry-run",
  "intent": "calendar_conflicts"
}
```

API architecture:

```text
HTTP request
  -> FastAPI endpoint
  -> WorkflowAgent
  -> Router / Parser
  -> Tools
  -> SQLiteStorage
  -> AgentResult + Tool Trace
  -> JSON response
```

## Tools

| Tool | Purpose |
| --- | --- |
| `search_email` | Find emails by sender, keyword, priority, or unread status |
| `get_email_by_id` | Read one exact email by id |
| `list_calendar_events` | Read calendar events |
| `detect_calendar_conflicts` | Find overlapping events |
| `reschedule_event` | Move an event to a new time range |
| `list_todos` | Read open or completed todos |
| `add_todo` | Add a task to the todo list |
| `complete_todo` | Mark a todo as done |
| `draft_reply` | Generate a reply draft |
| `daily_brief` | Summarize important work items |

## Roadmap

- Add a web dashboard
- Add OpenAI tool-calling planner
- Add persistent user profiles
- Add Gmail / Google Calendar adapter interfaces
- Add evaluation cases for agent decisions

## Portfolio Notes

This project is intentionally small but complete. It shows:

- Agent-oriented product thinking
- Tool design
- State management
- Dry-run safety
- SQLite persistence
- API service design
- Testing discipline

