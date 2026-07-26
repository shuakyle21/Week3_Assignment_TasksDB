# Week 3 Assignment - Task CRUD API on SQLite

A FastAPI REST API for managing a task list with full CRUD (Create, Read, Update,
Delete) operations. Week 2 kept the tasks in a Python list inside the running
process, so every restart wiped them. Week 3 keeps exactly the same endpoints but
stores the tasks in a SQLite database instead.

The whole app is two files: `main.py` holds the routes and the request/response
models, `db.py` holds the schema and every SQL statement.

## How to run

Run this from the repository root:

```bash
pip install -r requirements.txt && uvicorn main:app --reload
```

The API is then available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

## Why SQLite

- **It is a single file.** The entire database is one `tasks.db` file sitting next
  to the code - simple to inspect, copy, back up, or throw away and rebuild.
- **Zero setup.** There is no database server to install and no connection string
  to configure. The `sqlite3` driver is part of the Python standard library, so the
  command above is the only install step.
- **It survives restarts.** A task created through the API is still there after the
  server is stopped and started again, which is the one thing the in-memory list
  could never do.

## Where the database file lives

`tasks.db`, in the repository root, right beside `main.py` and `db.py`.

- **It is created automatically.** On startup the FastAPI `lifespan` handler calls
  `db.initialise()`, which creates the `tasks` table if it is missing and inserts
  the three starter tasks only when the table is empty. That makes startup
  idempotent: restarting the server never duplicates the seed rows.
- **It is git-ignored.** The database is local state, not source code, so it is
  listed in `.gitignore` and every clone starts fresh, building its own copy on
  the first run.
- **It does not follow your shell around.** `db.py` resolves the location as
  `Path(__file__).resolve().parent / "tasks.db"` - an absolute path anchored to the
  module - so the file always lands next to the code even if uvicorn was started
  from some other directory. A bare relative `"tasks.db"` would scatter half-empty
  databases wherever the server happened to be launched.

## Schema

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
);
```

| Column  | Type    | Notes                                                                             |
|---------|---------|-----------------------------------------------------------------------------------|
| `id`    | INTEGER | Primary key. As an alias for SQLite's `rowid` it is assigned automatically on insert. |
| `title` | TEXT    | Required. The CHECK rejects a title that is empty or nothing but whitespace.        |
| `done`  | INTEGER | 0 or 1 only, defaults to 0.                                                        |

**SQLite has no boolean type.** It stores true and false as the integers 1 and 0,
which is why `done` is an INTEGER column with `CHECK (done IN (0, 1))` to keep any
other value out. `db.py` converts it back with `bool(row["done"])` on the way out,
so the API still returns proper JSON `true` / `false` and clients never deal with
the 0/1 representation.

Both CHECK constraints are real defences, not decoration: they hold even when rows
are written from the `sqlite3` CLI or DB Browser rather than through the API. The
API refuses the same bad data earlier - `title` is stripped of surrounding
whitespace and then required to be non-empty by the Pydantic model, so `"   "` is a
clean 422 instead of a 500 raised by the database.

## Endpoints

| Method | Path          | Description                            | Success                     | Errors                                          |
|--------|---------------|----------------------------------------|-----------------------------|-------------------------------------------------|
| GET    | `/`           | API info                               | `200 OK`                    | -                                               |
| GET    | `/health`     | Health check                           | `200 OK`                    | -                                               |
| GET    | `/tasks`      | List every task, lowest id first       | `200 OK`                    | -                                               |
| GET    | `/tasks/{id}` | Fetch one task                         | `200 OK`                    | `404` unknown id, `422` non-integer id          |
| POST   | `/tasks`      | Create a task                          | `201 Created` + `Location`  | `422` invalid body                              |
| PUT    | `/tasks/{id}` | Replace a task                         | `200 OK`                    | `404` unknown id, `422` invalid body            |
| DELETE | `/tasks/{id}` | Delete a task                          | `204 No Content`, empty body| `404` unknown id, `422` non-integer id          |

A few rules the status codes depend on:

- **`PUT` is a full replacement.** Both `title` and `done` are required. Sending
  only one of them is a `422`, never a silent overwrite of the missing field with
  a default. `POST` is the exception: `done` may be omitted and defaults to `false`.
- **Unknown fields are rejected.** The models are configured with
  `extra="forbid"`, so `{"title": "Read", "prioriy": "high"}` is a `422` that names
  the offending field instead of a `201` that quietly drops the typo.
- **`DELETE` returns no body.** A `204` response carries zero bytes; deleting the
  same id twice gives `204` then `404`.

## Example requests

```bash
# Get all tasks
curl -i http://localhost:8000/tasks

