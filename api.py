from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.memory import UserMemory
from agent.models import AgentResult
from agent.planner import WorkflowAgent
from agent.storage import SQLiteStorage
from agent.tools import WorkflowTools


app = FastAPI(
    title="Personal Workflow Agent API",
    description="API service for a personal workflow agent with tool traces and SQLite persistence.",
    version="0.1.0",
)

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    commit: bool = False
    reset_db: bool = False


class AgentResponse(BaseModel):
    run_id: int
    title: str
    bullets: List[str]
    trace: List[Dict[str, Any]]
    react_steps: List[Dict[str, Any]]
    mode: str
    intent: str


def get_storage(reset_db: bool = False) -> SQLiteStorage:
    storage = SQLiteStorage()
    storage.seed_from_json(force=reset_db)
    return storage


def build_agent(storage: SQLiteStorage, commit: bool = False) -> WorkflowAgent:
    mode = "commit" if commit else "dry-run"
    return WorkflowAgent(
        tools=WorkflowTools(mode=mode, storage=storage),
        memory=UserMemory(storage=storage),
    )


def response_from_result(
    storage: SQLiteStorage,
    result: AgentResult,
    message: str,
    intent: str,
    mode: str,
) -> AgentResponse:
    run_id = storage.save_agent_run(message, intent, mode, result)
    if mode == "dry-run":
        save_pending_actions(storage, run_id, result)
    return AgentResponse(
        run_id=run_id,
        title=result.title,
        bullets=result.bullets,
        trace=[call.to_dict() for call in result.trace],
        react_steps=[step.to_dict() for step in result.react_steps],
        mode=mode,
        intent=intent,
    )


def save_pending_actions(storage: SQLiteStorage, run_id: int, result: AgentResult) -> None:
    for call in result.trace:
        if call.name not in {"add_todo", "complete_todo", "reschedule_event"}:
            continue
        if not isinstance(call.result, dict) or not call.result.get("dry_run"):
            continue
        storage.create_pending_action(
            run_id=run_id,
            action_type=call.name,
            description=describe_pending_action(call.name, call.arguments, call.result),
            payload=call.arguments,
        )


def describe_pending_action(tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> str:
    if tool_name == "add_todo":
        return f"Create todo: {result['title']} due {result['due']}"
    if tool_name == "complete_todo":
        return f"Complete todo: {result['title']}"
    if tool_name == "reschedule_event":
        return f"Move event {arguments['event_id']} to {arguments['new_start']}-{arguments['new_end']}"
    return tool_name


def execute_pending_action(storage: SQLiteStorage, action: Dict[str, Any]) -> Dict[str, Any]:
    tools = WorkflowTools(mode="commit", storage=storage)
    payload = action["payload"]

    if action["action_type"] == "add_todo":
        return tools.add_todo(**payload)
    if action["action_type"] == "complete_todo":
        return tools.complete_todo(**payload)
    if action["action_type"] == "reschedule_event":
        return tools.reschedule_event(**payload)
    raise ValueError(f"unsupported action type: {action['action_type']}")


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "name": "Personal Workflow Agent API",
        "status": "ok",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/chat", response_model=AgentResponse)
def chat(request: ChatRequest) -> AgentResponse:
    storage = get_storage(reset_db=request.reset_db)
    agent = build_agent(storage, commit=request.commit)
    result = agent.chat(request.message)
    intent = agent.router.route(request.message).intent
    mode = "commit" if request.commit else "dry-run"
    return response_from_result(storage, result, request.message, intent, mode)


@app.post("/agent/brief", response_model=AgentResponse)
def brief(commit: bool = False, reset_db: bool = False) -> AgentResponse:
    storage = get_storage(reset_db=reset_db)
    agent = build_agent(storage, commit=commit)
    result = agent.daily_brief()
    mode = "commit" if commit else "dry-run"
    return response_from_result(storage, result, "brief", "morning_brief", mode)


@app.get("/agent/runs")
def list_runs(limit: int = 10) -> List[Dict[str, Any]]:
    storage = get_storage()
    return storage.list_agent_runs(limit=limit)


@app.get("/agent/runs/{run_id}")
def get_run(run_id: int) -> Dict[str, Any]:
    storage = get_storage()
    try:
        return storage.get_agent_run(run_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/agent/pending-actions")
def list_pending_actions(include_resolved: bool = False) -> List[Dict[str, Any]]:
    storage = get_storage()
    return storage.list_pending_actions(include_resolved=include_resolved)


@app.post("/agent/actions/{action_id}/approve")
def approve_action(action_id: int) -> Dict[str, Any]:
    storage = get_storage()
    try:
        action = storage.get_pending_action(action_id)
        result = execute_pending_action(storage, action)
        updated = storage.mark_pending_action(action_id, "approved")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    updated["execution_result"] = result
    return updated


@app.post("/agent/actions/{action_id}/reject")
def reject_action(action_id: int) -> Dict[str, Any]:
    storage = get_storage()
    try:
        return storage.mark_pending_action(action_id, "rejected")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/emails")
def list_emails(
    keyword: Optional[str] = None,
    sender: Optional[str] = None,
    unread_only: bool = False,
    priority: Optional[str] = None,
) -> List[Dict[str, Any]]:
    storage = get_storage()
    return storage.search_email(keyword=keyword, sender=sender, unread_only=unread_only, priority=priority)


@app.get("/calendar")
def list_calendar(date: Optional[str] = None) -> List[Dict[str, Any]]:
    storage = get_storage()
    return storage.list_calendar_events(date=date)


@app.get("/todos")
def list_todos(include_done: bool = False, priority: Optional[str] = None) -> List[Dict[str, Any]]:
    storage = get_storage()
    return storage.list_todos(include_done=include_done, priority=priority)
