from flask import Blueprint, render_template, request, redirect, url_for, flash

from models.book    import get_all_books
from models.student import get_all_students
from models.transaction import issue_book, return_book, refresh_overdue_status

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


@transactions_bp.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
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
                f"Book issued! Transaction #{result['transaction_id']} — due in 14 days.",
                "success"
            )
            return redirect(url_for("dashboard.index"))
        else:
            flash(result["error"], "error")
            return redirect(url_for("transactions.issue"))

    # refresh before loading the form so available counts are current
    refresh_overdue_status()
    books    = get_all_books()
    students = get_all_students()
    return render_template("issue_return.html",
                           books=books,
                           students=students,
                           active_tab="issue")


@transactions_bp.route("/return", methods=["GET", "POST"])
def return_book_view():
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
                flash(f"Book returned. Fine: ₹{fine:.2f} — collect from student.", "warning")
            else:
                flash("Book returned on time. No fine.", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash(result["error"], "error")
            return redirect(url_for("transactions.return_book_view"))

    return render_template("issue_return.html",
                           books=[],
                           students=[],
                           active_tab="return")
