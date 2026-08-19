"""
AI-generated version of the Task CRUD API (Stage 7 Rematch quarantine).
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Task API AI Version")

# In-memory storage
tasks_db = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read a book", "done": True},
    {"id": 3, "title": "Complete assignment", "done": False},
]

class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

@app.get("/")
def get_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def get_health():
    return {"status": "ok"}

@app.get("/tasks")
def get_all_tasks():
    return tasks_db

@app.get("/tasks/{id}")
def get_single_task(id: int):
    for task in tasks_db:
        if task["id"] == id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {id} not found")

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_new_task(task_input: TaskCreate):
    if not task_input.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    next_id = max([t["id"] for t in tasks_db], default=0) + 1
    new_task = {
        "id": next_id,
        "title": task_input.title.strip(),
        "done": False
    }
    tasks_db.append(new_task)
    return new_task

@app.put("/tasks/{id}")
def update_existing_task(id: int, task_input: TaskUpdate):
    for task in tasks_db:
        if task["id"] == id:
            if task_input.title is not None:
                if not task_input.title.strip():
                    raise HTTPException(status_code=400, detail="Title cannot be empty")
                task["title"] = task_input.title.strip()
            if task_input.done is not None:
                task["done"] = task_input.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {id} not found")

@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_task(id: int):
    global tasks_db
    initial_len = len(tasks_db)
    tasks_db = [t for t in tasks_db if t["id"] != id]
    if len(tasks_db) == initial_len:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")
    return None
