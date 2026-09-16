# Guía de perfiles y pipelines de grafos públicos

## Qué es CoreGraph

`CoreGraph` es el orquestador común a todos los chatbots públicos
(`server/app/modules/agents_hub/agent/public_graphs/core/core_graph.py`).
Ejecuta siempre el mismo flujo:

```
detect_language → retrieve → merge → quality_gate
                                         ↓ ok          ↓ bajo
                                  generate_answer    fallback
                                         ↓
                                        log → END
```

No contiene lógica de dominio ni conoce el `retrieval_mode`. Toda la
variación entre chatbots se inyecta a través de cuatro estrategias:

| Estrategia | Responsabilidad |
|---|---|
| `RetrievalStrategy` | Decide cómo y de dónde recuperar evidencias |
| `MergeStrategy` | Fusiona los buckets de evidencia en una lista plana |
| `TemplateStrategy` | Construye el contexto de prompt para el LLM |
| `LanguagePolicy` | Detecta el idioma, filtra y genera warnings de traducción |

## Qué es un GraphProfile

Un perfil es un bundle de las cuatro estrategias adaptado a un caso de uso
concreto. Cada perfil se registra en `GraphProfileRegistry` como una factoría
`(cfg, deps, llm) → CoreGraph`. Los perfiles disponibles se definen en
`PublicGraphProfile` (`types.py`):

| Perfil | Caso de uso | Módulo |
|---|---|---|
| `PUBLIC_KB_RICH` | Chatbot genérico con KB enriquecida (grupos, FAQs, oferta académica) | `profiles/public_kb_rich.py` |
| `PUBLIC_PORTAL_AGGREGATOR` | Portal que agrega dos fuentes (procedimientos + normativa) | `profiles/public_portal_aggregator.py` |
| `PUBLIC_PORTAL_ROUTER` | Portal que enruta entre chatbots hijos disjuntos | `profiles/public_portal_router.py` |

## Qué es retrieval_mode

`retrieval_mode` es el mecanismo de recuperación de documentos que usa el
pipeline subyacente. Se resuelve en la cascada de config
(plataforma → organización → chatbot). Los tres modos disponibles son:

| Modo | Pipeline | Cuándo usarlo |
|---|---|---|
| `RAG` | `RagVectorPipeline` | KBs medianas con buen índice vectorial |
| `MD_LONG_CONTEXT` | `MdLongContextPipeline` | Corpus pequeño que cabe en contexto |
| `MD_AGENT_SELECTOR` | `MdAgentSelectorPipeline` | Selección agéntica (stub; evoluciona en 9B.8+) |

El `retrieval_mode` es **independiente** del perfil: cualquier perfil puede
operar con cualquier modo. El `CoreGraph` no conoce el modo; lo conoce la
`RetrievalStrategy` (o el perfil que la instancia).

## Aportar un perfil o un pipeline desde un paquete

**Desde PLG.1 no hace falta tocar este repositorio.** Un paquete Python instalado en el mismo
entorno que el servidor puede aportar perfiles y pipelines declarándolos como *entry points*, y el
núcleo entra **por ese mismo camino**: sus tres perfiles y sus tres modos están declarados en
`server/pyproject.toml` igual que los declararía un tercero.

Eso último no es simetría decorativa. Con dos caminos de registro, el motor puede acabar
dependiendo de algo que sólo el registro interno proporciona, y **no se nota hasta que llega el
primer tercero** — cuando ya está en el diseño. Con uno solo, el núcleo es el primer usuario de la
API pública y cualquier carencia sale a la primera.

### El ejemplo, y está vivo

Lo que sigue es **literalmente** el paquete
[`server/tests/fixtures/paquete_perfil_demo/`](../server/tests/fixtures/paquete_perfil_demo/), que
la suite instala y ejecuta en cada ejecución. Un guardarraíl
(`test_plg1_el_ejemplo_de_la_guia_es_el_del_paquete_demo`) comprueba que este fragmento y ese
fichero no divergen: un ejemplo de documentación que nadie ejecuta envejece en silencio, y éste no
puede.

```toml
# pyproject.toml del paquete que aporta
[project]
name = "govgenai-demo-perfil"
version = "0.1.0"
requires-python = ">=3.11"

[project.entry-points."govgenai.graph_profiles"]
DEMO_KB_RICH = "govgenai_demo_perfil:construir_perfil_demo"

[project.entry-points."govgenai.retrieval_pipelines"]
DEMO_PIPELINE = "govgenai_demo_perfil:PipelineDemo"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Y el código, que no importa nada de la plataforma para declararse:

```python
def construir_perfil_demo(cfg, deps, llm=None):
    """Factoría de perfil: `(cfg, deps, llm) -> CoreGraph`."""
    from server.app.modules.agents_hub.agent.public_graphs.core.graph_factory import (
        _make_public_kb_rich,
    )
    return _make_public_kb_rich(cfg, deps, llm)


