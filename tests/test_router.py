import unittest

from agent.parser import extract_event_id, extract_time_range, extract_todo_id
from agent.router import IntentRouter


class IntentRouterTest(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_routes_morning_brief(self):
        route = self.router.route("今天有什么重要事情？")
        self.assertEqual(route.intent, "morning_brief")

    def test_routes_email(self):
        route = self.router.route("有没有重要邮件？")
        self.assertEqual(route.intent, "important_emails")

    def test_routes_calendar_conflict(self):
        route = self.router.route("今天有没有日程冲突？")
        self.assertEqual(route.intent, "calendar_conflicts")

    def test_routes_complete_todo(self):
        route = self.router.route("完成 todo 1")
        self.assertEqual(route.intent, "complete_todo")

    def test_extract_todo_id(self):
        self.assertEqual(extract_todo_id("完成 todo 12"), 12)

    def test_extract_event_details(self):
        self.assertEqual(extract_event_id("把 event-001 改到 16:00-17:00"), "event-001")
        self.assertEqual(extract_time_range("把 event-001 改到 16:00-17:00"), ("16:00", "17:00"))


if __name__ == "__main__":
    unittest.main()

