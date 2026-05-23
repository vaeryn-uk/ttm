from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ttm.config import Settings
from ttm.server import create_server, create_service


def test_service_crud_flow(tmp_path: Path) -> None:
    service = create_service(tmp_path / "ttm.db")

    created = service.add_task(
        workspace="/repo/a",
        summary="Implement plan",
        description="Use SQLite",
        agent_session="agent-7",
    )
    assert created["task_id"] == "TTM#1"
    assert created["status"] == "todo"

    updated = service.update_task(created["task_id"], status="doing")
    assert updated["status"] == "doing"

    listed = service.list_tasks(workspace="/repo/a")
    assert listed["count"] == 1
    assert listed["items"][0]["task_id"] == created["task_id"]

    searched = service.search_tasks(workspace="/repo/a", query="sqlite")
    assert searched["count"] == 1

    deleted = service.delete_task(created["task_id"])
    assert deleted == {"deleted": True, "task_id": created["task_id"]}


def test_service_requires_workspace_and_summary(tmp_path: Path) -> None:
    service = create_service(tmp_path / "ttm.db")

    with pytest.raises(ValueError):
        service.add_task(workspace=" ", summary="ok")
    with pytest.raises(ValueError):
        service.add_task(workspace="/repo/a", summary=" ")


def test_create_server_exposes_expected_tools(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "ttm.db"))
    manager = server._tool_manager  # noqa: SLF001 - used for a targeted smoke test

    assert {tool.name for tool in manager.list_tools()} == {
        "add_task",
        "get_task",
        "update_task",
        "list_tasks",
        "search_tasks",
        "delete_task",
    }

    add_task_tool = next(tool for tool in manager.list_tools() if tool.name == "add_task")
    add_task_status = add_task_tool.parameters["properties"]["status"]
    assert add_task_status["enum"] == ["todo", "doing", "done"]
    assert add_task_status["default"] == "todo"

    update_task_tool = next(tool for tool in manager.list_tools() if tool.name == "update_task")
    update_task_status = update_task_tool.parameters["properties"]["status"]
    assert update_task_status["anyOf"][0]["enum"] == ["todo", "doing", "done"]
    assert update_task_status["anyOf"][1]["type"] == "null"


def test_create_server_exposes_docs_and_prompts(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "ttm.db"))

    resources = server._resource_manager.list_resources()  # noqa: SLF001 - targeted smoke test
    assert {str(resource.uri) for resource in resources} == {
        "ttm://docs/usage",
        "ttm://docs/task-model",
        "ttm://docs/examples",
    }

    prompts = server._prompt_manager.list_prompts()  # noqa: SLF001 - targeted smoke test
    assert {prompt.name for prompt in prompts} == {
        "create_workspace_task_plan",
        "review_open_tasks",
        "close_completed_work",
    }


def test_usage_doc_and_prompt_render(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "ttm.db"))

    doc = asyncio.run(server.read_resource("ttm://docs/usage"))
    assert len(doc) == 1
    assert doc[0].mime_type == "text/markdown"
    assert "Use the current repository or working directory as `workspace`." in doc[0].content
    assert "Infer `workspace` from the current work context" in doc[0].content
    assert "invented labels like `frontend`, `q3`, or `team-a`" in doc[0].content
    assert "full task ID like `TTM#7`" in doc[0].content

    messages = asyncio.run(
        server._prompt_manager.render_prompt(  # noqa: SLF001 - targeted smoke test
            "create_workspace_task_plan",
            {"workspace": "/repo/a", "goal": "Ship docs"},
        )
    )
    assert len(messages) == 1
    assert "Ship docs" in messages[0].content.text


def test_server_instructions_and_model_doc_define_workspace_usage(tmp_path: Path) -> None:
    server = create_server(Settings(db_path=tmp_path / "ttm.db"))

    assert "`workspace` should be the current repository or working directory" in server.instructions
    assert "Infer `workspace` from the current work context" in server.instructions
    assert "Do not invent labels like `frontend`, `q3`, or `team-a`" in server.instructions
    assert "full task ID like `TTM#7`" in server.instructions

    doc = asyncio.run(server.read_resource("ttm://docs/task-model"))
    assert len(doc) == 1
    assert "`workspace`: usually the current repository or working directory" in doc[0].content
    assert "Never use `workspace` for invented categorization" in doc[0].content
