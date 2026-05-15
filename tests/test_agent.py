import json
import tempfile
import unittest
from pathlib import Path

from agent.memory import UserMemory
from agent.planner import WorkflowAgent
from agent.tools import WorkflowTools


class WorkflowAgentTest(unittest.TestCase):
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
                        "id": "event-1",
                        "title": "Deep Work",
                        "date": "2026-05-14",
                        "start": "14:30",
                        "end": "15:30",
                    },
                    {
                        "id": "event-2",
                        "title": "Proposal Review",
                        "date": "2026-05-14",
                        "start": "15:00",
                        "end": "15:45",
                    },
                ]
            ),
            encoding="utf-8",
        )
        (data_dir / "todos.json").write_text("[]", encoding="utf-8")
        (data_dir / "memory.json").write_text(
            json.dumps({"today": "2026-05-14", "reply_tone": "friendly"}),
            encoding="utf-8",
        )
        self.agent = WorkflowAgent(
            WorkflowTools(str(data_dir), mode="commit"),
            UserMemory(str(data_dir / "memory.json")),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_daily_brief_uses_tools_and_creates_actions(self):
        result = self.agent.daily_brief()
        text = result.to_text()
        self.assertIn("Important email from Alex Chen", text)
        self.assertIn("Calendar conflict detected", text)
        self.assertGreaterEqual(len(result.trace), 5)
        tool_names = [call.name for call in result.trace]
        self.assertIn("list_todos", tool_names)

    def test_daily_brief_lists_open_todos(self):
        data_dir = Path(self.temp_dir.name)
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
        result = self.agent.daily_brief()
        self.assertIn("Open todos: Read morning inbox.", result.to_text())

    def test_calendar_conflicts_exposes_react_steps(self):
        result = self.agent.chat("Do I have calendar conflicts today?")
        step_types = [step.kind for step in result.react_steps]

        self.assertEqual(step_types[0], "thought")
        self.assertIn("action", step_types)
        self.assertIn("observation", step_types)
        self.assertEqual(step_types[-1], "final")
        self.assertIn("detect_calendar_conflicts", [step.tool_name for step in result.react_steps])


if __name__ == "__main__":
    unittest.main()