# Get a specific task
curl -i http://localhost:8000/tasks/1

# Create a new task - responds 201 with a Location header pointing at the new task
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Study FastAPI", "done": false}'

# Replace a task - both fields are required
curl -i -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Study FastAPI", "done": true}'

# Delete a task - responds 204 with an empty body
curl -i -X DELETE http://localhost:8000/tasks/1
```

## Looking at the database

The file can be opened directly in [DB Browser for SQLite](https://sqlitebrowser.org/),
which is the quickest way to confirm that data written through the API really is on
disk:

![Database open in DB Browser for SQLite](images/db_browser.png)

## Swagger UI

The interactive docs at `/docs` (screenshot captured in Week 2; the endpoint set is
unchanged):

![Screenshot](images/screenshot.png)

## Exploring the database with SQL

Everything below was run against `tasks.db` with the `sqlite3` command-line tool
(version 3.51.0) after starting the server once on a fresh database, so the table
holds only the three seeded tasks. The output is copied verbatim.

**The schema SQLite actually stored**

```
$ sqlite3 tasks.db ".schema tasks"
CREATE TABLE tasks (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
);
```

**Read the whole table**

```
$ sqlite3 tasks.db -header -column "SELECT * FROM tasks;"
id  title          done
--  -------------  ----
1   Clean room     0
2   Buy groceries  1
3   Walk the dog   0
```

`done` comes back as `0` / `1` because SQLite has no boolean type; the API turns
it back into `true` / `false` on the way out.

**Filter by `done`**

```
$ sqlite3 tasks.db -header -column "SELECT id, title FROM tasks WHERE done = 0;"
id  title
--  ------------
1   Clean room
3   Walk the dog
```

**Count how many tasks are in each state**

```
$ sqlite3 tasks.db -header -column "SELECT done, COUNT(*) AS total FROM tasks GROUP BY done;"
done  total
----  -----
0     2
1     1
```

**The CHECK constraints rejecting bad data**

A title that is only whitespace is refused by the database itself, not just by
the API:

```
$ sqlite3 tasks.db "INSERT INTO tasks (title, done) VALUES ('   ', 0);"
Error: stepping, CHECK constraint failed: length(trim(title)) > 0 (19)
```

So is a `done` value that is not 0 or 1:

```
$ sqlite3 tasks.db "UPDATE tasks SET done = 2 WHERE id = 1;"
Error: stepping, CHECK constraint failed: done IN (0, 1) (19)
```

Both statements failed, so nothing was written - the table is untouched:

```
$ sqlite3 tasks.db -header -column "SELECT COUNT(*) AS total FROM tasks;"
total
-----
3
```

## AI vs Me (Week 2 reflection)

_Written in Week 2, about the pre-SQLite version of this API that stored its tasks
in an in-memory Python list._

I gave an AI a prompt describing this same API from scratch, on a separate `ai-branch`, without letting it see my code. Comparing the two afterward:

**What did the AI do better — and do I understand it well enough to explain it?**
It is much more advanced and specific compared to my handwritten logic. It caught a real bug I didn't notice: my `POST /tasks` appends the new task to the list *before* checking whether `title` was provided, so a bad request still pollutes the data even though it returns a 400. The AI's version validates through a Pydantic model before the handler ever runs, so that class of bug can't happen there. It also uses consistent status codes (`201` on create, `422` on bad input) where mine leans on `400` everywhere. Yes — I understand why it works, it's standard FastAPI/Pydantic, nothing I'd need to look up.

**What did it get wrong or quietly ignore from my prompt?**
I typed "GET /task" (singular) in my prompt; it silently pluralized it to `/tasks` without flagging that it changed my wording. It also dropped `id` from the request body on create entirely — I'd described the task object as `{id, title, done}`, which reads like `id` is something a client could send, but the AI decided server-side auto-increment instead and didn't call out that it was overriding that.

**What did my prompt forget to specify — and what did the AI silently decide for me?**
I never said whether `PUT` should be a full or partial update, it chose "both fields required." I never gave a minimum title length, it picked `min_length=1` on its own. I also never said what a successful `DELETE` should return — it invented a `{"message": ...}` body instead of a plain `204 No Content`. And I never thought about concurrency at all, which its task counter is a bare global int, not safe under concurrent requests, and I didn't catch that until I went looking for what it had assumed.
