from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

DEFAULT_APP_NAME = "ttm"
DB_PATH_ENV = "TTM_DB_PATH"


@dataclass(slots=True)
class Settings:
    db_path: Path


def resolve_db_path() -> Path:
    db_override = os.getenv(DB_PATH_ENV)
    if db_override:
        return Path(db_override).expanduser().resolve()

    data_dir = Path(user_data_dir(DEFAULT_APP_NAME, DEFAULT_APP_NAME)).resolve()
    return data_dir / "ttm.db"


def load_settings() -> Settings:
    return Settings(db_path=resolve_db_path())
