import argparse
import json

from agent.planner import WorkflowAgent


def main():
    parser = argparse.ArgumentParser(description="Personal Workflow Agent demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("brief", help="Generate today's daily brief")
    subparsers.add_parser("emails", help="Show important emails")

    plan_parser = subparsers.add_parser("plan", help="Run the agent on a user goal")
    plan_parser.add_argument("goal", help="User goal")

    args = parser.parse_args()
    agent = WorkflowAgent()

    if args.command == "brief":
        result = agent.daily_brief()
    elif args.command == "emails":
        result = agent.important_emails()
    else:
        result = agent.run(args.goal)

    print(result.to_text())
    print("\nTool Trace")
    print(json.dumps([call.to_dict() for call in result.trace], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

