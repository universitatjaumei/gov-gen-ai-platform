# client_app/tests/unit/test_anonymizer_extended.py
import pytest
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

class TestAnonymizerExtended:
    """Tests para extension de modos (Masking vs Faker)."""

    def setup_method(self):
        self.ctx = AnonymizationContext()

    def test_email_masking(self):
        """Verificar enmascaramiento de email."""
        email = "usuario.prueba@dominio.com"
        masked = self.ctx._mask_generic("EMAIL", email)
        # Esperado: u***@d***.com o similar
        assert "@" in masked
        assert "*" in masked
        assert masked != email

    def test_phone_masking(self):
        """Verificar enmascaramiento de telefono."""
        phone = "612345678"
        masked = self.ctx._mask_generic("PHONE", phone)
        # Esperado: 6********
        assert masked.startswith("6") or masked.startswith("*")
        assert "*" in masked
        assert len(masked) == len(phone) # Masking usually preserves length or fixed width

    def test_name_masking(self):
        """Verificar enmascaramiento de nombre."""
        name = "Juan Pérez"
        masked = self.ctx._mask_generic("PERSON_NAME", name)
        # Esperado: J*** P***
        assert "*" in masked
        assert len(masked) > 0

    def test_anonymize_dataframe_masking_mode(self):
        """Verificar que el DF respeta el modo MASK global."""
        import pandas as pd
        df = pd.DataFrame({
            "email": ["test@test.com"],
            "nombre": ["Juan"]
        })
        
        config = {
            "email": {"type": "EMAIL", "mode": "MASK"},
            "nombre": {"type": "PERSON_NAME", "mode": "MASK"}
        }
        
        result_df = self.ctx.anonymize_dataframe(df, config)
        
        email_val = result_df.iloc[0]["email"]
        nome_val = result_df.iloc[0]["nombre"]
        
        assert "*" in email_val, f"Email no enmascarado: {email_val}"
        assert "*" in nome_val, f"Nombre no enmascarado: {nome_val}"
        assert "@" in email_val # Preserve structure

    def test_anonymize_dataframe_faker_mode(self):
        """Verificar que el DF respeta el modo FAKER global."""
        import pandas as pd
        df = pd.DataFrame({
            "email": ["test@test.com"]
        })
        
        config = {
            "email": {"type": "EMAIL", "mode": "FAKER"}
        }
        
        result_df = self.ctx.anonymize_dataframe(df, config)
        email_val = result_df.iloc[0]["email"]
        
        assert "*" not in email_val, "Faker no deberia usar asteriscos"
        assert "@" in email_val
        assert email_val != "test@test.com"

