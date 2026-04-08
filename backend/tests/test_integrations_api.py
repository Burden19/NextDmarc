from uuid import uuid4

from app.main import app
from app.services.integrations.store import reset_integration_store_for_tests
from fastapi.testclient import TestClient


def test_integrations_crud_and_connector_test_flow() -> None:
    reset_integration_store_for_tests()
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}

    client = TestClient(app)

    create_response = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "name": "SOC Slack",
            "kind": "slack",
            "config": {
                "webhook_url": "https://hooks.slack.com/services/test",
            },
            "enabled": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()

    list_response = client.get("/api/v1/integrations", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(f"/api/v1/integrations/{created['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["kind"] == "slack"

    test_response = client.post(
        f"/api/v1/integrations/{created['id']}/test",
        headers=headers,
    )
    assert test_response.status_code == 200
    assert test_response.json()["status"] == "ok"

    patch_response = client.patch(
        f"/api/v1/integrations/{created['id']}",
        headers=headers,
        json={"enabled": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["enabled"] is False

    delete_response = client.delete(f"/api/v1/integrations/{created['id']}", headers=headers)
    assert delete_response.status_code == 204


def test_integrations_test_endpoint_reports_failed_validation() -> None:
    reset_integration_store_for_tests()
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}

    client = TestClient(app)

    create_response = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "name": "Broken Email Connector",
            "kind": "email",
            "config": {"sender": "alerts@example.test"},
        },
    )
    assert create_response.status_code == 201
    integration_id = create_response.json()["id"]

    test_response = client.post(f"/api/v1/integrations/{integration_id}/test", headers=headers)
    assert test_response.status_code == 200
    assert test_response.json()["status"] == "failed"
