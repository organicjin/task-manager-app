import sqlite3
from datetime import datetime, date
from typing import Optional
from models import Task, Project

DB_PATH = "tasks.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT '업무',
            priority TEXT DEFAULT '중간',
            urgency TEXT DEFAULT '보통',
            quadrant INTEGER DEFAULT 4,
            project_id INTEGER,
            due_date DATE,
            status TEXT DEFAULT '진행전',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        );
    """)
    conn.commit()
    conn.close()


# --- Project CRUD ---

def add_project(name: str, description: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def get_projects() -> list[Project]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [
        Project(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def delete_project(project_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


# --- Task CRUD ---

def _row_to_task(r) -> Task:
    due = None
    if r["due_date"]:
        due = date.fromisoformat(r["due_date"]) if isinstance(r["due_date"], str) else r["due_date"]
    return Task(
        id=r["id"],
        title=r["title"],
        description=r["description"],
        category=r["category"],
        priority=r["priority"],
        urgency=r["urgency"],
        quadrant=r["quadrant"],
        project_id=r["project_id"],
        due_date=due,
        status=r["status"],
        created_at=r["created_at"],
    )


def add_task(task: Task) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO tasks (title, description, category, priority, urgency,
           quadrant, project_id, due_date, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task.title,
            task.description,
            task.category,
            task.priority,
            task.urgency,
            task.quadrant,
            task.project_id,
            task.due_date.isoformat() if task.due_date else None,
            task.status,
        ),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_tasks(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    order_by: str = "due_date",
) -> list[Task]:
    conn = get_conn()
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []

    if category and category != "전체":
        query += " AND category = ?"
        params.append(category)
    if project_id is not None:
        query += " AND project_id = ?"
        params.append(project_id)
    if status and status != "전체":
        query += " AND status = ?"
        params.append(status)

    if order_by == "due_date":
        query += " ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC"
    elif order_by == "priority":
        query += " ORDER BY CASE priority WHEN '높음' THEN 1 WHEN '중간' THEN 2 WHEN '낮음' THEN 3 END"
    elif order_by == "quadrant":
        query += " ORDER BY quadrant ASC"
    else:
        query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row_to_task(r) for r in rows]


def get_task(task_id: int) -> Optional[Task]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return _row_to_task(row) if row else None


def update_task(task: Task):
    conn = get_conn()
    conn.execute(
        """UPDATE tasks SET title=?, description=?, category=?, priority=?,
           urgency=?, quadrant=?, project_id=?, due_date=?, status=?
           WHERE id=?""",
        (
            task.title,
            task.description,
            task.category,
            task.priority,
            task.urgency,
            task.quadrant,
            task.project_id,
            task.due_date.isoformat() if task.due_date else None,
            task.status,
            task.id,
        ),
    )
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def get_project_progress(project_id: int) -> dict:
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as c FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()["c"]
    done = conn.execute(
        "SELECT COUNT(*) as c FROM tasks WHERE project_id = ? AND status = '완료'",
        (project_id,),
    ).fetchone()["c"]
    conn.close()
    return {"total": total, "done": done, "ratio": done / total if total > 0 else 0}
