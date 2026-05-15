from typing import Any, Dict, List

from agent.memory import UserMemory
from agent.models import AgentResult, ReActStep, ToolCall
from agent.parser import extract_event_id, extract_time_range, extract_todo_id
from agent.router import IntentRouter
from agent.tools import WorkflowTools


class WorkflowAgent:
    def __init__(self, tools: WorkflowTools = None, memory: UserMemory = None, router: IntentRouter = None):
        self.tools = tools or WorkflowTools()
        self.memory = memory or UserMemory()
        self.router = router or IntentRouter()
        self.trace: List[ToolCall] = []
        self.react_steps: List[ReActStep] = []

    def run(self, goal: str) -> AgentResult:
        self.trace = []
        lowered = goal.lower()

        if "email" in lowered or "mail" in lowered or "important" in lowered:
            return self.important_emails()
        return self.daily_brief()

    def chat(self, message: str) -> AgentResult:
        route = self.router.route(message)

        if route.intent == "morning_brief":
            return self.daily_brief()
        if route.intent == "important_emails":
            return self.important_emails()
        if route.intent == "today_calendar":
            return self.today_calendar()
        if route.intent == "open_todos":
            return self.open_todos()
        if route.intent == "calendar_conflicts":
            return self.calendar_conflicts()
        if route.intent == "complete_todo":
            todo_id = extract_todo_id(message)
            if todo_id is None:
                return AgentResult("Missing Todo ID", ["Please specify which todo to complete."], [])
            return self.complete_todo(todo_id)
        if route.intent == "reschedule_event":
            event_id = extract_event_id(message)
            time_range = extract_time_range(message)
            if event_id is None or time_range is None:
                return AgentResult(
                    "Missing Event Details",
                    ["Please specify an event id and time range, for example: move event-001 to 16:00-17:00."],
                    [],
                )
            return self.reschedule_event(event_id, time_range[0], time_range[1])

        return AgentResult(
            "Unknown Request",
            [
                "I can help with morning brief, important emails, today's calendar, open todos, conflicts, completing todos, and rescheduling events."
            ],
            [],
        )

    def important_emails(self) -> AgentResult:
        self._start_react("Find unread high-priority emails before answering.")
        emails = self._call("search_email", {"unread_only": True, "priority": "high"})

        if not emails:
            return self._finish("Important Emails", ["No high-priority unread email found."])

        bullets = []
        for email in emails:
            bullets.append(f"{email['sender']}: {email['subject']} due by {email['deadline']}.")

        return self._finish("Important Emails", bullets)

    def open_todos(self) -> AgentResult:
        self._start_react("List open todos so the response reflects current task state.")
        todos = self._call("list_todos", {"include_done": False})

        if not todos:
            return self._finish("Open Todos", ["No open todo found."])

        bullets = [
            f"{todo['title']} due {todo['due']} priority {todo['priority']}."
            for todo in todos
        ]
        return self._finish("Open Todos", bullets)

    def today_calendar(self) -> AgentResult:
        self._start_react("Load today's date, then inspect the calendar for that date.")
        memory = self._call("load_memory", {})
        events = self._call("list_calendar_events", {"date": memory["today"]})

        if not events:
            return self._finish("Today's Calendar", ["No calendar event found today."])

        bullets = [
            f"{event['start']}-{event['end']} {event['title']}"
            for event in events
        ]
        return self._finish("Today's Calendar", bullets)

    def calendar_conflicts(self) -> AgentResult:
        self._start_react("Load today's date, then check whether any calendar events overlap.")
        memory = self._call("load_memory", {})
        conflicts = self._call("detect_calendar_conflicts", {"date": memory["today"]})

        if not conflicts:
            return self._finish("Calendar Conflicts", ["No calendar conflict found today."])

        bullets = [
            f"{conflict['first']['title']} overlaps with {conflict['second']['title']}."
            for conflict in conflicts
        ]
        return self._finish("Calendar Conflicts", bullets)

    def complete_todo(self, todo_id: int) -> AgentResult:
        self._start_react("Complete the requested todo while respecting dry-run mode.")
        todo = self._call("complete_todo", {"todo_id": todo_id})
        action = "Todo would be completed" if todo.get("dry_run") else "Todo completed"
        return self._finish("Todo Completed", [f"{action}: {todo['title']}."])

    def reschedule_event(self, event_id: str, new_start: str, new_end: str) -> AgentResult:
        self._start_react("Move the requested calendar event while respecting dry-run mode.")
        event = self._call(
            "reschedule_event",
            {"event_id": event_id, "new_start": new_start, "new_end": new_end},
        )
        return self._finish(
            "Event Rescheduled",
            [
                (
                    "Event would be moved"
                    if event.get("dry_run")
                    else "Event moved"
                )
                + f": {event['title']} to {event['start']}-{event['end']}."
            ],
        )

    def daily_brief(self) -> AgentResult:
        self._start_react("Gather memory, email, calendar, todos, and conflicts for a daily brief.")
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
            action = "Todo would be created" if todo.get("dry_run") else "Todo created"
            bullets.append(f"{action}: {todo['title']} due {todo['due']}.")
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

        return self._finish("Daily Brief", bullets)

    def _call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name == "load_memory":
            result = self.memory.load()
        else:
            tool = getattr(self.tools, tool_name)
            result = tool(**arguments)

        self.trace.append(ToolCall(tool_name, arguments, result))
        self.react_steps.append(
            ReActStep(
                kind="action",
                content=f"Call {tool_name}.",
                tool_name=tool_name,
                arguments=arguments,
            )
        )
        self.react_steps.append(
            ReActStep(
                kind="observation",
                content=f"{tool_name} returned {self._summarize_observation(result)}.",
                tool_name=tool_name,
                observation=result,
            )
        )
        return result

    def _start_react(self, thought: str) -> None:
        self.trace = []
        self.react_steps = [ReActStep(kind="thought", content=thought)]

    def _finish(self, title: str, bullets: List[str]) -> AgentResult:
        self.react_steps.append(
            ReActStep(kind="final", content=f"Return {title} with {len(bullets)} bullet(s).")
        )
        return AgentResult(title, bullets, list(self.trace), list(self.react_steps))

    @staticmethod
    def _summarize_observation(result: Any) -> str:
        if isinstance(result, list):
            return f"{len(result)} item(s)"
        if isinstance(result, dict):
            return f"{len(result)} field(s)"
        return "a value"
