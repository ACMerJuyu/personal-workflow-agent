import json
import os
from typing import Any, Dict, List, Optional

from agent.memory import UserMemory
from agent.models import AgentResult, ReActStep, ToolCall
from agent.tools import WorkflowTools


class PlannerUnavailable(RuntimeError):
    pass


class OpenAIToolCallingPlanner:
    def __init__(
        self,
        tools: WorkflowTools,
        memory: UserMemory,
        client: Any = None,
        model: Optional[str] = None,
    ):
        self.tools = tools
        self.memory = memory
        self.client = client or self._build_client()
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        self.trace: List[ToolCall] = []
        self.react_steps: List[ReActStep] = []

    @classmethod
    def available(cls) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def chat(self, message: str) -> AgentResult:
        self.trace = []
        self.react_steps = [
            ReActStep(
                kind="thought",
                content="Use an LLM planner to choose workflow tools, then answer from observations.",
            )
        ]

        response = self.client.responses.create(
            model=self.model,
            input=self._initial_input(message),
            tools=self.tool_schemas(),
        )

        function_outputs = []
        for call in self._function_calls(response):
            arguments = json.loads(call.arguments or "{}")
            result = self._execute_tool(call.name, arguments)
            self.trace.append(ToolCall(call.name, arguments, result))
            self.react_steps.append(
                ReActStep(
                    kind="action",
                    content=f"OpenAI planner selected {call.name}.",
                    tool_name=call.name,
                    arguments=arguments,
                )
            )
            self.react_steps.append(
                ReActStep(
                    kind="observation",
                    content=f"{call.name} returned {self._summarize_observation(result)}.",
                    tool_name=call.name,
                    observation=result,
                )
            )
            function_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

        final_text = self._output_text(response)
        if function_outputs:
            final_response = self.client.responses.create(
                model=self.model,
                input=self._initial_input(message) + function_outputs,
                tools=self.tool_schemas(),
            )
            final_text = self._output_text(final_response) or final_text

        bullets = self._bullets_from_text(final_text)
        self.react_steps.append(
            ReActStep(kind="final", content=f"Return OpenAI planner answer with {len(bullets)} bullet(s).")
        )
        return AgentResult(
            "OpenAI Planner Response",
            bullets,
            list(self.trace),
            list(self.react_steps),
            planner_mode="openai",
        )

    def _build_client(self) -> Any:
        if not os.environ.get("OPENAI_API_KEY"):
            raise PlannerUnavailable("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise PlannerUnavailable("openai package is not installed") from error
        return OpenAI()

    def _initial_input(self, message: str) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are a personal workflow agent. Use tools for email, calendar, todos, "
                    "and memory. Write actions are protected by dry-run and approval workflow."
                ),
            },
            {"role": "user", "content": message},
        ]

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name == "load_memory":
            return self.memory.load()
        tool = getattr(self.tools, name)
        return tool(**arguments)

    @staticmethod
    def _function_calls(response: Any) -> List[Any]:
        return [item for item in getattr(response, "output", []) if getattr(item, "type", "") == "function_call"]

    @staticmethod
    def _output_text(response: Any) -> str:
        return getattr(response, "output_text", "") or ""

    @staticmethod
    def _bullets_from_text(text: str) -> List[str]:
        lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
        return lines or ["No answer returned by the OpenAI planner."]

    @staticmethod
    def _summarize_observation(result: Any) -> str:
        if isinstance(result, list):
            return f"{len(result)} item(s)"
        if isinstance(result, dict):
            return f"{len(result)} field(s)"
        return "a value"

    @staticmethod
    def tool_schemas() -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "load_memory",
                "description": "Load user memory such as today's date and reply tone.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "type": "function",
                "name": "search_email",
                "description": "Search email by keyword, sender, unread status, or priority.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "sender": {"type": "string"},
                        "unread_only": {"type": "boolean"},
                        "priority": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_calendar_events",
                "description": "List calendar events, optionally filtered by date.",
                "parameters": {
                    "type": "object",
                    "properties": {"date": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "detect_calendar_conflicts",
                "description": "Detect overlapping calendar events for a date.",
                "parameters": {
                    "type": "object",
                    "properties": {"date": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_todos",
                "description": "List todos, optionally including completed todos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_done": {"type": "boolean"},
                        "priority": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "add_todo",
                "description": "Create a todo. In dry-run mode this proposes an action.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "due": {"type": "string"},
                        "source": {"type": "string"},
                        "priority": {"type": "string"},
                    },
                    "required": ["title", "due", "source"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "complete_todo",
                "description": "Complete a todo. In dry-run mode this proposes an action.",
                "parameters": {
                    "type": "object",
                    "properties": {"todo_id": {"type": "integer"}},
                    "required": ["todo_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "reschedule_event",
                "description": "Move a calendar event. In dry-run mode this proposes an action.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                        "new_start": {"type": "string"},
                        "new_end": {"type": "string"},
                    },
                    "required": ["event_id", "new_start", "new_end"],
                    "additionalProperties": False,
                },
            },
        ]
