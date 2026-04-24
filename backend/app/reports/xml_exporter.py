"""Daily report XML exporter with XSD schema validation.

Produces a well-formed XML document compatible with the Xmail report schema.
Uses defusedxml for safe parsing and lxml for generation + validation.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lxml import etree

# Inline XSD schema — no external file dependency
_XSD_SOURCE = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="XmailReport">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Meta" type="MetaType"/>
        <xs:element name="Summary" type="SummaryType"/>
        <xs:element name="Contacts" type="ContactsType"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>

  <xs:complexType name="MetaType">
    <xs:sequence>
      <xs:element name="ReportDate" type="xs:date"/>
      <xs:element name="GeneratedAt" type="xs:dateTime"/>
      <xs:element name="Version" type="xs:string"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="SummaryType">
    <xs:sequence>
      <xs:element name="ContactsDiscovered" type="xs:nonNegativeInteger"/>
      <xs:element name="ContactsVerified" type="xs:nonNegativeInteger"/>
      <xs:element name="EmailsSent" type="xs:nonNegativeInteger"/>
      <xs:element name="EmailsDelivered" type="xs:nonNegativeInteger"/>
      <xs:element name="EmailsBounced" type="xs:nonNegativeInteger"/>
      <xs:element name="EmailsOpened" type="xs:nonNegativeInteger"/>
      <xs:element name="EmailsClicked" type="xs:nonNegativeInteger"/>
      <xs:element name="Unsubscribes" type="xs:nonNegativeInteger"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="ContactsType">
    <xs:sequence>
      <xs:element name="Contact" type="ContactType" minOccurs="0" maxOccurs="unbounded"/>
    </xs:sequence>
    <xs:attribute name="count" type="xs:nonNegativeInteger" use="required"/>
  </xs:complexType>

  <xs:complexType name="ContactType">
    <xs:sequence>
      <xs:element name="Email" type="xs:string"/>
      <xs:element name="Name" type="xs:string" minOccurs="0"/>
      <xs:element name="Company" type="xs:string" minOccurs="0"/>
      <xs:element name="Title" type="xs:string" minOccurs="0"/>
      <xs:element name="AudienceType" type="xs:string" minOccurs="0"/>
      <xs:element name="ConfidenceScore" type="xs:nonNegativeInteger" minOccurs="0"/>
      <xs:element name="VerifiedStatus" type="xs:string" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>
"""

_XSD_SCHEMA: etree.XMLSchema | None = None


def _get_schema() -> etree.XMLSchema:
    global _XSD_SCHEMA
    if _XSD_SCHEMA is None:
        _XSD_SCHEMA = etree.XMLSchema(etree.fromstring(_XSD_SOURCE))
    return _XSD_SCHEMA


def _text(parent: etree._Element, tag: str, value: str | int) -> None:
    el = etree.SubElement(parent, tag)
    el.text = str(value)


def generate_xml(
    report: Any,
    contacts: list[dict],
    output_path: Path | None = None,
    validate: bool = True,
) -> bytes:
    """Generate XML report. Returns UTF-8 XML bytes. Validates against XSD if validate=True."""
    root = etree.Element("XmailReport")

    # Meta
    meta = etree.SubElement(root, "Meta")
    _text(meta, "ReportDate", report.report_date.isoformat())
    _text(meta, "GeneratedAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _text(meta, "Version", "1.0")

    # Summary
    summary = etree.SubElement(root, "Summary")
    _text(summary, "ContactsDiscovered", report.contacts_discovered)
    _text(summary, "ContactsVerified", report.contacts_verified)
    _text(summary, "EmailsSent", report.emails_sent)
    _text(summary, "EmailsDelivered", report.emails_delivered)
    _text(summary, "EmailsBounced", report.emails_bounced)
    _text(summary, "EmailsOpened", report.emails_opened)
    _text(summary, "EmailsClicked", report.emails_clicked)
    _text(summary, "Unsubscribes", report.unsubscribes)

    # Contacts
    contacts_el = etree.SubElement(root, "Contacts", count=str(len(contacts)))
    for c in contacts:
        contact_el = etree.SubElement(contacts_el, "Contact")
        _text(contact_el, "Email", c.get("email", ""))
        if c.get("full_name"):
            _text(contact_el, "Name", c["full_name"])
        if c.get("company"):
            _text(contact_el, "Company", c["company"])
        if c.get("job_title"):
            _text(contact_el, "Title", c["job_title"])
        if c.get("audience_type"):
            _text(contact_el, "AudienceType", c["audience_type"])
        if c.get("confidence_score") is not None:
            _text(contact_el, "ConfidenceScore", c["confidence_score"])
        if c.get("verified_status"):
            _text(contact_el, "VerifiedStatus", c["verified_status"])

    # Validate
    if validate:
        schema = _get_schema()
        if not schema.validate(root):
            errors = "\n".join(str(e) for e in schema.error_log)
            raise ValueError(f"XML schema validation failed:\n{errors}")

    xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(xml_bytes)

    return xml_bytes
