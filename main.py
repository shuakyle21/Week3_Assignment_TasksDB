from fastapi import Depends, FastAPI, HTTPException
import sqlite3

import db


app = FastAPI()

def get_db():
    conn = sqlite3.connect(db.db_name)
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
def get_tasks(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    
    return {"tasks": [{"id": task[0], "title": task[1], "done": bool(task[2])} for task in tasks]}

@app.get("/tasks/{id}")
def get_task(id: int, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    task = cursor.fetchone()

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found, error code: {404}")

    return {"id": task[0], "title": task[1], "done": bool(task[2])}

#2
@app.post("/tasks")
def create_task(task: dict, conn: sqlite3.Connection = Depends(get_db)):    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (task.get("title"), task.get("done", False)))
    conn.commit()

    if task.get("title") is None:
        raise HTTPException(status_code=400, detail="Missing title is required")
    return {201: "Created", "task": {"id": cursor.lastrowid, "title": task.get("title"), "done": task.get("done", False)}}

@app.put("/tasks/{id}")
def update_task(id: int, task: dict):
    if task is None or task == {}:
        raise HTTPException(status_code=400, detail="Empty body")
    
    title = task.get("title")
    if title is not None and title.strip() == "":
        raise HTTPException(status_code=400, detail="invalid body")
    for t in tasks:
        if t["id"] == id:
            if title is not None:
                t["title"] = title
            if task.get("done") is not None:
                t["done"] = task.get("done")
            return {
                "message": f"Task {id} updated",
                "task": t
            }
    raise HTTPException(status_code=404, detail=f"Task {id} not found")

@app.delete("/tasks/{id}")
def delete_task(id: int):
    for task in tasks:
        if task["id"] == id:
            tasks.remove(task)
            return { "message": f"Task {id} deleted" }
    raise HTTPException(status_code=404, detail=f"Task {id} not found")