class PipelineDemo:
    """Cumple `RetrievalPipeline`: un único método `run`."""
    async def run(self, query, chatbot_id, cfg, deps): ...
```

Instalarlo basta. No hay que registrarse en ningún sitio ni avisar a nadie.

### Los grupos

| Grupo | Nombre del *entry point* | A qué apunta |
|---|---|---|
| `govgenai.graph_profiles` | el que verá quien configure el chatbot | factoría `(cfg, deps, llm) -> CoreGraph` |
| `govgenai.retrieval_pipelines` | el modo de recuperación | clase que cumple `RetrievalPipeline` |
| `govgenai.strategies` | `<eje>.<nombre>` | factoría de estrategia de ese eje (PLG.2) |

**El nombre de la izquierda se guarda en la base de datos** (`hub_chatbots.public_graph_profile`).
Cambiarlo después es cambiar un dato ya escrito: no se renombra sin migración. Usa un prefijo
propio para no chocar.

### Qué comprueba el arranque, y por qué ahí

El cargador (`public_graphs/plugins.py`) corre en el *lifespan*, **antes de servir**:

1. **Nombres duplicados** → aborta nombrando **las dos distribuciones**. Sin esto ganaría el
   último que cargara `importlib.metadata`, o sea un orden que nadie controla y sin ningún
   síntoma: el mismo perfil se comportaría distinto en dos máquinas.
2. **Un *entry point* que no carga** → aborta nombrando su distribución. La alternativa —avisar y
   seguir— deja un servidor en pie al que le falta un perfil, y quien lo tuviera seleccionado
   vería «perfil desconocido» sin ninguna pista del paquete roto.
3. **Un pipeline que no cumple `RetrievalPipeline`** → se rechaza al descubrir. El protocolo es
   `runtime_checkable`, con su límite dicho: comprueba **que los métodos existan**, no sus firmas.
4. **Cada perfil configurable se construye** y se comprueba que salen sus cuatro ejes. Es lo que
   `test_profile_contract.py` hace con lo que está en el árbol, llevado al arranque para **lo
   instalado**: un perfil que llega en un paquete no lo cubre ningún test de este repositorio.

Todo falla **en alto**. Un servidor que arranca a medias es peor que uno que no arranca: el fallo
aparece delante de un usuario y lejos de su causa.

### Estabilidad: los protocolos son 0.x

`RetrievalPipeline`, los protocolos de estrategia y la firma de las factorías **pueden cambiar
entre versiones menores**, y no hay política de deprecación. Se anuncia en
`planificacion/HISTORIAL.md` y nada más.

Es deliberado: han cambiado dos veces en un mes por medición —la puerta de calidad en HIB, la
política de lengua en LANG— y congelarlos hoy sería congelar errores conocidos. El contrato se fija
el día que exista el primer tercero real con un perfil que mantener, y entonces se dirá.

### La frontera de confianza, sin rodeos

**Un perfil o un pipeline instalado corre dentro del proceso del servidor y con los datos del
cliente. No hay *sandbox*.** La confianza está en quien instala, igual que en un plugin de pytest
o de Airflow. Se dice aquí para que nadie lea de este mecanismo una garantía de aislamiento que no
da; si algún día hace falta aislamiento, será otro diseño y no un ajuste de éste.

## Cómo añadir un perfil nuevo al núcleo

Los mismos tres pasos que para un paquete, con el `pyproject.toml` del servidor en vez del propio.
Ejemplo: perfil `OFERTA_ACADEMICA`.

### 1. Crear el módulo de perfil

```python
# profiles/oferta_academica.py
def make_oferta_academica(cfg, deps, llm=None) -> CoreGraph:
    return CoreGraph(
        retrieval_strategy=...,
        merge_strategy=...,
        template_strategy=...,
        language_policy=...,
        cfg=cfg, deps=deps, llm=llm,
    )
