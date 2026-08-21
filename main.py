from fastapi import FastAPI, Body, Path, Depends, Request
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from repository import get_repository, ping_redis
from auth_service import AuthService

app = FastAPI(
    title="Task API with Auth",
    version="4.0",
    description="A secure CRUD API backed by PostgreSQL/SQLite and protected with Supabase JWT Bearer Authentication."
)

repo = get_repository()
security = HTTPBearer(auto_error=False)


# --- Reusable Auth Dependency (Middleware Guard) ---
def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Reusable middleware/dependency that extracts and verifies Bearer JWT tokens."""
    if not credentials or not credentials.credentials:
        # Return 401 with JSON error when header is missing or malformed
        raise AuthenticationError("Access token required")

    token = credentials.credentials
    try:
        user = AuthService.verify_token(token)
        return user
    except Exception:
        raise AuthenticationError("Invalid or expired token")


class AuthenticationError(Exception):
    def __init__(self, message: str):
        self.message = message


@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(status_code=401, content={"error": exc.message})


# --- General / Public Endpoints ---

@app.get("/", summary="Get API Metadata", tags=["General"])
def read_root():
    """Returns metadata about the Task API, including name, version, and endpoints."""
    return {
        "name": "Task API",
        "version": "4.0",
        "endpoints": ["/auth/signup", "/auth/login", "/auth/logout", "/public/info", "/protected/profile", "/tasks"]
    }



@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    """Health check endpoint to verify that the server is alive and responding."""
    redis_info = ping_redis()
    return {
        "status": "ok",
        "database": "connected",
        "redis": redis_info.get("status", "unavailable")
    }


@app.get("/public/info", summary="Public Information", tags=["Public"])
def public_info():
    """Public lobby endpoint open to all unauthenticated users."""
    return {"message": "Welcome stranger! This info is public."}


# --- Authentication Endpoints ---

@app.post("/auth/signup", status_code=201, summary="User Sign Up", tags=["Auth"])
def sign_up(payload: dict = Body(default=None, examples=[{"email": "test@example.com", "password": "password123"}])):
    """Register a new user account."""
    if not payload or not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a valid JSON object"})

    email = payload.get("email")
    password = payload.get("password")

    if not email or not isinstance(email, str) or not email.strip():
        return JSONResponse(status_code=400, content={"error": "Email is required"})
    if not password or not isinstance(password, str) or not password.strip():
        return JSONResponse(status_code=400, content={"error": "Password is required"})

    try:
        user = AuthService.sign_up(email=email.strip(), password=password.strip())
        return JSONResponse(status_code=201, content=user)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/auth/login", summary="User Login", tags=["Auth"])
def sign_in(payload: dict = Body(default=None, examples=[{"email": "test@example.com", "password": "password123"}])):
    """Authenticate with email and password to receive a JWT access token."""
    if not payload or not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a valid JSON object"})

    email = payload.get("email")
    password = payload.get("password")

    if not email or not isinstance(email, str) or not email.strip():
        return JSONResponse(status_code=400, content={"error": "Email is required"})
    if not password or not isinstance(password, str) or not password.strip():
        return JSONResponse(status_code=400, content={"error": "Password is required"})

    try:
        auth_data = AuthService.sign_in(email=email.strip(), password=password.strip())
        return JSONResponse(status_code=200, content=auth_data)
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})


@app.post("/auth/logout", status_code=204, summary="User Logout", tags=["Auth"])
def sign_out(user: dict = Depends(get_current_user), credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """End the authenticated session (protected by Bearer token)."""
    if credentials and credentials.credentials:
        AuthService.sign_out(credentials.credentials)
    return Response(status_code=204)


# --- Protected Endpoints ---

@app.get("/protected/profile", summary="User Profile", tags=["Protected"])
def get_profile(user: dict = Depends(get_current_user)):
    """Retrieve private user profile details (ID, email, created date)."""
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "created_at": user.get("created_at")
    }


@app.get("/protected/dashboard", summary="User Dashboard", tags=["Protected"])
def get_dashboard(user: dict = Depends(get_current_user)):
    """Second protected endpoint demonstrating auth dependency reuse."""
    return {
        "message": f"Welcome back, {user.get('email')}!",
        "user_id": user.get("id"),
        "status": "authorized"
    }


@app.get("/protected/admin", summary="Admin Only (403 Demo)", tags=["Protected"])
def admin_only(user: dict = Depends(get_current_user)):
    """Demonstrates 403 Forbidden distinction for non-admin accounts."""
    if not user.get("email", "").startswith("admin@"):
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden: Admin access required"}
        )
    return {"message": "Welcome, Administrator!"}


# --- Task CRUD Endpoints ---

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