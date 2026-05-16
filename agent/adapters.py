from typing import Any, Dict, List, Optional

from agent.storage import SQLiteStorage


EmailAdapter = Any
CalendarAdapter = Any
TodoAdapter = Any


class SQLiteEmailAdapter:
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    def search_email(
        self,
        keyword: Optional[str] = None,
        sender: Optional[str] = None,
        unread_only: bool = False,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.storage.search_email(keyword, sender, unread_only, priority)

    def get_email_by_id(self, email_id: str) -> Dict[str, Any]:
        return self.storage.get_email_by_id(email_id)


class SQLiteCalendarAdapter:
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    def list_calendar_events(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.storage.list_calendar_events(date)

    def get_event_by_id(self, event_id: str) -> Dict[str, Any]:
        return self.storage.get_event_by_id(event_id)

    def reschedule_event(self, event_id: str, new_start: str, new_end: str) -> Dict[str, Any]:
        return self.storage.reschedule_event(event_id, new_start, new_end)


class SQLiteTodoAdapter:
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    def list_todos(self, include_done: bool = False, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.storage.list_todos(include_done, priority)

    def next_todo_id(self) -> int:
        return self.storage.next_todo_id()

    def add_todo(self, title: str, due: str, source: str, priority: str = "medium") -> Dict[str, Any]:
        return self.storage.add_todo(title, due, source, priority)

    def complete_todo(self, todo_id: int) -> Dict[str, Any]:
        return self.storage.complete_todo(todo_id)
