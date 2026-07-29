import os
import time

import psycopg2
from dotenv import load_dotenv

# Load .env when running outside Docker (e.g. `python db.py` on the host).
# Inside docker compose the variables are injected directly and this is a no-op,
# and load_dotenv() does not override variables that are already set.
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

SEED_TASKS = [
    {"title": "Read the FastAPI docs", "done": True},
    {"title": "Wire up SQLite", "done": True},
    {"title": "Write the Week 3 README", "done": False},
]

def create_connection():
    return psycopg2.connect(DATABASE_URL)

def wait_for_db(retries=10, delay=2):
    # The db container may accept connections a moment after it starts, so retry
    # a few times before giving up rather than crashing on the first attempt.
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            conn = create_connection()
            conn.close()
            return
        except psycopg2.OperationalError as e:
            last_error = e
            print(f"Database not ready (attempt {attempt}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError(
        f"Could not connect to the database after {retries} attempts"
    ) from last_error

def create_table():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done)')
        conn.commit()
    finally:
        conn.close()

def count_tasks():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM tasks')
            return cursor.fetchone()[0]
    finally:
        conn.close()

def insert_task(title, done):
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO tasks (title, done) VALUES (%s, %s)', (title, done))
        conn.commit()
    finally:
        conn.close()

def init_db():
    wait_for_db()
    create_table()
    if count_tasks() == 0:
        for task in SEED_TASKS:
            insert_task(task["title"], task["done"])

if __name__ == "__main__":

    try:
        init_db()
        print(f"Database ready with {count_tasks()} tasks.")

    except Exception as e:
        print(f"Error: {e}")
