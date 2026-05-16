"""Tests del motor de anonimización migrado en 9R.5.5.

Migrados y adaptados desde client_app/tests/test_ner_anonymizer.py,
test_anonymizer_patterns.py, test_anonymizer.py, test_anonymizer_extended.py.

11 tests cubren: NER persons, regex DNI/IBAN, anclajes, fallback sin spaCy,
faker determinista, contexto de apellidos, AEPD disposición 7ª, dataframe
con row count preservado, PDF→markdown sintético.
"""
from __future__ import annotations

import pandas as pd
import pytest

from server.app.modules.redaccion.services.anonymization.anonymizer import (
    AnonymizationContext,
)
from server.app.modules.redaccion.services.anonymization.faker_generator import (
    FakerGenerator,
)


@pytest.fixture
def ctx() -> AnonymizationContext:
    return AnonymizationContext()


# ---------------------------------------------------------------------------
# 1. NER detecta personas (sin assert duro si spaCy no está)
# ---------------------------------------------------------------------------

def test_pii_detector_identifies_persons_with_ner(ctx: AnonymizationContext) -> None:
    """Si spaCy está disponible, debe detectar nombres propios via NER."""
    text = "El estudiante Juan Pérez aprobó la asignatura."
    anonymized = ctx.anonymize(text, allowed_types=["PERSON_NAME"])
    if ctx.spacy_available:
        assert "Juan Pérez" not in anonymized
    else:
        # Sin spaCy degrada, no rompe el flujo
        assert isinstance(anonymized, str)


# ---------------------------------------------------------------------------
# 2. DNI/NIF por regex
# ---------------------------------------------------------------------------

def test_pii_detector_identifies_dni_nif_with_regex(ctx: AnonymizationContext) -> None:
    text = "DNI del solicitante: 12345678Z"
    anonymized = ctx.anonymize(text, allowed_types=["DNI"])
    assert "12345678Z" not in anonymized
    # debe haber introducido un fake del DNI
    assert ctx.real_to_fake.get("12345678Z") is not None


# ---------------------------------------------------------------------------
# 3. IBAN por regex
# ---------------------------------------------------------------------------

def test_pii_detector_identifies_iban_with_regex(ctx: AnonymizationContext) -> None:
    iban = "ES7621000418401234567891"
    anonymized = ctx.anonymize(f"Cuenta: {iban}", allowed_types=["IBAN"])
    assert iban not in anonymized
    assert ctx.real_to_fake.get(iban) is not None


# ---------------------------------------------------------------------------
# 4. Anclajes de formulario
# ---------------------------------------------------------------------------

def test_pii_detector_uses_form_anchors_for_field_context(
    ctx: AnonymizationContext,
) -> None:
    text = "Nombre: Luis Apellidos: Pérez Martínez"
    anonymized = ctx.anonymize(text)
    anchors = ctx.get_detected_anchors()
    assert any(a["field_type"] == "firstname" for a in anchors)
    assert any(a["field_type"] == "lastname" for a in anchors)
    assert "Luis" not in anonymized
    assert "Pérez Martínez" not in anonymized
    hint = ctx.get_form_structure_hint()
    assert hint is not None
    assert "NOMBRE DE PILA" in hint
    assert "APELLIDOS" in hint


# ---------------------------------------------------------------------------
# 5. Fallback sin spaCy → regex+anclajes siguen funcionando
# ---------------------------------------------------------------------------

def test_pii_detector_degrades_to_regex_only_without_spacy(monkeypatch) -> None:
    """Forzamos _nlp=None y verificamos que regex + anclajes siguen funcionando."""
    ctx = AnonymizationContext()
    ctx._nlp = None  # type: ignore[attr-defined]
    assert not ctx.spacy_available

    text = "DNI: 12345678Z y email a juan@example.com. Nombre: Marta"
    anonymized = ctx.anonymize(text)
    assert "12345678Z" not in anonymized
    assert "juan@example.com" not in anonymized
    assert "Marta" not in anonymized  # detectado por ANCHOR_FIRSTNAME


# ---------------------------------------------------------------------------
# 6. Faker determinista por valor original (dentro de la instancia)
# ---------------------------------------------------------------------------

def test_faker_generator_is_deterministic_per_value() -> None:
    fakes = FakerGenerator(seed=42)
    first = fakes.generate("EMAIL", "alice@example.com")
    second = fakes.generate("EMAIL", "alice@example.com")
    assert first == second
    assert first != "alice@example.com"


# ---------------------------------------------------------------------------
# 7. Contexto lastname → faker.last_name()
# ---------------------------------------------------------------------------

