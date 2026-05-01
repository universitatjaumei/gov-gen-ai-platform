import re

def main():
    with open('PLAN_TDD_DETALLADO.md', 'r', encoding='utf-8') as f:
        text = f.read()

    # Split by FASE headers. We use a regex that captures the headers and their content.
    # But simpler: just split by "^## FASE "
    parts = re.split(r'^(?=## FASE )', text, flags=re.MULTILINE)
    
    new_parts = []
    fase_4b_content = ""
    
    # 1. Extract Fase 4B
    for p in parts:
        if p.startswith('## FASE 4B'):
            fase_4b_content = p.replace('## FASE 4B', '## FASE 9B')
        else:
            new_parts.append(p)
            
    # Reassemble and insert 9B after Fase 9
    parts = new_parts
    new_parts = []
    for p in parts:
        new_parts.append(p)
        if p.startswith('## FASE 9:'):
            new_parts.append(fase_4b_content)
            
    text = "".join(new_parts)
    
    # 2. Compact Fases 1 to 8
    def compact_fase(match):
        header = match.group(1)
        # Keep the header, add a completed message, discard the rest
        return f"{header}\n\n> \u2705 **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.\n\n"

    # Fases 1 to 8 (ignoring 4B which is now 9B)
    for i in range(1, 9):
        # Match from "## FASE {i}..." up to the next "## FASE" or end of file
        pattern = rf'^(## FASE {i}:.*?)\n.*?(?=^## FASE |\Z)'
        text = re.sub(pattern, compact_fase, text, flags=re.MULTILINE | re.DOTALL)
        
    # 3. Prompt 9.16
    text = re.sub(
        r'(### Prompt 9\.16 - Módulo RPA.*?\n)(.*?(?=^###|^##|\Z))',
        r'\1\n**Objetivo**: Preparar la estructura básica para el RPA, pero **SIN implementar Playwright local**. La migración del módulo RPA local queda diferida. En esta fase NO se implementará Playwright local. El RPA se abordará exclusivamente como un *Worker en el servidor* para casos puntuales (ver Fase 21).\n\n',
        text,
        flags=re.MULTILINE | re.DOTALL
    )

    # 4. Prompt A.2
    text = re.sub(
        r'(### Prompt A\.2 - Servicio de Embeddings.*?\n)(.*?(?=^###|^##|\Z))',
        r'\1\n**Objetivo**: Verificar que el servicio de embeddings BGE-M3 local (implementado en la Fase 5B) funciona correctamente con el sistema completo. (Google/Vertex AI ha sido descartado a favor del modelo local BAAI/bge-m3).\n\n',
        text,
        flags=re.MULTILINE | re.DOTALL
    )

    # 5. Bloque 9.C
    if '### Bloque 9.C' in text or '## Bloque 9.C' in text:
        pass # We will just search for the specific instruction about deleting NiceGUI
        
    text = text.replace('eliminación del sistema NiceGUI', 'migración del sistema NiceGUI hacia React')
    text = text.replace('borrado del sistema NiceGUI', 'traslado del sistema NiceGUI a _legacy_nicegui')
    
    prompt_9c0 = """### Prompt 9.C.0 - Mapeo y Auditoría de Migración

**Objetivo**: Generar un mapa de dependencias entre la UI actual (NiceGUI) y la lógica de negocio profunda antes de iniciar la migración.
**Instrucciones**:
1. Analizar los directorios de NiceGUI y rastrear todas las importaciones hacia módulos compartidos.
2. Identificar qué partes de NiceGUI se deben trasladar a la carpeta `server/app/_legacy_nicegui/` para preservar la lógica que se utilizará en las Fases 13-18.
3. **Regla de oro**: NO borrar ningún archivo de NiceGUI. Moverlos a `_legacy_nicegui/` para mantenerlos como referencia viva. La eliminación definitiva solo ocurrirá al final de la Fase 18.

"""
    # Insert 9.C.0 before 9.C.1
    text = text.replace('### Prompt 9.C.1', prompt_9c0 + '### Prompt 9.C.1')
    
    # 6. Fase 10 Title
    text = text.replace('## FASE 10: Sistema de Plantillas y Temas Personalizables', '## FASE 10: Sistema de Plantillas y Temas (Chatbots, Panel Admin, Partners y UI Principal)')

    # 7. Fase 12 y 19 MCP
    text = text.replace('## FASE 12: Gestor de Expedientes — NUEVA', '## FASE 12: Gestor de Expedientes (Integración vía MCP)')
    text = text.replace('## FASE 19: Adaptadores UJI + Gestión 400 + Capa ENI/ENS', '## FASE 19: Adaptadores UJI + Gestión 400 + Capa ENI/ENS (Servidores MCP)')
    
    with open('PLAN_TDD_DETALLADO.md', 'w', encoding='utf-8') as f:
        f.write(text)

main()
