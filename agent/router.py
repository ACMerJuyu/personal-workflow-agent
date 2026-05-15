from dataclasses import dataclass


@dataclass
class Route:
    intent: str
    confidence: float


class IntentRouter:
    def route(self, message: str) -> Route:
        normalized = message.lower().strip()

        if self._has_any(normalized, ["brief", "summary", "morning", "早上", "今天重要", "今天有什么"]):
            return Route("morning_brief", 0.9)

        if self._has_any(normalized, ["email", "mail", "邮件", "邮箱"]):
            return Route("important_emails", 0.9)

        if self._has_any(normalized, ["reschedule", "move", "改到", "调整", "挪到"]):
            return Route("reschedule_event", 0.95)

        if self._has_any(normalized, ["calendar", "schedule", "日程", "安排", "会议"]):
            if self._has_any(normalized, ["conflict", "冲突", "overlap"]):
                return Route("calendar_conflicts", 0.95)
            return Route("today_calendar", 0.9)

        if self._has_any(normalized, ["todo", "task", "任务", "待办"]):
            if self._has_any(normalized, ["未完成", "open", "pending"]):
                return Route("open_todos", 0.9)
            if self._has_any(normalized, ["complete", "done", "finish", "完成", "做完"]):
                return Route("complete_todo", 0.95)
            return Route("open_todos", 0.9)

        if self._has_any(normalized, ["冲突", "conflict", "overlap"]):
            return Route("calendar_conflicts", 0.85)

        return Route("unknown", 0.0)

    @staticmethod
    def _has_any(text: str, keywords: list) -> bool:
        return any(keyword in text for keyword in keywords)
