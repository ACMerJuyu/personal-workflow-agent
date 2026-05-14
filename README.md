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
python app.py plan "Help me prepare for today's important work"
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

## Tools

| Tool | Purpose |
| --- | --- |
| `search_email` | Find emails by sender, keyword, priority, or unread status |
| `list_calendar_events` | Read today's calendar |
| `detect_calendar_conflicts` | Find overlapping events |
| `add_todo` | Add a task to the todo list |
| `draft_reply` | Generate a reply draft |
| `daily_brief` | Summarize important work items |

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

