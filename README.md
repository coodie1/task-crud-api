# Task CRUD API — PostgreSQL & Docker Stack

A production-ready **Task CRUD API** built with **FastAPI**, containerized with **Docker**, orchestrated with **Docker Compose**, and backed by a **PostgreSQL** database with volume persistence and optional **Redis** caching.

---

## 🎯 Architecture Overview

This project demonstrates the power of clean layered architecture using the **Repository Pattern**:
- **API & Routes (`main.py`)**: Defines HTTP endpoints, validates client requests, and returns standard HTTP status codes. **Routes remain completely unchanged** regardless of storage backend.
- **Repository Layer (`repository.py`)**: Implements `TaskRepository` interface supporting both:
  - `PostgresTaskRepository`: PostgreSQL with parameterized queries (`%s`), transactions, and connection management.
  - `SqliteTaskRepository`: SQLite with `sqlite3` for local standalone development.
- **Infrastructure (`docker-compose.yml`)**:
  - `app`: FastAPI service running on port `8000`.
  - `db`: PostgreSQL 15 container with persistent volume (`pgdata`) and `init.sql` schema initialization.
  - `redis`: Redis 7 container for high-speed caching and queues.

```
Client ──► FastAPI Router (main.py) ──► TaskRepository (repository.py) ──► PostgreSQL (tasks_db)
                                                                       └──► Redis (Cache)
```

---

## 🚀 Quickstart: Run the Whole Stack with One Command

### Option 1: Run with Docker Compose (Recommended)
Start the entire stack (FastAPI + PostgreSQL + Redis):
```bash
docker compose up --build
```
To run in the background (detached mode):
```bash
docker compose up -d
```

### Option 2: Run Standalone Locally (Without Docker)
```powershell
# Windows PowerShell
.\fast.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```
```bash
# Universal Python
python -m uvicorn main:app --reload --port 8000
```

---

## ⚙️ Environment Configuration (`.env`)

Configuration is managed via `.env` (gitignored, template provided in `.env.example`):

```env
# PostgreSQL connection string in Docker:
DATABASE_URL=postgresql://postgres:postgres@db:5432/tasks_db

# Local development fallback (SQLite):
# DATABASE_URL=sqlite:///tasks.db

# Optional Redis URL:
REDIS_URL=redis://redis:6379/0
```

---

## 💾 Proving Persistence Across Restarts

Data persistence is verified using a named Docker volume (`pgdata:/var/lib/postgresql/data`):

1. **Start the containers**:
   ```bash
   docker compose up -d
   ```
2. **Create a new task**:
   ```bash
   curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{\"title\": \"Persistent Task\"}"
   ```
3. **Restart the containers**:
   ```bash
   docker compose down
   docker compose up -d
   ```
4. **Verify data survived**:
   ```bash
   curl http://localhost:8000/tasks
   ```
   *The task is still present because the PostgreSQL data volume outlives container lifecycles.*

---

## 📋 API Endpoints

| HTTP Verb | Endpoint | Status Codes | Description | Query / Body Parameters |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | `200 OK` | API root metadata | _None_ |
| `GET` | `/health` | `200 OK` | Health check + DB & Redis ping | _None_ |
| `GET` | `/tasks` | `200 OK` | List tasks with filter/search/sort | `?done=true`, `?search=milk`, `?sort=title` |
| `GET` | `/tasks/{id}` | `200 OK` / `404 Not Found` | Retrieve single task by ID | Path parameter `id` |
| `POST` | `/tasks` | `201 Created` / `400 Bad Request` | Insert new task | Body: `{"title": "Buy milk"}` |
| `PUT` | `/tasks/{id}` | `200 OK` / `400 Bad Request` / `404 Not Found` | Update task title / status | Body: `{"title": "...", "done": true}` |
| `DELETE` | `/tasks/{id}` | `204 No Content` / `404 Not Found` | Delete task | Path parameter `id` |
| `GET` | `/stats` | `200 OK` | Aggregate statistics via SQL `COUNT()` | _None_ |

---

## 🧪 Automated Test Suite (26 Tests)

Run the test suite against the running API:
```bash
python test_api.py
```
```text
============================================================
  Results: 26/26 passed, 0 failed
============================================================
```

---

## 📸 Interactive Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

![Swagger UI Documentation](swagger_screenshot.png)

---

## 👤 Author
**coodie1** (`umairarif946@gmail.com`)
