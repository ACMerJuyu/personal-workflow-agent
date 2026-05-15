import json
import tempfile
import unittest
from pathlib import Path

from agent.models import AgentResult, ToolCall
from agent.storage import SQLiteStorage
from agent.tools import WorkflowTools


class SQLiteStorageTest(unittest.TestCase):
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

    def test_seed_and_search_email(self):
        emails = self.storage.search_email(priority="high", unread_only=True)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["sender"], "Alex Chen")

    def test_tools_dry_run_does_not_write_sqlite(self):
        tools = WorkflowTools(mode="dry-run", storage=self.storage)
        todo = tools.add_todo("Dry run task", "16:00", "manual")
        self.assertTrue(todo["dry_run"])
        todos = self.storage.list_todos(include_done=True)
        self.assertEqual(len(todos), 1)

    def test_tools_commit_writes_sqlite(self):
        tools = WorkflowTools(mode="commit", storage=self.storage)
        todo = tools.add_todo("Committed task", "16:00", "manual")
        self.assertEqual(todo["id"], 2)
        todos = self.storage.list_todos(include_done=True)
        self.assertEqual(len(todos), 2)

    def test_save_agent_run_with_tool_calls(self):
        result = AgentResult(
            "Demo Result",
            ["One thing happened."],
            [ToolCall("search_email", {"priority": "high"}, [{"id": "email-1"}])],
        )
        run_id = self.storage.save_agent_run("demo", "important_emails", "dry-run", result)
        run = self.storage.get_agent_run(run_id)
        self.assertEqual(run["user_message"], "demo")
        self.assertEqual(run["tool_calls"][0]["tool_name"], "search_email")

    def test_pending_action_lifecycle(self):
        action_id = self.storage.create_pending_action(
            run_id=7,
            action_type="complete_todo",
            description="Complete todo 1",
            payload={"todo_id": 1},
        )

        actions = self.storage.list_pending_actions()
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["id"], action_id)
        self.assertEqual(actions[0]["status"], "pending")
        self.assertEqual(actions[0]["payload"]["todo_id"], 1)

        approved = self.storage.mark_pending_action(action_id, "approved")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(self.storage.list_pending_actions(), [])


if __name__ == "__main__":
    unittest.main()
