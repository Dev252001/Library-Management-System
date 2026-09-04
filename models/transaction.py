"""
models/transaction.py
---------------------
All business logic for borrowing and returning books.

This is the most important file in the project.  It enforces:
  1. Availability check   — can't issue what isn't on the shelf
  2. Duplicate-issue check — can't issue the same book twice to one student
  3. Due-date calculation — always 14 days from today
  4. Overdue detection    — compares today's date to due_date
  5. Fine calculation     — ₹2/day overdue, hard-capped at ₹50

All writes that touch more than one table (issue: book + transaction,
return: transaction + book) share a single connection so they are atomic.
"""

import sqlite3
from datetime import date, timedelta

from models.database import get_db
from models.book import decrement_available, increment_available


# ---------------------------------------------------------------------------
# Constants — defined once so a professor can ask "where is ₹2 configured?"
# ---------------------------------------------------------------------------

LOAN_DAYS      = 14     # How long a student may keep a book
FINE_PER_DAY   = 2.0    # Rupees charged per overdue day
FINE_CAP       = 50.0   # Maximum fine regardless of how late the return is


# ---------------------------------------------------------------------------
# Helper: fine calculation
# ---------------------------------------------------------------------------

def calculate_fine(due_date_str: str, return_date_str: str = None) -> float:
    """
    Compute the fine (in ₹) for a given due_date and an optional return_date.

    Rules:
      - If the book was returned on or before due_date → fine is 0.
      - Otherwise: fine = overdue_days × FINE_PER_DAY, capped at FINE_CAP.
      - If return_date is None (book not yet returned), today is used as the
        reference date so the fine shown on the dashboard is always current.

    Why cap at ₹50?
    The library serves subsidized students.  An uncapped fine would become
    punitive for students who are uncontactable for weeks.  The cap keeps
    the fine a deterrent, not a debt.

    Args:
        due_date_str  : ISO-8601 date string for when the book was due.
        return_date_str: ISO-8601 date string for when it was returned,
                         or None if not yet returned.

    Returns:
        float — the fine amount in rupees (0.0 if not overdue).
    """
    due    = date.fromisoformat(due_date_str)
    end    = date.fromisoformat(return_date_str) if return_date_str else date.today()
    days_overdue = (end - due).days

    if days_overdue <= 0:
        return 0.0

    raw_fine = days_overdue * FINE_PER_DAY
    return min(raw_fine, FINE_CAP)   # cap enforced here


# ---------------------------------------------------------------------------
# Issue a book
# ---------------------------------------------------------------------------

