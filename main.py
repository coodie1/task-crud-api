from fastapi import FastAPI, Body, Path
from fastapi.responses import JSONResponse, Response
import sqlite3
import os

DB_PATH = "tasks.db"

app = FastAPI(
    title="Task API",
    version="2.0",
    description="A CRUD API for managing a to-do list, backed by SQLite for persistent storage."
)


def get_db():
    """Get a database connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tasks table if it doesn't exist and seed with example data if empty."""
    conn = get_db()
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
    """)

    # Insert example tasks only if the table is empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        example_tasks = [
            ("Buy groceries", False),
            ("Read a book", True),
            ("Complete assignment", False),
        ]
        cursor.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", example_tasks)

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


def row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict with bool for 'done'."""
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.get("/", summary="Get API Metadata", tags=["General"])
def read_root():
    """Returns metadata about the Task API, including name, version, and endpoints."""
    return {
        "name": "Task API",
        "version": "2.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Health check endpoint to verify that the server is alive and responding."""
    return {"status": "ok"}

@app.get("/tasks", summary="List All Tasks", tags=["Tasks"])
def get_tasks():
    """Retrieve all tasks from the SQLite database."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.get("/tasks/{id}", summary="Get Task by ID", tags=["Tasks"])
def get_task(id: int = Path(..., description="The unique numerical identifier of the task")):
    """Retrieve a single task by its unique ID. Returns 404 if the task does not exist."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    conn.close()
    if row is None:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    return row_to_dict(row)

@app.post("/tasks", status_code=201, summary="Create Task", tags=["Tasks"])
def create_task(task_data: dict = Body(default=None, examples=[{"title": "Buy milk"}])):
    """Create a new task. Requires a JSON body with a non-empty 'title'. Sets 'done' to false by default."""
    if task_data is None or not isinstance(task_data, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a valid JSON object"})

    title = task_data.get("title")
    if title is None or not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})

    conn = get_db()
    cursor = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title.strip(), False))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    new_task = {"id": new_id, "title": title.strip(), "done": False}
    return JSONResponse(status_code=201, content=new_task)

@app.put("/tasks/{id}", summary="Update Task", tags=["Tasks"])
def update_task(
    id: int = Path(..., description="The unique numerical identifier of the task to update"),
    task_data: dict = Body(default=None, examples=[{"title": "Buy organic milk", "done": True}])
):
    """Replace/update a task's title and/or done status. Returns 404 if not found, 400 for invalid body."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    if row is None:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

    if task_data is None or not isinstance(task_data, dict) or not task_data:
        conn.close()
        return JSONResponse(status_code=400, content={"error": "Invalid or empty update body"})

    current_title = row["title"]
    current_done = bool(row["done"])

    if "title" in task_data:
        title = task_data["title"]
        if not isinstance(title, str) or not title.strip():
            conn.close()
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        current_title = title.strip()

    if "done" in task_data:
        if not isinstance(task_data["done"], bool):
            conn.close()
            return JSONResponse(status_code=400, content={"error": "'done' field must be a boolean"})
        current_done = task_data["done"]

    conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (current_title, current_done, id))
    conn.commit()
    conn.close()

    return {"id": id, "title": current_title, "done": current_done}

@app.delete("/tasks/{id}", status_code=204, summary="Delete Task", tags=["Tasks"])
def delete_task(id: int = Path(..., description="The unique numerical identifier of the task to delete")):
    """Delete a task by ID. Returns status 204 with empty body on success, 404 if not found."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    if row is None:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

    conn.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return Response(status_code=204)