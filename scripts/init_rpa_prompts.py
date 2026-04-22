import asyncio
import sys
import os

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database.db import server_engine, init_db
from app.database.models import ExtractionServiceConfig

# 1. Prompt de Análisis (Generalización)
PROMPT_ANALYSIS = """
Eres un experto en automatización RPA y Playwright.

OBJETIVO:
Convertir un log de acciones de usuario ("recorded_actions") en un Playbook generalizado ROBUSTO.

CONTEXTO DE DATOS (Variables disponibles):
{context_string}

ACCIONES GRABADAS:
{logs_context}

INSTRUCCIONES CLAVE (SELECTORES SEMÁNTICOS):
El log ahora incluye información 'semantic' (etiquetas, texto, placeholders).
TU PRIORIDAD ABSOLUTA es generar selectores RESILIENTES al cambio. EVITA selectores posicionales frágiles.

JERARQUÍA DE SELECTORES (Usa el primero que aplique):
1. **Playwright explícito**: Si ves un texto claro o label.
   - `text="Guardar"`
   - `role="button", name="Enviar"`
   - `label="Nombre de usuario"`
   - `placeholder="Buscar..."`
2. **XPath Semántico**:
   - `//input[@id='...']` (SOLO si el ID parece "humano" y estable, ej: 'username'. NO uses IDs generados ej: 'input-x9s').
   - `//button[contains(normalize-space(), 'Guardar')]`
   - `//input[preceding-sibling::label[contains(text(), 'Nombre')]]` (o parent label).
3. **Atributos de Test**: `[data-testid="submit-btn"]`
4. **CSS (Últimísimo recurso)**: `#main div:nth-child(2) > input` (MARCAR COMO FRÁGIL).

OTROS REQUISITOS:
1. **Smart Waits**: NO uses `wait` con tiempo fijo (ej: 5000) salvo que sea imposible detectar el estado. PREFIERE `action: "wait", selector: "..."` para esperar a que aparezca un elemento clave (ej: spinner desaparece, o resultado aparece).
2. **Variables**: Si el valor coincide con el contexto {context_string}, usa {{Clave}}.
3. **Archivos**: Si action="setInputFiles", usa `os.path.join(attachments_path, "{{NombreColumna}}")` si coincide con el contexto.
4. **Login**: IGNORA pasos de login si la sesión ya existe.

FORMATO DE PASO ESPERADO:
{
    "selector": "xpath_o_playwright_selector",
    "action": "click" | "fill" | "select" | "navigate" | "wait" | "setInputFiles",
    "value": "valor_o_variable",
    "description": "Explicación semántica (ej: 'Clicar botón Guardar')"
}

Responde SOLO con el JSON.
"""

# 2. Prompt de Refinamiento (Debugging)
PROMPT_REFINEMENT = """
Eres un experto en debugging de Playwright y RPA (Nivel Senior).

OBJETIVO:
Reparar un script de automatización JSON (Playbook) que está fallando.

ESTADO DE LA INFORMACIÓN:
- ¿Tenemos logs de grabación originales?: {hay_logs_originales}

DATOS DE ENTRADA:
1. Contexto de Variables: {ctx_str}
2. Logs de Grabación Originales: {logs_str}
3. Playbook Actual (Con Fallos): {current_pb_str}

SINTOMAS DEL FALLO:
- Error Técnico Reportado: {error_logs}
- Pistas del Humano: 
{feedback_str}

INSTRUCCIONES DE REPARACIÓN:

CASO A) SI TIENES LOGS DE GRABACIÓN (Recuperación):
   - Los logs son la VERDAD ABSOLUTA de lo que quería hacer el usuario.
   - Úsalos para reconstruir el paso que falta o está mal en el Playbook.
   
CASO B) SI NO TIENES LOGS (Mantenimiento Puro):
   - Asume que el 'Playbook Actual' FUNCIONABA BIEN antes, pero la web ha cambiado (Selectores obsoletos, botones movidos).
   - Tu misión es QUIRÚRGICA: Modifica SOLO el paso que ha dado error (mencionado en 'Error Técnico') y sus dependencias directas.
   - NO re-inventes ni re-ordenes el script entero si no es imprescindible.
   - Básate fuertemente en el 'Feedback Humano' para saber qué ha cambiado (ej: "Ahora el botón es azul").

REGLAS GENERALES:
1. Identifica el índice del paso fallido basándote en el error reportado.
2. Genera un JSON válido con la lista completa de pasos corregida.
3. Mantén los pasos que funcionan intactos.

Responde SOLO con el JSON (lista de objetos).
"""

async def init_rpa_prompts():
    print("🚀 Inicializando Prompts RPA en DB...")
    
    # Asegurar tablas
    await init_db()
    
    configs = [
        ExtractionServiceConfig(
            service_id="sys_rpa_analysis",
            name="System: RPA Analysis",
            description="Motor de análisis de grabaciones para generar Playbooks",
            module="rpa",
            target_function="analyze_recording",
            system_prompt_template=PROMPT_ANALYSIS,
            suggested_model="gemini-2.0-flash-exp" # Fast & Smart
        ),
        ExtractionServiceConfig(
            service_id="sys_rpa_refinement",
            name="System: RPA Refinement",
            description="Motor de reparación y debugging de scripts RPA",
            module="rpa",
            target_function="refine_playbook",
            system_prompt_template=PROMPT_REFINEMENT,
            suggested_model="gemini-2.0-flash-exp" # Needs high reasoning context
        )
    ]
    
    async with AsyncSession(server_engine) as session:
        for cfg in configs:
            existing = await session.get(ExtractionServiceConfig, cfg.service_id)
            if existing:
                existing.system_prompt_template = cfg.system_prompt_template
                existing.suggested_model = cfg.suggested_model
                session.add(existing)
                print(f"🔄 Actualizado: {cfg.service_id}")
            else:
                session.add(cfg)
                print(f"✅ Creado: {cfg.service_id}")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(init_rpa_prompts())
