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
                    },
                    {
                        "id": "email-2",
                        "sender": "Mina Wu",
                        "subject": "Coffee",
                        "body": "Coffee tomorrow?",
                        "deadline": "tomorrow",
                        "priority": "low",
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
                    {"id": "c", "title": "C", "date": "2026-05-15", "start": "13:00", "end": "14:00"},
                ]
            ),
            encoding="utf-8",
        )
        (self.data_dir / "todos.json").write_text(
            json.dumps(
                [
                    {
                        "id": 1,
                        "title": "Open task",
                        "due": "10:00",
                        "source": "manual",
                        "priority": "medium",
                        "done": False,
                    },
                    {
                        "id": 2,
                        "title": "Done task",
                        "due": "11:00",
                        "source": "manual",
                        "priority": "low",
                        "done": True,
                    },
                ]
            ),
            encoding="utf-8",
        )
        self.tools = WorkflowTools(str(self.data_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_email_filters_priority(self):
        emails = self.tools.search_email(priority="high", unread_only=True)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["sender"], "Alex Chen")

    def test_get_email_by_id_returns_exact_email(self):
        email = self.tools.get_email_by_id("email-2")
        self.assertEqual(email["sender"], "Mina Wu")

    def test_detect_calendar_conflicts(self):
        conflicts = self.tools.detect_calendar_conflicts("2026-05-14")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["first"]["title"], "A")

    def test_reschedule_event_updates_time(self):
        event = self.tools.reschedule_event("c", "15:00", "16:00")
        self.assertEqual(event["start"], "15:00")
        events = self.tools.list_calendar_events("2026-05-15")
        self.assertEqual(events[0]["end"], "16:00")

    def test_list_todos_excludes_done_by_default(self):
        todos = self.tools.list_todos()
        self.assertEqual(len(todos), 1)
        self.assertEqual(todos[0]["title"], "Open task")

    def test_add_todo_persists_task(self):
        todo = self.tools.add_todo("Review proposal", "15:00", "email-1", "high")
        self.assertEqual(todo["id"], 3)
        todos = json.loads((self.data_dir / "todos.json").read_text(encoding="utf-8"))
        self.assertEqual(todos[-1]["title"], "Review proposal")

    def test_complete_todo_marks_task_done(self):
        todo = self.tools.complete_todo(1)
        self.assertTrue(todo["done"])
        open_todos = self.tools.list_todos()
        self.assertEqual(open_todos, [])


if __name__ == "__main__":
    unittest.main()
