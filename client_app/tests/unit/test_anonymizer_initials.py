
import pytest
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

class TestAnonymizerInitials:
    def test_anonymize_name_initials(self):
        """Verificar que el modo INITIALS convierte nombres a iniciales."""
        ctx = AnonymizationContext()
        
        # Caso simple
        name = "Juan Pérez García"
        result = ctx.anonymize_name(name, mode='INITIALS')
        assert result == "J. P. G.", f"Esperado 'J. P. G.', obtenido '{result}'"
        
        # Caso con espacios extra
        name_spaces = "  Maria   Luisa  "
        result = ctx.anonymize_name(name_spaces, mode='INITIALS')
        assert result == "M. L.", f"Esperado 'M. L.', obtenido '{result}'"
        
        # Caso string vacío
        result = ctx.anonymize_name("", mode='INITIALS')
        assert result == "", "String vacío debería retornar string vacío" # Ojo: la implementación en prompt dice return _mask_generic si not value
        
    def test_anonymize_name_mask_default(self):
        """Verificar que el modo por defecto es MASK (asteriscos)."""
        ctx = AnonymizationContext()
        name = "Carlos Ruiz"
        
        # Default arg
        result = ctx.anonymize_name(name)
        # _mask_generic para PERSON_NAME: "C***** R***" (depende de la implementación existente)
        # La implementación actual en _mask_generic para PERSON_NAME hace: w[0] + "*" * (len(w)-1)
        
        expected_parts = ["C*****", "R***"]
        parts = result.split()
        assert len(parts) == 2
        assert parts[0] == "C*****"
        assert parts[1] == "R***"
        
    def test_anonymize_name_explicit_mask(self):
        """Verificar que el modo MASK funciona explícitamente."""
        ctx = AnonymizationContext()
        name = "Ana"
        result = ctx.anonymize_name(name, mode='MASK')
        assert result == "A**", f"Esperado 'A**', obtenido '{result}'"

    def test_anonymize_dataframe_initials(self):
        """Verificar que anonymize_dataframe usa INITIALS correctamente."""
        import pandas as pd
        ctx = AnonymizationContext()
        df = pd.DataFrame({'Nombre': ['Juan Pérez', 'Ana Gómez']})
        
        config = {
            'Nombre': {'type': 'PERSON', 'mode': 'INITIALS'}
        }
        
        result_df = ctx.anonymize_dataframe(df, config)
        
        assert result_df['Nombre'].iloc[0] == "J. P."
        assert result_df['Nombre'].iloc[1] == "A. G."

if __name__ == "__main__":
    t = TestAnonymizerInitials()
    try:
        t.test_anonymize_name_initials()
        print("✅ Initials mode verificado.")
        t.test_anonymize_name_mask_default()
        print("✅ Default mask mode verificado.")
        t.test_anonymize_name_explicit_mask()
        print("✅ Explicit mask mode verificado.")
    except Exception as e:
        print(f"❌ Fallo en las pruebas de iniciales: {e}")
        exit(1)
