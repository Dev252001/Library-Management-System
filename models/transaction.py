import sqlite3
from datetime import date, timedelta

from models.database import get_db
from models.book import decrement_available, increment_available

# changing any of these three numbers is all you need to adjust the fine policy
LOAN_DAYS    = 14    # days before a book is overdue
FINE_PER_DAY = 2.0   # rupees per overdue day
FINE_CAP     = 50.0  # max fine — we don't want it to become a real debt


def calculate_fine(due_date_str, return_date_str=None):
    # if return_date is not given, use today — so the dashboard shows a live number
    due  = date.fromisoformat(due_date_str)
    end  = date.fromisoformat(return_date_str) if return_date_str else date.today()
    days = (end - due).days

    if days <= 0:
        return 0.0

    return min(days * FINE_PER_DAY, FINE_CAP)


def issue_book(book_id, student_id):
    # returns a dict so the route can show a proper message instead of crashing
    conn = get_db()
    try:
        book = conn.execute(
            "SELECT * FROM book WHERE id = ?", (book_id,)
        ).fetchone()

        if book is None:
            return {"success": False, "error": f"Book ID {book_id} not found."}

        if book["available_copies"] <= 0:
            return {"success": False,
                    "error": f"'{book['title']}' has no copies available right now."}

        # make sure this student doesn't already have this book out
        already_out = conn.execute(
            "SELECT id FROM borrow_transaction "
            "WHERE book_id = ? AND student_id = ? AND status IN ('issued', 'overdue')",
            (book_id, student_id)
        ).fetchone()

        if already_out:
            return {"success": False,
                    "error": "This student already has an unreturned copy of that book."}

        today    = date.today()
        due_date = today + timedelta(days=LOAN_DAYS)

        # insert the transaction and decrement copies in the same connection
        # so both writes are committed together or not at all
        cur = conn.execute(
            """
            INSERT INTO borrow_transaction
                (book_id, student_id, issue_date, due_date, status, fine_amount)
            VALUES (?, ?, ?, ?, 'issued', 0.0)
            """,
            (book_id, student_id, today.isoformat(), due_date.isoformat())
        )
        txn_id = cur.lastrowid
        decrement_available(book_id, conn)
        conn.commit()

        return {"success": True, "transaction_id": txn_id}

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return {"success": False, "error": f"DB error: {e}"}
    finally:
        conn.close()


def return_book(transaction_id):
    conn = get_db()
    try:
        txn = conn.execute(
            "SELECT * FROM borrow_transaction WHERE id = ?", (transaction_id,)
        ).fetchone()

        if txn is None:
            return {"success": False,
                    "error": f"Transaction ID {transaction_id} not found."}

        if txn["status"] == "returned":
            return {"success": False,
                    "error": "This book has already been marked as returned."}

        today = date.today()
        fine  = calculate_fine(txn["due_date"], today.isoformat())

        conn.execute(
            """
            UPDATE borrow_transaction
            SET status = 'returned', return_date = ?, fine_amount = ?
            WHERE id = ?
            """,
            (today.isoformat(), fine, transaction_id)
        )
        increment_available(txn["book_id"], conn)
        conn.commit()

        return {"success": True, "fine": fine}

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return {"success": False, "error": f"DB error: {e}"}
    finally:
        conn.close()


def refresh_overdue_status():
    # I call this on every page load instead of running a cron job —
    # it's fast enough for 40 students and keeps everything in one process
    today = date.today().isoformat()
    conn  = get_db()
    try:
        rows = conn.execute(
            "SELECT id, due_date FROM borrow_transaction "
            "WHERE status = 'issued' AND due_date < ?",
            (today,)
        ).fetchall()

        count = 0
        for row in rows:
            fine = calculate_fine(row["due_date"])
            conn.execute(
                "UPDATE borrow_transaction SET status = 'overdue', fine_amount = ? "
                "WHERE id = ?",
                (fine, row["id"])
            )
            count += 1

        conn.commit()
        return count
    finally:
        conn.close()


def get_transactions_for_student(student_id):
    # LEFT JOIN so even if a book was somehow deleted the row still shows up
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT t.*, b.title AS book_title, b.author AS book_author
            FROM borrow_transaction t
            LEFT JOIN book b ON b.id = t.book_id
            WHERE t.student_id = ?
            ORDER BY t.issue_date DESC
            """,
            (student_id,)
        ).fetchall()
    finally:
        conn.close()


def get_dashboard_stats():
    conn = get_db()
    try:
        books = conn.execute(
            "SELECT SUM(total_copies) AS total, SUM(available_copies) AS available "
            "FROM book"
        ).fetchone()

        txns = conn.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'issued'  THEN 1 ELSE 0 END) AS issued_count,
                SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) AS overdue_count,
                SUM(CASE WHEN status != 'returned' THEN fine_amount ELSE 0 END) AS total_fines
            FROM borrow_transaction
            """
        ).fetchone()

        return {
            "total_books"    : books["total"]          or 0,
            "available_books": books["available"]       or 0,
            "issued_count"   : txns["issued_count"]     or 0,
            "overdue_count"  : txns["overdue_count"]    or 0,
            "total_fines"    : txns["total_fines"]      or 0.0,
        }
    finally:
        conn.close()


def get_top_borrowed_books(limit=5):
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT b.title, b.author, COUNT(t.id) AS borrow_count
            FROM borrow_transaction t
            JOIN book b ON b.id = t.book_id
            GROUP BY t.book_id
            ORDER BY borrow_count DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
    finally:
        conn.close()


def get_monthly_borrow_volume():
    # strftime pulls YYYY-MM out of the stored ISO date string
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT strftime('%Y-%m', issue_date) AS month, COUNT(*) AS borrow_count
            FROM borrow_transaction
            GROUP BY month
            ORDER BY month
            """
        ).fetchall()
    finally:
        conn.close()
