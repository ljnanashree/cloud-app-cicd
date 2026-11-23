def test_index_page_loads(client):
    """Test that the index dashboard HTML renders successfully."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "CloudPulse" in html
    assert "Cloud Workload Tasks" in html
    assert "Activity Audit Stream" in html


def test_404_html_error_page(client):
    """Test custom 404 HTML error page when non-API route is requested."""
    response = client.get("/some-non-existent-page-url")
    assert response.status_code == 404
    html = response.get_data(as_text=True)
    assert "404 Error" in html
    assert "Endpoint Not Found" in html


def test_404_api_json_error(client):
    """Test custom 404 JSON response when /api/ non-existent route is requested."""
    response = client.get("/api/unknown-endpoint")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "Resource not found" in data["error"]
