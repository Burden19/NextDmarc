from app.main import app
from app.services.recommendation.resolution_store import (
    reset_recommendation_resolution_store_for_tests,
)
from app.services.recommendation.store import (
    get_recommendation_store,
    reset_recommendation_store_for_tests,
)
from app.workers.tasks.recommend import _generate_recommendations_async
from fastapi.testclient import TestClient

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def test_recommendations_api_list_detail_resolve_flow() -> None:
    reset_recommendation_store_for_tests()
    reset_recommendation_resolution_store_for_tests()

    store = get_recommendation_store()
    _ = store

    import asyncio

    asyncio.run(
        _generate_recommendations_async(
            payload={
                "tenant_id": TEST_TENANT_ID,
                "report_db_id": "report-1",
                "total_records": 100,
                "spf_pass_count": 75,
                "dkim_pass_count": 72,
                "dmarc_pass_count": 70,
                "conformance_rate": 0.7,
            }
        )
    )

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    listing = client.get("/api/v1/recommendations", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["report_db_id"] == "report-1"

    detail = client.get("/api/v1/recommendations/report-1", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["maturity_level"] in {
        "foundational",
        "developing",
        "managed",
        "advanced",
    }

    resolve = client.post(
        "/api/v1/recommendations/report-1/resolve",
        headers=headers,
        json={"resolved": True, "comment": "Mitigation applied"},
    )
    assert resolve.status_code == 200
    assert resolve.json()["resolved"] is True
    assert resolve.json()["comment"] == "Mitigation applied"

    detail_after = client.get("/api/v1/recommendations/report-1", headers=headers)
    assert detail_after.status_code == 200
    assert detail_after.json()["resolved"] is True


def test_recommendations_api_detail_not_found() -> None:
    reset_recommendation_store_for_tests()
    reset_recommendation_resolution_store_for_tests()

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    detail = client.get("/api/v1/recommendations/missing", headers=headers)
    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "recommendation_not_found"
