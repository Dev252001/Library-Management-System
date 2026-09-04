"""
routes/dashboard.py
-------------------
Blueprint for the home/dashboard page.

Responsibility: fetch live KPI numbers and render them.
The overdue-status refresh is triggered here so numbers are always
up-to-date the moment someone opens the app.
"""

from flask import Blueprint, render_template

from models.transaction import get_dashboard_stats, refresh_overdue_status

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """
    Render the dashboard with five KPI cards:
      - Total book copies in the catalogue
      - Copies currently available on the shelf
      - Active issues (books currently out)
      - Overdue issues
      - Total outstanding fines (₹) across all non-returned books

    Why call refresh_overdue_status() on every GET?
    There is no background scheduler.  This single call is cheap (one
    SELECT + N UPDATEs where N is usually 0) and ensures that the moment
    a student opens the app after a weekend, overdue rows are already
    flagged correctly without any manual trigger.
    """
    refresh_overdue_status()          # keep statuses and running fines current
    stats = get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)
