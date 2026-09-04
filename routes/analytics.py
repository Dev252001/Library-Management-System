import io
import base64

import matplotlib
matplotlib.use("Agg")  # don't try to open a window — we're running headless
import matplotlib.pyplot as plt

from flask import Blueprint, render_template

from models.transaction import get_top_borrowed_books, get_monthly_borrow_volume

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


def _fig_to_base64(fig):
    # save to memory instead of disk, then encode so we can embed it in the HTML
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _build_top_books_chart(rows):
    if not rows:
        return ""

    titles = [r["title"][:35] + "…" if len(r["title"]) > 35 else r["title"] for r in rows]
    counts = [r["borrow_count"] for r in rows]

    # reverse so the highest bar appears at the top of the chart
    titles = titles[::-1]
    counts = counts[::-1]

    fig, ax = plt.subplots(figsize=(8, max(3, len(titles) * 0.7)))
    bars = ax.barh(titles, counts, color="#4A90D9")
    ax.set_xlabel("Times Borrowed")
    ax.set_title("Top Most-Borrowed Books")
    ax.bar_label(bars, padding=3)
    ax.set_xlim(0, max(counts) * 1.2)
    fig.tight_layout()

    return _fig_to_base64(fig)


def _build_monthly_volume_chart(rows):
    if not rows:
        return ""

    months = [r["month"] for r in rows]
    counts = [r["borrow_count"] for r in rows]

    fig, ax = plt.subplots(figsize=(max(6, len(months) * 0.8), 4))
    ax.plot(months, counts, marker="o", color="#4A90D9", linewidth=2)
    ax.fill_between(range(len(months)), counts, alpha=0.15, color="#4A90D9")
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45, ha="right")
    ax.set_ylabel("Books Borrowed")
    ax.set_title("Monthly Borrow Volume")
    ax.yaxis.get_major_locator().set_params(integer=True)
    fig.tight_layout()

    return _fig_to_base64(fig)


@analytics_bp.route("/")
def analytics():
    top_books    = get_top_borrowed_books(limit=5)
    monthly_data = get_monthly_borrow_volume()

    return render_template(
        "analytics.html",
        top_books_chart   = _build_top_books_chart(top_books),
        monthly_vol_chart = _build_monthly_volume_chart(monthly_data),
        top_books         = top_books,
        monthly_data      = monthly_data,
    )
