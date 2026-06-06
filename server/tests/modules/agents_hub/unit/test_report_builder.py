"""Tests TDD — WebQualityReportBuilder (Prompt 9Q.8).

Builder que agrega hallazgos de un sitio en un informe estructurado.
Fakes en memoria: sin BD real.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


# ───────────────────────── Fakes ─────────────────────────


class _FakeOrmFinding:
    def __init__(
        self,
        site_id: uuid.UUID,
        finding_type: str,
        severity: str,
        status: str = "new",
        source_url: str | None = None,
        signal_json: dict | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.site_id = site_id
        self.finding_type = finding_type
        self.severity = severity
        self.status = status
        self.confidence = 1.0
        self.page_id = uuid.uuid4()
        self.related_page_id = None
        self.source_url = source_url or "https://ej.es/pagina"
        self.signal_json = signal_json or {}
        self.detected_at = NOW
        self.reviewed_at = None
        self.reviewed_by = None
        self.resolution_note = None
        self.created_at = NOW


class _FakeFindingRepo:
    def __init__(self, findings: list[_FakeOrmFinding]) -> None:
        self._findings = findings

    async def list_by_site(
        self,
        site_id: uuid.UUID,
        status: str | None = None,
        finding_type: str | None = None,
    ) -> list[_FakeOrmFinding]:
        out = [f for f in self._findings if f.site_id == site_id]
        if status:
            out = [f for f in out if f.status == status]
        if finding_type:
            out = [f for f in out if f.finding_type == finding_type]
        return out


class _FakeSite:
    def __init__(self, site_id: uuid.UUID, name: str = "Sitio Test") -> None:
        self.id = site_id
        self.name = name


class _FakeSiteRepo:
    def __init__(self, site: _FakeSite) -> None:
        self._site = site

    async def get(self, site_id: uuid.UUID) -> _FakeSite | None:
        return self._site if self._site.id == site_id else None


def _make_builder(findings, site_name="Sitio Test"):
    from server.app.modules.agents_hub.ingestion.quality.report_builder import (
        WebQualityReportBuilder,
    )

    site_id = uuid.uuid4()
    for f in findings:
        f.site_id = site_id

    repo = _FakeFindingRepo(findings)
    site_repo = _FakeSiteRepo(_FakeSite(site_id, site_name))
    return WebQualityReportBuilder(repo, site_repo), site_id


# ───────────────────────── Tests ─────────────────────────


@pytest.mark.asyncio
async def test_build_empty_when_no_findings():
    """build retorna informe vacío (totals a 0, sections=[]) si no hay hallazgos."""
    builder, site_id = _make_builder([])
    report = await builder.build(site_id)

    assert report.site_id == site_id
    assert report.totals_by_type == {}
    assert report.totals_by_severity == {}
    assert report.sections == []


@pytest.mark.asyncio
async def test_build_groups_findings_by_type():
    """build agrupa hallazgos en secciones por finding_type."""
    site_id = uuid.uuid4()
    findings = [
        _FakeOrmFinding(site_id, "stale", "info"),
        _FakeOrmFinding(site_id, "stale", "info"),
        _FakeOrmFinding(site_id, "empty", "critical"),
    ]
    builder, site_id = _make_builder(findings)
    report = await builder.build(site_id)

    types_in_report = {s.finding_type for s in report.sections}
    assert "stale" in types_in_report
    assert "empty" in types_in_report

    stale_section = next(s for s in report.sections if s.finding_type == "stale")
    assert len(stale_section.findings) == 2


@pytest.mark.asyncio
async def test_build_computes_totals_by_type_and_severity():
    """build calcula totals_by_type y totals_by_severity correctamente."""
    site_id = uuid.uuid4()
    findings = [
        _FakeOrmFinding(site_id, "stale", "info"),
        _FakeOrmFinding(site_id, "stale", "info"),
        _FakeOrmFinding(site_id, "empty", "critical"),
        _FakeOrmFinding(site_id, "thin", "warning"),
    ]
    builder, site_id = _make_builder(findings)
    report = await builder.build(site_id)

    assert report.totals_by_type["stale"] == 2
    assert report.totals_by_type["empty"] == 1
    assert report.totals_by_type["thin"] == 1
    assert report.totals_by_severity["info"] == 2
    assert report.totals_by_severity["critical"] == 1
    assert report.totals_by_severity["warning"] == 1


@pytest.mark.asyncio
async def test_build_generates_recommendation_per_section():
    """build genera un texto de recomendación no vacío para cada sección."""
    site_id = uuid.uuid4()
    findings = [_FakeOrmFinding(site_id, "stale", "info")]
    builder, site_id = _make_builder(findings)
    report = await builder.build(site_id)

    assert len(report.sections) == 1
    assert report.sections[0].recommendation  # no vacío
    assert isinstance(report.sections[0].recommendation, str)


@pytest.mark.asyncio
async def test_build_filters_by_status_filter():
    """build solo incluye hallazgos con status en status_filter."""
    site_id = uuid.uuid4()
    findings = [
        _FakeOrmFinding(site_id, "stale", "info", status="new"),
        _FakeOrmFinding(site_id, "stale", "info", status="dismissed"),
        _FakeOrmFinding(site_id, "stale", "info", status="confirmed"),
    ]
    builder, site_id = _make_builder(findings)
    # default status_filter = ("new", "confirmed") → excluye dismissed
    report = await builder.build(site_id)

    stale_section = next((s for s in report.sections if s.finding_type == "stale"), None)
    assert stale_section is not None
    assert len(stale_section.findings) == 2  # new + confirmed


@pytest.mark.asyncio
async def test_build_sets_site_name():
    """build incluye el nombre del sitio en el informe."""
    site_id = uuid.uuid4()
    findings = [_FakeOrmFinding(site_id, "empty", "critical")]
    builder, site_id = _make_builder(findings, site_name="Portal Institucional")
    report = await builder.build(site_id)

    assert report.site_name == "Portal Institucional"


@pytest.mark.asyncio
async def test_build_finding_view_has_url_and_detected_at():
    """ContentFindingView expone source_url y detected_at."""
    site_id = uuid.uuid4()
    url = "https://ej.es/obsoleta/2022/res"
    findings = [_FakeOrmFinding(site_id, "superseded", "warning", source_url=url)]
    builder, site_id = _make_builder(findings)
    report = await builder.build(site_id)

    section = report.sections[0]
    assert section.findings[0].page_url == url
    assert section.findings[0].detected_at == NOW
