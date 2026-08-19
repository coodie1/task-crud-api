from fastapi import FastAPI, Body, Path
from fastapi.responses import JSONResponse, Response

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A simple in-memory CRUD API for managing a to-do list built with FastAPI."
)

# In-memory list of task objects
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read a book", "done": True},
    {"id": 3, "title": "Complete assignment", "done": False},
]

@app.get("/", summary="Get API Metadata", tags=["General"])
def read_root():
    """Returns metadata about the Task API, including name, version, and endpoints."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Health check endpoint to verify that the server is alive and responding."""
    return {"status": "ok"}

@app.get("/tasks", summary="List All Tasks", tags=["Tasks"])
def get_tasks():
    """Retrieve all tasks from the in-memory store."""
    return tasks

@app.get("/tasks/{id}", summary="Get Task by ID", tags=["Tasks"])
def get_task(id: int = Path(..., description="The unique numerical identifier of the task")):
    """Retrieve a single task by its unique ID. Returns 404 if the task does not exist."""
    for task in tasks:
        if task["id"] == id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

@app.post("/tasks", status_code=201, summary="Create Task", tags=["Tasks"])
def create_task(task_data: dict = Body(default=None, example={"title": "Buy milk"})):
    """Create a new task. Requires a JSON body with a non-empty 'title'. Sets 'done' to false by default."""
    if task_data is None or not isinstance(task_data, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a valid JSON object"})
    
    title = task_data.get("title")
    if title is None or not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})
    
    next_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {
        "id": next_id,
        "title": title.strip(),
        "done": False
    }
    tasks.append(new_task)
    return JSONResponse(status_code=201, content=new_task)

@app.put("/tasks/{id}", summary="Update Task", tags=["Tasks"])
def update_task(
    id: int = Path(..., description="The unique numerical identifier of the task to update"),
    task_data: dict = Body(default=None, example={"title": "Buy organic milk", "done": True})
):
    """Replace/update a task's title and/or done status. Returns 404 if not found, 400 for invalid body."""
    task = next((t for t in tasks if t["id"] == id), None)
    if not task:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    
    if task_data is None or not isinstance(task_data, dict) or not task_data:
        return JSONResponse(status_code=400, content={"error": "Invalid or empty update body"})
    
    if "title" in task_data:
        title = task_data["title"]
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        task["title"] = title.strip()
    
    if "done" in task_data:
        if not isinstance(task_data["done"], bool):
            return JSONResponse(status_code=400, content={"error": "'done' field must be a boolean"})
        task["done"] = task_data["done"]
        
    return task

@app.delete("/tasks/{id}", status_code=204, summary="Delete Task", tags=["Tasks"])
def delete_task(id: int = Path(..., description="The unique numerical identifier of the task to delete")):
    """Delete a task by ID. Returns status 204 with empty body on success, 404 if not found."""
    global tasks
    task = next((t for t in tasks if t["id"] == id), None)
    if not task:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    
    tasks = [t for t in tasks if t["id"] != id]
    return Response(status_code=204)
