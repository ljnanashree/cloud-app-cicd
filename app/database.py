import os
import sqlite3
import logging
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("cloudpulse.database")

# Try importing psycopg2 for cloud PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not installed. Cloud PostgreSQL support disabled.")


class DatabaseManager:
    """
    Unified database manager providing transparent support for:
    1. Local / In-memory SQLite (development and automated testing)
    2. Cloud PostgreSQL (production deployment on Render, Neon, Supabase, etc.)
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or ""
        self.is_postgres = bool(
            self.database_url
            and (self.database_url.startswith("postgres://") or self.database_url.startswith("postgresql://"))
        )
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        logger.info(f"Initialized DatabaseManager: type={'PostgreSQL' if self.is_postgres else 'SQLite'}")

    def get_connection(self):
        """Get a raw connection to the configured database."""
        if self.is_postgres:
            if not PSYCOPG2_AVAILABLE:
                raise RuntimeError("psycopg2 is required for PostgreSQL connection but not installed.")
            # Normalize postgres:// to postgresql:// for compatibility
            url = self.database_url
            if url.startswith("postgres://"):
                url = "postgresql://" + url[len("postgres://"):]
            conn = psycopg2.connect(url)
            return conn
        else:
            # SQLite connection
            db_path = self.database_url.replace("sqlite:///", "") if self.database_url.startswith("sqlite:///") else self.database_url
            if not db_path:
                db_path = ":memory:"
            
            # For in-memory database, reuse connection so tables persist during test runs
            if db_path == ":memory:":
                if self._sqlite_conn is None:
                    self._sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
                    self._sqlite_conn.row_factory = sqlite3.Row
                return self._sqlite_conn

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def init_db(self):
        """Initialize database schema tables and indexes."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if self.is_postgres:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'Backlog',
                    priority VARCHAR(50) DEFAULT 'Medium',
                    category VARCHAR(100) DEFAULT 'General',
                    due_date VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(100) NOT NULL,
                    details TEXT,
                    entity_type VARCHAR(50),
                    entity_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
            """)
        else:
            # SQLite schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'Backlog',
                    priority TEXT DEFAULT 'Medium',
                    category TEXT DEFAULT 'General',
                    due_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    entity_type TEXT,
                    entity_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);")

        conn.commit()
        if not (not self.is_postgres and self.database_url == "sqlite:///:memory:"):
            conn.close()
        logger.info("Database schema initialized successfully.")

    def query(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return rows as list of dictionaries."""
        params = params or ()
        conn = self.get_connection()
        try:
            if self.is_postgres:
                # Convert ? to %s for PostgreSQL
                pg_sql = sql.replace("?", "%s")
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(pg_sql, params)
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]
            else:
                cur = conn.cursor()
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            if not (not self.is_postgres and self.database_url == "sqlite:///:memory:"):
                conn.close()

    def query_one(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return a single row as a dictionary."""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> int:
        """Execute an INSERT, UPDATE, or DELETE query and return the last inserted ID or rowcount."""
        params = params or ()
        conn = self.get_connection()
        try:
            if self.is_postgres:
                pg_sql = sql.replace("?", "%s")
                is_insert = pg_sql.strip().upper().startswith("INSERT")
                
                with conn.cursor() as cur:
                    if is_insert and "RETURNING" not in pg_sql.upper():
                        pg_sql += " RETURNING id"
                        cur.execute(pg_sql, params)
                        inserted_id = cur.fetchone()[0]
                        conn.commit()
                        return inserted_id
                    else:
                        cur.execute(pg_sql, params)
                        rowcount = cur.rowcount
                        conn.commit()
                        return rowcount
            else:
                cur = conn.cursor()
                cur.execute(sql, params)
                conn.commit()
                return cur.lastrowid if cur.lastrowid else cur.rowcount
        finally:
            if not (not self.is_postgres and self.database_url == "sqlite:///:memory:"):
                conn.close()

    def health_check(self) -> Tuple[bool, float, str]:
        """
        Check database connectivity and query latency.
        Returns: (is_healthy, latency_ms, db_type_label)
        """
        import time
        start_time = time.time()
        try:
            res = self.query_one("SELECT 1 as ping")
            latency_ms = round((time.time() - start_time) * 1000, 2)
            db_label = "PostgreSQL" if self.is_postgres else "SQLite"
            return (res is not None and res.get("ping") == 1, latency_ms, db_label)
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            db_label = "PostgreSQL" if self.is_postgres else "SQLite"
            logger.error(f"Database health check failed: {e}")
            return (False, latency_ms, db_label)
