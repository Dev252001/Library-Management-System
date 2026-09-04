from models.database import get_db


def get_all_students():
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM student ORDER BY name").fetchall()
    finally:
        conn.close()


def get_student_by_id(student_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM student WHERE id = ?", (student_id,)
        ).fetchone()
    finally:
        conn.close()


def add_student(name, contact, joining_date, fee_tier):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO student (name, contact, joining_date, fee_tier) "
            "VALUES (?, ?, ?, ?)",
            (name, contact, joining_date, fee_tier)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
