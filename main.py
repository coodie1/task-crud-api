from fastapi import FastAPI
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
