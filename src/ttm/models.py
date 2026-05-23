from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TaskStatus = Literal["todo", "doing", "done"]
VALID_STATUSES: set[str] = {"todo", "doing", "done"}


@dataclass(slots=True)
class Task:
    task_id: str
    workspace: str
    summary: str
    description: str | None
    status: TaskStatus
    agent_session: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
