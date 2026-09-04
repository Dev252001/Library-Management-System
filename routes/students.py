"""
routes/students.py
------------------
Blueprint for student membership management and profile pages.

Routes:
  GET  /students/              — list all students
  GET  /students/add           — render add-student form
  POST /students/add           — process add-student form
  GET  /students/<id>          — student profile: info + full borrow history
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date

from models.student     import get_all_students, get_student_by_id, add_student
from models.transaction import get_transactions_for_student, refresh_overdue_status

students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.route("/")
def list_students():
    """
    Render a simple table of all registered students.
    Used mainly for navigation — clicking a row leads to the profile page.
    """
    students = get_all_students()
    return render_template("students.html", students=students)


@students_bp.route("/add", methods=["GET", "POST"])
def add_student_view():
    """
    GET  — render the new-student registration form.
    POST — validate and insert the student record.

    Edge cases handled:
      - Name is blank → error
      - fee_tier not in allowed set → SQLite CHECK will raise IntegrityError,
        caught and shown as a friendly message (protects against direct
        HTTP POST tampering — someone sending fee_tier='free')
      - joining_date defaults to today if left blank (convenient for
        walk-in registrations)
    """
    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        contact      = request.form.get("contact", "").strip() or None
        joining_date = request.form.get("joining_date", "").strip()
        fee_tier     = request.form.get("fee_tier", "subsidized").strip()

        if not name:
            flash("Student name is required.", "error")
            return render_template("add_student.html", today=date.today().isoformat())

        # Default joining_date to today if blank
        if not joining_date:
            joining_date = date.today().isoformat()

        try:
            new_id = add_student(name, contact, joining_date, fee_tier)
            flash(f"Student '{name}' registered with ID #{new_id}.", "success")
            return redirect(url_for("students.profile", student_id=new_id))
        except Exception as e:
            flash(f"Could not register student: {e}", "error")
            return render_template("add_student.html", today=date.today().isoformat())

    return render_template("add_student.html", today=date.today().isoformat())


@students_bp.route("/<int:student_id>")
def profile(student_id: int):
    """
    Render the full profile for one student:
      - Personal details (name, contact, fee tier, joining date)
      - Complete borrow history: book title, issue date, due date,
        return date, status, fine amount
      - Summary: total fines outstanding (status != 'returned')

    Why compute outstanding_fines in the route rather than the template?
    Templates should contain presentation logic only.  Aggregating a sum
    is business logic — doing it in Python keeps the template clean and
    makes the calculation easy to unit-test.

    Returns 404 (via abort) if the student_id does not exist, so the
    browser shows a proper error page rather than a blank profile.
    """
    from flask import abort

    refresh_overdue_status()   # ensure this student's overdue rows are flagged

    student = get_student_by_id(student_id)
    if student is None:
        abort(404)

    transactions = get_transactions_for_student(student_id)

    # Sum fines only for non-returned (active) transactions
    outstanding_fines = sum(
        t["fine_amount"]
        for t in transactions
        if t["status"] != "returned"
    )

    return render_template(
        "student_profile.html",
        student=student,
        transactions=transactions,
        outstanding_fines=outstanding_fines,
    )
