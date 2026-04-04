from uuid import uuid4

from app.main import app
from app.services.domain_store import reset_domain_store_for_tests
from fastapi.testclient import TestClient


def test_domains_crud_and_policy_flow() -> None:
    reset_domain_store_for_tests()
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}

    client = TestClient(app)

    create_response = client.post(
        "/api/v1/domains",
        headers=headers,
        json={"fqdn": "Example.com", "dmarc_policy": "quarantine"},
    )
    assert create_response.status_code == 201
    created = create_response.json()

    list_response = client.get("/api/v1/domains", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    policy_response = client.get(f"/api/v1/domains/{created['id']}/policy", headers=headers)
    assert policy_response.status_code == 200
    assert policy_response.json()["dmarc_policy"] == "quarantine"

    patch_response = client.patch(
        f"/api/v1/domains/{created['id']}",
        headers=headers,
        json={"dmarc_policy": "reject"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["dmarc_policy"] == "reject"

    delete_response = client.delete(f"/api/v1/domains/{created['id']}", headers=headers)
    assert delete_response.status_code == 204
