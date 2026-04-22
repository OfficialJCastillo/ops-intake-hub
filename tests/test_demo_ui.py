from fastapi.testclient import TestClient

from main import app


def test_demo_ui_serves_html() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ops-intake-hub demo UI" in response.text
    assert "Assess intake" in response.text
    assert "Triage rules" in response.text
    assert "GET /triage/rules" in response.text
    assert "Routing rationale" in response.text


def test_triage_rules_endpoint_serves_policy() -> None:
    client = TestClient(app)

    response = client.get("/triage/rules")

    assert response.status_code == 200
    data = response.json()
    assert data["priority_due_windows"]["critical"] == "within 30 minutes"
    assert any(rule["triage_category"] == "incident" for rule in data["category_rules"])
