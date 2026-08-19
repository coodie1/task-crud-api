from fastapi import FastAPI

app = FastAPI(title="Task API", version="1.0")

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