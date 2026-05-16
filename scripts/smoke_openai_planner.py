import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.memory import UserMemory
from agent.openai_planner import OpenAIToolCallingPlanner, PlannerUnavailable
from agent.storage import SQLiteStorage
from agent.tools import WorkflowTools


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("SKIPPED: OPENAI_API_KEY is not set. Configure it before running this smoke test.")
        return 0

    storage = SQLiteStorage()
    storage.seed_from_json(force=True)
    planner = OpenAIToolCallingPlanner(
        tools=WorkflowTools(mode="dry-run", storage=storage),
        memory=UserMemory(storage=storage),
    )

    try:
        result = planner.chat("Help me prepare for today's work.")
    except PlannerUnavailable as error:
        print(str(error))
        return 2

    print(result.to_text())
    print("\nPlanner Mode:", result.planner_mode)
    print("\nTool Trace")
    print(json.dumps([call.to_dict() for call in result.trace], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
