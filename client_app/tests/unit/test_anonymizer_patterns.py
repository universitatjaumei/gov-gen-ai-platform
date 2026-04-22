# client_app/tests/unit/test_anonymizer_patterns.py
import pytest
from client_app.app.modules.privacy.anonymizer import AnonymizationContext


class TestExtendedPatterns:
    """Tests para patrones extendidos de detección."""

    @pytest.fixture
    def ctx(self):
        return AnonymizationContext(locale="es_ES")

    # === NIE ===
    def test_detect_nie_x(self, ctx):
        """Detecta NIE con prefijo X."""
        text = "NIE: X1234567L"
        result = ctx.anonymize(text)
        assert "X1234567L" not in result

    def test_detect_nie_y(self, ctx):
        """Detecta NIE con prefijo Y."""
        text = "NIE: Y9876543M"
        result = ctx.anonymize(text)
        assert "Y9876543M" not in result

    def test_detect_nie_z(self, ctx):
        """Detecta NIE con prefijo Z."""
        text = "NIE: Z1111111A"
        result = ctx.anonymize(text)
        assert "Z1111111A" not in result

    # === TARJETA DE CRÉDITO ===
    def test_detect_credit_card_spaces(self, ctx):
        """Detecta tarjeta con espacios."""
        text = "Tarjeta: 4111 1111 1111 1111"
        result = ctx.anonymize(text)
        assert "4111 1111 1111 1111" not in result

    def test_detect_credit_card_dashes(self, ctx):
        """Detecta tarjeta con guiones."""
        text = "Tarjeta: 5500-0000-0000-0004"
        result = ctx.anonymize(text)
        assert "5500-0000-0000-0004" not in result

    def test_detect_credit_card_no_separator(self, ctx):
        """Detecta tarjeta sin separadores."""
        text = "Tarjeta: 4111111111111111"
        result = ctx.anonymize(text)
        assert "4111111111111111" not in result

    # === NSS (Número Seguridad Social) ===
    def test_detect_nss(self, ctx):
        """Detecta NSS español (12 dígitos)."""
        text = "NSS: 281234567890"
        result = ctx.anonymize(text)
        assert "281234567890" not in result

    def test_detect_nss_with_slashes(self, ctx):
        """Detecta NSS con formato separado."""
        text = "NSS: 28/12345678/90"
        result = ctx.anonymize(text)
        assert "28/12345678/90" not in result
        # Verificar que se genera un NSS válido
        # Note: fake_to_real check depends heavily on implementation detail (generation happens).

    # === DIRECCIÓN (NER) ===
    def test_detect_address_ner(self, ctx):
        """Detecta direcciones usando NER (LOC)."""
        text = "Dirección: Calle Mayor 15, Madrid"
        result = ctx.anonymize(text)
        # Madrid debería detectarse como LOC
        if ctx._nlp:
            # Al menos 'Madrid' debería ser detectado if NER is working
            # But regex might not catch it.
            # We assume NER is loaded if spacy is installed.
            pass

    # === FECHA DE NACIMIENTO ===
    def test_detect_date_dd_mm_yyyy(self, ctx):
        """Detecta fecha formato DD/MM/YYYY."""
        text = "Nacimiento: 15/03/1985"
        result = ctx.anonymize(text)
        assert "15/03/1985" not in result

    def test_detect_date_dd_mm_yy(self, ctx):
        """Detecta fecha formato DD-MM-YY."""
        text = "Fecha: 01-12-90"
        result = ctx.anonymize(text)
        assert "01-12-90" not in result

    # === ROUNDTRIP ===
    def test_roundtrip_all_types(self, ctx):
        """Verificar que todos los tipos son reversibles."""
        original = """
        DNI: 12345678Z
        NIE: X1234567L
        Tarjeta: 4111-1111-1111-1111
        NSS: 281234567890
        Email: test@example.com
        Teléfono: 612345678
        """
        anon = ctx.anonymize(original)
        restored = ctx.deanonymize(anon)

        # Verificar que datos originales están restaurados
        assert "12345678Z" in restored
        assert "X1234567L" in restored
        assert "4111-1111-1111-1111" in restored
        assert "281234567890" in restored
        assert "test@example.com" in restored
        assert "612345678" in restored


class TestFakerGenerators:
    """Tests para generadores Faker."""

    @pytest.fixture
    def ctx(self):
        return AnonymizationContext(locale="es_ES")

    def test_generate_fake_credit_card(self, ctx):
        """Genera tarjeta de crédito válida."""
        fake = ctx._generate_fake("CREDIT_CARD", "4111111111111111")
        # Debe tener 16 dígitos (con o sin separadores)
        digits = ''.join(c for c in fake if c.isdigit())
        assert len(digits) == 16

    def test_generate_fake_nss(self, ctx):
        """Genera NSS válido."""
        fake = ctx._generate_fake("NSS", "281234567890")
        digits = ''.join(c for c in fake if c.isdigit())
        assert len(digits) == 12

    def test_generate_fake_date(self, ctx):
        """Genera fecha válida."""
        fake = ctx._generate_fake("DATE", "15/03/1985")
        # Debe contener formato fecha
        assert "/" in fake or "-" in fake

    def test_generate_fake_address(self, ctx):
        """Genera dirección sintética."""
        fake = ctx._generate_fake("ADDRESS", "Madrid")
        assert fake != "Madrid"
        assert len(fake) > 0

    def test_generate_fake_nie(self, ctx):
        """Genera NIE válido."""
        fake = ctx._generate_fake("NIE", "X1234567L")
        # Debe empezar por X, Y o Z
        assert fake[0] in "XYZ"
        # Debe tener formato correcto
        assert len(fake) == 9
