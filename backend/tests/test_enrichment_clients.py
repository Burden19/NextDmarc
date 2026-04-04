import httpx
import pytest
from app.services.enrichment.clients import (
    AbuseIpDbClient,
    AsnClient,
    GeoIpClient,
    VirusTotalClient,
)
from app.services.enrichment.service import EnrichmentService


@pytest.mark.asyncio
async def test_geoip_client_uses_cache() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        assert request.url.path == "/json/198.51.100.5"
        return httpx.Response(
            status_code=200,
            json={"country": "France", "countryCode": "FR", "as": "AS64500 EdgeNet"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url="http://mock.local", transport=transport) as client:
        geoip = GeoIpClient(base_url="http://mock.local", http_client=client)

        first = await geoip.lookup(source_ip="198.51.100.5")
        second = await geoip.lookup(source_ip="198.51.100.5")

    assert first is not None
    assert second is not None
    assert first.country == "France"
    assert second.country_code == "FR"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_enrichment_service_aggregates_provider_outputs() -> None:
    def geo_handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            status_code=200,
            json={"country": "France", "countryCode": "FR"},
        )

    def asn_handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, json={"as": "AS64500 ExampleNet"})

    def abuse_handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            status_code=200,
            json={"data": {"abuseConfidenceScore": 42, "totalReports": 12}},
        )

    def vt_handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            status_code=200,
            json={
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 3, "suspicious": 1}
                    }
                }
            },
        )

    async with httpx.AsyncClient(
        base_url="http://geo.local", transport=httpx.MockTransport(geo_handler)
    ) as geo_http:
        async with httpx.AsyncClient(
            base_url="http://asn.local", transport=httpx.MockTransport(asn_handler)
        ) as asn_http:
            async with httpx.AsyncClient(
                base_url="http://abuse.local", transport=httpx.MockTransport(abuse_handler)
            ) as abuse_http:
                async with httpx.AsyncClient(
                    base_url="http://vt.local", transport=httpx.MockTransport(vt_handler)
                ) as vt_http:
                    service = EnrichmentService(
                        geoip_client=GeoIpClient(base_url="http://geo.local", http_client=geo_http),
                        asn_client=AsnClient(base_url="http://asn.local", http_client=asn_http),
                        abuse_client=AbuseIpDbClient(
                            base_url="http://abuse.local",
                            api_key="test",
                            http_client=abuse_http,
                        ),
                        virustotal_client=VirusTotalClient(
                            base_url="http://vt.local",
                            api_key="test",
                            http_client=vt_http,
                        ),
                    )
                    result = await service.enrich(source_ip="198.51.100.9")

    assert result.source_ip == "198.51.100.9"
    assert result.geoip is not None and result.geoip.country == "France"
    assert result.asn is not None and result.asn.asn == 64500
    assert result.abuse is not None and result.abuse.abuse_confidence_score == 42
    assert result.virustotal is not None and result.virustotal.malicious_votes == 3
