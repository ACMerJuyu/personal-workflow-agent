import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class PlannerModeTest(unittest.TestCase):
    def test_api_falls_back_to_rule_planner_without_openai_key(self):
        with patch.dict(os.environ, {}, clear=True):
            from api import app

            client = TestClient(app)
            response = client.post(
                "/agent/chat",
                json={
                    "message": "Any important emails?",
                    "planner": "openai",
                    "reset_db": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["planner_mode"], "rule-based")
        self.assertEqual(payload["title"], "Important Emails")


if __name__ == "__main__":
    unittest.main()
