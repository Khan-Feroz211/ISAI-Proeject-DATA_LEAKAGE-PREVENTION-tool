"""Basic API smoke tests."""
import os
import pytest
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_dlp.db")
os.environ.setdefault("ADMIN_PASSWORD", "testpass")

from app import app as flask_app, _seed_admin  # noqa: E402


@pytest.fixture(scope="module")
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as c:
        with flask_app.app_context():
            _seed_admin()
        yield c


def _login(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=True,
    )


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"


def test_login_redirect(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (301, 302, 308)


def test_login_success(client):
    r = _login(client)
    assert r.status_code == 200


def test_stats_auth(client):
    _login(client)
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert "statistics" in data


def test_alerts_api(client):
    _login(client)
    r = client.get("/api/alerts")
    assert r.status_code == 200
    data = r.get_json()
    assert "alerts" in data
    assert "counts" in data


def test_policies_crud(client):
    _login(client)
    # Create
    r = client.post(
        "/api/policies",
        json={"name": "Test Policy", "pattern_type": "ssn", "severity": "high"},
    )
    assert r.status_code == 201
    pid = r.get_json()["policy"]["id"]

    # Read
    r = client.get("/api/policies")
    names = [p["name"] for p in r.get_json()["policies"]]
    assert "Test Policy" in names

    # Update
    r = client.put(f"/api/policies/{pid}", json={"severity": "critical"})
    assert r.get_json()["policy"]["severity"] == "critical"

    # Delete
    r = client.delete(f"/api/policies/{pid}")
    assert r.get_json()["success"] is True


def test_mlops_status(client):
    _login(client)
    r = client.get("/api/mlops/status")
    assert r.status_code == 200
    data = r.get_json()
    assert "model_name" in data
