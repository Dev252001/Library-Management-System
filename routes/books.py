"""
routes/books.py
---------------
Blueprint for browsing and searching the book catalogue.

Routes:
  GET  /books              — list all books (optionally filtered)
  GET  /books/add          — render the add-book form
  POST /books/add          — process the add-book form
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models.book import get_all_books, search_books, get_all_categories, add_book

books_bp = Blueprint("books", __name__, url_prefix="/books")


@books_bp.route("/")
def list_books():
    """
    Display the book catalogue with optional search and category filters.

    Query parameters (both optional, both default to empty string):
      ?q        — free-text search against title and author
      ?category — exact category filter

    Why read filters from request.args rather than POST?
    GET requests with query parameters are bookmarkable and shareable.
    A staff member can bookmark "/books/?category=Science" and return to
    the same filtered view without re-submitting a form.
    """
    query    = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    books      = search_books(query, category)
    categories = get_all_categories()

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        current_query=query,
        current_category=category,
    )


@books_bp.route("/add", methods=["GET", "POST"])
def add_book_view():
    """
    GET  — render an empty add-book form.
    POST — validate inputs and insert the book into the catalogue.

    Validation performed here (not in the model) because validation is
    a presentation-layer concern — the model trusts its caller to send
    clean data, and the route is responsible for ensuring that.

    Edge cases handled:
      - total_copies missing or non-integer → flash error, re-render form
      - total_copies < 1 → flash error (a book with 0 copies is useless)
      - Duplicate ISBN → SQLite UNIQUE constraint raises IntegrityError,
        caught here and shown as a friendly message
    """
    if request.method == "POST":
        title        = request.form.get("title", "").strip()
        author       = request.form.get("author", "").strip()
        isbn         = request.form.get("isbn", "").strip() or None
        category     = request.form.get("category", "").strip() or None
        copies_raw   = request.form.get("total_copies", "").strip()

        # --- input validation ---
        if not title or not author:
            flash("Title and Author are required.", "error")
            return render_template("add_book.html")

        try:
            total_copies = int(copies_raw)
            if total_copies < 1:
                raise ValueError
        except ValueError:
            flash("Total copies must be a whole number ≥ 1.", "error")
            return render_template("add_book.html")

        try:
            add_book(title, author, isbn, category, total_copies)
            flash(f"'{title}' added to the catalogue successfully.", "success")
            return redirect(url_for("books.list_books"))
        except Exception as e:
            # Catches UNIQUE constraint violation on ISBN among others
            flash(f"Could not add book: {e}", "error")
            return render_template("add_book.html")

    # GET request — just render the empty form
    return render_template("add_book.html")
