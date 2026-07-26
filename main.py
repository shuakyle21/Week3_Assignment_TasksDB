"""Task CRUD API, backed by the SQLite database in `db.py`.

Route handlers are plain `def` rather than `async def` on purpose: sqlite3 is a
blocking library, and FastAPI runs sync handlers in a worker threadpool, so a
slow query cannot stall the event loop.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, StringConstraints

import db

# Whitespace is stripped before the length check, so "   " is a clean 422 from
# the model rather than a 500 out of the database CHECK constraint, and the
# value that reaches SQL is the stripped one.
TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    """Base for every request and response model.

    `extra="forbid"` means an unknown field is a 422 rather than something
    quietly dropped on the floor, so a client typo cannot look like a success.
    """

    model_config = ConfigDict(extra="forbid")


class Task(StrictModel):
    """A task as returned by the API."""

    id: int
    title: str
    done: bool


class TaskCreate(StrictModel):
    """Request body of `POST /tasks`. `done` defaults to False when omitted."""

    title: TaskTitle
    done: bool = False


class ApiInfo(StrictModel):
    """Response body of `GET /`."""

    name: str
    version: str
    endpoints: list[str]


class Health(StrictModel):
    """Response body of `GET /health`."""

    status: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the database before the first request is served."""
    db.initialise()
    yield


app = FastAPI(title="Task API", lifespan=lifespan)


@app.get("/", response_model=ApiInfo, status_code=status.HTTP_200_OK)
def root() -> ApiInfo:
    return ApiInfo(name="Task API", version="1.0", endpoints=["/tasks"])


@app.get("/health", response_model=Health, status_code=status.HTTP_200_OK)
def health() -> Health:
    return Health(status="ok")


@app.get("/tasks", response_model=list[Task], status_code=status.HTTP_200_OK)
def get_tasks() -> list[db.TaskRecord]:
    return db.list_tasks()


@app.get("/tasks/{id}", response_model=Task, status_code=status.HTTP_200_OK)
def get_task(id: int) -> db.TaskRecord:
    task = db.get_task(id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {id} not found",
        )
    return task


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, response: Response) -> db.TaskRecord:
    # `payload` is already validated: a malformed body is rejected by the model
    # before this function runs, so nothing invalid ever reaches SQL.
    task = db.insert_task(payload.title, payload.done)
    response.headers["Location"] = f"/tasks/{task['id']}"
    return task


# Update and delete are migrated to SQLite in Stage 3. Until then they answer
# honestly with 501 instead of mutating state that no longer exists - the
# in-memory list they used to write to is gone.
@app.put("/tasks/{id}", response_model=None, status_code=status.HTTP_501_NOT_IMPLEMENTED)
def update_task(id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update is not wired to the database yet",
    )


@app.delete("/tasks/{id}", response_model=None, status_code=status.HTTP_501_NOT_IMPLEMENTED)
def delete_task(id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete is not wired to the database yet",
    )
