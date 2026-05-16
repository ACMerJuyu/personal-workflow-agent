import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.adapters import CalendarAdapter, EmailAdapter, SQLiteCalendarAdapter, SQLiteEmailAdapter, SQLiteTodoAdapter, TodoAdapter
from agent.storage import SQLiteStorage


class WorkflowTools:
    def __init__(
        self,
        data_dir: str = "data",
        mode: str = "dry-run",
        storage: Optional[SQLiteStorage] = None,
        email_adapter: Optional[EmailAdapter] = None,
        calendar_adapter: Optional[CalendarAdapter] = None,
        todo_adapter: Optional[TodoAdapter] = None,
    ):
        if mode not in {"dry-run", "commit"}:
            raise ValueError("mode must be 'dry-run' or 'commit'")
        self.data_dir = Path(data_dir)
        self.mode = mode
        self.storage = storage
        self.email_adapter = email_adapter
        self.calendar_adapter = calendar_adapter
        self.todo_adapter = todo_adapter

        if storage:
            self.email_adapter = self.email_adapter or SQLiteEmailAdapter(storage)
            self.calendar_adapter = self.calendar_adapter or SQLiteCalendarAdapter(storage)
            self.todo_adapter = self.todo_adapter or SQLiteTodoAdapter(storage)

    def search_email(
        self,
        keyword: Optional[str] = None,
        sender: Optional[str] = None,
        unread_only: bool = False,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.email_adapter:
            return self.email_adapter.search_email(keyword, sender, unread_only, priority)

        emails = self._read_json("emails.json")
        results = []

        for email in emails:
            if sender and sender.lower() not in email["sender"].lower():
                continue
            if unread_only and not email.get("unread", False):
                continue
            if priority and email.get("priority") != priority:
                continue
            if keyword:
                haystack = f"{email['subject']} {email['body']}".lower()
                if keyword.lower() not in haystack:
                    continue
            results.append(email)

        return results

    def get_email_by_id(self, email_id: str) -> Dict[str, Any]:
        if self.email_adapter:
            return self.email_adapter.get_email_by_id(email_id)

        emails = self._read_json("emails.json")
        for email in emails:
            if email["id"] == email_id:
                return email
        raise ValueError(f"email not found: {email_id}")

    def list_calendar_events(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.calendar_adapter:
            return self.calendar_adapter.list_calendar_events(date)

        events = self._read_json("calendar.json")
        if date is None:
            return events
        return [event for event in events if event["date"] == date]

    def detect_calendar_conflicts(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        events = sorted(self.list_calendar_events(date), key=lambda event: event["start"])
        conflicts = []

        for index in range(len(events) - 1):
            current = events[index]
            next_event = events[index + 1]
            if self._to_minutes(current["end"]) > self._to_minutes(next_event["start"]):
                conflicts.append(
                    {
                        "first": current,
                        "second": next_event,
                        "reason": "overlapping calendar events",
                    }
                )

        return conflicts

    def reschedule_event(self, event_id: str, new_start: str, new_end: str) -> Dict[str, Any]:
        if self.calendar_adapter:
            original = self.calendar_adapter.get_event_by_id(event_id)
            if self.mode == "commit":
                return self.calendar_adapter.reschedule_event(event_id, new_start, new_end)
            dry_run_event = dict(original)
            dry_run_event["start"] = new_start
            dry_run_event["end"] = new_end
            dry_run_event["dry_run"] = True
            dry_run_event["original"] = original
            return dry_run_event

        events = self._read_json("calendar.json")
        for index, event in enumerate(events):
            if event["id"] == event_id:
                original = dict(event)
                event["start"] = new_start
                event["end"] = new_end
                if self.mode == "commit":
                    self._write_json("calendar.json", events)
                    return event
                dry_run_event = dict(event)
                dry_run_event["dry_run"] = True
                dry_run_event["original"] = original
                events[index] = original
                return dry_run_event
        raise ValueError(f"calendar event not found: {event_id}")

    def list_todos(
        self,
        include_done: bool = False,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.todo_adapter:
            return self.todo_adapter.list_todos(include_done, priority)

        todos = self._read_json("todos.json")
        results = []

        for todo in todos:
            if not include_done and todo.get("done", False):
                continue
            if priority and todo.get("priority") != priority:
                continue
            results.append(todo)

        return results

    def add_todo(self, title: str, due: str, source: str, priority: str = "medium") -> Dict[str, Any]:
        if self.todo_adapter:
            if self.mode == "commit":
                return self.todo_adapter.add_todo(title, due, source, priority)
            return {
                "id": self.todo_adapter.next_todo_id(),
                "title": title,
                "due": due,
                "source": source,
                "priority": priority,
                "done": False,
                "dry_run": True,
            }

        todos = self._read_json("todos.json")
        todo = {
            "id": len(todos) + 1,
            "title": title,
            "due": due,
            "source": source,
            "priority": priority,
            "done": False,
        }
        if self.mode == "dry-run":
            todo["dry_run"] = True
            return todo
        todos.append(todo)
        self._write_json("todos.json", todos)
        return todo

    def complete_todo(self, todo_id: int) -> Dict[str, Any]:
        if self.todo_adapter:
            if self.mode == "commit":
                return self.todo_adapter.complete_todo(todo_id)
            todos = self.todo_adapter.list_todos(include_done=True)
            for todo in todos:
                if todo["id"] == todo_id:
                    updated_todo = dict(todo)
                    updated_todo["done"] = True
                    updated_todo["dry_run"] = True
                    return updated_todo
            raise ValueError(f"todo not found: {todo_id}")

        todos = self._read_json("todos.json")
        for todo in todos:
            if todo["id"] == todo_id:
                updated_todo = dict(todo)
                updated_todo["done"] = True
                if self.mode == "commit":
                    todo["done"] = True
                    self._write_json("todos.json", todos)
                    return todo
                updated_todo["dry_run"] = True
                return updated_todo
        raise ValueError(f"todo not found: {todo_id}")

    def draft_reply(self, email: Dict[str, Any], tone: str = "concise") -> Dict[str, str]:
        greeting_name = email["sender"].split()[0]
        subject = "Re: " + email["subject"]

        if tone == "friendly":
            body = (
                f"Hi {greeting_name},\n\n"
                "Thanks for the note. I will review this today and send you a clear update before the deadline.\n\n"
                "Best,\nACMerJuyu"
            )
        else:
            body = (
                f"Hi {greeting_name},\n\n"
                "Received. I will review this today and follow up before the deadline.\n\n"
                "Best,\nACMerJuyu"
            )

        return {"to": email["sender"], "subject": subject, "body": body}

    def _read_json(self, name: str) -> Any:
        with (self.data_dir / name).open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write_json(self, name: str, value: Any) -> None:
        with (self.data_dir / name).open("w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")

    @staticmethod
    def _to_minutes(value: str) -> int:
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.hour * 60 + parsed.minute
