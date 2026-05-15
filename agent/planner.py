from typing import Any, Dict, List

from agent.memory import UserMemory
from agent.models import AgentResult, ToolCall
from agent.tools import WorkflowTools


class WorkflowAgent:
    def __init__(self, tools: WorkflowTools = None, memory: UserMemory = None):
        self.tools = tools or WorkflowTools()
        self.memory = memory or UserMemory()
        self.trace: List[ToolCall] = []

    def run(self, goal: str) -> AgentResult:
        self.trace = []
        lowered = goal.lower()

        if "email" in lowered or "mail" in lowered or "important" in lowered:
            return self.important_emails()
        return self.daily_brief()

    def important_emails(self) -> AgentResult:
        self.trace = []
        emails = self._call("search_email", {"unread_only": True, "priority": "high"})

        if not emails:
            return AgentResult("Important Emails", ["No high-priority unread email found."], self.trace)

        bullets = []
        for email in emails:
            bullets.append(f"{email['sender']}: {email['subject']} due by {email['deadline']}.")

        return AgentResult("Important Emails", bullets, self.trace)

    def open_todos(self) -> AgentResult:
        self.trace = []
        todos = self._call("list_todos", {"include_done": False})

        if not todos:
            return AgentResult("Open Todos", ["No open todo found."], self.trace)

        bullets = [
            f"{todo['title']} due {todo['due']} priority {todo['priority']}."
            for todo in todos
        ]
        return AgentResult("Open Todos", bullets, self.trace)

    def today_calendar(self) -> AgentResult:
        self.trace = []
        memory = self._call("load_memory", {})
        events = self._call("list_calendar_events", {"date": memory["today"]})

        if not events:
            return AgentResult("Today's Calendar", ["No calendar event found today."], self.trace)

        bullets = [
            f"{event['start']}-{event['end']} {event['title']}"
            for event in events
        ]
        return AgentResult("Today's Calendar", bullets, self.trace)

    def daily_brief(self) -> AgentResult:
        self.trace = []
        memory = self._call("load_memory", {})
        important_emails = self._call("search_email", {"unread_only": True, "priority": "high"})
        events = self._call("list_calendar_events", {"date": memory["today"]})
        todos = self._call("list_todos", {"include_done": False})
        conflicts = self._call("detect_calendar_conflicts", {"date": memory["today"]})

        bullets = []

        if important_emails:
            email = important_emails[0]
            bullets.append(
                f"Important email from {email['sender']}: {email['subject']} by {email['deadline']}."
            )
            todo = self._call(
                "add_todo",
                {
                    "title": "Review A1 product proposal",
                    "due": email["deadline"],
                    "source": f"email:{email['id']}",
                    "priority": "high",
                },
            )
            bullets.append(f"Todo created: {todo['title']} due {todo['due']}.")
            draft = self._call("draft_reply", {"email": email, "tone": memory["reply_tone"]})
            bullets.append(f"Reply draft prepared to {draft['to']}.")

        if conflicts:
            conflict = conflicts[0]
            bullets.append(
                "Calendar conflict detected: "
                f"{conflict['first']['title']} overlaps with {conflict['second']['title']}."
            )

        if todos:
            todo_titles = ", ".join(todo["title"] for todo in todos)
            bullets.append(f"Open todos: {todo_titles}.")

        if events:
            titles = ", ".join(event["title"] for event in events)
            bullets.append(f"Today's calendar: {titles}.")

        if not bullets:
            bullets.append("No urgent work found today.")

        return AgentResult("Daily Brief", bullets, self.trace)

    def _call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name == "load_memory":
            result = self.memory.load()
        else:
            tool = getattr(self.tools, tool_name)
            result = tool(**arguments)

        self.trace.append(ToolCall(tool_name, arguments, result))
        return result
