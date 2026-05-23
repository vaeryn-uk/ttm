# ttm

`ttm` is a small MCP server for todo and task management, with tasks stored locally on your device. It is intentionally lightweight and quick to install.

## What It Does

- Lets an agent capture, organize, and track tasks without leaving its MCP tool workflow
- Stores structured tasks locally on your device so they persist across agent sessions
- Supports workspace-scoped task lists so an agent can keep work tied to the current repo or working directory

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

After connecting it, use it through your agent.

Typical flow:

1. Open your agent in a repo or working directory.
2. Ask it to list your open tasks.
3. Ask it to add tasks, start tasks, and close tasks.

Examples:

- "ttm what next?"
- "ttm add task to document the CLI flags."
- "Start work on TTM#12."
- "Mark TTM#12 complete."

**Note: prefixing task requests with `ttm` can help your agent route them to the task tool more consistently.**

What to expect:

- Tasks are scoped to the current repository or working directory.
- If you switch to another project, you get that project's tasks instead.

## Upgrading

To get the latest version, run the following to refresh the cached copy that `uvx` will run:

```
uvx --refresh --from git+https://github.com/vaeryn-uk/ttm ttm
```

Once packages have been installed, `Ctrl`+`C` to stop the MCP server that was started. Restarting your agent will now have the latest version of `ttm`.

## Core Tools

### `add_task`

Create a task.

Inputs:
- `workspace` required string: usually the current repository or working directory
- `summary` required string
- `description` optional string
- `status` optional `todo|doing|done`, defaults to `todo`
- `agent_session` optional string

### `get_task`

Fetch one task by `task_id`.

### `update_task`

Update any subset of:
- `workspace`: usually the current repository or working directory
- `summary`
- `description`
- `status`
- `agent_session`

### `list_tasks`

List tasks for a `workspace`.

Inputs:
- `workspace` required string: usually the current repository or working directory
- `status` optional `todo|doing|done`
- `limit` optional integer, default `50`
- `offset` optional integer, default `0`

### `search_tasks`

Search `summary` and `description` within a `workspace`.

Inputs:
- `workspace` required string: usually the current repository or working directory
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
