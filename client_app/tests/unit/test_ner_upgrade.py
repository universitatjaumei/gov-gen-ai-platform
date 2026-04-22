
import pytest
from client_app.app.modules.privacy.anonymizer import AnonymizationContext, _NLP
import spacy

class TestNerUpgrade:
    def test_model_loading(self):
        """Verificar que se carga el modelo medium y no el small."""
        # Verificar que _NLP existe y es el modelo correcto
        assert _NLP is not None, "El modelo spaCy no se ha cargado."
        assert _NLP.meta['name'] == 'core_news_md', f"Se esperaba 'core_news_md', pero se obtuvo {_NLP.meta['name']}"
        assert _NLP.meta['lang'] == 'es', "El idioma del modelo debe ser español."

    def test_small_model_removed(self):
        """Verificar que el modelo small ha sido eliminado del sistema."""
        with pytest.raises(OSError):
            spacy.load("es_core_news_sm")

    def test_ner_detection_quality(self):
        """Verificar la detección de entidades en textos complejos con el modelo medium."""
        ctx = AnonymizationContext()
        
        # Texto complejo con nombres, cargos y direcciones
        text = "El Director General, Sr. Juan Pérez García, se reunió en la Calle Mayor 123 de Madrid."
        
        entities = ctx._detect_with_ner(text)
        
        # Verificar que se detectan las entidades clave
        # El modelo medium es más preciso y captura "Sr. Juan Pérez García" y "Calle Mayor 123 de Madrid"
        
        detected_texts = [e.text for e in entities]
        detected_types = [e.type for e in entities]
        
        # Flexibilidad en la detección: buscamos substrings clave si la detección exacta varía
        # Pero el objetivo es demostrar que detecta MEJOR que el small.
        
        # Validar Nombre
        person_match = any("Juan Pérez García" in t for t in detected_texts)
        assert person_match, f"No se detectó a Juan Pérez García. Detectado: {detected_texts}"
        
        # Validar Dirección 
        # El modelo medium suele capturar la calle completa
        address_match = any("Madrid" in t for t in detected_texts)
        assert address_match, f"No se detectó Madrid. Detectado: {detected_texts}"

if __name__ == "__main__":
    # Script manual execution
    try:
        t = TestNerUpgrade()
        t.test_model_loading()
        print("✅ Validación de Carga: Modelo medium cargado correctamente.")
        t.test_small_model_removed()
        print("✅ Integridad de Espacio: Modelo small no encontrado.")
        t.test_ner_detection_quality()
        print("✅ Verificación de Detección: Detección de entidades correcta.")
    except Exception as e:
        print(f"❌ Fallo en las pruebas: {e}")
        exit(1)
