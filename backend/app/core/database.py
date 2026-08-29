from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# Ensure raw data and sqlite database directory exist
if settings.RAW_DATA_DIR:
    Path(settings.RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)

if settings.DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if sqlite_path and not sqlite_path.startswith(":memory:"):
        db_file = Path(sqlite_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL, connect_args=connect_args, echo=False
)


# SQLite foreign keys and WAL mode for concurrent reads/writes
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()


def init_db() -> None:
    """Create all database tables registered with SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency providing a transactional database session."""
    with Session(engine) as session:
        yield session
