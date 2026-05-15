import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.models import AgentResult, ToolCall


class SQLiteStorage:
    def __init__(self, db_path: str = "data/workflow.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    unread INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS calendar_events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    date TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    due TEXT NOT NULL,
                    source TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    done INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_memory (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_message TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    final_title TEXT NOT NULL,
                    final_bullets_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES agent_runs(id)
                );

                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES agent_runs(id)
                );
                """
            )

    def seed_from_json(self, data_dir: str = "data", force: bool = False) -> None:
        data_path = Path(data_dir)
        self.initialize()

        with self._connect() as conn:
            if force:
                conn.execute("DELETE FROM emails")
                conn.execute("DELETE FROM calendar_events")
                conn.execute("DELETE FROM todos")
                conn.execute("DELETE FROM user_memory")
                conn.execute("DELETE FROM pending_actions")

            if force or self._table_is_empty(conn, "emails"):
                for email in self._read_json(data_path / "emails.json"):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO emails
                        (id, sender, subject, body, deadline, priority, unread)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            email["id"],
                            email["sender"],
                            email["subject"],
                            email["body"],
                            email["deadline"],
                            email["priority"],
                            int(email["unread"]),
                        ),
                    )

            if force or self._table_is_empty(conn, "calendar_events"):
                for event in self._read_json(data_path / "calendar.json"):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO calendar_events
                        (id, title, date, start, end)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (event["id"], event["title"], event["date"], event["start"], event["end"]),
                    )

            if force or self._table_is_empty(conn, "todos"):
                for todo in self._read_json(data_path / "todos.json"):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO todos
                        (id, title, due, source, priority, done)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            todo["id"],
                            todo["title"],
                            todo["due"],
                            todo["source"],
                            todo["priority"],
                            int(todo["done"]),
                        ),
                    )

            if force or self._table_is_empty(conn, "user_memory"):
                memory = self._read_json(data_path / "memory.json")
                for key, value in memory.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO user_memory (key, value_json) VALUES (?, ?)",
                        (key, json.dumps(value, ensure_ascii=False)),
                    )

    def load_memory(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value_json FROM user_memory").fetchall()
        return {row["key"]: json.loads(row["value_json"]) for row in rows}

    def search_email(
        self,
        keyword: Optional[str] = None,
        sender: Optional[str] = None,
        unread_only: bool = False,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []

        if sender:
            clauses.append("LOWER(sender) LIKE ?")
            params.append(f"%{sender.lower()}%")
        if unread_only:
            clauses.append("unread = 1")
        if priority:
            clauses.append("priority = ?")
            params.append(priority)
        if keyword:
            clauses.append("(LOWER(subject) LIKE ? OR LOWER(body) LIKE ?)")
            params.extend([f"%{keyword.lower()}%", f"%{keyword.lower()}%"])

        sql = "SELECT * FROM emails"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._email_from_row(row) for row in rows]

    def get_email_by_id(self, email_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
        if row is None:
            raise ValueError(f"email not found: {email_id}")
        return self._email_from_row(row)

    def list_calendar_events(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        if date:
            sql = "SELECT * FROM calendar_events WHERE date = ? ORDER BY start"
            params: Tuple[Any, ...] = (date,)
        else:
            sql = "SELECT * FROM calendar_events ORDER BY date, start"
            params = ()

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def reschedule_event(self, event_id: str, new_start: str, new_end: str) -> Dict[str, Any]:
        event = self.get_event_by_id(event_id)
        with self._connect() as conn:
            conn.execute(
                "UPDATE calendar_events SET start = ?, end = ? WHERE id = ?",
                (new_start, new_end, event_id),
            )
        event["start"] = new_start
        event["end"] = new_end
        return event

    def get_event_by_id(self, event_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            raise ValueError(f"calendar event not found: {event_id}")
        return dict(row)

    def list_todos(self, include_done: bool = False, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []

        if not include_done:
            clauses.append("done = 0")
        if priority:
            clauses.append("priority = ?")
            params.append(priority)

        sql = "SELECT * FROM todos"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._todo_from_row(row) for row in rows]

    def next_todo_id(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM todos").fetchone()
        return int(row["next_id"])

    def add_todo(self, title: str, due: str, source: str, priority: str = "medium") -> Dict[str, Any]:
        todo_id = self.next_todo_id()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO todos (id, title, due, source, priority, done)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (todo_id, title, due, source, priority),
            )
        return {
            "id": todo_id,
            "title": title,
            "due": due,
            "source": source,
            "priority": priority,
            "done": False,
        }

    def complete_todo(self, todo_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
            if row is None:
                raise ValueError(f"todo not found: {todo_id}")
            conn.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
        todo = self._todo_from_row(row)
        todo["done"] = True
        return todo

    def save_agent_run(
        self,
        user_message: str,
        intent: str,
        mode: str,
        result: AgentResult,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_runs
                (user_message, intent, mode, final_title, final_bullets_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_message,
                    intent,
                    mode,
                    result.title,
                    json.dumps(result.bullets, ensure_ascii=False),
                ),
            )
            run_id = int(cursor.lastrowid)
            for call in result.trace:
                self.save_tool_call(conn, run_id, call)
        return run_id

    def save_tool_call(self, conn: sqlite3.Connection, run_id: int, call: ToolCall) -> None:
        conn.execute(
            """
            INSERT INTO tool_calls
            (run_id, tool_name, arguments_json, result_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                call.name,
                json.dumps(call.arguments, ensure_ascii=False),
                json.dumps(call.result, ensure_ascii=False),
            ),
        )

    def list_agent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._agent_run_from_row(row) for row in rows]

    def get_agent_run(self, run_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise ValueError(f"agent run not found: {run_id}")
            calls = conn.execute(
                "SELECT * FROM tool_calls WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        run = self._agent_run_from_row(row)
        run["tool_calls"] = [self._tool_call_from_row(call) for call in calls]
        return run

    def create_pending_action(
        self,
        run_id: Optional[int],
        action_type: str,
        description: str,
        payload: Dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pending_actions
                (run_id, action_type, description, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, action_type, description, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def list_pending_actions(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM pending_actions"
        params: Tuple[Any, ...] = ()
        if not include_resolved:
            sql += " WHERE status = ?"
            params = ("pending",)
        sql += " ORDER BY id DESC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._pending_action_from_row(row) for row in rows]

    def get_pending_action(self, action_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM pending_actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            raise ValueError(f"pending action not found: {action_id}")
        return self._pending_action_from_row(row)

    def mark_pending_action(self, action_id: int, status: str) -> Dict[str, Any]:
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be 'approved' or 'rejected'")

        action = self.get_pending_action(action_id)
        if action["status"] != "pending":
            raise ValueError(f"pending action already resolved: {action_id}")

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, action_id),
            )
        action["status"] = status
        return action

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _table_is_empty(conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        return int(row["count"]) == 0

    @staticmethod
    def _email_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        email = dict(row)
        email["unread"] = bool(email["unread"])
        return email

    @staticmethod
    def _todo_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        todo = dict(row)
        todo["done"] = bool(todo["done"])
        return todo

    @staticmethod
    def _agent_run_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        run = dict(row)
        run["final_bullets"] = json.loads(run.pop("final_bullets_json"))
        return run

    @staticmethod
    def _tool_call_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        call = dict(row)
        call["arguments"] = json.loads(call.pop("arguments_json"))
        call["result"] = json.loads(call.pop("result_json"))
        return call

    @staticmethod
    def _pending_action_from_row(row: sqlite3.Row) -> Dict[str, Any]:
        action = dict(row)
        action["payload"] = json.loads(action.pop("payload_json"))
        return action
