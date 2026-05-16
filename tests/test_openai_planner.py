import json
import unittest
from types import SimpleNamespace

from agent.memory import UserMemory
from agent.openai_planner import OpenAIToolCallingPlanner
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
        self.assertIn("function_call_output", json.dumps(client.responses.calls[1]["input"]))


if __name__ == "__main__":
    unittest.main()
