from app.database import DatabaseManager


def test_sqlite_in_memory_crud():
    """Test raw SQLite DatabaseManager in-memory CRUD operations."""
    db = DatabaseManager(database_url="sqlite:///:memory:")
    db.init_db()

    # Health check
    healthy, latency, db_type = db.health_check()
    assert healthy is True
    assert db_type == "SQLite"
    assert latency >= 0.0

    # Insert
    insert_id = db.execute(
        "INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)",
        ("DB Test Task", "Testing raw execution", "Backlog")
    )
    assert insert_id is not None
    assert insert_id > 0

    # Query one
    row = db.query_one("SELECT * FROM tasks WHERE id = ?", (insert_id,))
    assert row is not None
    assert row["title"] == "DB Test Task"
    assert row["status"] == "Backlog"

    # Update
    rowcount = db.execute("UPDATE tasks SET status = ? WHERE id = ?", ("Completed", insert_id))
    assert rowcount is not None

    # Query all
    rows = db.query("SELECT * FROM tasks WHERE status = ?", ("Completed",))
    assert len(rows) == 1
    assert rows[0]["id"] == insert_id

    # Delete
    del_count = db.execute("DELETE FROM tasks WHERE id = ?", (insert_id,))
    assert del_count == 1
    assert db.query_one("SELECT * FROM tasks WHERE id = ?", (insert_id,)) is None
