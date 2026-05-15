# Personal Workflow Agent

A lightweight personal AI assistant prototype for coordinating email, calendar, todos, and daily work communication.

This project is built as a portfolio-ready mini version of a next-generation personal assistant: it reads a user's daily work context, calls tools, detects conflicts, drafts replies, and produces a concise daily brief.

## Why This Project

Modern personal assistants should not only chat. They should coordinate across tools:

- Email
- Calendar
- Todos
- Chat-style instructions
- User preferences and memory

This repository demonstrates an agent loop with tool calling, structured outputs, and deterministic tests.

## Demo

```bash
python app.py brief
```

Example output:

```text
Daily Brief
1. Important email from Alex Chen: confirm product proposal by 15:00.
2. Calendar conflict detected: Deep Work overlaps with proposal review.
3. Suggested action: draft a reply and move Deep Work to 16:00.
4. Todo created: Review A1 product proposal.
```

## Features

- Reads mock email inbox
- Reads mock calendar events
- Reads and writes mock todos
- Detects urgent emails
- Detects calendar conflicts
- Creates todos
- Drafts email replies
- Produces tool-call traces
- Runs without external services

## Project Structure

```text
personal-workflow-agent/
  app.py
  agent/
    __init__.py
    planner.py
    tools.py
    memory.py
    models.py
  data/
    calendar.json
    emails.json
    memory.json
    todos.json
  tests/
    test_agent.py
    test_tools.py
```

## Quick Start

```bash
python app.py brief
python app.py emails
python app.py calendar
python app.py todos
python app.py plan "Help me prepare for today's important work"
python app.py chat "今天有没有日程冲突？"
python app.py chat "我有哪些未完成任务？"
python app.py chat "完成 todo 1"
python app.py chat "把 event-001 改到 16:00-17:00"
python app.py --commit chat "完成 todo 1"
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Agent Design

The agent follows a simple loop:

1. Understand the user goal
2. Inspect context using tools
3. Detect priority and conflicts
4. Take safe actions
5. Return a human-readable brief and structured trace

The current implementation is deterministic and rule-based. This makes it easy to test. A future version can replace the planner with an LLM while keeping the same tool layer.

## Conversational Router

The project includes a lightweight intent router for simple natural-language commands.

Supported intents:

| Intent | Example |
| --- | --- |
| `morning_brief` | `今天有什么重要事情？` |
| `important_emails` | `有没有重要邮件？` |
| `today_calendar` | `今天有什么安排？` |
| `open_todos` | `我有哪些未完成任务？` |
| `calendar_conflicts` | `今天有没有日程冲突？` |
| `complete_todo` | `完成 todo 1` |
| `reschedule_event` | `把 event-001 改到 16:00-17:00` |

This is intentionally rule-based for now. It teaches the same core pattern as LLM tool calling:

```text
message -> intent -> parameter extraction -> tool call -> observation -> response
```

## Execution Safety

The agent runs in `dry-run` mode by default.

In dry-run mode, write tools simulate actions without changing files:

```bash
python app.py chat "今天有什么安排？"
python app.py chat "把 event-001 改到 16:00-17:00"
```

Example wording:

```text
Todo would be created: Review A1 product proposal due 15:00.
Event would be moved: Deep Work to 16:00-17:00.
```

To persist write actions, explicitly use `--commit`:

```bash
python app.py --commit chat "完成 todo 1"
python app.py --commit chat "把 event-001 改到 16:00-17:00"
```

This mirrors a real agent safety pattern:

```text
plan action -> show proposed change -> require confirmation -> commit side effect
```

## Tools

| Tool | Purpose |
| --- | --- |
| `search_email` | Find emails by sender, keyword, priority, or unread status |
| `get_email_by_id` | Read one exact email by id |
| `list_calendar_events` | Read today's calendar |
| `detect_calendar_conflicts` | Find overlapping events |
| `reschedule_event` | Move an event to a new time range |
| `list_todos` | Read open or completed todos |
| `add_todo` | Add a task to the todo list |
| `complete_todo` | Mark a todo as done |
| `draft_reply` | Generate a reply draft |
| `daily_brief` | Summarize important work items |

## Morning Workflow

The main portfolio scenario is a morning assistant flow:

```text
1. Load user memory and today's date
2. Check high-priority unread emails
3. Read today's calendar
4. List open todos
5. Detect calendar conflicts
6. Create a todo from urgent email
7. Draft a reply
8. Return a concise daily brief with tool trace
```

This maps directly to the personal assistant use case: "Every morning, help me check email, calendar, and tasks."

## Roadmap

- Add FastAPI service wrapper
- Add simple web UI
- Add OpenAI tool-calling planner
- Add persistent SQLite storage
- Add Google Calendar / Gmail adapter interfaces
- Add evaluation cases for agent decisions

## Portfolio Notes

This project is intentionally small but complete. It shows:

- Agent-oriented product thinking
- Tool design
- State management
- Testing discipline
- Clear README and runnable demo
