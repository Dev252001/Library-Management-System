from flask import Blueprint, render_template

from models.transaction import get_dashboard_stats, refresh_overdue_status

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    # scan for newly overdue books before pulling stats — keeps numbers honest
    refresh_overdue_status()
    stats = get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)