def issue_book(book_id: int, student_id: int) -> dict:
    """
    Attempt to issue a book to a student.  Returns a result dict:
        {"success": True,  "transaction_id": <int>}   on success
        {"success": False, "error": "<message>"}       on any failure

    Why return a dict instead of raising exceptions?
    Routes need to show user-friendly error messages in the UI, not a 500
    page.  A result dict lets the route check success and pass the error
    string directly to the template without a try/except wrapper.

    Steps (all within one connection = one atomic transaction):
      1. Fetch the book — error if not found.
      2. Check available_copies > 0 — error if 0.
      3. Check no existing 'issued' transaction for this (book, student) pair
         — error if duplicate.
      4. Insert the transaction row with due_date = today + LOAN_DAYS.
      5. Decrement available_copies.
      6. Commit.
    """
    conn = get_db()
    try:
        # -- Step 1: does the book exist? ------------------------------------
        book = conn.execute(
            "SELECT * FROM book WHERE id = ?", (book_id,)
        ).fetchone()
        if book is None:
            return {"success": False, "error": f"Book ID {book_id} not found."}

        # -- Step 2: is a copy available? ------------------------------------
        if book["available_copies"] <= 0:
            return {
                "success": False,
                "error": f"'{book['title']}' has no copies available right now."
            }

        # -- Step 3: duplicate-issue check -----------------------------------
        # A student should not be able to hold two copies of the same book
        # simultaneously (accidental double-scan at the desk).
        existing = conn.execute(
            """
            SELECT id FROM borrow_transaction
            WHERE book_id = ? AND student_id = ? AND status IN ('issued', 'overdue')
            """,
            (book_id, student_id)
        ).fetchone()
        if existing:
            return {
                "success": False,
                "error": "This student already has an unreturned copy of that book."
            }

        # -- Step 4: insert transaction row ----------------------------------
        today    = date.today()
        due_date = today + timedelta(days=LOAN_DAYS)

        cur = conn.execute(
            """
            INSERT INTO borrow_transaction
                (book_id, student_id, issue_date, due_date, status, fine_amount)
            VALUES (?, ?, ?, ?, 'issued', 0.0)
            """,
            (book_id, student_id,
             today.isoformat(), due_date.isoformat())
        )
        txn_id = cur.lastrowid

        # -- Step 5: decrement available copies (shares this connection) -----
        decrement_available(book_id, conn)

        # -- Step 6: commit both writes atomically ---------------------------
        conn.commit()
        return {"success": True, "transaction_id": txn_id}

    except sqlite3.IntegrityError as e:
        # FK violation or CHECK constraint breach — roll back implicitly
        conn.rollback()
        return {"success": False, "error": f"Database constraint error: {e}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Return a book
# ---------------------------------------------------------------------------

def return_book(transaction_id: int) -> dict:
    """
    Mark a transaction as returned, compute and store the final fine,
    and increment available_copies.  Returns a result dict:
        {"success": True,  "fine": <float>}   on success
        {"success": False, "error": "<str>"}  on failure

    Steps (atomic, single connection):
      1. Fetch the transaction — error if not found.
      2. Guard against double-return — error if status is already 'returned'.
      3. Compute final fine using today as the return date.
      4. Update transaction: status='returned', return_date=today, fine_amount.
      5. Increment available_copies on the book.
      6. Commit.
    """
    conn = get_db()
    try:
        # -- Step 1: fetch transaction ----------------------------------------
        txn = conn.execute(
            "SELECT * FROM borrow_transaction WHERE id = ?", (transaction_id,)
        ).fetchone()
        if txn is None:
            return {"success": False,
                    "error": f"Transaction ID {transaction_id} not found."}

        # -- Step 2: guard against duplicate return --------------------------
        if txn["status"] == "returned":
            return {"success": False,
                    "error": "This book has already been marked as returned."}

        # -- Step 3: compute fine --------------------------------------------
        today     = date.today()
        fine      = calculate_fine(txn["due_date"], today.isoformat())

        # -- Step 4: update the transaction row ------------------------------
        conn.execute(
            """
            UPDATE borrow_transaction
            SET status = 'returned',
                return_date = ?,
                fine_amount = ?
            WHERE id = ?
            """,
            (today.isoformat(), fine, transaction_id)
        )

        # -- Step 5: give the copy back to the shelf -------------------------
        increment_available(txn["book_id"], conn)

        # -- Step 6: commit both writes atomically ---------------------------
        conn.commit()
        return {"success": True, "fine": fine}

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return {"success": False, "error": f"Database constraint error: {e}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Overdue detection
# ---------------------------------------------------------------------------

def refresh_overdue_status() -> int:
    """
    Scan all 'issued' transactions whose due_date < today and flip their
    status to 'overdue'.  Also updates fine_amount to the current running
    total so the dashboard shows live numbers.

    Returns the count of rows updated (useful for logging).

    Why run this on every page load instead of a scheduled job?
    A scheduled job (cron, APScheduler) adds infrastructure complexity.
    For a 40-student local tool, running this scan on every request is
    imperceptibly fast and keeps the system self-contained with no daemons.
    """
    today = date.today().isoformat()
    conn  = get_db()
    try:
        # Fetch all still-issued transactions that are now past their due date
        overdue_rows = conn.execute(
            """
            SELECT id, due_date FROM borrow_transaction
            WHERE status = 'issued' AND due_date < ?
            """,
            (today,)
        ).fetchall()

        count = 0
        for row in overdue_rows:
            fine = calculate_fine(row["due_date"])   # return_date=None → uses today
            conn.execute(
                """
                UPDATE borrow_transaction
                SET status = 'overdue', fine_amount = ?
                WHERE id = ?
                """,
                (fine, row["id"])
            )
            count += 1

        conn.commit()
        return count
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Query helpers used by routes
# ---------------------------------------------------------------------------

def get_transactions_for_student(student_id: int) -> list:
    """
    Return all transactions for a student, newest first, joined with the
    book title for display on the student profile page.

    Why LEFT JOIN?
    Every transaction must have a book (FK constraint), so INNER JOIN would
    work too.  LEFT JOIN is used defensively in case data is ever imported
    manually with broken references — the row still shows, just with a NULL
    title instead of disappearing silently.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT t.*, b.title AS book_title, b.author AS book_author
            FROM borrow_transaction t
            LEFT JOIN book b ON b.id = t.book_id
            WHERE t.student_id = ?
            ORDER BY t.issue_date DESC
            """,
            (student_id,)
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_dashboard_stats() -> dict:
    """
    Return a single dict of KPI numbers for the dashboard:
        total_books      : sum of all total_copies
        available_books  : sum of all available_copies
        issued_count     : transactions with status 'issued'
        overdue_count    : transactions with status 'overdue'
        total_fines      : sum of fine_amount across all non-returned txns

    Why aggregate in SQL rather than Python?
    Aggregations in SQL are processed close to the data — faster and less
    memory-intensive than fetching all rows and looping in Python.
    """
    conn = get_db()
    try:
        books_row = conn.execute(
            "SELECT SUM(total_copies) AS total, "
            "       SUM(available_copies) AS available "
            "FROM book"
        ).fetchone()

        txn_row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'issued'   THEN 1 ELSE 0 END) AS issued_count,
                SUM(CASE WHEN status = 'overdue'  THEN 1 ELSE 0 END) AS overdue_count,
                SUM(CASE WHEN status != 'returned' THEN fine_amount ELSE 0 END)
                    AS total_fines
            FROM borrow_transaction
            """
        ).fetchone()

        return {
            "total_books"    : books_row["total"]     or 0,
            "available_books": books_row["available"] or 0,
            "issued_count"   : txn_row["issued_count"]  or 0,
            "overdue_count"  : txn_row["overdue_count"] or 0,
            "total_fines"    : txn_row["total_fines"]   or 0.0,
        }
    finally:
        conn.close()


def get_top_borrowed_books(limit: int = 5) -> list:
    """
    Return the top N most-borrowed books (by transaction count), with the
    book title and total borrow count.

    Used by the analytics page.  All statuses are counted — we want lifetime
    borrows, not just currently-issued copies.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT b.title, b.author,
                   COUNT(t.id) AS borrow_count
            FROM borrow_transaction t
            JOIN book b ON b.id = t.book_id
            GROUP BY t.book_id
            ORDER BY borrow_count DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_monthly_borrow_volume() -> list:
    """
    Return borrow counts grouped by year-month (YYYY-MM), ordered
    chronologically.  Used to plot the monthly volume bar chart.

    SQLite's strftime('%Y-%m', issue_date) extracts the year-month portion
    from the ISO-8601 date string stored in the column.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m', issue_date) AS month,
                   COUNT(*) AS borrow_count
            FROM borrow_transaction
            GROUP BY month
            ORDER BY month
            """
        ).fetchall()
        return rows
    finally:
        conn.close()
