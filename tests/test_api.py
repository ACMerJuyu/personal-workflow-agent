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

    def test_dashboard_static_assets(self):
        response = self.client.get("/static/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("runAgent", response.text)

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
        self.assertEqual(payload["trace"][0]["name"], "search_email")

        history = self.client.get("/agent/runs").json()
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["final_title"], "Important Emails")

    def test_list_todos(self):
        response = self.client.get("/todos")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)


if __name__ == "__main__":
    unittest.main()
