"""
models/book.py
--------------
All database operations that concern the 'book' table.

Design choice: every function opens its own connection and closes it in a
finally block.  This is intentional for a single-user local tool — it keeps
each function self-contained and avoids leaked connections if a caller forgets
to close.  In a multi-user production app you would use a connection pool
instead.
"""

from models.database import get_db


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_all_books() -> list:
    """
    Return every book in the catalogue as a list of sqlite3.Row objects.

    Why ORDER BY title?
    Predictable ordering makes the UI consistent across restarts and makes
    test assertions reliable.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM book ORDER BY title"
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_book_by_id(book_id: int):
    """
    Return a single book row by primary key, or None if not found.

    Why return None instead of raising?
    The caller (a route) needs to decide whether to show a 404 page or an
    error message.  Returning None keeps that decision in the route layer
    where HTTP context lives.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM book WHERE id = ?", (book_id,)
        ).fetchone()
        return row  # None if no match
    finally:
        conn.close()


def search_books(query: str = "", category: str = "") -> list:
    """
    Return books whose title or author contains 'query' (case-insensitive)
    and, optionally, whose category matches exactly.

    Why LIKE with % wildcards?
    LIKE in SQLite is case-insensitive for ASCII characters, which covers
    every realistic book title in this context.  A full-text index would be
    overkill for a 40-student library.

    Why build the WHERE clause dynamically?
    We want to avoid sending 'AND category LIKE %%' when no category filter
    is supplied — that would still work but is misleading SQL.
    """
    conn = get_db()
    try:
        sql = "SELECT * FROM book WHERE (title LIKE ? OR author LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY title"
        rows = conn.execute(sql, params).fetchall()
        return rows
    finally:
        conn.close()


def get_all_categories() -> list:
    """
    Return a sorted list of distinct category strings present in the catalogue.

    Used to populate the filter dropdown on the books page so the user only
    sees categories that actually exist in the data.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT category FROM book "
            "WHERE category IS NOT NULL ORDER BY category"
        ).fetchall()
        return [row["category"] for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def add_book(title: str, author: str, isbn: str,
             category: str, total_copies: int) -> int:
    """
    Insert a new book into the catalogue and return its new primary key.

    available_copies is set equal to total_copies on creation because a newly
    catalogued book has not been issued to anyone yet.

    Returns the lastrowid so the caller can redirect to the new book's detail
    page if needed.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO book (title, author, isbn, category,
                              total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, author, isbn, category, total_copies, total_copies)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def decrement_available(book_id: int, conn) -> None:
    """
    Reduce available_copies by 1 for the given book.

    Why does this accept an external 'conn' instead of opening its own?
    Because issuing a book involves TWO writes that must succeed or fail
    together: decrement the book AND insert the transaction row.  The caller
    (transaction.py) passes its own connection so both writes share one
    database transaction (committed or rolled back atomically).

    The CHECK constraint on available_copies (>= 0) acts as a last-resort
    guard: if application logic somehow calls this when copies == 0, SQLite
    will raise an IntegrityError rather than silently storing -1.
    """
    conn.execute(
        "UPDATE book SET available_copies = available_copies - 1 "
        "WHERE id = ?",
        (book_id,)
    )


def increment_available(book_id: int, conn) -> None:
    """
    Increase available_copies by 1 when a book is returned.

    Same shared-connection pattern as decrement_available: the caller
    (transaction.py's return_book function) owns the transaction boundary.

    The CHECK constraint (available_copies <= total_copies) prevents a bug
    where a duplicate return call would push available above total.
    """
    conn.execute(
        "UPDATE book SET available_copies = available_copies + 1 "
        "WHERE id = ?",
        (book_id,)
    )
