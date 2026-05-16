import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class APITest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        self.project_root = Path(__file__).resolve().parents[1]
        os.chdir(self.project_root)

        self.db_path = self.project_root / "data" / "workflow.db"
        if self.db_path.exists():
            self.db_path.unlink()

        from api import app

        self.client = TestClient(app)

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_dashboard(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Agent Dashboard", response.text)
        self.assertIn("Planner", response.text)
        self.assertIn("Quick Commands", response.text)
        self.assertIn("System Capabilities", response.text)

    def test_dashboard_static_assets(self):
        response = self.client.get("/static/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("runAgent", response.text)
        self.assertIn("approveAction", response.text)

    def test_agent_chat_persists_run(self):
        response = self.client.post(
            "/agent/chat",
            json={"message": "有没有重要邮件？", "reset_db": True},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "Important Emails")
        self.assertGreaterEqual(payload["run_id"], 1)
        self.assertEqual(payload["intent"], "important_emails")
        self.assertEqual(payload["planner_mode"], "rule-based")
        self.assertEqual(payload["trace"][0]["name"], "search_email")
        self.assertEqual(payload["react_steps"][0]["kind"], "thought")
        self.assertIn("action", [step["kind"] for step in payload["react_steps"]])

        history = self.client.get("/agent/runs").json()
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["final_title"], "Important Emails")

    def test_agent_uses_sqlite_adapters_when_storage_is_configured(self):
        from api import build_agent, get_storage

        storage = get_storage(reset_db=True)
        agent = build_agent(storage)

        self.assertIsNotNone(agent.tools.email_adapter)
        self.assertIsNotNone(agent.tools.calendar_adapter)
        self.assertIsNotNone(agent.tools.todo_adapter)

    def test_dashboard_mentions_react_timeline(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ReAct Timeline", response.text)

    def test_dashboard_mentions_pending_actions(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Pending Actions", response.text)

    def test_list_todos(self):
        response = self.client.get("/todos")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_dry_run_write_creates_pending_action_and_approve_commits_it(self):
        chat_response = self.client.post(
            "/agent/chat",
            json={"message": "Move event-001 to 16:00-17:00", "reset_db": True},
        )
        self.assertEqual(chat_response.status_code, 200)

        actions = self.client.get("/agent/pending-actions").json()
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action_type"], "reschedule_event")
        self.assertEqual(actions[0]["status"], "pending")

        approve_response = self.client.post(f"/agent/actions/{actions[0]['id']}/approve")
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")

        events = self.client.get("/calendar").json()
        moved = [event for event in events if event["id"] == "event-001"][0]
        self.assertEqual(moved["start"], "16:00")
        self.assertEqual(moved["end"], "17:00")

    def test_reject_pending_action_does_not_commit_it(self):
        self.client.post(
            "/agent/chat",
            json={"message": "Move event-001 to 16:00-17:00", "reset_db": True},
        )
        action = self.client.get("/agent/pending-actions").json()[0]

        reject_response = self.client.post(f"/agent/actions/{action['id']}/reject")
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")

        events = self.client.get("/calendar").json()
        original = [event for event in events if event["id"] == "event-001"][0]
        self.assertNotEqual(original["start"], "16:00")


if __name__ == "__main__":
    unittest.main()