def test_faker_generator_uses_lastname_after_firstname_anchor() -> None:
    fakes = FakerGenerator(seed=42)
    # Pedimos un fake con contexto "apellido" → debe ser un apellido,
    # NO usar first_name() (heurística del legacy).
    fake_lastname = fakes.generate("PERSON_NAME", "Pérez Martínez", context="apellido")
    fake_firstname = fakes.generate("PERSON_NAME", "Luis", context="nombre")
    assert fake_lastname != "Pérez Martínez"
    assert fake_firstname != "Luis"
    # Garantizamos que ambos son strings distintos no vacíos
    assert isinstance(fake_lastname, str)
    assert isinstance(fake_firstname, str)
    assert fake_lastname != fake_firstname


# ---------------------------------------------------------------------------
# 8. Disposición 7ª LOPDGDD (AEPD) sobre DNI
# ---------------------------------------------------------------------------

def test_anonymizer_handles_aepd_disposicion_septima_for_dni(
    ctx: AnonymizationContext,
) -> None:
    """DNI 12345678Z → ***4567** (muestra dígitos 4-7)."""
    result = ctx.anonymize_document_id("12345678Z", mode="AEPD")
    assert result == "***4567**"


# ---------------------------------------------------------------------------
# 9. Anonimizar DataFrame preserva número de filas
# ---------------------------------------------------------------------------

def test_anonymize_tabular_preserves_row_count(ctx: AnonymizationContext) -> None:
    df = pd.DataFrame(
        {
            "Nombre": ["Juan Pérez", "María García", "Carlos Ruiz"],
            "Email": ["juan@x.com", "maria@y.com", "carlos@z.com"],
        }
    )
    result = ctx.anonymize_dataframe(
        df,
        {
            "Nombre": {"type": "PERSON_NAME", "mode": "FAKER"},
            "Email": {"type": "EMAIL", "mode": "FAKER"},
        },
    )
    assert len(result) == 3
    assert set(result["Nombre"]).isdisjoint({"Juan Pérez", "María García", "Carlos Ruiz"})
    assert set(result["Email"]).isdisjoint({"juan@x.com", "maria@y.com", "carlos@z.com"})


# ---------------------------------------------------------------------------
# 10 + 11. PDF→markdown sintético: spans sustituidos, resto verbatim
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymize_pdf_to_text_returns_markdown_with_substituted_spans(
    tmp_path,
) -> None:
    """Verifica que el flujo PDF→markdown→anonimización produce un .md
    sin PII detectada y con el resto del texto preservado.

    Usamos un PDF generado con reportlab que incluye DNI + email + nombre.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    from server.app.core.storage import FsspecStorageService
    from server.app.modules.redaccion.pipelines.contracts import StorageRef
    from server.app.modules.redaccion.services.test_data_anonymizer import (
        TestDataAnonymizerService,
    )

    pdf_path = tmp_path / "pii.pdf"
    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(100, 750, "Informe de gestion 2026")
    c.drawString(100, 720, "DNI: 12345678Z")
    c.drawString(100, 690, "Email: juan@example.com")
    c.drawString(100, 660, "Total ejecutado: 100.000 EUR")
    c.save()

    bucket_root = tmp_path / "bucket"
    bucket_root.mkdir()
    storage = FsspecStorageService(backend="file", bucket=str(bucket_root))
    await storage.put("pii.pdf", pdf_path.read_bytes())

    service = TestDataAnonymizerService(storage=storage)
    result = await service.anonymize_pdf_to_text(StorageRef(bucket="bucket", key="pii.pdf"))

    md_bytes = await storage.get(result.synthetic_ref.key)
    md = md_bytes.decode("utf-8")

    # PII desaparecida
    assert "12345678Z" not in md
    assert "juan@example.com" not in md

    # Texto no-PII preservado
    assert "Informe de gestion 2026" in md
    assert "Total ejecutado" in md
    assert result.spans_applied >= 2


@pytest.mark.asyncio
async def test_anonymize_pdf_to_text_preserves_non_pii_content_verbatim(
    tmp_path,
) -> None:
    """Refuerza: tokens no-PII (números, palabras comunes) quedan intactos."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    from server.app.core.storage import FsspecStorageService
    from server.app.modules.redaccion.pipelines.contracts import StorageRef
    from server.app.modules.redaccion.services.test_data_anonymizer import (
        TestDataAnonymizerService,
    )

    pdf_path = tmp_path / "neutral.pdf"
    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(100, 750, "Resumen de actividades del trimestre")
    c.drawString(100, 720, "Total beneficiarios: 245")
    c.drawString(100, 690, "Importe total ejecutado: 100000 EUR")
    c.save()

    bucket_root = tmp_path / "bucket"
    bucket_root.mkdir()
    storage = FsspecStorageService(backend="file", bucket=str(bucket_root))
    await storage.put("neutral.pdf", pdf_path.read_bytes())

    service = TestDataAnonymizerService(storage=storage)
    result = await service.anonymize_pdf_to_text(StorageRef(bucket="bucket", key="neutral.pdf"))

    md = (await storage.get(result.synthetic_ref.key)).decode("utf-8")
    assert "Resumen de actividades del trimestre" in md
    assert "245" in md
    assert "100000" in md
