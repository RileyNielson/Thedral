import sqlite3
import os
from pathlib import Path
from backend.config import DB_PATH

def get_db(custom_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Creates and configures an authoritative SQLite connection.
    - Enables WAL mode for high-concurrency read/write operations.
    - Enforces foreign key constraint checks.
    - Sets busy timeout to prevent database locked exceptions.
    - Configures row_factory for dictionary-like column access.
    """
    target_path = str(custom_path) if custom_path else str(DB_PATH)
    
    conn = sqlite3.connect(target_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # Authoritative performance and integrity pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    
    return conn
