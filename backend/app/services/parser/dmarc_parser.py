from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from ipaddress import ip_address
from typing import Literal

from defusedxml import ElementTree as SafeElementTree
from defusedxml.common import DefusedXmlException


class DmarcParserError(Exception):
    pass


class Provider(StrEnum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    YAHOO = "yahoo"
    PROTON = "proton"
    OTHER = "other"


@dataclass(slots=True)
class DmarcParsedRecord:
    source_ip: str
    count: int
    disposition: str
    dkim: Literal["pass", "fail"]
    spf: Literal["pass", "fail"]
    header_from: str
    envelope_from: str | None
    envelope_to: str | None


@dataclass(slots=True)
class DmarcParsedReport:
    report_id: str
    provider: Provider
    provider_org_name: str
    provider_email: str
    policy_domain: str
    date_range_begin: datetime
    date_range_end: datetime
    records: list[DmarcParsedRecord]


class DmarcParser:
    def __init__(self, *, validate_schema: bool = False) -> None:
        self._validate_schema = validate_schema

    def parse(self, xml_payload: bytes) -> DmarcParsedReport:
        root = self._safe_parse(xml_payload)
        if self._validate_schema:
            self._run_schema_validation(root)

        report_metadata = _required_child(root, "report_metadata")
        policy_published = _required_child(root, "policy_published")

        org_name = _required_text(report_metadata, "org_name")
        provider_email = _required_text(report_metadata, "email")
        report_id = _required_text(report_metadata, "report_id")
        policy_domain = _required_text(policy_published, "domain").lower()

        date_range = _required_child(report_metadata, "date_range")
        begin = _required_epoch(date_range, "begin")
        end = _required_epoch(date_range, "end")
        if begin > end:
            raise DmarcParserError("date_range begin is greater than end")

        records: list[DmarcParsedRecord] = []
        for record_node in root.findall("record"):
            records.append(self._parse_record(record_node))

        if not records:
            raise DmarcParserError("DMARC report must contain at least one record")

        return DmarcParsedReport(
            report_id=report_id,
            provider=_normalize_provider(org_name=org_name, email=provider_email),
            provider_org_name=org_name,
            provider_email=provider_email,
            policy_domain=policy_domain,
            date_range_begin=datetime.fromtimestamp(begin, tz=UTC),
            date_range_end=datetime.fromtimestamp(end, tz=UTC),
            records=records,
        )

    def _safe_parse(self, xml_payload: bytes) -> SafeElementTree.Element:
        try:
            return SafeElementTree.fromstring(xml_payload)
        except (DefusedXmlException, SafeElementTree.ParseError) as exc:
            raise DmarcParserError("Invalid or unsafe DMARC XML payload") from exc

    def _run_schema_validation(self, root: SafeElementTree.Element) -> None:
        required_paths = [
            "report_metadata/org_name",
            "report_metadata/email",
            "report_metadata/report_id",
            "report_metadata/date_range/begin",
            "report_metadata/date_range/end",
            "policy_published/domain",
        ]

        for path in required_paths:
            if root.find(path) is None:
                raise DmarcParserError(f"Schema validation failed: missing '{path}'")

        for record_node in root.findall("record"):
            if record_node.find("row/source_ip") is None:
                raise DmarcParserError("Schema validation failed: missing 'row/source_ip'")
            if record_node.find("row/count") is None:
                raise DmarcParserError("Schema validation failed: missing 'row/count'")
            if record_node.find("row/policy_evaluated") is None:
                raise DmarcParserError(
                    "Schema validation failed: missing 'row/policy_evaluated'"
                )

    def _parse_record(self, record_node: SafeElementTree.Element) -> DmarcParsedRecord:
        row = _required_child(record_node, "row")
        policy = _required_child(row, "policy_evaluated")
        identifiers = _required_child(record_node, "identifiers")

        source_ip = _required_text(row, "source_ip")
        _validate_ip(source_ip)

        count = _required_int(row, "count", min_value=1)
        disposition = _required_text(policy, "disposition").lower()
        dkim = _required_result(policy, "dkim")
        spf = _required_result(policy, "spf")

        return DmarcParsedRecord(
            source_ip=source_ip,
            count=count,
            disposition=disposition,
            dkim=dkim,
            spf=spf,
            header_from=_required_text(identifiers, "header_from").lower(),
            envelope_from=_optional_text(identifiers, "envelope_from"),
            envelope_to=_optional_text(identifiers, "envelope_to"),
        )


def _normalize_provider(*, org_name: str, email: str) -> Provider:
    normalized = f"{org_name} {email}".lower()

    if "google" in normalized or "googlemail" in normalized:
        return Provider.GOOGLE
    if "microsoft" in normalized or "outlook" in normalized:
        return Provider.MICROSOFT
    if "yahoo" in normalized:
        return Provider.YAHOO
    if "proton" in normalized:
        return Provider.PROTON
    return Provider.OTHER


def _required_child(node: SafeElementTree.Element, name: str) -> SafeElementTree.Element:
    child = node.find(name)
    if child is None:
        raise DmarcParserError(f"Missing required element '{name}'")
    return child


def _required_text(node: SafeElementTree.Element, name: str) -> str:
    child = _required_child(node, name)
    value = (child.text or "").strip()
    if not value:
        raise DmarcParserError(f"Element '{name}' must not be empty")
    return value


def _optional_text(node: SafeElementTree.Element, name: str) -> str | None:
    child = node.find(name)
    if child is None:
        return None

    value = (child.text or "").strip()
    return value or None


def _required_int(node: SafeElementTree.Element, name: str, *, min_value: int) -> int:
    raw_value = _required_text(node, name)
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise DmarcParserError(f"Element '{name}' must be an integer") from exc

    if parsed < min_value:
        raise DmarcParserError(f"Element '{name}' must be >= {min_value}")
    return parsed


def _required_epoch(node: SafeElementTree.Element, name: str) -> int:
    return _required_int(node, name, min_value=0)


def _required_result(node: SafeElementTree.Element, name: str) -> Literal["pass", "fail"]:
    value = _required_text(node, name).lower()
    if value not in {"pass", "fail"}:
        raise DmarcParserError(f"Element '{name}' must be either 'pass' or 'fail'")
    return value


def _validate_ip(value: str) -> None:
    try:
        ip_address(value)
    except ValueError as exc:
        raise DmarcParserError("Invalid source IP in record") from exc
