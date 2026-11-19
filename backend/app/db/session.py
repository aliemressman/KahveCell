from pathlib import Path
from collections.abc import Iterator
from uuid import uuid4

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from app import models

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "kahvecell.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _record) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def create_tables() -> None:
    models.Base.metadata.create_all(bind=engine)
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "password_hash" not in user_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"
            )

    for table_name in ("users", "shops", "orders"):
        columns = {
            column["name"]
            for column in inspect(engine).get_columns(table_name)
        }
        if "public_id" not in columns:
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN public_id VARCHAR(36)"
                )
        with engine.begin() as connection:
            rows = connection.exec_driver_sql(
                f"SELECT id FROM {table_name} WHERE public_id IS NULL"
            ).all()
            for (record_id,) in rows:
                connection.exec_driver_sql(
                    f"UPDATE {table_name} SET public_id = ? WHERE id = ?",
                    (str(uuid4()), record_id),
                )
            connection.exec_driver_sql(
                f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table_name}_public_id "
                f"ON {table_name} (public_id)"
            )

    order_columns = {column["name"] for column in inspect(engine).get_columns("orders")}
    if "qr_signature" not in order_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE orders ADD COLUMN qr_signature VARCHAR(64)"
            )

    otp_columns = {
        column["name"]
        for column in inspect(engine).get_columns("otp_challenges")
    }
    if "full_name" not in otp_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE otp_challenges ADD COLUMN full_name VARCHAR(100)"
            )
    if "password_hash" not in otp_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE otp_challenges ADD COLUMN password_hash VARCHAR(255)"
            )
