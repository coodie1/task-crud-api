from fastapi import FastAPI, Body, Path
from fastapi.responses import JSONResponse, Response
from typing import Optional
from repository import get_repository, ping_redis

app = FastAPI(
    title="Task API",
    version="3.0",
    description="A multi-backend CRUD API for managing a to-do list, backed by PostgreSQL (Docker) and SQLite repositories."
)

repo = get_repository()


@app.get("/", summary="Get API Metadata", tags=["General"])
def read_root():
    """Returns metadata about the Task API, including name, version, and endpoints."""
    return {
        "name": "Task API",
        "version": "3.0",
        "endpoints": ["/tasks"]
    }


@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Health check endpoint to verify that the server is alive and responding."""
    redis_info = ping_redis()
    return {
        "status": "ok",
        "database": "connected",
        "redis": redis_info["status"]
    }


@app.get("/tasks", summary="List All Tasks", tags=["Tasks"])
def get_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None
):
    """Retrieve all tasks from the active repository (Postgres/SQLite) with optional filter/search."""
    return repo.get_all(done=done, search=search, sort=sort)


@app.get("/stats", summary="Task Statistics", tags=["General"])
def get_stats():
    """Returns task statistics calculated using SQL COUNT aggregate queries."""
    return repo.get_stats()


@app.get("/tasks/{id}", summary="Get Task by ID", tags=["Tasks"])
def get_task(id: int = Path(..., description="The unique numerical identifier of the task")):
    """Retrieve a single task by its unique ID. Returns 404 if the task does not exist."""
    task = repo.get_by_id(id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    return task


@app.post("/tasks", status_code=201, summary="Create Task", tags=["Tasks"])
def create_task(task_data: dict = Body(default=None, examples=[{"title": "Buy milk"}])):
    """Create a new task. Requires a JSON body with a non-empty 'title'. Sets 'done' to false by default."""
    if task_data is None or not isinstance(task_data, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a valid JSON object"})

    title = task_data.get("title")
    if title is None or not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})

    new_task = repo.create(title=title.strip())
    return JSONResponse(status_code=201, content=new_task)


@app.put("/tasks/{id}", summary="Update Task", tags=["Tasks"])
def update_task(
    id: int = Path(..., description="The unique numerical identifier of the task to update"),
    task_data: dict = Body(default=None, examples=[{"title": "Buy organic milk", "done": True}])
):
    """Replace/update a task's title and/or done status. Returns 404 if not found, 400 for invalid body."""
    existing = repo.get_by_id(id)
    if existing is None:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

    if task_data is None or not isinstance(task_data, dict) or not task_data:
        return JSONResponse(status_code=400, content={"error": "Invalid or empty update body"})

    new_title = None
    if "title" in task_data:
        title = task_data["title"]
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        new_title = title.strip()

    new_done = None
    if "done" in task_data:
        if not isinstance(task_data["done"], bool):
            return JSONResponse(status_code=400, content={"error": "'done' field must be a boolean"})
        new_done = task_data["done"]

    updated_task = repo.update(id, title=new_title, done=new_done)
    return updated_task


@app.delete("/tasks/{id}", status_code=204, summary="Delete Task", tags=["Tasks"])
def delete_task(id: int = Path(..., description="The unique numerical identifier of the task to delete")):
    """Delete a task by ID. Returns status 204 with empty body on success, 404 if not found."""
    deleted = repo.delete(id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    return Response(status_code=204)