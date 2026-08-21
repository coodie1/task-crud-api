# Task CRUD API with Supabase Authentication & Docker Stack

A production-ready, secure **Task CRUD API** built with **FastAPI**, containerized with **Docker**, backed by **PostgreSQL/SQLite**, and secured with **Supabase Auth & JWT Bearer Token Middleware**.

---

## 🔐 The Big Idea: Authentication & The Trust Triangle

Secure authentication follows a **trust triangle** between three parties:
1. **The Client**: Sends credentials (email & password) and receives a signed **JSON Web Token (JWT)**.
2. **The Identity Provider (Supabase Auth)**: Stores user accounts, securely hashes passwords, issues signed JWTs, and verifies user tokens.
3. **Your Backend API (FastAPI)**: Never stores or hashes passwords. It extracts the Bearer token from incoming `Authorization: Bearer <token>` headers, verifies the signature, and guards protected endpoints via reusable dependency middleware.

```
                  ┌───────────────────────────────┐
                  │   Supabase Auth (IdP)         │
                  │   - Hashes passwords          │
                  │   - Issues & verifies JWTs    │
                  └──────────────▲────────────────┘
                                 │
                 1. Login / JWT  │ 3. Verify Token
                                 │
┌──────────────┐                 │                 ┌──────────────────────────────┐
│    Client    ├─────────────────┴────────────────►│  FastAPI Backend             │
│ (Swagger/UI) │ 2. Request with Bearer <token>   │  - Auth Dependency Guard     │
└──────────────┘                                   │  - PostgreSQL / SQLite Repo  │
                                                   └──────────────────────────────┘
```

---

## ⚙️ Environment Configuration (`.env`)

Secrets are managed via a git-ignored `.env` file. A committed template is available at [`.env.example`](.env.example):

```env
# Supabase Authentication Secrets
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here

# Local JWT Secret for standalone verification
JWT_SECRET=super-secret-auth-key-for-local-jwt-verification-12345

# Database Connection URL (PostgreSQL / SQLite)
DATABASE_URL=postgresql://postgres:postgres@db:5432/tasks_db

# Optional Redis Connection
REDIS_URL=redis://redis:6379/0
```

> **Security Note:** Real API keys are stored solely in `.env` and are strictly git-ignored via `.gitignore`.

---

## 🚀 Quickstart & How to Run

### Option 1: Run with Docker Compose (App + Postgres + Redis)
```bash
docker compose up --build
```

### Option 2: Run Standalone Locally
```powershell
# Windows PowerShell
.\fast.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```
```bash
# Universal Python
python -m uvicorn main:app --reload --port 8000
```

### Run Test Suites
```bash
# Auth & Security Test Suite (15 Tests)
python test_auth.py

# Task CRUD Test Suite (26 Tests)
python test_api.py
```

---

## 📋 API Endpoints Reference Table

| HTTP Verb | Endpoint | Status Codes | Auth Required | Description |
| :--- | :--- | :--- | :---: | :--- |
| `GET` | `/` | `200 OK` | ❌ None | API Root metadata & available endpoints |
| `GET` | `/health` | `200 OK` | ❌ None | Health check (reports Database & Redis status) |
| `GET` | `/public/info` | `200 OK` | ❌ None | Public lobby open to unauthenticated users |
| `POST` | `/auth/signup` | `201 Created` / `400 Bad Request` | ❌ None | Register a new user account with email & password |
| `POST` | `/auth/login` | `200 OK` / `400 Bad Request` / `401 Unauthorized` | ❌ None | Authenticate and obtain a signed JWT `access_token` |
| `POST` | `/auth/logout` | `204 No Content` / `401 Unauthorized` | ✅ `Bearer <token>` | Invalidate current user session |
| `GET` | `/protected/profile` | `200 OK` / `401 Unauthorized` | ✅ `Bearer <token>` | Retrieve authenticated user's private profile |
| `GET` | `/protected/dashboard` | `200 OK` / `401 Unauthorized` | ✅ `Bearer <token>` | Second protected endpoint proving middleware reuse |
| `GET` | `/protected/admin` | `200 OK` / `403 Forbidden` | ✅ `Bearer <token>` | Role-based authorization demo (admin only) |
| `GET` | `/tasks` | `200 OK` | ❌ None | List all tasks (supports `?done=`, `?search=`, `?sort=`) |
| `GET` | `/tasks/{id}` | `200 OK` / `404 Not Found` | ❌ None | Retrieve a single task by ID |
| `POST` | `/tasks` | `201 Created` / `400 Bad Request` | ❌ None | Create a new task |
| `PUT` | `/tasks/{id}` | `200 OK` / `400 Bad Request` / `404 Not Found` | ❌ None | Update task title and/or status |
| `DELETE` | `/tasks/{id}` | `204 No Content` / `404 Not Found` | ❌ None | Delete a task by ID |
| `GET` | `/stats` | `200 OK` | ❌ None | Aggregate statistics via SQL `COUNT()` |

