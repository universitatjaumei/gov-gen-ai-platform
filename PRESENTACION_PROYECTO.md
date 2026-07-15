# Gov Gen AI Platform — Presentación del proyecto

> **Naturaleza del documento**: introducción descriptiva del proyecto para personas que se
> incorporan o quieren conocerlo. No es documentación técnica ni normativa: para cada tema
> remite al documento especializado correspondiente (§6).
>
> Fecha: julio de 2026.

---

## 1. Qué es y para qué sirve

**Gov Gen AI Platform** es una plataforma de inteligencia artificial diseñada específicamente
para **administraciones públicas**. Su objeto es aplicar IA generativa y automatización a
procesos administrativos reales —atención ciudadana, redacción de documentos, extracción de
datos, tramitación de expedientes— de forma **auditable, trazable y conforme a la normativa
europea y española** (Reglamento de IA, RGPD, Ley 39/2015 y 40/2015, ENS/ENI).

La idea central que la diferencia de un despliegue genérico de chatbots es que la conformidad
normativa no se trata como documentación aparte, sino que está **incorporada al diseño**: cada
actuación asistida por IA deja evidencia de supervisión humana, procedencia de la información
y protección de datos. El principio rector es *compliance-as-code*: las obligaciones legales
se traducen en comprobaciones ejecutables y en tests automáticos, no en buena fe.

El primer despliegue piloto está previsto en la **Universitat Jaume I** (asistente sobre
normativa propia), y el proyecto se publicará como **software libre (AGPLv3)** con licencia
dual comercial para partners, de modo que otras instituciones puedan autoalojarlo.

## 2. Los tres módulos de la plataforma

La plataforma integra tres módulos sobre una base común (autenticación, gateway LLM
multi-proveedor, almacenamiento portable, frontera edge/cloud):

| Módulo | Propósito | Capacidades clave |
|---|---|---|
| **AI Agents Hub** | Atención y asistencia mediante IA | Chatbots públicos multilingües (CA/ES/EN) con RAG y **citas trazables a la fuente**, widget embebible en webs institucionales, ingesta documental (Docling), evaluación de calidad (recuperación y respuesta), agentes identificados para personal interno |
| **AutomatIA** | Automatización de procesos internos | Flujos, ETL, extracción de datos de PDF, scripts generados y firmados, ejecución local (RPA) cuando es imprescindible, sandbox aislado de ejecución |
| **Gestor de Expedientes** | Tramitación administrativa asistida | Tipos de expediente con fases y acciones, supervisión humana obligatoria (HITL), auditoría encadenada con valor probatorio, explicabilidad, integración con gestores externos (UJI, G400) vía MCP |

Transversalmente, la plataforma incorpora mecanismos que responden directamente al marco de
gobernanza: **anonimización/seudonimización reversible** antes de enviar datos al LLM
(NER + vault), **determinismo primero** (el LLM solo interviene donde las reglas no llegan, y
la ruta usada queda registrada), **calidad del contenido web ingestado** (detección de
contenido obsoleto o contradictorio antes de que alimente respuestas), **accesibilidad WCAG**
verificada en CI, y un **servidor MCP** que permite operar la configuración de la plataforma
desde agentes de IA con confirmación humana.

## 3. Arquitectura en dos frases

Es un **monorepo servidor-first**: backend FastAPI (Python, asíncrono, contrato OpenAPI como
única fuente de verdad), frontend React "tonto" que se genera contra ese contrato
(Server-Driven UI: el servidor decide formularios y acciones permitidas, el cliente solo
renderiza), y PostgreSQL + pgvector.

El mismo código sirve a dos modos de despliegue: **cloud-only** (todo en el servidor del
partner, con anonimización contractual) y **edge + cloud** (la lógica y los datos del cliente
final viven en un nodo dentro de la nube de la institución; el cloud solo guarda configuración
y métricas anonimizadas). Esta **frontera edge/cloud está implementada en código** —bases de
datos separadas, routers etiquetados, tests de frontera—, no solo declarada en papel, porque
es el requisito de soberanía del dato que exigen las administraciones. El detalle completo
está en `Arquitectura.md`.

## 4. Estado de desarrollo (julio 2026)

El proyecto se ha desarrollado hasta ahora **en solitario**, con disciplina TDD estricta
(test antes que código). La **Fase 1 (MVP)** está funcionalmente completa en su núcleo:

**Completado y verificado** (~943 tests backend + ~209 frontend en verde):

- **Chatbots públicos** (bloque 9B): RAG híbrido, LangGraph, chat en streaming, widget
  embebible, spiders de ingesta web.
- **Redacción asistida Contract-First** (9R): plantillas de informe definidas por contrato,
  formularios generados dinámicamente por el servidor, grafo de redacción, exportación DOCX.
- **Personalización visual** (Fase 10): temas en cascada Plataforma → Organización → Chatbot.
- **Privacidad y exportación** (1C) y **NER reversible** (Fase 13): anonimización pre-LLM en
  el flujo de redacción.
- **Accesibilidad WCAG** (Fase 20): gate automático en CI.
- **Sandbox de scripts** (SBX): microservicio de ejecución aislado y endurecido.
- **Calidad de contenido web** (9Q): crawler con detectores de patologías documentales e
  informes de calidad del corpus.
- **Autenticación institucional** (AUTH): SSO SAML 2.0 con provisioning automático + tokens
  personales (PAT) con permisos acotados para clientes máquina.
