
import pytest
from client_app.app.menu_config import get_menu_structure

class TestMenuStructure:
    def test_utilities_section(self):
        """Verificar que la sección 'Utilidades' existe y contiene los items correctos."""
        menu = get_menu_structure()
        
        # Verificar que existe la clave 'utilidades'
        assert 'utilidades' in menu, "La sección 'Utilidades' no se encontró en el menú."
        
        utils_section = menu['utilidades']
        assert utils_section['type'] == 'expansion'
        assert utils_section['label'] == 'Utilidades'
        
        items = utils_section['items']
        routes = [item['route'] for item in items]
        
        # Verificar items específicos
        assert '/anonymizer' in routes, "La ruta '/anonymizer' debería estar en 'Utilidades'."
        assert '/reports/designer' in routes, "La ruta '/reports/designer' debería estar en 'Utilidades'."
        
    def test_anonymizer_moved_from_automations(self):
        """Verificar que 'Anonimización' ya no está en 'Automatizaciones'."""
        menu = get_menu_structure()
        
        if 'automatizaciones' not in menu:
            # Si se eliminó la sección automatizaciones (poco probable), también es válido
            return

        auto_section = menu['automatizaciones']
        items = auto_section['items']
        routes = [item['route'] for item in items]
        
        assert '/anonymizer' not in routes, "La ruta '/anonymizer' no debería estar en 'Automatizaciones'."

if __name__ == "__main__":
    t = TestMenuStructure()
    try:
        t.test_utilities_section()
        print("✅ Sección Utilidades verificada correctamente.")
        t.test_anonymizer_moved_from_automations()
        print("✅ Anonimizador movido correctamente.")
    except Exception as e:
        print(f"❌ Fallo en las pruebas de menú: {e}")
        exit(1)
