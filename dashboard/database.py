import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


load_dotenv()


@st.cache_resource
def get_database_engine() -> Engine:
    database_url = os.getenv(
        "DATABASE_URL",
        (
            "postgresql+psycopg2://commerce_user:"
            "commerce_password@localhost:5432/commerce"
        ),
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )


@st.cache_data(ttl=30)
def execute_query(query: str) -> pd.DataFrame:
    engine = get_database_engine()

    with engine.connect() as connection:
        return pd.read_sql_query(
            sql=text(query),
            con=connection,
        )


def test_connection() -> bool:
    engine = get_database_engine()

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar() == 1


def clear_query_cache() -> None:
    execute_query.clear()