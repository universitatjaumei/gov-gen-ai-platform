import re

def main():
    with open('PLAN_TDD_DETALLADO.md', 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. BLOQUE 9C
    prompt_9c0 = """

### Prompt 9.C.0 - Mapeo y Auditoría de Migración

**Objetivo**: Generar un mapa de dependencias entre la UI actual (NiceGUI) y la lógica de negocio profunda antes de iniciar la migración.
**Instrucciones**:
1. Analizar los directorios de NiceGUI y rastrear todas las importaciones hacia módulos compartidos.
2. Identificar qué partes de NiceGUI se deben trasladar a la carpeta `server/app/_legacy_nicegui/` para preservar la lógica que se utilizará en las Fases 13-18.
3. **Regla de oro**: NO borrar ningún archivo de NiceGUI. Moverlos a `_legacy_nicegui/` para mantenerlos como referencia viva. La eliminación definitiva solo ocurrirá al final de la Fase 18.

"""
    # Insert 9C0 if not already there
    if 'Prompt 9.C.0' not in text:
        text = text.replace('## BLOQUE 9C - Automatización (migración NiceGUI)', '## BLOQUE 9C - Automatización (migración NiceGUI a _legacy_nicegui)\n' + prompt_9c0)
    
    # Replace NiceGUI cleaning terms
    text = text.replace('Limpieza NiceGUI restante', 'Traslado final NiceGUI a _legacy_nicegui')
    text = text.replace('Limpieza NiceGUI', 'Traslado NiceGUI a _legacy_nicegui')
    text = text.replace('borrado del equivalente NiceGUI', 'traslado del equivalente NiceGUI a _legacy_nicegui')
    text = text.replace('borrado del fichero NiceGUI equivalente', 'traslado del fichero NiceGUI equivalente a _legacy_nicegui')
    text = text.replace('eliminado (no comentado, no archivado)', 'movido a _legacy_nicegui (no borrado)')

    # 2. Add MCP details to Fase 12 and 19
    mcp_note_12 = "\n> **Arquitectura MCP**: La integración con el Gestor de Expedientes legacy se realizará exponiendo dicho sistema como un Servidor MCP (Model Context Protocol) que GovGenAI consumirá como cliente agnóstico. Esto aísla la plataforma de las especificidades del sistema antiguo.\n"
    text = re.sub(r'(## FASE 12: Gestor de Expedientes.*?)\n', r'\1\n' + mcp_note_12, text, count=1)

    mcp_note_19 = "\n> **Arquitectura MCP**: Se desarrollarán Servidores MCP para UJI, Gestión 400 y ENI/ENS, estandarizando la integración con la capa de inteligencia artificial.\n"
    text = re.sub(r'(## FASE 19: Adaptadores UJI.*?)\n', r'\1\n' + mcp_note_19, text, count=1)

    # 3. Prompt A.2 Embeddings update
    text = re.sub(
        r'(### Prompt A\.2 - Servicio de Embeddings.*?\n).*?(?=^###|^##|\Z)',
        r'\1\n**Objetivo**: Verificar que el servicio de embeddings BGE-M3 local (implementado en la Fase 5B) funciona correctamente con el sistema completo. (La implementación inicial basada en Google/Vertex AI fue descartada a favor del modelo local BAAI/bge-m3 para asegurar la privacidad Zero-Knowledge).\n\n',
        text,
        flags=re.MULTILINE | re.DOTALL
    )

    with open('PLAN_TDD_DETALLADO.md', 'w', encoding='utf-8') as f:
        f.write(text)

main()
