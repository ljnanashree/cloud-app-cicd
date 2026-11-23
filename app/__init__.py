import logging
import os
import time
from flask import Flask, jsonify, render_template, request

from app.config import config_by_name, DevelopmentConfig
from app.database import DatabaseManager
from app.models import TaskModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("cloudpulse")


def create_app(config_name: str = None, test_config: dict = None) -> Flask:
    """Application factory for CloudPulse."""
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configuration
    if config_name:
        config_class = config_by_name.get(config_name, DevelopmentConfig)
    else:
        env = os.environ.get("FLASK_ENV", "development").lower()
        config_class = config_by_name.get(env, DevelopmentConfig)

    app.config.from_object(config_class)

    if test_config:
        app.config.update(test_config)

    # Initialize database manager & schema
    db_manager = DatabaseManager(database_url=app.config.get("DATABASE_URL"))
    db_manager.init_db()
    app.db_manager = db_manager
    app.task_model = TaskModel(db_manager)

    # Seed initial demo tasks if database is empty (and not in testing mode)
    if not app.config.get("TESTING"):
        seed_initial_data(app.task_model)

    # Register blueprints
    from app.routes.web import web_bp
    from app.routes.api import api_bp
    from app.routes.health import health_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(health_bp)

    # Security headers & Request Logging Middleware
    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": False, "error": "Resource not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {error}")
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": False, "error": "Internal server error"}), 500
        return render_template("500.html"), 500

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": False, "error": "Bad request"}), 400
        return render_template("404.html"), 400

    logger.info(f"CloudPulse initialized successfully in {app.config.get('ENV', 'production')} mode.")
    return app


def seed_initial_data(task_model: TaskModel):
    """Seed sample tasks on first launch to showcase app functionality."""
    try:
        existing = task_model.get_all(limit=1)
        if not existing:
            sample_tasks = [
                ("Deploy Cloud Infrastructure", "Set up Render web service and managed PostgreSQL cluster.", "Completed", "High", "DevOps", "2026-11-25"),
                ("Implement GitHub Actions CI/CD", "Automate pytest runs, linting checks, and auto-deploy webhook on push.", "Completed", "Urgent", "CI/CD", "2026-11-24"),
                ("Configure Application Health Probes", "Integrate /health and /api/metrics endpoints for real-time monitoring.", "In Progress", "High", "Backend", "2026-11-26"),
                ("Optimize Database Query Indexing", "Add indexes on task status and priority columns for high-throughput queries.", "In Progress", "Medium", "Database", "2026-11-28"),
                ("Audit Security & Input Sanitization", "Verify parameter binding, XSS guards, and HTTP security response headers.", "Review", "High", "Security", "2026-11-29"),
                ("Design Interactive Responsive UI", "Build dark/light modern dashboard with real-time stats and modal forms.", "Completed", "Medium", "Frontend", "2026-11-23"),
            ]
            for title, desc, status, priority, cat, due in sample_tasks:
                task_model.create(title, desc, status, priority, cat, due)
            logger.info("Demo data seeded successfully.")
    except Exception as e:
        logger.warning(f"Could not seed sample data: {e}")
