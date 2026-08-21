"""
AI-generated containerized Postgres version (A3 Stage 6 AI Rematch).
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://postgres:dev@localhost:5432/tasks")

app = FastAPI(title="Task API AI Postgres Stack")


def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        );
    """)
    cursor.execute("SELECT COUNT(*) AS count FROM tasks")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
            INSERT INTO tasks (title, done) VALUES
            ('Buy groceries', FALSE),
            ('Read a book', TRUE),
            ('Complete assignment', FALSE);
        """)
    conn.commit()
    cursor.close()
    conn.close()


@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception:
        pass


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/")
def get_root():
    return {"name": "Task API", "version": "3.0", "endpoints": ["/tasks"]}


@app.get("/health")
def get_health():
    return {"status": "ok"}


@app.get("/tasks")
def get_all_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks ORDER BY id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]


@app.get("/tasks/{id}")
def get_single_task(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_new_task(task_input: TaskCreate):
    if not task_input.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
        (task_input.title.strip(), False)
    )
    new_row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": new_row["id"], "title": new_row["title"], "done": bool(new_row["done"])}


@app.put("/tasks/{id}")
def update_existing_task(id: int, task_input: TaskUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    title = task_input.title.strip() if task_input.title is not None else row["title"]
    done = task_input.done if task_input.done is not None else row["done"]

    cursor.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
        (title, done, id)
    )
    updated = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": updated["id"], "title": updated["title"], "done": bool(updated["done"])}


@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_task(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tasks WHERE id = %s", (id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return None
