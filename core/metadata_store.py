"""
core/metadata_store.py
SQLite-based project and analysis run management.
Plain Python — no Qt dependency.
"""

import sqlite3
import json
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app_data.db")


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db(db_path: str = None):
    """Create tables on first run. Safe to call multiple times."""
    global DB_PATH
    path = db_path or DB_PATH
    DB_PATH = path

    con = sqlite3.connect(path)
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            save_location   TEXT DEFAULT '',
            dataset_path    TEXT DEFAULT '',
            column_map      TEXT DEFAULT '{}',
            params          TEXT DEFAULT '{}',
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analysis_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      INTEGER NOT NULL REFERENCES projects(id),
            descriptor_name TEXT NOT NULL,
            params_json     TEXT DEFAULT '{}',
            result_path     TEXT DEFAULT '',
            created_at      TEXT NOT NULL
        );
    """)

    con.commit()
    con.close()


def save_project(name: str, description: str = "", save_location: str = "") -> int:
    """Insert a new project. Returns the new project ID."""
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO projects (name, description, save_location, created_at) VALUES (?, ?, ?, ?)",
        (name, description, save_location, datetime.now().isoformat())
    )
    project_id = cur.lastrowid
    con.commit()
    con.close()
    return project_id


def update_project_dataset(project_id: int, dataset_path: str, column_map: dict, params: dict):
    """Update a project with dataset path, column map and params after import/mapping."""
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "UPDATE projects SET dataset_path=?, column_map=?, params=? WHERE id=?",
        (dataset_path, json.dumps(column_map), json.dumps(params), project_id)
    )
    con.commit()
    con.close()


def get_recent_projects(n: int = 10) -> list:
    """Return list of recent projects, most recent first."""
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, name, description, save_location, dataset_path, created_at "
        "FROM projects ORDER BY created_at DESC LIMIT ?",
        (n,)
    )
    rows = cur.fetchall()
    con.close()

    return [
        {
            "id":           row[0],
            "name":         row[1],
            "description":  row[2],
            "save_location": row[3],
            "dataset_path": row[4],
            "created_at":   row[5],
        }
        for row in rows
    ]


def get_project_count() -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM projects")
    count = cur.fetchone()[0]
    con.close()
    return count


def save_analysis_run(project_id: int, descriptor_name: str, params: dict, result_path: str = "") -> int:
    """Log an analysis run. Returns the run ID."""
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO analysis_runs (project_id, descriptor_name, params_json, result_path, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, descriptor_name, json.dumps(params), result_path, datetime.now().isoformat())
    )
    run_id = cur.lastrowid
    con.commit()
    con.close()
    return run_id


def get_analysis_runs(project_id: int) -> list:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, descriptor_name, params_json, result_path, created_at "
        "FROM analysis_runs WHERE project_id=? ORDER BY created_at DESC",
        (project_id,)
    )
    rows = cur.fetchall()
    con.close()
    return [
        {
            "id": row[0],
            "descriptor_name": row[1],
            "params": json.loads(row[2]),
            "result_path": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]
