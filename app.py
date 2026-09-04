"""
app.py
------
Entry point for the Library Management System.

Responsibilities:
  1. Create the Flask application instance.
  2. Register all Blueprints (one per functional area).
  3. Add a Jinja2 global helper (enumerate) used in analytics.html.
  4. Register a custom 404 error handler.
  5. Initialise the database (create tables if they don't exist).
  6. Start the development server when run directly.

Why keep this file short?
app.py should be a wiring diagram, not a logic dump.  Every piece of real
logic lives in models/ or routes/.  If someone reads only this file they
should understand the shape of the whole application in under a minute.
"""

from flask import Flask, render_template

from models.database import init_db

from routes.dashboard    import dashboard_bp
from routes.books        import books_bp
from routes.students     import students_bp
from routes.transactions import transactions_bp
from routes.analytics    import analytics_bp


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """
    Construct and configure the Flask application.

    Using a factory function (rather than a module-level `app = Flask(...)`)
    is a Flask best practice: it makes the app testable by allowing different
    configurations to be injected, and it avoids circular import problems that
    arise when models try to import from a module-level app object.

    Returns a fully configured Flask instance ready to serve requests.
    """
    app = Flask(__name__)

    # ── Secret key ────────────────────────────────────────────────────────
    # Required by Flask's session mechanism, which powers flash messages.
    # For a local single-user admin tool, a hardcoded key is acceptable.
    # In a deployed app this must come from an environment variable.
    app.secret_key = "library-ms-local-secret-2024"

    # ── Register Blueprints ───────────────────────────────────────────────
    # Each Blueprint carries its own url_prefix (defined in the routes file),
    # except the dashboard which sits at the root "/".
    app.register_blueprint(dashboard_bp)        # /
    app.register_blueprint(books_bp)            # /books/
    app.register_blueprint(students_bp)         # /students/
    app.register_blueprint(transactions_bp)     # /transactions/
    app.register_blueprint(analytics_bp)        # /analytics/

    # ── Jinja2 global: enumerate ──────────────────────────────────────────
    # Jinja2 does not expose Python's built-in enumerate() by default.
    # analytics.html uses it to show rank numbers (1, 2, 3 …) in the table.
    # Adding it as a global makes it available in every template without
    # needing to pass it explicitly from every route.
    app.jinja_env.globals["enumerate"] = enumerate

    # ── 404 handler ───────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        """
        Render a friendly 404 page instead of Flask's default HTML error.
        Triggered when a route calls abort(404) — e.g. unknown student ID.
        """
        return render_template("404.html"), 404

    return app


# ---------------------------------------------------------------------------
# Database initialisation + server start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # init_db() uses CREATE TABLE IF NOT EXISTS, so it is safe to run on
    # every startup — existing data is never touched.
    init_db()

    app = create_app()

    print("=" * 55)
    print("  Library Management System")
    print("  Running at http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop.")
    print("=" * 55)

    # debug=True gives live-reload on code changes and a browser debugger
    # on errors.  Acceptable for a local admin tool; must be False in prod.
    app.run(debug=True, port=5000)
