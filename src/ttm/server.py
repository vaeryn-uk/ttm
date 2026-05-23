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
    "`project` is an opaque string passed by the caller for create, list, and search. "
    "`project` is an internal scoping key between the agent and TTM, not a user-facing field to present back to the user unless directly relevant. "
    "In practice it should usually be the directory or repository identifier the agent is operating in. "
    "Do not invent taxonomy, labels, teams, initiatives, or other arbitrary categories for `project`. "
    "Use statuses todo, doing, and done. "
    "Read the ttm://docs/* resources for usage details and workflows."
)

USAGE_DOC = """# TTM Usage

TTM manages project-scoped tasks over MCP.

## Core rules

- Treat `project` as an opaque caller-provided string with no required path validation or platform-specific format.
- Treat `project` as an internal scoping key between the agent and TTM, not user-facing output by default.
- In practice, set `project` to the directory or repository identifier the agent is operating in.
- Do not use `project` for arbitrary taxonomy such as teams, themes, initiatives, labels, or workflow buckets.
- Use `summary` for the short task title.
- Use `description` for optional markdown details.
- Use `agent_session` when you want to record which agent run created or updated a task.
- Use only `todo`, `doing`, or `done` as statuses.

## Recommended workflow

1. Call `list_tasks` for the current project before creating duplicates.
2. Call `add_task` with a concise summary and optional markdown description.
3. Move active work to `doing` with `update_task`.
4. Mark finished work as `done`.
5. Use `search_tasks` to find prior work before creating new tasks.
"""

TASK_MODEL_DOC = """# TTM Task Model

Each task stores:

- `task_id`: stable public ID like `TTM#12`
- `project`: opaque internal scoping string, usually a directory or repository identifier for the working context
- `summary`: required short title
- `description`: optional markdown body
- `status`: `todo`, `doing`, or `done`
- `agent_session`: optional caller-provided session identifier
- `created_at`: creation timestamp in UTC
- `updated_at`: last update timestamp in UTC

Deleting a task removes it. There is no archive or restore behavior.

Never use `project` for invented categorization like `frontend`, `documentation`, `team-a`, or `q3-priority` when those are not the actual working-context identifier.
"""

EXAMPLES_DOC = """# TTM Examples

## Create a task

Use `add_task` with:
- `project`: `/path/to/repo`
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
- `project`: `/path/to/repo`
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
        title="Create Project Task Plan",
        description="Guide the assistant to break down work into TTM tasks for one project.",
    )
    def create_project_task_plan(project: str, goal: str) -> list[UserMessage]:
        return [
            UserMessage(
                f"Use TTM to break down work for project `{project}`.\n\n"
                f"Goal: {goal}\n\n"
                "First inspect existing tasks with list_tasks or search_tasks to avoid duplicates. "
                "Then create a small set of concrete tasks with concise summaries and markdown descriptions. "
                "Use `todo` for new tasks unless one should start immediately as `doing`."
            )
        ]

    @server.prompt(
        title="Review Open Tasks",
        description="Guide the assistant to review current non-complete work in a project.",
    )
    def review_open_tasks(project: str) -> list[UserMessage]:
        return [
            UserMessage(
                f"Review active work for project `{project}` using TTM.\n\n"
                "List `todo` and `doing` tasks, summarize duplicates or stale items, "
                "and propose status updates or cleanup actions before making changes."
            )
        ]

    @server.prompt(
        title="Close Completed Work",
        description="Guide the assistant to mark finished tasks as done after verifying completion.",
    )
    def close_completed_work(project: str, completion_notes: str | None = None) -> list[UserMessage]:
        notes = completion_notes or "No extra completion notes were provided."
        return [
            UserMessage(
                f"Close completed work for project `{project}` using TTM.\n\n"
                f"Notes: {notes}\n\n"
                "Find tasks that appear complete, verify the work from available context, "
                "and update only the confirmed tasks to `done`. "
                "Keep unfinished or ambiguous tasks in `doing` or `todo`."
            )
        ]

    @server.tool()
    def add_task(
        project: str,
        summary: str,
        description: str | None = None,
        status: TaskStatus = "todo",
        agent_session: str | None = None,
    ) -> dict[str, object]:
        """Create a task in a project."""
        return service.add_task(
            project=project,
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
        project: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        agent_session: str | None = None,
    ) -> dict[str, object]:
        """Update one or more task fields."""
        return service.update_task(
            task_id,
            project=project,
            summary=summary,
            description=description,
            status=status,
            agent_session=agent_session,
        )

    @server.tool()
    def list_tasks(
        project: str,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        """List tasks for a project."""
        return service.list_tasks(project=project, status=status, limit=limit, offset=offset)

    @server.tool()
    def search_tasks(
        project: str,
        query: str,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        """Search tasks within a project."""
        return service.search_tasks(
            project=project,
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
