"""
routes/transactions.py
----------------------
Blueprint for issuing and returning books.

Routes:
  GET  /transactions/issue         — render the issue-book form
  POST /transactions/issue         — process the issue request
  GET  /transactions/return        — render the return-book form
  POST /transactions/return        — process the return request

Both forms live on the same template (issue_return.html) to keep the UI
compact — a single page the librarian uses all day.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models.book    import get_all_books
from models.student import get_all_students
from models.transaction import issue_book, return_book, refresh_overdue_status

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


@transactions_bp.route("/issue", methods=["GET", "POST"])
def issue():
    """
    GET  — render the issue form pre-populated with all books and students.
    POST — attempt to issue the selected book to the selected student.

    On success: flash a confirmation with the due date and redirect back.
    On failure: flash the error message from the model and re-render the form
                so the librarian can correct the selection without losing context.

    Why reload books/students on every GET?
    The lists change (new additions, returns) and we never want to serve
    stale dropdown data from a cached object.
    """
    if request.method == "POST":
        # --- parse and coerce form values ---
        book_id_raw    = request.form.get("book_id", "").strip()
        student_id_raw = request.form.get("student_id", "").strip()

        if not book_id_raw or not student_id_raw:
            flash("Please select both a book and a student.", "error")
            return redirect(url_for("transactions.issue"))

        try:
            book_id    = int(book_id_raw)
            student_id = int(student_id_raw)
        except ValueError:
            flash("Invalid book or student selection.", "error")
            return redirect(url_for("transactions.issue"))

        result = issue_book(book_id, student_id)

        if result["success"]:
            flash(
                f"Book issued successfully! "
                f"Transaction #{result['transaction_id']} — "
                f"due in 14 days.",
                "success"
            )
            return redirect(url_for("dashboard.index"))
        else:
            flash(result["error"], "error")
            return redirect(url_for("transactions.issue"))

    # GET — render form
    refresh_overdue_status()   # ensure available counts reflect reality
    books    = get_all_books()
    students = get_all_students()
    return render_template("issue_return.html",
                           books=books,
                           students=students,
                           active_tab="issue")


@transactions_bp.route("/return", methods=["GET", "POST"])
def return_book_view():
    """
    GET  — render the return form.
    POST — attempt to mark the transaction as returned.

    The librarian enters the numeric Transaction ID (printed on the
    issue slip or looked up from a student's profile page).

    On success: flash the fine amount (₹0 if returned on time).
    On failure: flash the specific error (already returned, ID not found).
    """
    if request.method == "POST":
        txn_id_raw = request.form.get("transaction_id", "").strip()

        if not txn_id_raw:
            flash("Please enter a Transaction ID.", "error")
            return redirect(url_for("transactions.return_book_view"))

        try:
            txn_id = int(txn_id_raw)
        except ValueError:
            flash("Transaction ID must be a number.", "error")
            return redirect(url_for("transactions.return_book_view"))

        result = return_book(txn_id)

        if result["success"]:
            fine = result["fine"]
            if fine > 0:
                flash(
                    f"Book returned. Overdue fine: ₹{fine:.2f} — "
                    f"please collect from student.",
                    "warning"
                )
            else:
                flash("Book returned on time. No fine due.", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash(result["error"], "error")
            return redirect(url_for("transactions.return_book_view"))

    # GET — render form
    return render_template("issue_return.html",
                           books=[],
                           students=[],
                           active_tab="return")
