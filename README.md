# Week 3 Assignment - Task CRUD API with SQLite

A FastAPI REST API for managing a task list with full CRUD (Create, Read, Update, Delete) operations. This week the tasks moved out of an in-memory Python list and into a real SQLite database, so they survive a server restart.

## How to run

One command, from the repo root:

```bash
pip install -r requirements.txt && uvicorn main:app --reload
```

That's the whole setup. The database doesn't exist in a fresh clone — `main.py` calls `db.init_db()` on startup, which creates `tasks.db`, creates the `tasks` table, and seeds three starter tasks if the table is empty. Nothing to run by hand first.

The API will be available at `http://localhost:8000`.

Run it from the repo root — `db_name` in [db.py](db.py) is the relative path `tasks.db`, so starting the server from somewhere else puts the database somewhere else.

## Why SQLite

- **It's a single file.** The whole database is `tasks.db` sitting next to the code. I can copy it, delete it to start over, or open it in a GUI without any of that touching a server process.
- **Zero setup.** `sqlite3` ships with Python, so there's no database server to install, no port to configure, no user and password to create. The `pip install` line above is genuinely all a stranger needs.
- **It survives restarts.** This was the actual point of the week. In Week 2 my tasks lived in a Python list, so every `--reload` wiped them. Now a task I create with `POST /tasks` is still there after I stop and start the server.

## Where the database file lives

`tasks.db`, in the repo root, right next to [main.py](main.py).

It's created automatically on first startup and it's listed in [.gitignore](.gitignore), so it is **not** committed to the repo. That's deliberate: my database has whatever junk tasks I made while testing, and there's no reason to push that to anyone else. Every clone starts fresh and generates its own copy with the same three seeded tasks.

## Database schema

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL CHECK (done IN (0, 1))
)
```

SQLite has no real boolean type, so `done` is stored as `0` or `1`. The `CHECK` constraint stops anything else getting in, and the API converts it back with `bool()` on the way out.

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
