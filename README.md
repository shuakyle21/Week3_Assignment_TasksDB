# Week 3 Assignment - Task CRUD API with PostgreSQL + Docker

A FastAPI REST API for managing a task list with full CRUD (Create, Read, Update, Delete) operations. The tasks have moved through three storage backends over the course of this assignment: an in-memory Python list (Week 2), a SQLite file (Stages 1-5 below), and now PostgreSQL running as its own server in a Docker container. The app and the database each run in their own container, and `docker compose up` starts both.

## How to run

One-time setup — copy the example environment file and (optionally) change the password:

```bash
cp .env.example .env
```

Then, from the repo root:

```bash
docker compose up
```

That's it. Compose builds the `web` image from the [Dockerfile](Dockerfile), starts a `postgres:16` container, waits for Postgres to report healthy, then starts the API. `main.py` calls `db.init_db()` on startup, which retries the connection until the database is reachable, creates the `tasks` table, and seeds three starter tasks if the table is empty.

The API is available at `http://localhost:8000`, and the database itself is published on `localhost:5432` if you want to connect to it directly (e.g. with `psql` or a GUI) using the credentials in `.env`.

Stop everything with `docker compose down`. Task data lives in a named Docker volume (`pgdata`), so it survives a `down`/`up` cycle — add `-v` to `docker compose down` if you want to wipe it and start fresh.

## Why a `.env` file

The database password is never hardcoded or committed. [.env](.env) holds it locally and is listed in [.gitignore](.gitignore); [.env.example](.env.example) is the committed template with safe throwaway defaults, so a fresh clone works immediately after the one-time `cp` step above without anyone having to invent their own values.

## Why PostgreSQL and Docker

- **A real database server, not a file.** SQLite worked, but it's a single file one process writes to. Postgres runs as its own long-lived server process that the API connects to over the network (`db.py` uses `psycopg2` and talks to the `db` host on port 5432) — the same model as most production backends, FlyRank included.
- **Docker kills "works on my machine."** Instead of installing Postgres and matching versions by hand, `docker-compose.yml` pulls a pinned `postgres:16` image and runs it as a disposable container that behaves identically on any machine with Docker installed.
- **One command starts the whole stack.** `docker compose up` builds the app image, starts the database, waits for its healthcheck, then starts the app — no separate steps, no manual `db.init_db()` call before the server can run.

## Where the data lives

Postgres stores its data files inside the container, in the named volume `pgdata` (declared in [docker-compose.yml](docker-compose.yml)). Unlike the SQLite file, there's nothing to see in the repo directory — the data survives container restarts because the volume is separate from the container's filesystem, but it's gone if you explicitly remove the volume (`docker compose down -v`).

## Database schema

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL
)
```

Postgres has a native `BOOLEAN` type, so unlike SQLite there's no need for a `CHECK (done IN (0, 1))` workaround — the column simply can't hold anything else. `SERIAL` replaces `INTEGER PRIMARY KEY AUTOINCREMENT` as Postgres's auto-incrementing id.

## Endpoints

| Method | Path         | Description                              |
|--------|--------------|------------------------------------------|
| GET    | /            | Welcome message with API info            |
| GET    | /health      | Health check endpoint                    |
| GET    | /tasks       | Retrieve all tasks                       |
| GET    | /tasks/{id}  | Retrieve a specific task by ID           |
| POST   | /tasks       | Create a new task                        |
| PUT    | /tasks/{id}  | Update an existing task                  |
| DELETE | /tasks/{id}  | Delete a task                            |

## Example request

```bash
# Get all tasks
curl -i http://localhost:8000/tasks

# Get a specific task
curl -i http://localhost:8000/tasks/1

# Create a new task
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Study FastAPI", "done": false}'

# Update a task
curl -i -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Study FastAPI", "done": true}'

# Delete a task
curl -i -X DELETE http://localhost:8000/tasks/1
```

## Stage 4: exploring the database in DB Browser

Kept from the SQLite stage of this assignment, before the move to PostgreSQL — the point about being able to inspect the database directly still holds, it's just `psql`/a Postgres GUI now instead of DB Browser for SQLite.

![Database open in DB Browser for SQLite](images/db_browser.png)

One of the queries I ran in the Execute SQL tab, to see the split between finished and unfinished tasks:

```sql
SELECT done, COUNT(*) AS how_many
FROM tasks
GROUP BY done;
```

On a freshly seeded database that gives:

| done | how_many |
|------|----------|
| 0    | 1        |
| 1    | 2        |

Two done, one not. What I got out of this stage is that the database is readable without going through my API at all — the same rows my `GET /tasks` endpoint returns are just sitting there in a file I can open and query directly. Useful when I want to check whether a bug is in my SQL or in my FastAPI code.

## Swagger UI

![Screenshot](images/screenshot.png)

## AI vs Me (Week 2 reflection)

Kept from Week 2, so it describes the in-memory list version of the app, before the SQLite rewrite.

I gave an AI a prompt describing this same API from scratch, on a separate `ai-branch`, without letting it see my code. Comparing the two afterward:

**What did the AI do better — and do I understand it well enough to explain it?**
It is much more advanced and specific compared to my handwritten logic. It caught a real bug I didn't notice: my `POST /tasks` appends the new task to the list *before* checking whether `title` was provided, so a bad request still pollutes the data even though it returns a 400. The AI's version validates through a Pydantic model before the handler ever runs, so that class of bug can't happen there. It also uses consistent status codes (`201` on create, `422` on bad input) where mine leans on `400` everywhere. Yes — I understand why it works, it's standard FastAPI/Pydantic, nothing I'd need to look up.

**What did it get wrong or quietly ignore from my prompt?**
I typed "GET /task" (singular) in my prompt; it silently pluralized it to `/tasks` without flagging that it changed my wording. It also dropped `id` from the request body on create entirely — I'd described the task object as `{id, title, done}`, which reads like `id` is something a client could send, but the AI decided server-side auto-increment instead and didn't call out that it was overriding that.

**What did my prompt forget to specify — and what did the AI silently decide for me?**
I never said whether `PUT` should be a full or partial update, it chose "both fields required." I never gave a minimum title length, it picked `min_length=1` on its own. I also never said what a successful `DELETE` should return — it invented a `{"message": ...}` body instead of a plain `204 No Content`. And I never thought about concurrency at all, which its task counter is a bare global int, not safe under concurrent requests, and I didn't catch that until I went looking for what it had assumed.
