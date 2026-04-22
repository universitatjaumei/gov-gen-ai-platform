# client_app/tests/unit/test_ner_anonymizer.py
from app.modules.privacy.anonymizer import AnonymizationContext


def test_ner_detects_person_names():
    """Verificar deteccion NER de nombres propios"""
    ctx = AnonymizationContext()
    txt = "Juan Perez firmo con Maria Lopez el contrato."

    ents = ctx._detect_with_ner(txt)
    person_names = [e for e in ents if e.type == "PERSON_NAME"]

    assert len(person_names) >= 2
    assert any("Juan" in e.text for e in person_names)
    assert any("Maria" in e.text or "María" in e.text for e in person_names)


def test_ner_fallback_without_model():
    """Verificar que funciona sin modelo spaCy (degradacion elegante)"""
    ctx = AnonymizationContext()
    ctx._nlp = None  # Simular ausencia de modelo

    txt = "Juan Perez tiene DNI 12345678Z"
    ents = ctx._detect_with_ner(txt)

    # No debe crashear, solo retornar lista vacia
    assert ents == []

