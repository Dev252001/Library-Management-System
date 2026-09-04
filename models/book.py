from models.database import get_db


def get_all_books():
    # grab everything, sorted by title so the list is predictable
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM book ORDER BY title").fetchall()
    finally:
        conn.close()


def get_book_by_id(book_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM book WHERE id = ?", (book_id,)
        ).fetchone()  # returns None if not found, caller handles that
    finally:
        conn.close()


def search_books(query="", category=""):
    # builds the WHERE clause dynamically so we don't add a category filter
    # when the user didn't ask for one
    conn = get_db()
    try:
        sql    = "SELECT * FROM book WHERE (title LIKE ? OR author LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY title"
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def get_all_categories():
    # used to populate the filter dropdown — only shows categories that exist
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT category FROM book "
            "WHERE category IS NOT NULL ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]
    finally:
        conn.close()


def add_book(title, author, isbn, category, total_copies):
    # available_copies starts equal to total_copies — nothing is issued yet
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


def decrement_available(book_id, conn):
    # takes an external conn so this update and the transaction insert
    # happen inside the same atomic commit (called from transaction.py)
    conn.execute(
        "UPDATE book SET available_copies = available_copies - 1 WHERE id = ?",
        (book_id,)
    )


def increment_available(book_id, conn):
    # same shared-connection pattern as above, used when a book is returned
    conn.execute(
        "UPDATE book SET available_copies = available_copies + 1 WHERE id = ?",
        (book_id,)
    )
