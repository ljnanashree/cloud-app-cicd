from flask import Blueprint, request, jsonify, current_app

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/tasks", methods=["GET"])
def list_tasks():
    """Retrieve all tasks with optional filtering."""
    status = request.args.get("status")
    priority = request.args.get("priority")
    category = request.args.get("category")
    search = request.args.get("search")
    
    try:
        limit = min(int(request.args.get("limit", 100)), 500)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    tasks = current_app.task_model.get_all(
        status=status,
        priority=priority,
        category=category,
        search=search,
        limit=limit,
        offset=offset
    )
    return jsonify({
        "success": True,
        "count": len(tasks),
        "tasks": tasks
    }), 200


@api_bp.route("/tasks", methods=["POST"])
def create_task():
    """Create a new task."""
    data = request.get_json(silent=True) or {}
    errors = current_app.task_model.validate(data, is_update=False)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    task = current_app.task_model.create(
        title=data.get("title", ""),
        description=data.get("description", ""),
        status=data.get("status", "Backlog"),
        priority=data.get("priority", "Medium"),
        category=data.get("category", "General"),
        due_date=data.get("due_date")
    )
    return jsonify({"success": True, "task": task}), 201


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """Retrieve a single task by ID."""
    task = current_app.task_model.get_by_id(task_id)
    if not task:
        return jsonify({"success": False, "error": f"Task #{task_id} not found"}), 404
    return jsonify({"success": True, "task": task}), 200


@api_bp.route("/tasks/<int:task_id>", methods=["PUT", "PATCH"])
def update_task(task_id):
    """Update an existing task."""
    data = request.get_json(silent=True) or {}
    errors = current_app.task_model.validate(data, is_update=True)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    updated = current_app.task_model.update(task_id, data)
    if not updated:
        return jsonify({"success": False, "error": f"Task #{task_id} not found"}), 404
    return jsonify({"success": True, "task": updated}), 200


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task by ID."""
    success = current_app.task_model.delete(task_id)
    if not success:
        return jsonify({"success": False, "error": f"Task #{task_id} not found"}), 404
    return jsonify({"success": True, "message": f"Task #{task_id} deleted successfully"}), 200


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """Retrieve task aggregates and completion rates."""
    stats = current_app.task_model.get_stats()
    return jsonify({"success": True, "stats": stats}), 200


@api_bp.route("/activity", methods=["GET"])
def get_activity():
    """Retrieve audit activity logs."""
    limit = min(int(request.args.get("limit", 15)), 50)
    logs = current_app.task_model.get_recent_activity(limit=limit)
    return jsonify({"success": True, "activity": logs}), 200
