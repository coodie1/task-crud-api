# Task CRUD API — SQLite Database Edition

A production-ready **Task CRUD API** built with **FastAPI** and backed by a persistent **SQLite database (`tasks.db`)**, maintaining the exact same RESTful contract while persisting data across server restarts.

---

## 💡 About this Assignment (W3 · A1)

In Assignment 1 (Week 2), task data lived solely in volatile memory and vanished whenever the server stopped. In this assignment, we migrated the storage layer to **SQLite** without changing any external API contracts.

### Why SQLite was Chosen
- **Zero Configuration**: SQLite is a serverless, self-contained relational database embedded directly in Python's standard library (`sqlite3`). No external database daemon or setup required.
- **Single File Storage**: All tables, schema, and rows reside in a single portable file (`tasks.db`) in the project root.
- **ACID Compliant**: Full transactional integrity for `INSERT`, `UPDATE`, and `DELETE` queries.
- **Clean Separation of Concerns**: Proves that APIs describe *what* your application does, while databases describe *where* your application stores its data.

### Where the Database is Stored
The database file is automatically created on first startup at:
```text
./tasks.db (in the project root directory)
```
If `tasks.db` does not exist or the `tasks` table is empty, the application automatically creates the schema and seeds 3 initial example tasks. Subsequent restarts preserve all modified and created records.

---

## 🚀 Quickstart & How to Run

### Run Server (PowerShell / Windows)
```powershell
.\fast.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

### Run Server (Universal Python)
```bash
python -m uvicorn main:app --reload --port 8000
```

### Run Automated Tests (26 Tests)
```bash
python test_api.py
```

### Interactive Documentation
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 📋 API Endpoints

| HTTP Verb | Endpoint | Status Codes | Description | Query / Body Parameters |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | `200 OK` | API root metadata | _None_ |
| `GET` | `/health` | `200 OK` | Server health check (`{"status": "ok"}`) | _None_ |
| `GET` | `/tasks` | `200 OK` | List tasks (supports search & filter) | `?done=true`, `?search=milk`, `?sort=title` |
| `GET` | `/tasks/{id}` | `200 OK` / `404 Not Found` | Retrieve single task by ID | Path parameter `id` |
| `POST` | `/tasks` | `201 Created` / `400 Bad Request` | Insert new task into database | Body: `{"title": "Buy milk"}` |
| `PUT` | `/tasks/{id}` | `200 OK` / `400 Bad Request` / `404 Not Found` | Update task title and/or done status | Body: `{"title": "...", "done": true}` |
| `DELETE` | `/tasks/{id}` | `204 No Content` / `404 Not Found` | Delete task from database | Path parameter `id` |
| `GET` | `/stats` | `200 OK` | Task count statistics via SQL `COUNT()` | _None_ |

---

## 🗄️ SQL Schema & Queries Executed

### Database Table Schema
```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT 0
);
```

### Core SQL Queries Used by the API
1. **List all tasks**:
   ```sql
   SELECT * FROM tasks ORDER BY id ASC;
   ```
2. **Filter completed tasks**:
   ```sql
   SELECT * FROM tasks WHERE done = 1;
   ```
3. **Search by keyword**:
   ```sql
   SELECT * FROM tasks WHERE title LIKE '%groceries%';
   ```
4. **Get task by ID**:
   ```sql
   SELECT * FROM tasks WHERE id = ?;
   ```
5. **Insert new task**:
   ```sql
   INSERT INTO tasks (title, done) VALUES (?, ?);
   ```
6. **Update task**:
   ```sql
   UPDATE tasks SET title = ?, done = ? WHERE id = ?;
   ```
7. **Delete task**:
   ```sql
   DELETE FROM tasks WHERE id = ?;
   ```
8. **Count & Aggregate statistics**:
   ```sql
   SELECT COUNT(*) FROM tasks;
   SELECT COUNT(*) FROM tasks WHERE done = 1;
   ```

---

## 🧪 Sample `curl -i` Outputs

### 1. Insert Task into SQLite (`POST /tasks`)
```http
HTTP/1.1 201 Created
date: Fri, 21 Aug 2026 13:20:00 GMT
server: uvicorn
content-length: 44
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

### 2. Read Single Task (`GET /tasks/1`)
```http
HTTP/1.1 200 OK
date: Fri, 21 Aug 2026 13:20:01 GMT
server: uvicorn
content-length: 50
content-type: application/json

{"id":1,"title":"Buy groceries","done":false}
```

### 3. Task Statistics (`GET /stats`)
```http
HTTP/1.1 200 OK
date: Fri, 21 Aug 2026 13:20:02 GMT
server: uvicorn
content-length: 32
content-type: application/json

{"total":3,"done":1,"open":2}
```

---

## 📸 Swagger UI & Database Documentation

![Swagger UI Documentation](swagger_screenshot.png)

---

## 👤 Author
**coodie1** (`umairarif946@gmail.com`)
