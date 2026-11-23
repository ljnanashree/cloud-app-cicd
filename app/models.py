from datetime import datetime
from typing import Any, Dict, List, Optional
from app.database import DatabaseManager

VALID_STATUSES = ["Backlog", "In Progress", "Review", "Completed"]
VALID_PRIORITIES = ["Low", "Medium", "High", "Urgent"]


class TaskModel:
    """Task model handling all CRUD and querying logic."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def validate(self, data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """Validate input payload."""
        errors = []
        if not is_update or "title" in data:
            title = data.get("title")
            if not title or not str(title).strip():
                errors.append("Title is required and cannot be empty.")
            elif len(str(title)) > 200:
                errors.append("Title cannot exceed 200 characters.")

        if "status" in data and data["status"] not in VALID_STATUSES:
            errors.append(f"Invalid status. Allowed values: {', '.join(VALID_STATUSES)}")

        if "priority" in data and data["priority"] not in VALID_PRIORITIES:
            errors.append(f"Invalid priority. Allowed values: {', '.join(VALID_PRIORITIES)}")

        return errors

    def create(self, title: str, description: str = "", status: str = "Backlog",
               priority: str = "Medium", category: str = "General",
               due_date: Optional[str] = None) -> Dict[str, Any]:
        """Create a new task and log the action."""
        status = status if status in VALID_STATUSES else "Backlog"
        priority = priority if priority in VALID_PRIORITIES else "Medium"
        category = category.strip() if category else "General"
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        sql = """
            INSERT INTO tasks (title, description, status, priority, category, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        task_id = self.db.execute(sql, (
            title.strip(),
            description.strip(),
            status,
            priority,
            category,
            due_date or "",
            now_str,
            now_str
        ))

        # Log activity
        self.log_activity("create_task", f"Created task #{task_id}: {title.strip()}", "task", task_id)

        return self.get_by_id(task_id)

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single task by ID."""
        sql = "SELECT * FROM tasks WHERE id = ?"
        row = self.db.query_one(sql, (task_id,))
        if not row:
            return None
        return self._format_task(row)

    def get_all(self, status: Optional[str] = None, priority: Optional[str] = None,
                category: Optional[str] = None, search: Optional[str] = None,
                limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch tasks with filtering, search, and pagination."""
        clauses = []
        params = []

        if status:
            clauses.append("status = ?")
            params.append(status)
        if priority:
            clauses.append("priority = ?")
            params.append(priority)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if search:
            search_pattern = f"%{search.strip()}%"
            clauses.append("(title LIKE ? OR description LIKE ? OR category LIKE ?)")
            params.extend([search_pattern, search_pattern, search_pattern])

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM tasks {where_stmt} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.db.query(sql, tuple(params))
        return [self._format_task(r) for r in rows]

    def update(self, task_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update existing task fields."""
        existing = self.get_by_id(task_id)
        if not existing:
            return None

        allowed_fields = ["title", "description", "status", "priority", "category", "due_date"]
        set_clauses = []
        params = []

        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = ?")
                params.append(updates[field])

        if not set_clauses:
            return existing

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        set_clauses.append("updated_at = ?")
        params.append(now_str)

        params.append(task_id)
        sql = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"
        self.db.execute(sql, tuple(params))

        self.log_activity("update_task", f"Updated task #{task_id}", "task", task_id)
        return self.get_by_id(task_id)

    def delete(self, task_id: int) -> bool:
        """Delete task by ID."""
        existing = self.get_by_id(task_id)
        if not existing:
            return False

        sql = "DELETE FROM tasks WHERE id = ?"
        self.db.execute(sql, (task_id,))
        self.log_activity("delete_task", f"Deleted task #{task_id} ({existing['title']})", "task", task_id)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate task metrics and counts."""
        total_tasks = self.db.query_one("SELECT COUNT(*) as count FROM tasks")
        total = total_tasks["count"] if total_tasks else 0

        # Group by status
        status_rows = self.db.query("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
        status_counts = {s: 0 for s in VALID_STATUSES}
        for r in status_rows:
            if r["status"] in status_counts:
                status_counts[r["status"]] = r["count"]

        # Group by priority
        priority_rows = self.db.query("SELECT priority, COUNT(*) as count FROM tasks GROUP BY priority")
        priority_counts = {p: 0 for p in VALID_PRIORITIES}
        for r in priority_rows:
            if r["priority"] in priority_counts:
                priority_counts[r["priority"]] = r["count"]

        completed_count = status_counts.get("Completed", 0)
        completion_rate = round((completed_count / total * 100), 1) if total > 0 else 0.0

        return {
            "total_tasks": total,
            "completion_rate": completion_rate,
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
        }

    def log_activity(self, action: str, details: str, entity_type: str = "", entity_id: Optional[int] = None):
        """Record an audit trail activity log."""
        sql = """
            INSERT INTO activity_logs (action, details, entity_type, entity_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute(sql, (action, details, entity_type, entity_id, now_str))

    def get_recent_activity(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch latest activity logs."""
        sql = "SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ?"
        rows = self.db.query(sql, (limit,))
        return [dict(r) for r in rows]

    def _format_task(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Format database row for API consumption."""
        d = dict(row)
        for key in ["created_at", "updated_at"]:
            if key in d and d[key] and not isinstance(d[key], str):
                d[key] = str(d[key])
        return d