- **Servidor MCP** (bloque MCP): 16 herramientas y 5 recursos para administrar plantillas y
  chatbots desde agentes de IA, con confirmación humana en operaciones sensibles.
- **Renombrado institucional** (bloque ROL): alineación de roles y entidades en código y
  documentación (Partner → Admin, Cliente → Organización) antes de crecer el coste del cambio.
- **Contrato OpenAPI + Orval** operativo: el frontend consume tipos y hooks generados
  automáticamente del contrato del servidor.

En julio de 2026 se realizó una **valoración global del proyecto** (`VALORACION_PROYECTO.md`)
que auditó código, seguridad y planificación. Sus conclusiones han reordenado el tramo final
de la Fase 1: antes de cualquier despliegue con datos reales se ejecutará un **bloque de
endurecimiento de seguridad** (autenticación de administradores, aislamiento estricto entre
inquilinos, límites de uso), junto con un bloque de deuda de calidad previo a la apertura del
repositorio.

## 5. Qué queda por hacer

**Resto de la Fase 1** (orden acordado, cursor y detalle en `PROJECT_STATE.md`):

1. **Fase 11 — Autoinstalación** (en curso): generador de configuración, compose de producción y
   script de inicialización, prerrequisito de la distribución como software libre.
2. **Bloque ING — Ingesta del corpus curado**: la vía principal para cargar la normativa real del
   piloto (~300 documentos); se ejecuta ya con un corpus de prueba en local, mientras la carga
   definitiva espera a la revisión del corpus (prevista para septiembre).
3. **Bloque RAG — Refuerzo de la recuperación**: derivado de una comparativa arquitectónica con
   otra plataforma RAG del sector educativo (`docs/COMPARATIVA_RAG_LAMB.md`), consolida el motor de
   recuperación con búsqueda híbrida real (semántica + léxica), *reranking*, evaluación medible
   (dataset dorado como *gate* de CI) y reescritura conversacional de la consulta. Se apoya en el
   corpus de prueba del bloque anterior para medir la mejora antes del despliegue.
4. **Bloque SEC — Seguridad** (bloqueante de despliegue): corrección de los hallazgos de la
   valoración, con test de aislamiento multi-tenant como gate de CI.
5. **Bloque CAL — Deuda de calidad** antes de abrir el repositorio público.
6. **Deploy GCP**: primer despliegue real (Cloud Run + Cloud SQL + GCS), previsto para septiembre
   de 2026 con el corpus definitivo revisado.

**Fase 2** (2027) — replanteada en 2026-07: la migración en bloque del cliente de escritorio
legacy ya no se recomienda; se reduce a construir el **Thin Client** (agente ligero de
ejecución local, infraestructura necesaria para la Fase 3) más limpieza, migrando el resto
por goteo según lo demande el piloto.

**Fase 3** (2027-28) — **Gestor de Expedientes**: la pieza de mayor valor regulatorio.
Tramitación multi-fase con acciones calculadas en servidor (HATEOAS), auditoría encadenada
SHA-256, snapshots normativos con fecha de referencia (Ley 39/2015), auditoría de equidad
(art. 13 del Reglamento de IA) e integración con los gestores corporativos vía MCP.

**Hitos orientativos**: piloto UJI en el cuarto trimestre de 2026, apertura del repositorio
AGPLv3 en la misma ventana, Fases 2 y 3 durante 2027-28.

## 6. Mapa de documentación

| Documento | Qué contiene | Para quién |
|---|---|---|
| `Arquitectura.md` | Arquitectura funcional y técnica objetivo: módulos, roles, frontera cloud/edge/local, privacidad, stack, decisiones estructurales | Quien quiera entender *cómo* está construido |
| `MARCO_GOBERNANZA_IA.md` | Marco normativo interno: principios de gobernanza (determinismo primero, frugalidad, supervisión humana…) y las obligaciones de desarrollo que imponen | Quien quiera entender el *porqué* regulatorio |
| `PROJECT_STATE.md` | Estado vivo del desarrollo: cursor actual, bloques completados, historial prompt a prompt | Quien quiera saber *en qué punto exacto* está |
| `PLAN_DESARROLLO.md` | Plan de desarrollo completo del monorepo y decisiones durables (licencias, stack, auth) | Visión de conjunto de la planificación |
| `Plan_TDD_Fase1.md` / `Plan_TDD_Fase2.md` / `Plan_TDD_Fase3.md` | Planes TDD detallados por fase, prompt a prompt | Equipo de desarrollo |
| `VALORACION_PROYECTO.md` | Auditoría global (julio 2026): calidad, seguridad, sentido de producto y revisión de la planificación pendiente | Quien quiera una evaluación crítica e independiente del estado |
| `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` y `docs/EU_GOVERNANCE_TOPICS.md` | Proyección del marco de gobernanza hacia consorcios y financiación europea | Contexto de colaboración/financiación |
| `docs/MCP_SERVER.md`, `docs/REDACCION_CONTRACT_FIRST.md`, `docs/SANDBOX_SECURITY.md`, `docs/A11Y_CHECKLIST.md` | Documentación técnica de módulos concretos | Referencia por módulo |
| `CLAUDE.md` | Reglas vinculantes para los agentes de programación (arquitectura, TDD, limpieza, fronteras) | Quien desarrolle con agentes de IA |

---

*Para una demo o para profundizar en cualquier módulo, el punto de entrada recomendado es
`Arquitectura.md` §2 (resumen ejecutivo) seguido del documento específico del módulo.*
