from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    database_url: str
    incoming_directory: Path
    archive_directory: Path
    rejected_directory: Path
    log_level: str


def get_required_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is missing."
        )

    return value


def load_settings() -> Settings:
    return Settings(
        database_url=get_required_environment_variable(
            "DATABASE_URL"
        ),
        incoming_directory=PROJECT_ROOT
        / os.getenv("DATA_INCOMING_DIR", "data/incoming"),
        archive_directory=PROJECT_ROOT
        / os.getenv("DATA_ARCHIVE_DIR", "data/archive"),
        rejected_directory=PROJECT_ROOT
        / os.getenv("DATA_REJECTED_DIR", "data/rejected"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )