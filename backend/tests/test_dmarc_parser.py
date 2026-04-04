import pytest
from app.services.parser.dmarc_parser import DmarcParser, DmarcParserError, Provider


def _valid_report_xml(org_name: str = "Google") -> bytes:
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<feedback>
  <report_metadata>
    <org_name>{org_name}</org_name>
    <email>noreply-dmarc-support@google.com</email>
    <report_id>report-123</report_id>
    <date_range>
      <begin>1712000000</begin>
      <end>1712086400</end>
    </date_range>
  </report_metadata>
  <policy_published>
    <domain>Example.COM</domain>
  </policy_published>
  <record>
    <row>
      <source_ip>203.0.113.10</source_ip>
      <count>42</count>
      <policy_evaluated>
        <disposition>none</disposition>
        <dkim>pass</dkim>
        <spf>fail</spf>
      </policy_evaluated>
    </row>
    <identifiers>
      <header_from>Example.COM</header_from>
      <envelope_from>mail.example.com</envelope_from>
    </identifiers>
  </record>
</feedback>
""".encode()


def test_dmarc_parser_parses_safe_xml_and_normalizes_provider() -> None:
    parser = DmarcParser(validate_schema=True)

    parsed = parser.parse(_valid_report_xml(org_name="Google LLC"))

    assert parsed.report_id == "report-123"
    assert parsed.provider == Provider.GOOGLE
    assert parsed.policy_domain == "example.com"
    assert len(parsed.records) == 1
    record = parsed.records[0]
    assert record.source_ip == "203.0.113.10"
    assert record.count == 42
    assert record.dkim == "pass"
    assert record.spf == "fail"
    assert record.header_from == "example.com"
    assert record.envelope_from == "mail.example.com"


def test_dmarc_parser_provider_normalization_microsoft() -> None:
    parser = DmarcParser()

    parsed = parser.parse(
        _valid_report_xml(org_name="Microsoft Outlook").replace(
            b"noreply-dmarc-support@google.com",
            b"dmarcreport@outlook.com",
        )
    )

    assert parsed.provider == Provider.MICROSOFT


def test_dmarc_parser_schema_validation_rejects_missing_required_path() -> None:
    parser = DmarcParser(validate_schema=True)
    invalid = _valid_report_xml().replace(b"<policy_published>", b"<policy_removed>")

    with pytest.raises(DmarcParserError):
        parser.parse(invalid)


def test_dmarc_parser_rejects_unsafe_xml_entity_expansion() -> None:
    parser = DmarcParser()
    xml = b"""<?xml version=\"1.0\"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM \"file:///etc/passwd\"> ]>
<feedback>
  <report_metadata>
    <org_name>&xxe;</org_name>
    <email>x@example.com</email>
    <report_id>id-1</report_id>
    <date_range><begin>1</begin><end>2</end></date_range>
  </report_metadata>
  <policy_published><domain>example.com</domain></policy_published>
  <record>
    <row>
      <source_ip>203.0.113.11</source_ip>
      <count>1</count>
      <policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf></policy_evaluated>
    </row>
    <identifiers><header_from>example.com</header_from></identifiers>
  </record>
</feedback>
"""

    with pytest.raises(DmarcParserError):
        parser.parse(xml)


def test_dmarc_parser_rejects_invalid_ip() -> None:
    parser = DmarcParser()
    invalid = _valid_report_xml().replace(b"203.0.113.10", b"not-an-ip")

    with pytest.raises(DmarcParserError):
        parser.parse(invalid)
