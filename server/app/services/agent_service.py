"""
Servicio de Agentes - Envoltorio para agentes autónomos basados en navegador.

Proporciona la capacidad de ejecutar tareas complejas de varios pasos
utilizando la librería browser-use, integrándose con el motor RPA de AutomatIA.
"""

from typing import Optional
from dataclasses import dataclass

# Playwright
from playwright.async_api import BrowserContext

# Database / Config
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import AIConfig

# Services
from server.app.services.api_key_service import get_api_key

# External Libs (Browser Use & LangChain)
# These libraries may not be installed in all environments
try:
    from browser_use import Agent
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI
except ImportError:
    print(
        "[AgentService] browser-use or langchain not installed. Agent functionality unavailable."
    )
    Agent = None


@dataclass
class AgentResult:
    success: bool
    output: str
    error: Optional[str] = None
    action_log: Optional[str] = None


class BrowserAgentWrapper:
    """
    Envoltorio para agentes autónomos (browser-use) vinculados a RPA.

    Permite "enganchar" un agente inteligente a un contexto de navegador
    Playwright existente para realizar misiones autónomas (ej: "Busca el
    CIF indicado y descarga la última factura").
    """

    async def _get_supervision_llm(self):
        """
        Configura el modelo de lenguaje de Supervisión (Tier 3-4) para el agente.

        Recupera la configuración de 'supervision' desde la base de datos para
        instanciar el objeto Chat adecuado de LangChain (Google o OpenAI/OpenRouter).

        Returns:
            BaseChatModel: Instancia del modelo de lenguaje configurado.
        """
        async with AsyncSession(server_engine) as session:
            stmt = select(AIConfig).where(AIConfig.role_key == "supervision")
            res = await session.exec(stmt)
            config = res.first()

            if config:
                provider = config.provider
                model_id = config.model_id
                print(
                    f"[AgentService] Loaded from DB: provider={provider}, model={model_id}"
                )
            else:
                # Default fallback if not configured - log warning
                provider = "google"
                model_id = "gemini-2.0-flash-exp"
                print(
                    "[AgentService] WARNING: Role 'supervision' NOT FOUND in DB. Using hardcoded fallback (google)."
                )

        print(f"[AgentService] Usando modelo de supervision: {provider}/{model_id}")

        if provider == "google":
            api_key = await get_api_key("google")
            if not api_key:
                raise ValueError("Google API Key no encontrada")

            return ChatGoogleGenerativeAI(model=model_id, google_api_key=api_key)

        elif provider == "openrouter" or provider == "openai":
            api_key = await get_api_key(
                "openrouter"
            )  # Ojo: api_key_service usa 'openrouter' como key name
            if not api_key:
                raise ValueError("OpenRouter API Key no encontrada")

            return ChatOpenAI(
                model=model_id,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
                if provider == "openrouter"
                else None,
            )

        else:
            raise ValueError(f"Proveedor no soportado para Agentes: {provider}")

    async def run_agent_task(
        self, context: BrowserContext, task_instruction: str
    ) -> AgentResult:
        """
        Ejecuta una misión autónoma sobre el contexto de navegación actual.

        Args:
            context: El contexto de Playwright donde el agente debe actuar.
            task_instruction: Descripción en lenguaje natural de la tarea.

        Returns:
            AgentResult: Objeto con el estado de éxito, salida y logs de acción.
        """
        if not Agent:
            return AgentResult(False, "", error="Libreria browser_use no disponible.")

        print(f"[AgentService] Iniciando Agente Autonomo: '{task_instruction}'")

        try:
            # 1. Configurar LLM (Tier 3 - Supervision)
            llm = await self._get_supervision_llm()

            # 2. Instanciar Agente
            # Nota: browser-use 0.x usa 'browser_context' en el constructor si queremos reusar.
            agent = Agent(
                task=task_instruction,
                llm=llm,
                browser_context=context,  # Enganche critico
                use_vision=True,  # Usar vision si el modelo lo soporta (Gemini 2.0 lo hace)
            )

            # 3. Ejecutar
            # history devuelve un objeto con .result(), .errors(), etc.
            history = await agent.run()

            # 4. Procesar Resultado
            # Dependiendo de la version de browser-use, history.final_result() puede ser el texto
            final_output = (
                history.final_result()
                if hasattr(history, "final_result")
                else str(history)
            )

            print(f"[AgentService] Agente finalizo. Resultado: {final_output[:100]}...")

            return AgentResult(
                success=True, output=final_output, action_log=str(history)
            )

        except Exception as e:
            err_msg = f"Error fatal del agente: {str(e)}"
            print(f"[AgentService] {err_msg}")

            # No cerramos el navegador, solo reportamos el fallo de la mision autonoma
            return AgentResult(success=False, output="", error=err_msg)
