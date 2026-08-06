import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()


class AssistantSettings(BaseModel):
    database_url: str
    maximum_failed_tests: int = 25
    maximum_logs: int = 25
    maximum_similar_incidents: int = 5
    maximum_affected_assets: int = 50


@lru_cache
def get_settings() -> AssistantSettings:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Add it to the project .env file."
        )

    return AssistantSettings(database_url=database_url)


@lru_cache
def get_database_engine() -> Engine:
    settings = get_settings()

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )
