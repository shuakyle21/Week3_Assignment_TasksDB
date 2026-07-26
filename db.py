import sqlite3

db_name = "tasks.db"

SEED_TASKS = [
    {"title": "Read the FastAPI docs", "done": True},
    {"title": "Wire up SQLite", "done": True},
    {"title": "Write the Week 3 README", "done": False},
]

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(db_name)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table():
    conn = create_connection()

    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL CHECK (done IN (0, 1))
                )
            ''')
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()

def count_tasks():
    conn = create_connection()
    count = 0
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tasks')
            count = cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()
    return count

def insert_task(title, done):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO tasks (title, done) VALUES (?, ?)', (title, done))
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()

def init_db():
    create_table()
    if count_tasks() == 0:
        for task in SEED_TASKS:
            insert_task(task["title"], task["done"])

if __name__ == "__main__":

    try:
        init_db()
        print(f"{db_name} ready with {count_tasks()} tasks.")

    except Exception as e:
        print(f"Error: {e}")



