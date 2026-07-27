from fastapi import Depends, FastAPI, HTTPException
import psycopg2
import db

# Create the tasks table and seed it before the app starts serving, so a fresh
# stack works with no manual setup step. db.init_db() first waits for the
# PostgreSQL container to be ready.
db.init_db()

app = FastAPI()

def get_db():
    conn = db.create_connection()
    try:
        yield conn
    finally:
        conn.close()

@app.get("/")
def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ["/tasks"] }

@app.get("/health")
def health():
    return { "status": "ok" }

#1
@app.get("/tasks")
def get_tasks(conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()

    return {"tasks": [{"id": task[0], "title": task[1], "done": bool(task[2])} for task in tasks]}

@app.get("/tasks/{id}")
def get_task(id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
    task = cursor.fetchone()

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found, error code: {404}")

    return {"id": task[0], "title": task[1], "done": bool(task[2])}

#2
@app.post("/tasks")
def create_task(task: dict, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id", (task.get("title"), task.get("done", False)))
    new_id = cursor.fetchone()[0]
    conn.commit()

    if task.get("title") is None:
        raise HTTPException(status_code=400, detail=f"Error {400}, missing title is required")
    return {201: "Created", "task": {"id": new_id, "title": task.get("title"), "done": task.get("done", False)}}

@app.put("/tasks/{id}")
def update_task(id: int, task: dict, conn = Depends(get_db)):
    if task is None or task == {}:
        raise HTTPException(status_code=400, detail=f"Error {400}, empty body")

    title = task.get("title")
    if title is not None and title.strip() == "":
        raise HTTPException(status_code=400, detail=f"Error {400}, invalid body")

    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET title = %s, done = %s WHERE id = %s", (title, task.get("done", False), id))
    conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

    return {"message": f"Task {id} updated", "task": {"id": id, "title": title, "done": task.get("done", False)}}

@app.delete("/tasks/{id}")
def delete_task(id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

    return {"message": f"Task {id} deleted"}
