import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.memory import UserMemory
from agent.planner import WorkflowAgent
from agent.storage import SQLiteStorage
from agent.tools import WorkflowTools
from api import save_pending_actions


DEFAULT_CASES_PATH = PROJECT_ROOT / "evals" / "workflow_cases.json"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "evals.db"


def run_evals(cases_path: Optional[Path] = None) -> Dict[str, Any]:
    cases = _load_cases(cases_path or DEFAULT_CASES_PATH)
    results = [_run_case(case) for case in cases]
    failed = [result for result in results if not result["passed"]]

    return {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
    }


def _run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()

    storage = SQLiteStorage(str(DEFAULT_DB_PATH))
    storage.seed_from_json(str(PROJECT_ROOT / "data"), force=True)

    agent = WorkflowAgent(
        tools=WorkflowTools(mode="dry-run", storage=storage),
        memory=UserMemory(storage=storage),
    )
    route = agent.router.route(case["message"])
    result = agent.chat(case["message"])
    run_id = storage.save_agent_run(case["message"], route.intent, "dry-run", result)
    save_pending_actions(storage, run_id, result)

    actual_tools = [call.name for call in result.trace]
    pending_actions = storage.list_pending_actions()
    checks = [
        _check_equal("intent", route.intent, case["expected_intent"]),
        _check_equal("title", result.title, case["expected_title"]),
        _check_contains_all("tools", actual_tools, case["expected_tools"]),
        _check_equal("pending_actions", len(pending_actions), case["expected_pending_actions"]),
    ]
    failures = [check for check in checks if not check["passed"]]

    return {
        "id": case["id"],
        "message": case["message"],
        "passed": not failures,
        "failures": failures,
        "actual": {
            "intent": route.intent,
            "title": result.title,
            "tools": actual_tools,
            "pending_actions": len(pending_actions),
        },
    }


def _load_cases(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _check_equal(name: str, actual: Any, expected: Any) -> Dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_contains_all(name: str, actual: List[str], expected: List[str]) -> Dict[str, Any]:
    missing = [item for item in expected if item not in actual]
    return {
        "name": name,
        "passed": not missing,
        "actual": actual,
        "expected": expected,
        "missing": missing,
    }


def main() -> int:
    report = run_evals()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
