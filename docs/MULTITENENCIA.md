# Multitenencia: qué está acotado, por qué camino, y qué es de plataforma a propósito

> Escrito en **MT.7** (2026-08-24) porque la auditoría que originó el Bloque MT consistió en
> reconstruir esto a mano leyendo 31 tablas y 32 routers. Lo mantiene honesto
> `server/tests/core/test_mt7_el_inventario_esta_escrito.py`: si una tabla de configuración falta
> aquí, o su ámbito no coincide con el que declara el código, el test se pone rojo. **No es
> documentación que se actualiza cuando alguien se acuerda.**

## Para qué existe todo esto

El objetivo del diseño es que **una Diputación pueda desplegar una instancia para varios
municipios**: un superadministrador da de alta las organizaciones, cada una tiene su
administrador, y las personas de una organización sólo alcanzan el contenido de la suya.

Lo que **no** es: esto no convierte la instalación en multiinstancia. Sigue siendo una base de
datos con organizaciones dentro. La separación **física** por municipio es el modo `edge` que
describe `AGENTS.md` — un despliegue por cliente, con la configuración sincronizada desde el
cloud.

## Los cuatro ámbitos

Toda tabla de `HubConfigBase` declara el suyo en `__ambito__`, y una que no lo declare pone rojo
el guardarraíl de MT.1. La declaración **no se hereda** de una clase padre: heredar de una base
común es normal, heredar la decisión de quién es el dueño de los datos no.

| Ámbito | Qué significa | Columna |
|---|---|---|
| `plataforma` | Una sola configuración para la instalación entera. No hay nivel de organización. | — |
| `organizacion` | Siempre de una organización. | `organizacion_id` NOT NULL |
| `heredable` | **Nulo = de la plataforma, y se hereda.** | `organizacion_id` nullable |
| `derivada` | La organización se alcanza por otra tabla. | la que diga `via` |

Son cuatro y no tres porque varias tablas llegan a la organización **por otra tabla**
(`hub_prompt_templates` por su chatbot), y meterlas en «de organización» diría que tienen una
columna que no tienen.

La cascada de `heredable` la resuelve `core/ambito.py`, escrita una vez: **campo a campo**, no
fila entera —con reemplazo de fila, una organización que quiera cambiar un color tendría que
repetir la configuración completa— y distinguiendo `None` («heredar») de `""` («lo quiero
vacío»), sin lo cual no se puede vaciar un valor heredado desde la pantalla.

## Tablas de configuración (`HubConfigBase`, se sincronizan cloud→edge)

| Tabla | Ámbito | Camino a la organización | Nota |
|---|---|---|---|
| `hub_organizaciones` | `plataforma` | — | Es el eje sobre el que se acota todo lo demás, no algo acotable. |
| `hub_platform_modules` | `plataforma` | — | Catálogo de módulos de la instalación. |
| `hub_providers` | `plataforma` | — | **A propósito**: es un catálogo de *tipos* (Google, Vertex, Ollama, OpenRouter). Google es Google en todos los municipios. Lo que se separa es la credencial. |
| `hub_provider_credentials` | `heredable` | `organizacion_id` | MT.2. Con qué credencial habla cada organización. Tres métodos: clave literal, **nombre** de variable de entorno (el único que da credenciales por organización sin meter secretos en la base) y ADC. |
| `hub_llm_configs` | `heredable` | `organizacion_id` | MT.2. `is_default` es único por (nivel, propósito, organización). |
| `hub_chatbots` | `organizacion` | `organizacion_id` | Un asistente es siempre de una organización. |
| `hub_vocabulary_terms` | `organizacion` | `organizacion_id` | Cada organización tiene su vocabulario; no hay nivel de plataforma que heredar. |
| `hub_prompt_templates` | `derivada` | `chatbot_id` | Cuelga de un chatbot, por idioma y versionada. Lo acota `/hub/prompts-catalog` (REV.13). |
| `hub_widget_keys` | `derivada` | `chatbot_id` | La credencial pública de un asistente concreto (SEC.8.5). |
| `hub_activity_prompts` | `heredable` | `organizacion_id` | MT.6. Cadena organización → plataforma → **código**; el texto del código nunca se copia a una fila. |
| `hub_themes` | `heredable` | `organizacion_id` | La cascada visual, de la que salió el patrón. |
| `hub_users` | `heredable` | `organizacion_id` | Nulo = cuenta que no pertenece a ninguna. **El filtro del listado falta**: es MT.9, fase 2. |
| `hub_module_grants` | `heredable` | `organizacion_id` | MT.5. **Nulo = en todas**, que es lo que valen las concesiones de siempre. Eje perpendicular al de `subject_type`. |
| `hub_personal_access_tokens` | `heredable` | `organizacion_id` | MT.5. Nulo = donde valga su dueño. Cuando lo declara **acota, nunca amplía**. |

