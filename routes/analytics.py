"""
routes/analytics.py
-------------------
Blueprint for the analytics page.

Produces two charts as base64-encoded PNG images embedded directly in the
HTML response — no static files are written to disk, no external CDN needed.

Charts:
  1. Horizontal bar chart — top 5 most-borrowed books
  2. Line chart           — monthly borrow volume over time

Why embed as base64 rather than saving files?
  Saving chart files to /static creates a stale-data problem (the file on
  disk might be from a previous run).  Embedding as data URIs means the
  chart is always generated fresh from the current database state.

Why Matplotlib rather than Plotly?
  Matplotlib is synchronous and has no JS dependency.  For a local admin
  tool, a static image is perfectly adequate and avoids loading a large
  JavaScript bundle.
"""

import io
import base64

import matplotlib
matplotlib.use("Agg")          # non-interactive backend — no display required
import matplotlib.pyplot as plt

from flask import Blueprint, render_template

from models.transaction import get_top_borrowed_books, get_monthly_borrow_volume

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


def _fig_to_base64(fig) -> str:
    """
    Convert a Matplotlib Figure object to a base64-encoded PNG string
    suitable for embedding in an HTML <img src="data:image/png;base64,...">.

    Steps:
      1. Write the figure to an in-memory BytesIO buffer (no disk I/O).
      2. Base64-encode the raw bytes.
      3. Decode to a UTF-8 string so Jinja2 can render it inline.

    The figure is explicitly closed after conversion to free memory.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _build_top_books_chart(rows: list) -> str:
    """
    Build a horizontal bar chart of the top N most-borrowed books.

    Horizontal bars are used (instead of vertical) because book titles are
    long strings that overlap badly on a vertical x-axis.

    Returns the chart as a base64 PNG string.
    """
    if not rows:
        return ""

    titles = [r["title"][:35] + "…" if len(r["title"]) > 35
              else r["title"] for r in rows]
    counts = [r["borrow_count"] for r in rows]

    # Reverse so highest bar is at the top
    titles = titles[::-1]
    counts = counts[::-1]

    fig, ax = plt.subplots(figsize=(8, max(3, len(titles) * 0.7)))
    bars = ax.barh(titles, counts, color="#4A90D9")

    ax.set_xlabel("Times Borrowed")
    ax.set_title("Top Most-Borrowed Books")
    ax.bar_label(bars, padding=3)         # show count at end of each bar
    ax.set_xlim(0, max(counts) * 1.2)    # leave room for labels
    fig.tight_layout()

    return _fig_to_base64(fig)


def _build_monthly_volume_chart(rows: list) -> str:
    """
    Build a line chart showing how many books were borrowed each month.

    Month labels (YYYY-MM) are rotated 45° so they don't overlap.
    A marker on each data point makes individual months easy to identify
    on a sparsely-populated chart (e.g. when the library is new).

    Returns the chart as a base64 PNG string.
    """
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
    ax.yaxis.get_major_locator().set_params(integer=True)  # whole numbers only
    fig.tight_layout()

    return _fig_to_base64(fig)


@analytics_bp.route("/")
def analytics():
    """
    Render the analytics page with two embedded charts.

    If there is not enough data yet (e.g. fresh install with no transactions),
    the chart helper functions return empty strings.  The template checks for
    empty strings and shows a 'No data yet' message instead of a broken image.
    """
    top_books    = get_top_borrowed_books(limit=5)
    monthly_data = get_monthly_borrow_volume()

    top_books_chart    = _build_top_books_chart(top_books)
    monthly_vol_chart  = _build_monthly_volume_chart(monthly_data)

    return render_template(
        "analytics.html",
        top_books_chart=top_books_chart,
        monthly_vol_chart=monthly_vol_chart,
        top_books=top_books,
        monthly_data=monthly_data,
    )
