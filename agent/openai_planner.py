import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from agent.memory import UserMemory
from agent.models import AgentResult, ReActStep, ToolCall
from agent.tools import WorkflowTools


class PlannerUnavailable(RuntimeError):
    pass


class OpenAIResponsesHTTPClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        transport: Optional[Callable[[str, Dict[str, str], Dict[str, Any], int], Dict[str, Any]]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport or self._post_json
        self.responses = self

    def create(self, **payload: Any) -> Dict[str, Any]:
        return self.transport(
            f"{self.base_url}/responses",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload,
            self.timeout,
        )

    @staticmethod
    def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise PlannerUnavailable(f"OpenAI Responses API error: {error.code} {detail}") from error
        except urllib.error.URLError as error:
            raise PlannerUnavailable(f"OpenAI Responses API unavailable: {error.reason}") from error


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
            tool_name = self._get(call, "name")
            call_id = self._get(call, "call_id")
            arguments = json.loads(self._get(call, "arguments", "{}") or "{}")
            result = self._execute_tool(tool_name, arguments)
            self.trace.append(ToolCall(tool_name, arguments, result))
            self.react_steps.append(
                ReActStep(
                    kind="action",
                    content=f"OpenAI planner selected {tool_name}.",
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
            function_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

        final_text = self._output_text(response)
        if function_outputs:
            conversation_input = (
                self._initial_input(message)
                + self._serializable_output_items(response)
                + function_outputs
            )
            final_response = self.client.responses.create(
                model=self.model,
                input=conversation_input,
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
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise PlannerUnavailable("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError:
            return OpenAIResponsesHTTPClient(api_key=api_key)
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
        return [
            item
            for item in OpenAIToolCallingPlanner._get(response, "output", [])
            if OpenAIToolCallingPlanner._get(item, "type", "") == "function_call"
        ]

    @staticmethod
    def _serializable_output_items(response: Any) -> List[Dict[str, Any]]:
        items = []
        for item in OpenAIToolCallingPlanner._get(response, "output", []):
            if isinstance(item, dict):
                items.append(item)
            elif hasattr(item, "model_dump"):
                items.append(item.model_dump())
            elif hasattr(item, "dict"):
                items.append(item.dict())
            elif hasattr(item, "__dict__"):
                items.append(dict(item.__dict__))
        return items

    @staticmethod
    def _output_text(response: Any) -> str:
        output_text = OpenAIToolCallingPlanner._get(response, "output_text", "")
        if output_text:
            return output_text

        for item in OpenAIToolCallingPlanner._get(response, "output", []):
            if OpenAIToolCallingPlanner._get(item, "type", "") != "message":
                continue
            for content in OpenAIToolCallingPlanner._get(item, "content", []):
                if OpenAIToolCallingPlanner._get(content, "type", "") == "output_text":
                    text = OpenAIToolCallingPlanner._get(content, "text", "")
                    if text:
                        return text
        return ""

    @staticmethod
    def _get(value: Any, key: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

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
