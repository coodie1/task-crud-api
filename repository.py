"""
Repository layer for Task CRUD API.
Implements a unified interface supporting both PostgreSQL (via psycopg2)
and SQLite (via sqlite3) based on the DATABASE_URL environment variable.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tasks.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class TaskRepository(ABC):
    """Abstract Task Repository Interface."""

    @abstractmethod
    def init_db(self) -> None:
        pass

    @abstractmethod
    def get_all(self, done: Optional[bool] = None, search: Optional[str] = None, sort: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def create(self, title: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update(self, task_id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        pass


class PostgresTaskRepository(TaskRepository):
    """PostgreSQL Task Repository using psycopg2 with parameterized queries."""

    def __init__(self, db_url: str):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        self.db_url = db_url
        self.psycopg2 = psycopg2
        self.RealDictCursor = RealDictCursor
        self.init_db()

    def _get_conn(self):
        return self.psycopg2.connect(self.db_url, cursor_factory=self.RealDictCursor)

    def init_db(self) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            );
        """)
        cursor.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()["count"]
        if count == 0:
            cursor.execute("""
                INSERT INTO tasks (title, done) VALUES
                ('Buy groceries', FALSE),
                ('Read a book', TRUE),
                ('Complete assignment', FALSE);
            """)
        conn.commit()
        cursor.close()
        conn.close()

    def get_all(self, done: Optional[bool] = None, search: Optional[str] = None, sort: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        query = "SELECT id, title, done FROM tasks WHERE 1=1"
        params = []

        if done is not None:
            query += " AND done = %s"
            params.append(done)

        if search:
            query += " AND title ILIKE %s"
            params.append(f"%{search}%")

        if sort == "title":
            query += " ORDER BY title ASC"
        elif sort == "-title":
            query += " ORDER BY title DESC"
        else:
            query += " ORDER BY id ASC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

    def create(self, title: str) -> Dict[str, Any]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
            (title, False)
        )
        new_row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return {"id": new_row["id"], "title": new_row["title"], "done": bool(new_row["done"])}

    def update(self, task_id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            return None

        new_title = title if title is not None else existing["title"]
        new_done = done if done is not None else existing["done"]

        cursor.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
            (new_title, new_done, task_id)
        )
        updated_row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return {"id": updated_row["id"], "title": updated_row["title"], "done": bool(updated_row["done"])}

    def delete(self, task_id: int) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return False
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def get_stats(self) -> Dict[str, int]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM tasks")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS done FROM tasks WHERE done = TRUE")
        done_count = cursor.fetchone()["done"]
        cursor.execute("SELECT COUNT(*) AS open FROM tasks WHERE done = FALSE")
        open_count = cursor.fetchone()["open"]
        cursor.close()
        conn.close()
        return {"total": total, "done": done_count, "open": open_count}


class SqliteTaskRepository(TaskRepository):
    """SQLite Task Repository using sqlite3 with parameterized queries."""

    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self.init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [("Buy groceries", 0), ("Read a book", 1), ("Complete assignment", 0)]
            )
        conn.commit()
        conn.close()

    def get_all(self, done: Optional[bool] = None, search: Optional[str] = None, sort: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        query = "SELECT id, title, done FROM tasks WHERE 1=1"
        params = []
        if done is not None:
            query += " AND done = ?"
            params.append(1 if done else 0)
        if search:
            query += " AND title LIKE ?"
            params.append(f"%{search}%")
        if sort == "title":
            query += " ORDER BY title ASC"
        elif sort == "-title":
            query += " ORDER BY title DESC"
        else:
            query += " ORDER BY id ASC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

    def create(self, title: str) -> Dict[str, Any]:
        conn = self._get_conn()
        cursor = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, 0))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"id": new_id, "title": title, "done": False}

    def update(self, task_id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            conn.close()
            return None
        current_title = title if title is not None else row["title"]
        current_done = int(done) if done is not None else row["done"]
        conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (current_title, current_done, task_id))
        conn.commit()
        conn.close()
        return {"id": task_id, "title": current_title, "done": bool(current_done)}

    def delete(self, task_id: int) -> bool:
        conn = self._get_conn()
        row = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            conn.close()
            return False
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True

    def get_stats(self) -> Dict[str, int]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        open_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0]
        conn.close()
        return {"total": total, "done": done_count, "open": open_count}


def get_repository() -> TaskRepository:
    """Factory function providing the appropriate database repository."""
    url = os.getenv("DATABASE_URL", "sqlite:///tasks.db")
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        try:
            return PostgresTaskRepository(url)
        except Exception:
            # Fallback gracefully to SQLite if PostgreSQL service is offline
            return SqliteTaskRepository()
    return SqliteTaskRepository()


def ping_redis() -> Dict[str, Any]:
    """Optional stretch feature: Ping Redis cache instance."""
    try:
        import redis
        r = redis.from_url(REDIS_URL, socket_connect_timeout=1)
        r.ping()
        return {"status": "connected", "redis_url": REDIS_URL}
    except Exception as e:
        return {"status": "unavailable", "detail": str(e)}
