from __future__ import annotations

from ttm.models import Task, TaskStatus, VALID_STATUSES
from ttm.repository import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def add_task(
        self,
        *,
        project: str,
        summary: str,
        description: str | None = None,
        status: TaskStatus = "todo",
        agent_session: str | None = None,
    ) -> dict[str, object]:
        self._validate_project(project)
        self._validate_summary(summary)
        self._validate_optional_status(status)
        task = self.repository.create_task(
            project=project.strip(),
            summary=summary.strip(),
            description=description,
            status=status,
            agent_session=self._normalize_optional(agent_session),
        )
        return task.to_dict()

    def get_task(self, task_id: str) -> dict[str, object]:
        return self.repository.get_task(task_id).to_dict()

    def update_task(
        self,
        task_id: str,
        *,
        project: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        agent_session: str | None = None,
    ) -> dict[str, object]:
        if project is not None:
            self._validate_project(project)
            project = project.strip()
        if summary is not None:
            self._validate_summary(summary)
            summary = summary.strip()
        if status is not None:
            self._validate_optional_status(status)
        task = self.repository.update_task(
            task_id,
            project=project,
            summary=summary,
            description=description,
            status=status,
            agent_session=self._normalize_optional(agent_session) if agent_session is not None else None,
        )
        return task.to_dict()

    def list_tasks(
        self,
        *,
        project: str,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        self._validate_project(project)
        self._validate_paging(limit=limit, offset=offset)
        if status is not None:
            self._validate_optional_status(status)
        tasks = self.repository.list_tasks(
            project=project.strip(),
            status=status,
            limit=limit,
            offset=offset,
        )
        return self._task_list_response(tasks, limit=limit, offset=offset)

    def search_tasks(
        self,
        *,
        project: str,
        query: str,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        self._validate_project(project)
        if not query.strip():
            raise ValueError("query is required")
        self._validate_paging(limit=limit, offset=offset)
        if status is not None:
            self._validate_optional_status(status)
        tasks = self.repository.search_tasks(
            project=project.strip(),
            query=query.strip(),
            status=status,
            limit=limit,
            offset=offset,
        )
        return {
            "query": query.strip(),
            **self._task_list_response(tasks, limit=limit, offset=offset),
        }

    def delete_task(self, task_id: str) -> dict[str, object]:
        self.repository.delete_task(task_id)
        return {"deleted": True, "task_id": task_id}

    @staticmethod
    def _task_list_response(tasks: list[Task], *, limit: int, offset: int) -> dict[str, object]:
        return {
            "items": [task.to_dict() for task in tasks],
            "count": len(tasks),
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def _validate_project(project: str) -> None:
        if not project.strip():
            raise ValueError("project is required")

    @staticmethod
    def _validate_summary(summary: str) -> None:
        if not summary.strip():
            raise ValueError("summary is required")

    @staticmethod
    def _validate_optional_status(status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Expected one of {sorted(VALID_STATUSES)}")

    @staticmethod
    def _validate_paging(*, limit: int, offset: int) -> None:
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if offset < 0:
            raise ValueError("offset must be 0 or greater")

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
