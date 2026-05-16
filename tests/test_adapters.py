import json
import tempfile
import unittest
from pathlib import Path

from agent.adapters import SQLiteCalendarAdapter, SQLiteEmailAdapter, SQLiteTodoAdapter
from agent.storage import SQLiteStorage
from agent.tools import WorkflowTools


class AdapterLayerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "data"
        self.data_dir.mkdir()
        (self.data_dir / "emails.json").write_text(
            json.dumps(
                [
                    {
                        "id": "email-1",
                        "sender": "Alex Chen",
                        "subject": "Confirm proposal",
                        "body": "Please confirm today.",
                        "deadline": "15:00",
                        "priority": "high",
                        "unread": True,
                    }
                ]
            ),
            encoding="utf-8",
        )
        (self.data_dir / "calendar.json").write_text(
            json.dumps(
                [
                    {
                        "id": "event-1",
                        "title": "Deep Work",
                        "date": "2026-05-14",
                        "start": "14:30",
                        "end": "15:30",
                    }
                ]
            ),
            encoding="utf-8",
        )
        (self.data_dir / "todos.json").write_text(
            json.dumps(
                [
                    {
                        "id": 1,
                        "title": "Read inbox",
                        "due": "10:00",
                        "source": "manual",
                        "priority": "medium",
                        "done": False,
                    }
                ]
            ),
            encoding="utf-8",
        )
        (self.data_dir / "memory.json").write_text(
            json.dumps({"today": "2026-05-14", "reply_tone": "friendly"}),
            encoding="utf-8",
        )
        self.storage = SQLiteStorage(str(self.root / "workflow.db"))
        self.storage.seed_from_json(str(self.data_dir), force=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_workflow_tools_can_use_sqlite_adapters(self):
        tools = WorkflowTools(
            mode="commit",
            email_adapter=SQLiteEmailAdapter(self.storage),
            calendar_adapter=SQLiteCalendarAdapter(self.storage),
            todo_adapter=SQLiteTodoAdapter(self.storage),
        )

        emails = tools.search_email(priority="high", unread_only=True)
        moved = tools.reschedule_event("event-1", "16:00", "17:00")
        todo = tools.complete_todo(1)

        self.assertEqual(emails[0]["sender"], "Alex Chen")
        self.assertEqual(moved["start"], "16:00")
        self.assertTrue(todo["done"])


if __name__ == "__main__":
    unittest.main()
