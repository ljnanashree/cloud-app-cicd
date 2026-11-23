from flask import Blueprint, render_template, current_app

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    """Render main dashboard view."""
    stats = current_app.task_model.get_stats()
    recent_tasks = current_app.task_model.get_all(limit=6)
    recent_activity = current_app.task_model.get_recent_activity(limit=8)
    db_healthy, latency, db_type = current_app.db_manager.health_check()

    return render_template(
        "index.html",
        app_name=current_app.config.get("APP_NAME", "CloudPulse"),
        app_version=current_app.config.get("APP_VERSION", "1.0.0"),
        stats=stats,
        recent_tasks=recent_tasks,
        recent_activity=recent_activity,
        db_healthy=db_healthy,
        db_latency=latency,
        db_type=db_type
    )
