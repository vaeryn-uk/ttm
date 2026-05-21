from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from ttm.models import Task, VALID_STATUSES


class TaskNotFoundError(LookupError):
    """Raised when a task does not exist."""


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class TaskRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE,
                    project TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    agent_session TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK (status IN ('todo', 'doing', 'done'))
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project, status)"
            )

    def create_task(
        self,
        *,
        project: str,
        summary: str,
        description: str | None,
        status: str,
        agent_session: str | None,
    ) -> Task:
        self._validate_status(status)
        timestamp = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (project, summary, description, status, agent_session, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project, summary, description, status, agent_session, timestamp, timestamp),
            )
            row_id = cursor.lastrowid
            task_id = f"TTM#{row_id}"
            connection.execute(
                "UPDATE tasks SET task_id = ? WHERE id = ?",
                (task_id, row_id),
            )
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (row_id,),
            ).fetchone()
        return self._row_to_task(row)

    def get_task(self, task_id: str) -> Task:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return self._row_to_task(row)

    def update_task(
        self,
        task_id: str,
        *,
        project: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        status: str | None = None,
        agent_session: str | None = None,
    ) -> Task:
        current = self.get_task(task_id)
        next_project = current.project if project is None else project
        next_summary = current.summary if summary is None else summary
        next_description = current.description if description is None else description
        next_status = current.status if status is None else status
        next_agent_session = current.agent_session if agent_session is None else agent_session
        self._validate_status(next_status)
        timestamp = utc_now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET project = ?, summary = ?, description = ?, status = ?, agent_session = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    next_project,
                    next_summary,
                    next_description,
                    next_status,
                    next_agent_session,
                    timestamp,
                    task_id,
                ),
            )
        return self.get_task(task_id)

    def list_tasks(
        self,
        *,
        project: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        if status is not None:
            self._validate_status(status)
        if status is None:
            query = """
                SELECT * FROM tasks
                WHERE project = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params: tuple[object, ...] = (project, limit, offset)
        else:
            query = """
                SELECT * FROM tasks
                WHERE project = ? AND status = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params = (project, status, limit, offset)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def search_tasks(
        self,
        *,
        project: str,
        query: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        if status is not None:
            self._validate_status(status)
        search_term = f"%{query.lower()}%"
        if status is None:
            sql = """
                SELECT * FROM tasks
                WHERE project = ?
                  AND (
                    lower(summary) LIKE ?
                    OR lower(COALESCE(description, '')) LIKE ?
                  )
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params: tuple[object, ...] = (project, search_term, search_term, limit, offset)
        else:
            sql = """
                SELECT * FROM tasks
                WHERE project = ?
                  AND status = ?
                  AND (
                    lower(summary) LIKE ?
                    OR lower(COALESCE(description, '')) LIKE ?
                  )
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params = (project, status, search_term, search_term, limit, offset)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def delete_task(self, task_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE task_id = ?",
                (task_id,),
            )
        if cursor.rowcount == 0:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return True

    def _validate_status(self, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Expected one of {sorted(VALID_STATUSES)}")

    @staticmethod
    def _row_to_task(row: sqlite3.Row | None) -> Task:
        if row is None:
            raise TaskNotFoundError("Task row missing")
        return Task(
            task_id=row["task_id"],
            project=row["project"],
            summary=row["summary"],
            description=row["description"],
            status=row["status"],
            agent_session=row["agent_session"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
