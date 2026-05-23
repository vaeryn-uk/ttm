from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage

from ttm.config import Settings, load_settings
from ttm.models import TaskStatus
from ttm.repository import TaskRepository
from ttm.service import TaskService

INSTRUCTIONS = (
    "TTM manages structured todo tasks. "
    "`workspace` should be the current repository or working directory the agent is operating in. "
    "Infer `workspace` from the current work context instead of asking the user for it unless needed. "
    "Do not invent labels like `frontend`, `q3`, or `team-a` for `workspace`. "
    "If the user provides a full task ID like `TTM#7`, use that exact task ID for `get_task`, `update_task`, or `delete_task` rather than converting it into a scoped workspace lookup. "
    "Use statuses todo, doing, and done. "
    "Read the ttm://docs/* resources for usage details and workflows."
)

USAGE_DOC = """# TTM Usage

TTM manages workspace-scoped tasks over MCP.

## Core rules

- Use the current repository or working directory as `workspace`.
- Infer `workspace` from the current work context instead of asking the user for it unless needed.
- Do not use invented labels like `frontend`, `q3`, or `team-a` as `workspace`.
- Use `summary` for the short task title.
- Use `description` for optional markdown details.
- Use `agent_session` when you want to record which agent run created or updated a task.
- Use only `todo`, `doing`, or `done` as statuses.
- If the user provides a full task ID like `TTM#7`, call `get_task`, `update_task`, or `delete_task` with that exact ID instead of turning it into a workspace-scoped search.

## Recommended workflow

1. Call `list_tasks` for the current workspace before creating duplicates.
2. Call `add_task` with a concise summary and optional markdown description.
3. Move active work to `doing` with `update_task`.
4. Mark finished work as `done`.
5. Use `search_tasks` to find prior work before creating new tasks.
"""

TASK_MODEL_DOC = """# TTM Task Model

Each task stores:

- `task_id`: stable public ID like `TTM#12`
- `workspace`: usually the current repository or working directory
- `summary`: required short title
- `description`: optional markdown body
- `status`: `todo`, `doing`, or `done`
- `agent_session`: optional caller-provided session identifier
- `created_at`: creation timestamp in UTC
- `updated_at`: last update timestamp in UTC

Deleting a task removes it. There is no archive or restore behavior.

Never use `workspace` for invented categorization like `frontend`, `documentation`, `team-a`, or `q3-priority` when it should refer to the current repository or working directory.
"""

EXAMPLES_DOC = """# TTM Examples

## Create a task

Use `add_task` with:
- `workspace`: `/path/to/repo`
- `summary`: `Ship MCP docs`
- `description`: `Document resources and prompts`

## Start work

Use `update_task` with:
- `task_id`: `TTM#7`
- `status`: `doing`

## Finish work

Use `update_task` with:
- `task_id`: `TTM#7`
- `status`: `done`

## Find existing tasks

Use `search_tasks` with:
- `workspace`: `/path/to/repo`
- `query`: `docs`
"""


def create_service(db_path: Path) -> TaskService:
    return TaskService(TaskRepository(db_path))


def create_server(settings: Settings | None = None) -> FastMCP:
    resolved_settings = settings or load_settings()
    service = create_service(resolved_settings.db_path)
    server = FastMCP("ttm", instructions=INSTRUCTIONS)

    @server.resource(
        "ttm://docs/usage",
        name="ttm-usage",
        title="TTM Usage",
        description="Overview of how to use TTM effectively.",
        mime_type="text/markdown",
    )
    def usage_doc() -> str:
        return USAGE_DOC

    @server.resource(
        "ttm://docs/task-model",
        name="ttm-task-model",
        title="TTM Task Model",
        description="Field and lifecycle reference for TTM tasks.",
        mime_type="text/markdown",
    )
    def task_model_doc() -> str:
        return TASK_MODEL_DOC

    @server.resource(
        "ttm://docs/examples",
        name="ttm-examples",
        title="TTM Examples",
        description="Example calls and common task flows.",
        mime_type="text/markdown",
    )
    def examples_doc() -> str:
        return EXAMPLES_DOC

    @server.prompt(
        title="Create Workspace Task Plan",
        description="Guide the assistant to break down work into TTM tasks for one workspace.",
    )
    def create_workspace_task_plan(workspace: str, goal: str) -> list[UserMessage]:
        return [
            UserMessage(
                f"Use TTM to break down work for workspace `{workspace}`.\n\n"
                f"Goal: {goal}\n\n"
                "First inspect existing tasks with list_tasks or search_tasks to avoid duplicates. "
                "Then create a small set of concrete tasks with concise summaries and markdown descriptions. "
                "Use `todo` for new tasks unless one should start immediately as `doing`."
            )
        ]

    @server.prompt(
        title="Review Open Tasks",
        description="Guide the assistant to review current non-complete work in a workspace.",
    )
    def review_open_tasks(workspace: str) -> list[UserMessage]:
        return [
            UserMessage(
                f"Review active work for workspace `{workspace}` using TTM.\n\n"
                "List `todo` and `doing` tasks, summarize duplicates or stale items, "
                "and propose status updates or cleanup actions before making changes."
            )
        ]

    @server.prompt(
        title="Close Completed Work",
        description="Guide the assistant to mark finished tasks as done after verifying completion.",
    )
    def close_completed_work(workspace: str, completion_notes: str | None = None) -> list[UserMessage]:
        notes = completion_notes or "No extra completion notes were provided."
        return [
            UserMessage(
                f"Close completed work for workspace `{workspace}` using TTM.\n\n"
                f"Notes: {notes}\n\n"
                "Find tasks that appear complete, verify the work from available context, "
                "and update only the confirmed tasks to `done`. "
                "Keep unfinished or ambiguous tasks in `doing` or `todo`."
            )
        ]

    @server.tool()
    def add_task(
        workspace: str,
        summary: str,
        description: str | None = None,
        status: TaskStatus = "todo",
        agent_session: str | None = None,
    ) -> dict[str, object]:
        """Create a task in a workspace."""
        return service.add_task(
            workspace=workspace,
            summary=summary,
            description=description,
            status=status,
            agent_session=agent_session,
        )

    @server.tool()
    def get_task(task_id: str) -> dict[str, object]:
        """Fetch a single task by ID."""
        return service.get_task(task_id)

    @server.tool()
    def update_task(
        task_id: str,
        workspace: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        agent_session: str | None = None,
    ) -> dict[str, object]:
        """Update one or more task fields."""
        return service.update_task(
            task_id,
            workspace=workspace,
            summary=summary,
            description=description,
            status=status,
            agent_session=agent_session,
        )

    @server.tool()
    def list_tasks(
        workspace: str,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        """List tasks for a workspace."""
        return service.list_tasks(workspace=workspace, status=status, limit=limit, offset=offset)

    @server.tool()
    def search_tasks(
        workspace: str,
        query: str,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        """Search tasks within a workspace."""
        return service.search_tasks(
            workspace=workspace,
            query=query,
            status=status,
            limit=limit,
            offset=offset,
        )

    @server.tool()
    def delete_task(task_id: str) -> dict[str, object]:
        """Delete a task by ID."""
        return service.delete_task(task_id)

    return server
