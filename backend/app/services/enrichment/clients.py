from typing import Any

import httpx

from app.services.enrichment.cache import TtlCache
from app.services.enrichment.models import AbuseIpDbInfo, AsnInfo, GeoIpInfo, VirusTotalInfo
from app.services.enrichment.ratelimit import RateProtector


class _CachedHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        cache_ttl_seconds: int,
        requests_per_second: float,
        headers: dict[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._headers = headers or {}
        self._cache = TtlCache(ttl_seconds=cache_ttl_seconds)
        self._rate = RateProtector(requests_per_second=requests_per_second)
        self._http_client = http_client

    async def _get_json(
        self,
        cache_key: str,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        await self._rate.wait_turn()

        if self._http_client is not None:
            response = await self._http_client.get(path, params=params, headers=self._headers)
        else:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.get(path, params=params, headers=self._headers)

        if response.status_code >= 400:
            return None

        payload: dict[str, Any] = response.json()
        await self._cache.set(cache_key, payload)
        return payload


class GeoIpClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 8.0,
        cache_ttl_seconds: int = 900,
        requests_per_second: float = 5.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = _CachedHttpClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            requests_per_second=requests_per_second,
            http_client=http_client,
        )

    async def lookup(self, *, source_ip: str) -> GeoIpInfo | None:
        payload = await self._client._get_json(
            cache_key=f"geoip:{source_ip}",
            path=f"/json/{source_ip}",
            params={},
        )
        if payload is None:
            return None
        return GeoIpInfo(
            source_ip=source_ip,
            country=_as_str(payload.get("country")),
            country_code=_as_str(payload.get("countryCode")),
        )


class AsnClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 8.0,
        cache_ttl_seconds: int = 900,
        requests_per_second: float = 5.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = _CachedHttpClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            requests_per_second=requests_per_second,
            http_client=http_client,
        )

    async def lookup(self, *, source_ip: str) -> AsnInfo | None:
        payload = await self._client._get_json(
            cache_key=f"asn:{source_ip}",
            path=f"/json/{source_ip}",
            params={},
        )
        if payload is None:
            return None

        as_value = _as_str(payload.get("as"))
        asn: int | None = None
        organization: str | None = None
        if as_value:
            parts = as_value.split(maxsplit=1)
            if parts and parts[0].startswith("AS"):
                try:
                    asn = int(parts[0][2:])
                except ValueError:
                    asn = None
            if len(parts) > 1:
                organization = parts[1]

        return AsnInfo(
            source_ip=source_ip,
            asn=asn,
            organization=organization,
        )


class AbuseIpDbClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 8.0,
        cache_ttl_seconds: int = 900,
        requests_per_second: float = 2.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = _CachedHttpClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            requests_per_second=requests_per_second,
            headers={"Key": api_key, "Accept": "application/json"} if api_key else {},
            http_client=http_client,
        )

    async def lookup(self, *, source_ip: str) -> AbuseIpDbInfo | None:
        payload = await self._client._get_json(
            cache_key=f"abuse:{source_ip}",
            path="/api/v2/check",
            params={"ipAddress": source_ip, "maxAgeInDays": 90},
        )
        if payload is None:
            return None

        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        return AbuseIpDbInfo(
            source_ip=source_ip,
            abuse_confidence_score=_as_int(data.get("abuseConfidenceScore")),
            total_reports=_as_int(data.get("totalReports")),
        )


class VirusTotalClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 8.0,
        cache_ttl_seconds: int = 900,
        requests_per_second: float = 2.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = _CachedHttpClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            requests_per_second=requests_per_second,
            headers={"x-apikey": api_key} if api_key else {},
            http_client=http_client,
        )

    async def lookup(self, *, source_ip: str) -> VirusTotalInfo | None:
        payload = await self._client._get_json(
            cache_key=f"vt:{source_ip}",
            path=f"/api/v3/ip_addresses/{source_ip}",
            params={},
        )
        if payload is None:
            return None

        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        attributes = data.get("attributes")
        if not isinstance(attributes, dict):
            return None
        stats = attributes.get("last_analysis_stats")
        if not isinstance(stats, dict):
            return None

        return VirusTotalInfo(
            source_ip=source_ip,
            malicious_votes=_as_int(stats.get("malicious")),
            suspicious_votes=_as_int(stats.get("suspicious")),
        )


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate if candidate else None


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return int(candidate)
        except ValueError:
            return None
    return None
