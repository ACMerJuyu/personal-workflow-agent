import json
import tempfile
import unittest
from pathlib import Path

from agent.tools import WorkflowTools


class WorkflowToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        (self.data_dir / "emails.json").write_text(
            json.dumps(
                [
                    {
                        "id": "email-1",
                        "sender": "Alex Chen",
                        "subject": "Urgent proposal",
                        "body": "Please confirm today",
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
                    {"id": "a", "title": "A", "date": "2026-05-14", "start": "10:00", "end": "11:00"},
                    {"id": "b", "title": "B", "date": "2026-05-14", "start": "10:30", "end": "11:30"},
                ]
            ),
            encoding="utf-8",
        )
        (self.data_dir / "todos.json").write_text("[]", encoding="utf-8")
        self.tools = WorkflowTools(str(self.data_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_email_filters_priority(self):
        emails = self.tools.search_email(priority="high", unread_only=True)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["sender"], "Alex Chen")

    def test_detect_calendar_conflicts(self):
        conflicts = self.tools.detect_calendar_conflicts("2026-05-14")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["first"]["title"], "A")

    def test_add_todo_persists_task(self):
        todo = self.tools.add_todo("Review proposal", "15:00", "email-1", "high")
        self.assertEqual(todo["id"], 1)
        todos = json.loads((self.data_dir / "todos.json").read_text(encoding="utf-8"))
        self.assertEqual(todos[0]["title"], "Review proposal")


if __name__ == "__main__":
    unittest.main()

