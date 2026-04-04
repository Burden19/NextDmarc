from dataclasses import dataclass


@dataclass(slots=True)
class GeoIpInfo:
    source_ip: str
    country: str | None
    country_code: str | None


@dataclass(slots=True)
class AsnInfo:
    source_ip: str
    asn: int | None
    organization: str | None


@dataclass(slots=True)
class AbuseIpDbInfo:
    source_ip: str
    abuse_confidence_score: int | None
    total_reports: int | None


@dataclass(slots=True)
class VirusTotalInfo:
    source_ip: str
    malicious_votes: int | None
    suspicious_votes: int | None


@dataclass(slots=True)
class EnrichmentResult:
    source_ip: str
    geoip: GeoIpInfo | None
    asn: AsnInfo | None
    abuse: AbuseIpDbInfo | None
    virustotal: VirusTotalInfo | None
