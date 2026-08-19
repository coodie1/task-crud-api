from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

app = FastAPI(title="Task API", version="1.0")

# In-memory list of task objects
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read a book", "done": True},
    {"id": 3, "title": "Complete assignment", "done": False},
]

@app.get("/")
def read_root():
    """Root endpoint providing API metadata."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health_check():
    """Health check endpoint to verify server is running."""
    return {"status": "ok"}

@app.get("/tasks")
def get_tasks():
    """List all tasks."""
    return tasks

@app.get("/tasks/{id}")
def get_task(id: int):
    """Get a single task by ID."""
    for task in tasks:
        if task["id"] == id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

@app.post("/tasks", status_code=201)
def create_task(task_data: dict = Body(default=None)):
    """Create a new task with validation."""
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

