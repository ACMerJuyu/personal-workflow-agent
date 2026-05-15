from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
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


class ChatRequest(BaseModel):
    message: str
    commit: bool = False
    reset_db: bool = False


class AgentResponse(BaseModel):
    run_id: int
    title: str
    bullets: List[str]
    trace: List[Dict[str, Any]]
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
    return AgentResponse(
        run_id=run_id,
        title=result.title,
        bullets=result.bullets,
        trace=[call.to_dict() for call in result.trace],
        mode=mode,
        intent=intent,
    )


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "name": "Personal Workflow Agent API",
        "status": "ok",
        "docs": "/docs",
    }


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