## Tablas operacionales (`HubOperationalBase`, viven sólo en el edge)

No declaran `__ambito__`: son datos del cliente final, y su acotación es la del camino por el que
se llega a ellas. La columna dice **por dónde** las acota un router.

| Tabla | Camino a la organización |
|---|---|
| `hub_web_sites` | `organizacion_id` |
| `hub_crawled_pages` | `site_id` → sitio |
| `hub_content_findings` | `site_id` / `chatbot_id` |
| `hub_corpus_selections` | `site_id` / `chatbot_id` |
| `hub_documents` | `chatbot_id` |
| `hub_document_chunks` | `chatbot_id` |
| `hub_ingestion_jobs` | `chatbot_id` |
| `hub_interactions` | `chatbot_id` |
| `hub_test_scenarios` | `chatbot_id` |
| `hub_test_runs` | por su escenario |
| `hub_report_templates` | `organizacion_id` (MT.4) |
| `hub_report_template_versions` | `template_id` → plantilla |
| `hub_workspaces` | `organizacion_id` (MT.4) |
| `hub_workspace_blocks` | `workspace_id` → informe |
| `hub_workspace_audit_events` | `workspace_id` → informe |
| `hub_run_manifests` | `workspace_id` → informe |
| `hub_script_proposals` | por su informe |
| `hub_usage_counters` | `subject_type='organizacion'` desde SEC.4 |

## Las dos capas que hacen cumplir la frontera

No son lo mismo y es fácil confundirlas:

- **`core/auth/tenancy.py` — quién puede ver qué.** `assert_org_access` (403 sobre una entidad ya
  leída) y `scope_query_to_orgs` (acota un listado). Recibe un principal. **El superadministrador
  no se acota, y es correcto como permiso**: lo que falta es la *vista*, y eso es MT.8.
- **`core/ambito.py` — qué fila gana** cuando la misma configuración está puesta en dos niveles.
  No recibe principal.

`scope_query_to_orgs` con un principal **sin** organizaciones devuelve un `IN ()` vacío, que no
devuelve nada. Es intencionado, y es la diferencia entre «no ve nada» y «no se filtra»: devolver
el listado entero cuando el claim viene vacío era el hallazgo A2 de SEC.2.

## Qué sigue abierto (fase 2, después del piloto)

La fase 1 metió el **esquema** antes del piloto porque añadir una columna a una tabla casi vacía
es gratis y añadirla con meses de informes firmados es una migración con riesgo. La **vista** y
los **permisos** van después, porque dependen de cómo quede el piloto:

- **MT.8** — el selector de la cabecera **filtra** los listados de un superadministrador. Filtro,
  no permiso: seguir pudiendo verlo todo es correcto; verlo todo **a la vez** es lo que estorba.
- **MT.9** — un administrador gestiona a las personas de su organización.
- **MT.10** a **MT.15** — pantallas de modelos, plantillas, prompts, alta de organización con su
  administrador, concesiones y cuotas.
- **MT.16** — prueba de aislamiento de punta a punta con dos organizaciones.
- **MT.17** a **MT.21** — reutilizar configuración entre organizaciones: `capacidades`/`requiere`,
  plantilla de asistente, catálogo, exportar/importar y el mismo mecanismo en automatizaciones y
  expedientes. El detalle está en `planificacion/Plan_TDD_Fase1.md` §Bloque MT.
