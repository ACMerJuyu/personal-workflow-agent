import argparse
import json

from agent.memory import UserMemory
from agent.planner import WorkflowAgent
from agent.storage import SQLiteStorage
from agent.tools import WorkflowTools


def main():
    parser = argparse.ArgumentParser(description="Personal Workflow Agent demo")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist write actions. Default is dry-run mode.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset SQLite demo data from JSON seed files before running.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("brief", help="Generate today's daily brief")
    subparsers.add_parser("emails", help="Show important emails")
    subparsers.add_parser("todos", help="Show open todos")
    subparsers.add_parser("calendar", help="Show today's calendar events")

    plan_parser = subparsers.add_parser("plan", help="Run the agent on a user goal")
    plan_parser.add_argument("goal", help="User goal")

    chat_parser = subparsers.add_parser("chat", help="Chat with the workflow agent")
    chat_parser.add_argument("message", help="Natural language message")

    history_parser = subparsers.add_parser("history", help="Show saved agent runs")
    history_parser.add_argument("run_id", nargs="?", type=int, help="Optional run id to inspect")

    args = parser.parse_args()
    mode = "commit" if args.commit else "dry-run"
    storage = SQLiteStorage()
    storage.seed_from_json(force=args.reset_db)
    agent = WorkflowAgent(
        tools=WorkflowTools(mode=mode, storage=storage),
        memory=UserMemory(storage=storage),
    )

    if args.command == "brief":
        result = agent.daily_brief()
        intent = "morning_brief"
        user_message = "brief"
    elif args.command == "emails":
        result = agent.important_emails()
        intent = "important_emails"
        user_message = "emails"
    elif args.command == "todos":
        result = agent.open_todos()
        intent = "open_todos"
        user_message = "todos"
    elif args.command == "calendar":
        result = agent.today_calendar()
        intent = "today_calendar"
        user_message = "calendar"
    elif args.command == "plan":
        result = agent.run(args.goal)
        intent = "plan"
        user_message = args.goal
    elif args.command == "history":
        show_history(storage, args.run_id)
        return
    else:
        result = agent.chat(args.message)
        intent = agent.router.route(args.message).intent
        user_message = args.message

    run_id = storage.save_agent_run(user_message, intent, mode, result)

    print(result.to_text())
    print(f"\nSaved Run: #{run_id}")
    print("\nTool Trace")
    print(json.dumps([call.to_dict() for call in result.trace], ensure_ascii=False, indent=2))


def show_history(storage: SQLiteStorage, run_id: int = None) -> None:
    if run_id is not None:
        run = storage.get_agent_run(run_id)
        print(f"Run #{run['id']}")
        print(f"Message: {run['user_message']}")
        print(f"Intent: {run['intent']}")
        print(f"Mode: {run['mode']}")
        print(f"Created: {run['created_at']}")
        print(f"Result: {run['final_title']}")
        for index, bullet in enumerate(run["final_bullets"], start=1):
            print(f"{index}. {bullet}")
        print("\nTool Calls")
        for call in run["tool_calls"]:
            print(f"- {call['tool_name']}: {json.dumps(call['arguments'], ensure_ascii=False)}")
        return

    runs = storage.list_agent_runs()
    if not runs:
        print("No saved agent runs.")
        return

    for run in runs:
        print(
            f"#{run['id']} [{run['mode']}] {run['intent']} - "
            f"{run['final_title']} ({run['created_at']})"
        )


if __name__ == "__main__":
    main()
