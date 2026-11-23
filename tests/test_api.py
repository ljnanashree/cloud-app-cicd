import json


def test_list_tasks_initially_empty(client):
    """Test retrieving tasks list."""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["tasks"], list)


def test_create_task_success(client):
    """Test creating a valid task via POST."""
    payload = {
        "title": "Provision Managed Redis Cluster",
        "description": "Cache database queries to achieve sub-millisecond latencies.",
        "status": "In Progress",
        "priority": "High",
        "category": "Infrastructure",
        "due_date": "2026-12-01"
    }
    response = client.post(
        "/api/tasks",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["task"]["title"] == payload["title"]
    assert data["task"]["status"] == "In Progress"
    assert data["task"]["priority"] == "High"
    assert data["task"]["category"] == "Infrastructure"
    assert "id" in data["task"]


def test_create_task_validation_failure(client):
    """Test validation errors on missing required fields."""
    # Empty title
    response = client.post(
        "/api/tasks",
        data=json.dumps({"title": ""}),
        content_type="application/json"
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert len(data["errors"]) > 0

    # Invalid status & priority
    response = client.post(
        "/api/tasks",
        data=json.dumps({
            "title": "Valid Title",
            "status": "NonExistentStatus",
            "priority": "InvalidPriority"
        }),
        content_type="application/json"
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert len(data["errors"]) == 2


def test_get_single_task(client):
    """Test fetching a task by ID."""
    # Create task
    create_res = client.post(
        "/api/tasks",
        data=json.dumps({"title": "Test Fetch", "status": "Backlog"}),
        content_type="application/json"
    )
    task_id = create_res.get_json()["task"]["id"]

    # Fetch task
    get_res = client.get(f"/api/tasks/{task_id}")
    assert get_res.status_code == 200
    data = get_res.get_json()
    assert data["success"] is True
    assert data["task"]["id"] == task_id
    assert data["task"]["title"] == "Test Fetch"


def test_get_nonexistent_task(client):
    """Test 404 response for nonexistent task."""
    response = client.get("/api/tasks/999999")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_update_task(client):
    """Test updating task fields via PUT/PATCH."""
    create_res = client.post(
        "/api/tasks",
        data=json.dumps({"title": "Initial Title", "status": "Backlog", "priority": "Low"}),
        content_type="application/json"
    )
    task_id = create_res.get_json()["task"]["id"]

    update_payload = {
        "title": "Updated Title",
        "status": "Completed",
        "priority": "Urgent"
    }
    update_res = client.put(
        f"/api/tasks/{task_id}",
        data=json.dumps(update_payload),
        content_type="application/json"
    )
    assert update_res.status_code == 200
    updated_data = update_res.get_json()["task"]
    assert updated_data["title"] == "Updated Title"
    assert updated_data["status"] == "Completed"
    assert updated_data["priority"] == "Urgent"


def test_delete_task(client):
    """Test deleting task and verifying subsequent 404."""
    create_res = client.post(
        "/api/tasks",
        data=json.dumps({"title": "Task to Delete"}),
        content_type="application/json"
    )
    task_id = create_res.get_json()["task"]["id"]

    # Delete
    del_res = client.delete(f"/api/tasks/{task_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Confirm deletion
    get_res = client.get(f"/api/tasks/{task_id}")
    assert get_res.status_code == 404


def test_search_and_filter_tasks(client):
    """Test query filtering by status, priority, and search."""
    client.post("/api/tasks", data=json.dumps({"title": "Kubernetes Pod Tuning", "status": "In Progress", "priority": "High"}), content_type="application/json")
    client.post("/api/tasks", data=json.dumps({"title": "AWS IAM Least Privilege", "status": "Completed", "priority": "Low"}), content_type="application/json")

    # Filter by status
    res = client.get("/api/tasks?status=Completed")
    data = res.get_json()
    assert all(t["status"] == "Completed" for t in data["tasks"])

    # Filter by search
    res = client.get("/api/tasks?search=Kubernetes")
    data = res.get_json()
    assert len(data["tasks"]) >= 1
    assert "Kubernetes" in data["tasks"][0]["title"]


def test_task_stats_and_activity(client):
    """Test statistics and audit log endpoints."""
    # Stats
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.get_json()
    assert stats_data["success"] is True
    assert "total_tasks" in stats_data["stats"]
    assert "completion_rate" in stats_data["stats"]

    # Activity log
    act_res = client.get("/api/activity")
    assert act_res.status_code == 200
    act_data = act_res.get_json()
    assert act_data["success"] is True
    assert isinstance(act_data["activity"], list)
