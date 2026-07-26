"""SQLite persistence layer for the Task API.

All SQL lives here; `main.py` never opens a connection of its own. Every
statement is parameterised, and every function borrows a connection from
`connection()` - the single context manager that owns commit, rollback and
close. Database errors are deliberately allowed to propagate: swallowing them
would report a failed write to the client as a success.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypedDict

# Anchored to this module rather than the process working directory, so the
# database file always lands next to the code no matter where the server was
# started from. A bare relative "tasks.db" would follow the shell around.
DATABASE_PATH: Path = Path(__file__).resolve().parent / "tasks.db"

# SQLite has no native boolean type, so `done` is an INTEGER pinned to 0/1.
# Both CHECK constraints are load-bearing: they reject bad data even if it
# arrives from the sqlite3 CLI or DB Browser rather than through the API.
SCHEMA: str = """
CREATE TABLE IF NOT EXISTS tasks (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
)
"""

# The same three tasks the in-memory list carried, so behaviour before and
# after the migration is comparable.
SEED_TASKS: tuple[tuple[str, bool], ...] = (
    ("Clean room", False),
    ("Buy groceries", True),
    ("Walk the dog", False),
)


class TaskRecord(TypedDict):
    """A single row of `tasks`, with `done` already converted back to a bool."""

    id: int
    title: str
    done: bool


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Yield a connection, committing on success and rolling back on failure."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _to_task(row: sqlite3.Row) -> TaskRecord:
    """Convert a row to a plain dict, reading columns by name, never by index."""
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def initialise() -> None:
    """Create the table if absent and seed it only when empty.

    Idempotent by design: restarting the server re-runs this and must not
    duplicate the seed rows.
    """
    with connection() as conn:
        conn.execute(SCHEMA)
        row = conn.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()
        if row["total"] == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                SEED_TASKS,
            )


def list_tasks() -> list[TaskRecord]:
    """Return every task, oldest id first."""
    with connection() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [_to_task(row) for row in rows]


def get_task(task_id: int) -> TaskRecord | None:
    """Return one task, or None when no row has that id."""
    with connection() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    return _to_task(row) if row is not None else None
