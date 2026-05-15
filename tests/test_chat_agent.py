import json
import tempfile
import unittest
from pathlib import Path

from agent.memory import UserMemory
from agent.planner import WorkflowAgent
from agent.tools import WorkflowTools


class ChatAgentTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(self.temp_dir.name)
        (data_dir / "emails.json").write_text(
            json.dumps(
                [
                    {
                        "id": "email-1",
                        "sender": "Alex Chen",
                        "subject": "Confirm product proposal",
                        "body": "Please confirm by 15:00.",
                        "deadline": "15:00",
                        "priority": "high",
                        "unread": True,
                    }
                ]
            ),
            encoding="utf-8",
        )
        (data_dir / "calendar.json").write_text(
            json.dumps(
                [
                    {
                        "id": "event-001",
                        "title": "Deep Work",
                        "date": "2026-05-14",
                        "start": "14:30",
                        "end": "15:30",
                    },
                    {
                        "id": "event-002",
                        "title": "Proposal Review",
                        "date": "2026-05-14",
                        "start": "15:00",
                        "end": "15:45",
                    },
                ]
            ),
            encoding="utf-8",
        )
        (data_dir / "todos.json").write_text(
            json.dumps(
                [
                    {
                        "id": 1,
                        "title": "Read morning inbox",
                        "due": "09:30",
                        "source": "manual",
                        "priority": "medium",
                        "done": False,
                    }
                ]
            ),
            encoding="utf-8",
        )
        (data_dir / "memory.json").write_text(
            json.dumps({"today": "2026-05-14", "reply_tone": "friendly"}),
            encoding="utf-8",
        )
        self.data_dir = data_dir
        self.agent = WorkflowAgent(
            WorkflowTools(str(data_dir), mode="commit"),
            UserMemory(str(data_dir / "memory.json")),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_chat_lists_open_todos(self):
        result = self.agent.chat("我有哪些未完成任务？")
        self.assertEqual(result.title, "Open Todos")
        self.assertIn("Read morning inbox", result.to_text())

    def test_chat_lists_conflicts(self):
        result = self.agent.chat("今天有没有日程冲突？")
        self.assertEqual(result.title, "Calendar Conflicts")
        self.assertIn("Deep Work overlaps with Proposal Review", result.to_text())

    def test_chat_completes_todo(self):
        result = self.agent.chat("完成 todo 1")
        self.assertEqual(result.title, "Todo Completed")
        self.assertIn("Todo completed: Read morning inbox", result.to_text())

    def test_chat_reschedules_event(self):
        result = self.agent.chat("把 event-001 改到 16:00-17:00")
        self.assertEqual(result.title, "Event Rescheduled")
        self.assertIn("Event moved: Deep Work to 16:00-17:00", result.to_text())

    def test_chat_dry_run_does_not_persist_reschedule(self):
        dry_run_agent = WorkflowAgent(
            WorkflowTools(str(self.data_dir), mode="dry-run"),
            UserMemory(str(self.data_dir / "memory.json")),
        )
        result = dry_run_agent.chat("把 event-001 改到 16:00-17:00")
        self.assertIn("Event would be moved", result.to_text())
        events = json.loads((self.data_dir / "calendar.json").read_text(encoding="utf-8"))
        self.assertEqual(events[0]["start"], "14:30")


if __name__ == "__main__":
    unittest.main()
