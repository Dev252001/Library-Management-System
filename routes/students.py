from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from datetime import date

from models.student     import get_all_students, get_student_by_id, add_student
from models.transaction import get_transactions_for_student, refresh_overdue_status

students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.route("/")
def list_students():
    students = get_all_students()
    return render_template("students.html", students=students)


@students_bp.route("/add", methods=["GET", "POST"])
def add_student_view():
    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        contact      = request.form.get("contact", "").strip() or None
        joining_date = request.form.get("joining_date", "").strip()
        fee_tier     = request.form.get("fee_tier", "subsidized").strip()

        if not name:
            flash("Student name is required.", "error")
            return render_template("add_student.html", today=date.today().isoformat())

        # default to today if they left the date blank
        if not joining_date:
            joining_date = date.today().isoformat()

        try:
            new_id = add_student(name, contact, joining_date, fee_tier)
            flash(f"'{name}' registered with ID #{new_id}.", "success")
            return redirect(url_for("students.profile", student_id=new_id))
        except Exception as e:
            flash(f"Could not register student: {e}", "error")
            return render_template("add_student.html", today=date.today().isoformat())

    return render_template("add_student.html", today=date.today().isoformat())


@students_bp.route("/<int:student_id>")
def profile(student_id):
    refresh_overdue_status()

    student = get_student_by_id(student_id)
    if student is None:
        abort(404)

    transactions = get_transactions_for_student(student_id)

    # only sum fines that haven't been settled yet
    outstanding_fines = sum(
        t["fine_amount"] for t in transactions if t["status"] != "returned"
    )

    return render_template(
        "student_profile.html",
        student=student,
        transactions=transactions,
        outstanding_fines=outstanding_fines,
    )