```

### 2. Declararlo como *entry point*

```toml
# server/pyproject.toml
[project.entry-points."govgenai.graph_profiles"]
OFERTA_ACADEMICA = "server.app.modules.agents_hub.agent.public_graphs.profiles.oferta_academica:make_oferta_academica"
```

**Ya no se registra por código** y **ya no hay enum que tocar**: `PublicGraphProfile` se retiró en
PLG.1 porque un perfil aportado desde fuera no cabe en un enum del núcleo. Tras editar el
manifiesto hace falta un `uv sync` para que la distribución se reinstale y el *entry point* sea
visible.

### 3. Los tests de contrato se aplican solos

`test_profile_contract.py` se parametriza sobre `list_profiles()`, así que el perfil nuevo entra
sin tocar ningún fichero de test. Si no debe exigírsele todavía, va a `PERFILES_SIN_CONFIGURAR`.

## Cómo añadir un pipeline nuevo al núcleo

Igual: la clase, y su línea en `[project.entry-points."govgenai.retrieval_pipelines"]`.
`test_pipeline_contract_suite.py` se parametriza sobre `list_modes()` y lo recoge solo; lo único
que hay que añadir es su rama de *mocking* en el fichero de contrato.

## Estrategias: los cuatro ejes, cómo registrar una, cómo seleccionarla por configuración

Un `CoreGraph` compone **cuatro** protocolos, y cada uno es un *eje*:

| Eje | Protocolo | Qué decide |
|---|---|---|
| `retrieval` | `RetrievalStrategy` | cómo se busca la evidencia |
| `merge` | `MergeStrategy` | cómo se fusionan los *buckets* en una lista plana |
| `template` | `TemplateStrategy` | qué contexto de prompt recibe el LLM |
| `language` | `LanguagePolicy` | detección de lengua, filtros y aviso de traducción |

**Los ejes son estructura; los nombres de estrategia son vocabulario.** Por eso los ejes son un
`StrEnum` cerrado y los nombres se registran: añadir un eje exige de todos modos escribir el nodo
del grafo que lo consuma, así que no puede llegar por instalación. Una estrategia sí.

**El bucle agéntico NO es un eje**, y conviene decir por qué: lo monta
`build_agentic_loop_if_needed` a partir del modo de recuperación y de sus dependencias, y
convertirlo en enchufe exigiría antes separar sus tres colaboradores —lector, buscador y
puntuador—, que hoy se construyen juntos. Declararlo eje sin eso sería ofrecer un enchufe que no
se puede sustituir de verdad. Queda como candidato.

### Registrar una

Igual que un perfil, con el nombre `<eje>.<nombre>`:

```toml
[project.entry-points."govgenai.strategies"]
"merge.dedup_por_documento" = "govgenai_demo_perfil:merge_dedup_por_documento"
```

La factoría tiene la firma `(cfg, deps, llm) -> instancia`. Recibe `cfg` porque una estrategia
puede necesitar la configuración efectiva del chatbot para construirse — la plantilla genérica del
núcleo, por ejemplo, lee de ahí el prompt de sistema.

El eje va **en el nombre del *entry point*** y no dentro del objeto: así el cargador sabe en qué
eje va **antes de importar nada**, y puede rechazar un eje inventado sin ejecutar código del
paquete. Al arrancar se instancia cada estrategia y se comprueba `isinstance` contra el protocolo
de su eje: estar registrada en `merge` no la convierte en una `MergeStrategy`, y equivocarse de
eje es fácil.

### Seleccionarla por configuración

Dos columnas `JSONB` con forma `{eje: nombre}`:

- `hub_organizaciones.default_estrategias`
- `hub_chatbots.estrategias`

**Se fusionan CLAVE A CLAVE**, no como valor entero:

```
composición del perfil  ←  default_estrategias (organización)  ←  estrategias (chatbot)
```

Una organización que fija `merge` **no** pisa el `template` que haya elegido el chatbot. Clave
ausente, `null` o cadena vacía significan «hereda»; el resultado trae **siempre los cuatro ejes**,
para que quien lo lea no tenga que tratar el caso «falta la clave».

Así, un chatbot que quiera deduplicar por documento cambia **una clave** —no hace falta un perfil
nuevo ni código:

```json
{"estrategias": {"merge": "dedup_por_documento"}}
```

**Un nombre no registrado revienta en alto**, nombrando eje, nombre y chatbot. Nunca se cae al
valor por defecto en silencio: es la lección del hallazgo I5 de la auditoría, donde un asistente
respondía «no encuentro información» con el corpus perfectamente cargado.

### El cruce con `language_mode`

`language_mode` (LANG) elige la política **por defecto** del eje `language`. Una sobreescritura
explícita del eje manda sobre él, porque es más específica: quien escribe `{"language":
"neutral"}` está pidiendo exactamente ésa. Sin sobreescritura, `language_mode` sigue mandando como
siempre.

## Reglas de extensión

- Un perfil nuevo **no modifica** `CoreGraph` ni los protocolos existentes.
- Un modo nuevo **no modifica** los perfiles existentes.
- El contrato `RetrievalResult` con `items: list[EvidenceItem]` es inmutable:
  todo pipeline nuevo debe respetarlo.
- Los tests de contrato (`test_profile_contract.py`,
  `test_pipeline_contract_suite.py`) se ejecutan automáticamente sobre el
  nuevo perfil/pipeline sin modificar los archivos de test.
