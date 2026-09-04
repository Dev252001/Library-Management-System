"""
models/student.py
-----------------
All database operations that concern the 'student' table.

Students are the membership holders.  This module intentionally has no
knowledge of transactions or fines — that coupling lives in transaction.py
so changes to fine logic never require edits here.
"""

from models.database import get_db


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_all_students() -> list:
    """
    Return every student row ordered alphabetically by name.

    Used by dropdowns in the issue/return forms so staff can quickly locate
    a student without knowing their numeric ID.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM student ORDER BY name"
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_student_by_id(student_id: int):
    """
    Return a single student row by primary key, or None if not found.

    Returning None (instead of raising) lets the route layer decide whether
    this is a 404 or an inline form error — the model should not know about
    HTTP status codes.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM student WHERE id = ?", (student_id,)
        ).fetchone()
        return row
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def add_student(name: str, contact: str,
                joining_date: str, fee_tier: str) -> int:
    """
    Insert a new student record and return the new primary key.

    joining_date must be passed as an ISO-8601 string (YYYY-MM-DD).
    The CHECK constraint on fee_tier in the schema will raise an
    IntegrityError if an invalid tier string is supplied — this is caught
    and re-raised with a friendlier message in the route layer.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO student (name, contact, joining_date, fee_tier)
            VALUES (?, ?, ?, ?)
            """,
            (name, contact, joining_date, fee_tier)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
