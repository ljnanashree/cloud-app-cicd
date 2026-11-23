import json


def test_health_check_endpoint(client):
    """Test that /health returns 200 OK and valid health telemetry."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "app" in data
    assert data["app"]["name"] == "CloudPulse-Test"
    assert "uptime_seconds" in data["app"]
    assert "database" in data
    assert data["database"]["connected"] is True
    assert "latency_ms" in data["database"]
    assert data["database"]["type"] == "SQLite"


def test_metrics_endpoint(client):
    """Test that /api/metrics returns system metrics and task stats."""
    response = client.get("/api/metrics")
    assert response.status_code == 200

    data = response.get_json()
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert "application_metrics" in data
    assert "total_tasks" in data["application_metrics"]
    assert "completion_rate_pct" in data["application_metrics"]
