import sqlite3

from main import tasks

db_name = "tasks.db"

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

if __name__ == "__main__":

    try:
        create_table()
        if count_tasks() == 0:
            for task in tasks:
                insert_task(task["title"], task["done"])
        else:
            print("Tasks already exist in the database. Skipping insertion.")

    except Exception as e:
        print(f"Error: {e}")



