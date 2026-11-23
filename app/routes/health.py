import time
import os
import sys
from datetime import datetime
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)
START_TIME = time.time()


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Standard Cloud Health Check Endpoint.
    Used by Cloud Load Balancers, Render health monitors, and Kubernetes probes.
    """
    db_manager = current_app.db_manager
    db_healthy, db_latency_ms, db_type = db_manager.health_check()

    uptime_seconds = round(time.time() - START_TIME, 1)
    status_code = 200 if db_healthy else 503

    payload = {
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "app": {
            "name": current_app.config.get("APP_NAME", "CloudPulse"),
            "version": current_app.config.get("APP_VERSION", "1.0.0"),
            "environment": os.environ.get("FLASK_ENV", "production"),
            "python_version": sys.version.split()[0],
            "uptime_seconds": uptime_seconds,
        },
        "database": {
            "connected": db_healthy,
            "type": db_type,
            "latency_ms": db_latency_ms,
        }
    }
    return jsonify(payload), status_code


@health_bp.route("/api/metrics", methods=["GET"])
def system_metrics():
    """Application telemetry and resource metrics endpoint."""
    uptime_seconds = round(time.time() - START_TIME, 1)
    db_manager = current_app.db_manager
    task_model = current_app.task_model
    stats = task_model.get_stats()
    db_healthy, latency, db_type = db_manager.health_check()

    return jsonify({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": uptime_seconds,
        "database": {
            "status": "connected" if db_healthy else "disconnected",
            "type": db_type,
            "latency_ms": latency
        },
        "application_metrics": {
            "total_tasks": stats["total_tasks"],
            "completion_rate_pct": stats["completion_rate"],
            "status_counts": stats["status_breakdown"],
            "priority_counts": stats["priority_breakdown"]
        }
    }), 200
