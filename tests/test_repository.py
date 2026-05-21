from __future__ import annotations

from pathlib import Path

import pytest

from ttm.repository import TaskNotFoundError, TaskRepository


def create_repository(tmp_path: Path) -> TaskRepository:
    return TaskRepository(tmp_path / "ttm.db")


def test_create_and_fetch_task(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)

    created = repository.create_task(
        project="/repo/a",
        summary="Ship MVP",
        description="Need a usable server",
        status="todo",
        agent_session="agent-1",
    )

    fetched = repository.get_task(created.task_id)
    assert fetched.task_id == "TTM#1"
    assert fetched.project == "/repo/a"
    assert fetched.summary == "Ship MVP"
    assert fetched.description == "Need a usable server"
    assert fetched.status == "todo"
    assert fetched.agent_session == "agent-1"


def test_update_changes_timestamp_and_fields(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    created = repository.create_task(
        project="/repo/a",
        summary="Ship MVP",
        description=None,
        status="todo",
        agent_session=None,
    )

    updated = repository.update_task(
        created.task_id,
        summary="Ship MCP MVP",
        status="doing",
        agent_session="session-2",
    )

    assert updated.summary == "Ship MCP MVP"
    assert updated.status == "doing"
    assert updated.agent_session == "session-2"
    assert updated.updated_at >= created.updated_at


def test_list_and_search_are_project_scoped(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    repository.create_task(
        project="/repo/a",
        summary="Write docs",
        description="README examples",
        status="todo",
        agent_session=None,
    )
    repository.create_task(
        project="/repo/b",
        summary="Write docs",
        description="Other project",
        status="done",
        agent_session=None,
    )

    listed = repository.list_tasks(project="/repo/a")
    searched = repository.search_tasks(project="/repo/a", query="readme")

    assert len(listed) == 1
    assert listed[0].project == "/repo/a"
    assert len(searched) == 1
    assert searched[0].description == "README examples"


def test_delete_removes_task(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    created = repository.create_task(
        project="/repo/a",
        summary="Delete me",
        description=None,
        status="todo",
        agent_session=None,
    )

    assert repository.delete_task(created.task_id) is True
    with pytest.raises(TaskNotFoundError):
        repository.get_task(created.task_id)


def test_invalid_status_is_rejected(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    with pytest.raises(ValueError):
        repository.create_task(
            project="/repo/a",
            summary="Bad status",
            description=None,
            status="blocked",
            agent_session=None,
        )
