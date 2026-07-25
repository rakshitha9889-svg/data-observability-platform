from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


def main() -> None:
    load_dotenv(ENV_FILE)

    import os

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing from the .env file."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        database_information = connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    version() AS database_version
                """
            )
        ).mappings().one()

        schemas = connection.execute(
            text(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN (
                    'raw',
                    'staging',
                    'analytics',
                    'observability',
                    'quarantine'
                )
                ORDER BY schema_name
                """
            )
        ).scalars().all()

        table_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema IN (
                    'raw',
                    'observability',
                    'quarantine'
                )
                """
            )
        ).scalar_one()

    engine.dispose()

    print("Database connection successful.")
    print(f"Database: {database_information['database_name']}")
    print(f"User: {database_information['database_user']}")
    print(f"Schemas: {', '.join(schemas)}")
    print(f"Initial table count: {table_count}")


if __name__ == "__main__":
    main()