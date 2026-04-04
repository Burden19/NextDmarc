import asyncio

from app.core.config import get_settings
from app.services.enrichment.clients import (
    AbuseIpDbClient,
    AsnClient,
    GeoIpClient,
    VirusTotalClient,
)
from app.services.enrichment.models import EnrichmentResult


class EnrichmentService:
    def __init__(
        self,
        *,
        geoip_client: GeoIpClient,
        asn_client: AsnClient,
        abuse_client: AbuseIpDbClient,
        virustotal_client: VirusTotalClient,
    ) -> None:
        self._geoip_client = geoip_client
        self._asn_client = asn_client
        self._abuse_client = abuse_client
        self._virustotal_client = virustotal_client

    async def enrich(self, *, source_ip: str) -> EnrichmentResult:
        geoip, asn, abuse, virustotal = await asyncio.gather(
            self._geoip_client.lookup(source_ip=source_ip),
            self._asn_client.lookup(source_ip=source_ip),
            self._abuse_client.lookup(source_ip=source_ip),
            self._virustotal_client.lookup(source_ip=source_ip),
        )

        return EnrichmentResult(
            source_ip=source_ip,
            geoip=geoip,
            asn=asn,
            abuse=abuse,
            virustotal=virustotal,
        )


def build_enrichment_service() -> EnrichmentService:
    settings = get_settings()

    return EnrichmentService(
        geoip_client=GeoIpClient(
            base_url=settings.enrichment_geoip_base_url,
            timeout_seconds=settings.enrichment_timeout_seconds,
            cache_ttl_seconds=settings.enrichment_cache_ttl_seconds,
            requests_per_second=5.0,
        ),
        asn_client=AsnClient(
            base_url=settings.enrichment_asn_base_url,
            timeout_seconds=settings.enrichment_timeout_seconds,
            cache_ttl_seconds=settings.enrichment_cache_ttl_seconds,
            requests_per_second=5.0,
        ),
        abuse_client=AbuseIpDbClient(
            base_url=settings.enrichment_abuseipdb_base_url,
            api_key=settings.enrichment_abuseipdb_api_key,
            timeout_seconds=settings.enrichment_timeout_seconds,
            cache_ttl_seconds=settings.enrichment_cache_ttl_seconds,
            requests_per_second=2.0,
        ),
        virustotal_client=VirusTotalClient(
            base_url=settings.enrichment_virustotal_base_url,
            api_key=settings.enrichment_virustotal_api_key,
            timeout_seconds=settings.enrichment_timeout_seconds,
            cache_ttl_seconds=settings.enrichment_cache_ttl_seconds,
            requests_per_second=2.0,
        ),
    )
