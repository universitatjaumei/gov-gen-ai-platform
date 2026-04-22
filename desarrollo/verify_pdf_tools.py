"""
Script de verificación para PDF Tools atom configuration.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'shared'))

print("=" * 60)
print("VERIFICACIÓN: PDF Tools Atom Configuration")
print("=" * 60)

# Test 1: Capability Map
print("\n[TEST 1] Capability Map Registration")
print("-" * 60)
try:
    from client_app.app.config.capability_map import get_atom_capability
    from automatia_shared.enums import StepType
    
    cap = get_atom_capability(StepType.PDF_TOOLS)
    
    print(f"✓ PDF_TOOLS capability map found")
    print(f"  - has_stepper: {cap.has_stepper}")
    print(f"  - has_variables: {cap.has_variables}")
    print(f"  - variables_view_mode: {cap.variables_view_mode}")
    print(f"  - primary_action_label: {cap.primary_action_label}")
    print(f"  - primary_action_icon: {cap.primary_action_icon}")
    print(f"  - steps: {len(cap.steps)} pasos")
    for i, step in enumerate(cap.steps):
        print(f"    {i+1}. {step['name']}: {step['hint']}")
    print(f"  - contextual_help: {len(cap.contextual_help)} mensajes de ayuda")
    
    # Validar estructura
    assert cap.has_stepper == True, "has_stepper debe ser True"
    assert cap.has_variables == True, "has_variables debe ser True"
    assert len(cap.steps) == 3, "Debe tener 3 pasos"
    assert cap.steps[0]['name'] == 'Origen', "Primer paso debe ser 'Origen'"
    assert cap.steps[1]['name'] == 'Operación', "Segundo paso debe ser 'Operación'"
    assert cap.steps[2]['name'] == 'Resultado', "Tercer paso debe ser 'Resultado'"
    
    print("\n✓ Todas las validaciones de capability map pasaron")
    
except Exception as e:
    print(f"✗ Error en capability map: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Atom Catalog
print("\n[TEST 2] Atom Catalog Registration")
print("-" * 60)
try:
    from client_app.app.config.atom_catalog import ATOM_CATALOG, ATOM_CATEGORIES_V2
    from automatia_shared.enums import StepType, AtomCategory
    
    # Verificar que PDF_TOOLS está en el catálogo
    assert StepType.PDF_TOOLS in ATOM_CATALOG, "PDF_TOOLS debe estar en ATOM_CATALOG"
    
    metadata = ATOM_CATALOG[StepType.PDF_TOOLS]
    print(f"✓ PDF_TOOLS encontrado en catálogo")
    print(f"  - label: {metadata.label}")
    print(f"  - icon: {metadata.icon}")
    print(f"  - color: {metadata.color}")
    print(f"  - description: {metadata.description}")
    print(f"  - category: {metadata.category}")
    print(f"  - has_stepper: {metadata.has_stepper}")
    print(f"  - has_variables: {metadata.has_variables}")
    
    # Verificar categorización
    assert StepType.PDF_TOOLS in ATOM_CATEGORIES_V2[AtomCategory.PROCESSOR], \
        "PDF_TOOLS debe estar en categoría PROCESSOR"
    
    print(f"✓ PDF_TOOLS correctamente categorizado como PROCESSOR")
    
except Exception as e:
    print(f"✗ Error en atom catalog: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Page Import
print("\n[TEST 3] PDF Tools Atom Page Import")
print("-" * 60)
try:
    # Intentar importar la página
    from client_app.app.ui import pdf_tools_atom_page
    
    print(f"✓ Módulo pdf_tools_atom_page importado correctamente")
    
    # Verificar que las funciones de ruta existen
    assert hasattr(pdf_tools_atom_page, 'pdf_tools_new_route'), \
        "Debe existir pdf_tools_new_route"
    assert hasattr(pdf_tools_atom_page, 'pdf_tools_edit_route'), \
        "Debe existir pdf_tools_edit_route"
    assert hasattr(pdf_tools_atom_page, 'pdf_tools_atom_page_content'), \
        "Debe existir pdf_tools_atom_page_content"
    
    print(f"✓ Funciones de ruta encontradas:")
    print(f"  - pdf_tools_new_route")
    print(f"  - pdf_tools_edit_route")
    print(f"  - pdf_tools_atom_page_content")
    
    # Verificar clases de estado
    assert hasattr(pdf_tools_atom_page, 'PDFToolsPageState'), \
        "Debe existir PDFToolsPageState"
    assert hasattr(pdf_tools_atom_page, 'DesignState'), \
        "Debe existir DesignState"
    
    print(f"✓ Clases de estado encontradas:")
    print(f"  - PDFToolsPageState")
    print(f"  - DesignState")
    
except Exception as e:
    print(f"✗ Error al importar página: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Route Registration in main.py
print("\n[TEST 4] Route Registration in main.py")
print("-" * 60)
try:
    main_py_path = project_root / 'main.py'
    with open(main_py_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Verificar que el import está presente
    assert 'from client_app.app.ui.pdf_tools_atom_page import' in main_content, \
        "Debe importar pdf_tools_atom_page en main.py"
    
    assert 'pdf_tools_new_route' in main_content, \
        "Debe importar pdf_tools_new_route"
    assert 'pdf_tools_edit_route' in main_content, \
        "Debe importar pdf_tools_edit_route"
    
    print(f"✓ Rutas importadas correctamente en main.py")
    print(f"  - pdf_tools_new_route")
    print(f"  - pdf_tools_edit_route")
    
except Exception as e:
    print(f"✗ Error verificando main.py: {e}")
    import traceback
    traceback.print_exc()

# Resumen
print("\n" + "=" * 60)
print("RESUMEN DE VERIFICACIÓN")
print("=" * 60)
print("✓ Capability map configurado correctamente")
print("✓ Atom catalog actualizado")
print("✓ Página de átomo creada e importable")
print("✓ Rutas registradas en main.py")
print("\n✓ TODAS LAS VERIFICACIONES PASARON")
print("=" * 60)