---

## 🔒 401 Unauthorized vs 403 Forbidden

- **`401 Unauthorized`**: *"I don't know who you are."* Returned when the `Authorization` header is missing, malformed, or the JWT token has expired or been forged.
- **`403 Forbidden`**: *"I know who you are, but you are not allowed in."* Returned when a valid authenticated user attempts to access a resource that requires higher privileges (e.g. `/protected/admin`).

---

## 🧪 Sample `curl -i` Verification Flows

### 1. User Sign Up (`POST /auth/signup`)
```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"password123"}'
```
```http
HTTP/1.1 201 Created
content-type: application/json

{"id":"096b7978-ecb3-4fe6-bc2c-7389a997ba7e","email":"student@example.com","created_at":"2026-08-21T21:00:00Z"}
```

### 2. User Log In (`POST /auth/login`)
```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"password123"}'
```
```http
HTTP/1.1 200 OK
content-type: application/json

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer","user":{"email":"student@example.com"}}
```

### 3. Protected Profile with Bearer Token (`GET /protected/profile`)
```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <PASTE_YOUR_ACCESS_TOKEN_HERE>"
```
```http
HTTP/1.1 200 OK
content-type: application/json

{"id":"096b7978-ecb3-4fe6-bc2c-7389a997ba7e","email":"student@example.com","created_at":"2026-08-21T21:00:00Z"}
```

### 4. Forged / Tampered Token Rejection (`401 Unauthorized`)
```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer forged_invalid_token"
```
```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"error":"Invalid or expired token"}
```

---

## 📸 Interactive Documentation (Swagger UI with Bearer Auth)

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
  - Features the **Authorize Padlock 🔒** configured via FastAPI's `HTTPBearer` security scheme.
  - Paste your token once in the Authorize modal to test all protected endpoints interactively.
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

![Swagger UI Documentation](swagger_screenshot.png)

---

## 🤖 Stage 7: AI vs Me (Secured Auth Rematch)

### The Prompt
> "Build a secured FastAPI backend with Supabase Auth integration. Create public routes (GET /public/info), auth routes (POST /auth/signup, POST /auth/login, POST /auth/logout), and protected routes (GET /protected/profile, GET /protected/dashboard). Implement a reusable HTTPBearer dependency guard that verifies the token with Supabase and returns 401 with a standard JSON error on missing or invalid tokens."

### 3 Concrete Differences Found

1. **Error Response Standardization**:
   - *AI Version*: Used default `HTTPException` which outputs `{"detail": "..."}`, violating the expected `{"error": "..."}` JSON format.
   - *Hand-built Version*: Implemented custom `AuthenticationError` and `@app.exception_handler` returning standard `{"error": "..."}` matching all test suites.

2. **Offline & Standalone Fallback**:
   - *AI Version*: Hard-crashed if Supabase project credentials were unset or if network requests timed out.
   - *Hand-built Version*: Graciously handles both Supabase cloud authentication and local signed JWT verification for 100% offline test suite reliability.

3. **HTTPBearer Auto-Error Handling**:
   - *AI Version*: Relied on `HTTPBearer()` default which returns plain 403/detail errors when no header is passed.
   - *Hand-built Version*: Configured `HTTPBearer(auto_error=False)` inside a custom dependency to ensure a clean `401 Unauthorized` with `{"error": "Access token required"}`.

---

## 👤 Author
**coodie1** (`umairarif946@gmail.com`)
