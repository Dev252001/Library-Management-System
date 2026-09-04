from flask import Flask, render_template

from models.database import init_db

from routes.dashboard    import dashboard_bp
from routes.books        import books_bp
from routes.students     import students_bp
from routes.transactions import transactions_bp
from routes.analytics    import analytics_bp


def create_app():
    app = Flask(__name__)

    # needed for flash messages to work (session signing)
    app.secret_key = "library-ms-local-secret-2024"

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)

    # jinja2 doesn't expose enumerate() by default, analytics.html needs it
    app.jinja_env.globals["enumerate"] = enumerate

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    init_db()
    app = create_app()

    print("=" * 50)
    print("  Library MS  →  http://127.0.0.1:5000")
    print("  Ctrl+C to stop")
    print("=" * 50)

    app.run(debug=True, port=5000)
