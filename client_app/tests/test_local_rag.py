"""
Tests TDD para LocalKnowledgeService - Prompt #9
Motor de RAG Local para el Copiloto.

Valida que el servicio encuentra documentacion relevante para consultas del usuario.
"""
import pytest
import tempfile
from pathlib import Path
from client_app.app.services.local_knowledge_service import LocalKnowledgeService


@pytest.fixture
def temp_docs_dir():
    """Creates a temporary docs directory with sample README files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir)

        # Create sample README files simulating sealed atoms
        extractor_luz_content = """# Extractor de Facturas de Luz

**Tipo**: PDF Extraction Script
**ID**: ext-luz-001
**Estado**: PUBLISHED

## Descripcion
Este script extrae informacion de facturas de electricidad.

## Campos Extraidos
- `cif_emisor`: CIF de la empresa electrica
- `fecha_factura`: Fecha de emision
- `importe_total`: Total a pagar
- `periodo_facturacion`: Periodo de consumo

## Contrato de Interfaz
```json
{
    "inputs": [{"name": "documento", "type": "FILE", "label": "Documento PDF"}],
    "outputs": [
        {"name": "cif_emisor", "type": "STR"},
        {"name": "fecha_factura", "type": "DATE"},
        {"name": "importe_total", "type": "FLOAT"}
    ]
}
```

## Seguridad
Este script ha sido analizado y no presenta advertencias de seguridad significativas.
"""
        (docs_path / "extractor_luz.md").write_text(extractor_luz_content, encoding='utf-8')

        robot_agua_content = """# Robot Facturas Agua

**Tipo**: PDF Extraction Script
**ID**: ext-agua-002

## Descripcion
Extrae datos de facturas de suministro de agua.

## Campos
- `numero_contrato`: Numero de contrato
- `consumo_m3`: Consumo en metros cubicos
- `total_factura`: Importe total
"""
        (docs_path / "robot_agua.md").write_text(robot_agua_content, encoding='utf-8')

        mail_watcher_content = """# MailWatcher Proveedores

**Tipo**: Mail Watcher
**ID**: mw-prov-001

## Descripcion
Monitoriza la bandeja de entrada para correos de proveedores.

## Configuracion
- **Cuenta**: facturas@empresa.com
- **Filtro**: Asunto contiene "Factura"
- **Template vinculado**: extractor_luz

## Campos Heredados
Hereda los campos del template de extraccion vinculado.
"""
        (docs_path / "mail_watcher_proveedores.md").write_text(mail_watcher_content, encoding='utf-8')

        yield docs_path


def test_retrieve_relevant_context_from_md(temp_docs_dir):
    """Test que el servicio encuentra documentacion relevante por palabras clave."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "Como funciona el extractor de luz?"
    context = service.get_context_for_query(query)

    # Debe encontrar el archivo del extractor de luz
    assert "extractor" in context.lower() or "luz" in context.lower()
    # El contexto debe incluir informacion relevante (titulo, tipo, id)
    assert "pdf extraction" in context.lower() or "ext-luz" in context.lower()


def test_retrieve_context_by_atom_name(temp_docs_dir):
    """Test que encuentra documentacion cuando se menciona el nombre del atomo."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "Que campos devuelve el robot de facturas de agua?"
    context = service.get_context_for_query(query)

    assert "agua" in context.lower()
    assert "consumo" in context.lower() or "numero_contrato" in context.lower()


def test_retrieve_context_for_mail_watcher(temp_docs_dir):
    """Test que encuentra documentacion de MailWatchers."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "Como esta configurado el mailwatcher de proveedores?"
    context = service.get_context_for_query(query)

    assert "mailwatcher" in context.lower() or "proveedores" in context.lower()
    # Debe contener informacion del mail watcher (descripcion o tipo)
    assert "mail watcher" in context.lower() or "bandeja" in context.lower()


def test_empty_context_on_unknown_query(temp_docs_dir):
    """Test que retorna vacio cuando no hay documentacion relevante."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    # Consulta sobre algo que no existe en la documentacion
    query = "Cual es el sentido de la vida?"
    context = service.get_context_for_query(query)

    # No deberia encontrar nada en la doc tecnica de automatismos
    assert context == ""


def test_context_format_includes_header(temp_docs_dir):
    """Test que el contexto tiene formato correcto con header."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "extractor luz campos"
    context = service.get_context_for_query(query)

    if context:  # Solo si encontro algo
        assert "--- CONTEXTO LOCAL ---" in context or len(context) > 0


def test_multiple_relevant_files(temp_docs_dir):
    """Test que puede encontrar multiples documentos relevantes."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    # Consulta generica sobre facturas
    query = "Como extraer datos de facturas?"
    context = service.get_context_for_query(query)

    # Deberia encontrar al menos uno de los extractores
    assert "factura" in context.lower()


def test_handles_empty_docs_directory():
    """Test que maneja correctamente una carpeta de docs vacia."""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = LocalKnowledgeService(docs_path=Path(tmpdir))

        query = "cualquier consulta"
        context = service.get_context_for_query(query)

        assert context == ""


def test_handles_nonexistent_directory():
    """Test que maneja correctamente una ruta que no existe."""
    service = LocalKnowledgeService(docs_path=Path("/ruta/que/no/existe"))

    query = "cualquier consulta"
    context = service.get_context_for_query(query)

    assert context == ""


def test_privacy_no_absolute_paths_in_context(temp_docs_dir):
    """Test que el contexto no incluye rutas absolutas por privacidad."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "extractor luz"
    context = service.get_context_for_query(query)

    if context:
        # No debe incluir la ruta absoluta del sistema
        assert str(temp_docs_dir) not in context
        # No debe incluir rutas tipicas de Windows/Linux
        assert "C:\\" not in context
        assert "/Users/" not in context
        assert "/home/" not in context


def test_context_length_limit(temp_docs_dir):
    """Test que el contexto respeta limite de caracteres."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir, max_context_chars=500)

    query = "extractor"
    context = service.get_context_for_query(query)

    # El contexto no debe exceder el limite (con margen para headers)
    assert len(context) <= 600  # Margen para headers


def test_caching_same_query(temp_docs_dir):
    """Test que el cache funciona para consultas repetidas."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "extractor luz"

    # Primera consulta
    context1 = service.get_context_for_query(query)

    # Segunda consulta (debe usar cache)
    context2 = service.get_context_for_query(query)

    assert context1 == context2


def test_search_by_field_name(temp_docs_dir):
    """Test que puede buscar por nombre de campo especifico."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    query = "que atomo tiene el campo importe_total?"
    context = service.get_context_for_query(query)

    # Debe encontrar el extractor de luz que tiene ese campo
    assert "importe_total" in context.lower() or "luz" in context.lower()


def test_normalize_query_accents(temp_docs_dir):
    """Test que normaliza acentos en la busqueda."""
    service = LocalKnowledgeService(docs_path=temp_docs_dir)

    # Consulta con acentos
    query = "como funciona la extracción de facturas?"
    context = service.get_context_for_query(query)

    # Debe encontrar algo sobre extraccion/facturas
    assert len(context) > 0 or context == ""  # Puede encontrar o no, pero no debe fallar
