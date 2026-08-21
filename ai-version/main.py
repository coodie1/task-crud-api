"""
AI-generated version of the SQLite Task CRUD API (W3 Stage 6 AI Rematch quarantine).
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import sqlite3

DB_PATH = "ai_tasks.db"

app = FastAPI(title="Task API AI SQLite Version")


def get_ai_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_ai_db():
    conn = get_ai_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        example_tasks = [
            ("Buy groceries", 0),
            ("Read a book", 1),
            ("Complete assignment", 0),
        ]
        cursor.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", example_tasks)
    conn.commit()
    conn.close()


init_ai_db()


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/")
def get_root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}


@app.get("/health")
def get_health():
    return {"status": "ok"}


@app.get("/tasks")
def get_all_tasks():
    conn = get_ai_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]


@app.get("/tasks/{id}")
def get_single_task(id: int):
    conn = get_ai_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_new_task(task_input: TaskCreate):
    if not task_input.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    conn = get_ai_db()
    cursor = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (task_input.title.strip(), 0))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "title": task_input.title.strip(), "done": False}


@app.put("/tasks/{id}")
def update_existing_task(id: int, task_input: TaskUpdate):
    conn = get_ai_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

    title = task_input.title.strip() if task_input.title is not None else row["title"]
    done = int(task_input.done) if task_input.done is not None else row["done"]

    conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (title, done, id))
    conn.commit()
    conn.close()
    return {"id": id, "title": title, "done": bool(done)}


@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_task(id: int):
    conn = get_ai_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {id} not found")
    conn.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return None
