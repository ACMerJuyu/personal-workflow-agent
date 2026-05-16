import json
import unittest
from types import SimpleNamespace

from agent.memory import UserMemory
from agent.openai_planner import OpenAIResponsesHTTPClient, OpenAIToolCallingPlanner
from agent.tools import WorkflowTools


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call-1",
                        name="list_todos",
                        arguments=json.dumps({"include_done": False}),
                    )
                ],
                output_text="",
            )
        return SimpleNamespace(output=[], output_text="Open todos: Read inbox.")


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


class OpenAIPlannerTest(unittest.TestCase):
    def test_openai_planner_executes_function_call_and_returns_result(self):
        client = FakeClient()
        tools = WorkflowTools()
        planner = OpenAIToolCallingPlanner(
            tools=tools,
            memory=UserMemory(),
            client=client,
            model="test-model",
        )

        result = planner.chat("Show my open todos")

        self.assertEqual(result.title, "OpenAI Planner Response")
        self.assertEqual(result.bullets, ["Open todos: Read inbox."])
        self.assertEqual(result.trace[0].name, "list_todos")
        self.assertEqual(result.react_steps[0].kind, "thought")
        second_input_types = [
            item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            for item in client.responses.calls[1]["input"]
        ]
        self.assertIn("function_call", second_input_types)
        self.assertIn("function_call_output", second_input_types)

    def test_openai_planner_accepts_responses_api_dict_shape(self):
        class DictResponses:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                if len(self.calls) == 1:
                    return {
                        "output": [
                            {
                                "type": "function_call",
                                "call_id": "call-1",
                                "name": "list_todos",
                                "arguments": json.dumps({"include_done": False}),
                            }
                        ]
                    }
                return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Open todos ready."}]}]}

        client = SimpleNamespace(responses=DictResponses())
        planner = OpenAIToolCallingPlanner(
            tools=WorkflowTools(),
            memory=UserMemory(),
            client=client,
            model="test-model",
        )

        result = planner.chat("Show my open todos")

        self.assertEqual(result.bullets, ["Open todos ready."])
        self.assertEqual(result.trace[0].name, "list_todos")

    def test_http_client_posts_to_responses_api(self):
        calls = []

        def fake_transport(url, headers, payload, timeout):
            calls.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {"output": []}

        client = OpenAIResponsesHTTPClient(
            api_key="test-key",
            transport=fake_transport,
        )

        response = client.responses.create(
            model="test-model",
            input=[{"role": "user", "content": "hello"}],
            tools=[],
        )

        self.assertEqual(response["output"], [])
        self.assertEqual(calls[0]["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["payload"]["model"], "test-model")


if __name__ == "__main__":
    unittest.main()
