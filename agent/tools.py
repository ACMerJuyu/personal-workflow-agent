import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkflowTools:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def search_email(
        self,
        keyword: Optional[str] = None,
        sender: Optional[str] = None,
        unread_only: bool = False,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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

    def list_calendar_events(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
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

    def add_todo(self, title: str, due: str, source: str, priority: str = "medium") -> Dict[str, Any]:
        todos = self._read_json("todos.json")
        todo = {
            "id": len(todos) + 1,
            "title": title,
            "due": due,
            "source": source,
            "priority": priority,
            "done": False,
        }
        todos.append(todo)
        self._write_json("todos.json", todos)
        return todo

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

