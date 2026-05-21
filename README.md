# ttm

`ttm` is a quick SQLite-backed MCP server for todo and task management. It is intentionally small, single-user, and optimized for direct GitHub install/run.

## Features

- Structured tasks with stable IDs like `TTM#1`
- Explicit project scoping for create/list/search
- Optional `agent_session` tracking
- SQLite storage with automatic local initialization
- Small MCP tool surface: add, get, update, list, search, delete

## Storage

By default, the database is created as `ttm.db` inside the OS-appropriate user data directory for `ttm` as resolved by `platformdirs`.

Overrides:

- `TTM_DB_PATH`: full SQLite database path

## Install and Run

For local development:

```bash
uv sync --extra dev
uv run ttm
```

For direct GitHub usage in an MCP client, use a `uvx`/`uv tool run` command that installs from the repo:

```json
{
  "mcpServers": {
    "ttm": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/<you>/ttm", "ttm"]
    }
  }
}
```

## MCP Tools

### `add_task`

Create a task.

Inputs:
- `project` required string
- `summary` required string
- `description` optional string
- `status` optional `todo|doing|done`, defaults to `todo`
- `agent_session` optional string

### `get_task`

Fetch one task by `task_id`.

### `update_task`

Update any subset of:
- `project`
- `summary`
- `description`
- `status`
- `agent_session`

### `list_tasks`

List tasks for a `project`.

Inputs:
- `project` required string
- `status` optional `todo|doing|done`
- `limit` optional integer, default `50`
- `offset` optional integer, default `0`

### `search_tasks`

Search `summary` and `description` within a `project`.

Inputs:
- `project` required string
- `query` required string
- `status` optional `todo|doing|done`
- `limit` optional integer, default `50`
- `offset` optional integer, default `0`

### `delete_task`

Hard delete a task by `task_id`.
