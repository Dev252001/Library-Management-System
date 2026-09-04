"""
models/database.py
------------------
Owns the SQLite connection and the full schema definition.

Design choice: we use sqlite3 directly (no ORM) so that every query in this
project is readable plain SQL.  This makes it easy to explain each operation
to a reviewer without needing to trace through ORM magic.

The module exposes two public symbols:
  - get_db()   : returns a per-request connection with row_factory set so
                 that rows behave like dicts (row["column"] syntax).
  - init_db()  : called once at startup to CREATE TABLE IF NOT EXISTS for
                 every entity.  Safe to call on every restart.
"""

import sqlite3
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Store the database file next to this package, one level up (project root).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "library.db")


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """
    Open (or reuse) a SQLite connection to library.db and return it.

    Why row_factory = sqlite3.Row?
    sqlite3.Row makes every result row accessible by column name
    (e.g. row["title"]) instead of only by index (row[0]).  This removes a
    whole class of silent bugs where column order matters.

    Why not store the connection globally?
    SQLite connections are not thread-safe.  Flask can serve requests on
    multiple threads, so each call to get_db() returns a fresh connection.
    For a single-user local tool the overhead is negligible.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # dict-like access by column name
    conn.execute("PRAGMA foreign_keys = ON")  # enforce FK constraints
    return conn


# ---------------------------------------------------------------------------
# Schema (DDL)
# ---------------------------------------------------------------------------

SCHEMA = """
-- ------------------------------------------------------------
-- Books catalogue
-- total_copies   : physical copies owned by the library
-- available_copies: copies currently on the shelf (not issued)
-- The CHECK constraint prevents available from going negative
-- or exceeding total — a safeguard against application bugs.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS book (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    author           TEXT    NOT NULL,
    isbn             TEXT    UNIQUE,
    category         TEXT,
    total_copies     INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 1
                     CHECK(available_copies >= 0
                           AND available_copies <= total_copies)
);

-- ------------------------------------------------------------
-- Student membership
-- fee_tier: 'subsidized' | 'standard'
--   subsidized  — the library charges a reduced membership fee
--   standard    — full-rate membership
-- Both tiers share the same overdue-fine schedule (₹2/day).
-- joining_date is stored as TEXT in ISO-8601 format (YYYY-MM-DD)
-- so SQLite's date functions work on it without extra conversion.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    contact      TEXT,
    joining_date TEXT    NOT NULL DEFAULT (date('now')),
    fee_tier     TEXT    NOT NULL DEFAULT 'subsidized'
                 CHECK(fee_tier IN ('subsidized', 'standard'))
);

-- ------------------------------------------------------------
-- Borrow / return transactions
-- issue_date, due_date, return_date: TEXT ISO-8601 (YYYY-MM-DD)
-- due_date is always issue_date + 14 days (set in application layer)
-- status:
--   'issued'   — book is currently with the student
--   'returned' — book has been brought back
--   'overdue'  — issued but past due_date (updated by a nightly scan
--                or on-demand when any dashboard/profile page loads)
-- fine_amount: computed in Python, stored for display without re-calc
-- FOREIGN KEY constraints ensure no orphan transactions exist.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS borrow_transaction (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id      INTEGER NOT NULL REFERENCES book(id),
    student_id   INTEGER NOT NULL REFERENCES student(id),
    issue_date   TEXT    NOT NULL DEFAULT (date('now')),
    due_date     TEXT    NOT NULL,
    return_date  TEXT,
    status       TEXT    NOT NULL DEFAULT 'issued'
                 CHECK(status IN ('issued', 'returned', 'overdue')),
    fine_amount  REAL    NOT NULL DEFAULT 0.0
);
"""


# ---------------------------------------------------------------------------
# Initialiser
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Execute the schema DDL to create all tables.

    Uses CREATE TABLE IF NOT EXISTS, so calling this on an already-populated
    database is completely safe — existing data is never touched.
    Called once from app.py before the development server starts.
    """
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        print(f"[init_db] Database ready at: {DB_PATH}")
    finally:
        conn.close()
