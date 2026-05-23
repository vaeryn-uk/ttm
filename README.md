# ttm

`ttm` is a small MCP server for todo and task management, with tasks stored locally on your device. It is intentionally lightweight and quick to install.

## What It Does

- Lets an agent capture, organize, and track tasks without leaving its MCP tool workflow
- Stores structured tasks locally on your device so they persist across agent sessions
- Supports project-scoped task lists so an agent can keep work tied to the current repo or workspace

## How To Use It

To use it directly from GitHub in an MCP client, use a `uvx` or `uv tool run` command that installs from the repo:

```json
{
  "mcpServers": {
    "ttm": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vaeryn-uk/ttm", "ttm"]
    }
  }
}
```

Once connected, use the MCP tools to create, update, list, and search tasks within an explicit `project`.
`project` is an opaque string with no required path validation or platform-specific format.
It is an internal scoping key between the agent and TTM, not something that normally needs to be exposed to the end user.
In practice, agents should usually use their current working directory or repository identifier, not an invented taxonomy label.

## Core Tools

### `add_task`

Create a task.

Inputs:
- `project` required string: opaque internal scoping string, usually the current working directory or repository identifier
- `summary` required string
- `description` optional string
- `status` optional `todo|doing|done`, defaults to `todo`
- `agent_session` optional string

### `get_task`

Fetch one task by `task_id`.

### `update_task`

Update any subset of:
- `project`: opaque internal scoping string, usually the current working directory or repository identifier
- `summary`
- `description`
- `status`
- `agent_session`

### `list_tasks`

List tasks for a `project`.

Inputs:
- `project` required string: opaque internal scoping string, usually the current working directory or repository identifier
- `status` optional `todo|doing|done`
- `limit` optional integer, default `50`
- `offset` optional integer, default `0`

### `search_tasks`

Search `summary` and `description` within a `project`.

Inputs:
- `project` required string: opaque internal scoping string, usually the current working directory or repository identifier
- `query` required string
- `status` optional `todo|doing|done`
- `limit` optional integer, default `50`
- `offset` optional integer, default `0`

### `delete_task`

Hard delete a task by `task_id`.

## Internal Details

### Storage

Tasks are stored in SQLite with automatic local initialization.

By default, the database is created as `ttm.db` inside the OS-appropriate user data directory for `ttm` as resolved by `platformdirs`.

Override:

- `TTM_DB_PATH`: full SQLite database path

### Local Development

```bash
uv sync --extra dev
uv run ttm
```
