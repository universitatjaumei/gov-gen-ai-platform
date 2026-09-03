# Metodología de desarrollo agéntico por bloques

> Regla operativa para agentes de programación. `AGENTS.md` es la fuente dominante;
> este documento desarrolla en detalle la sección "Ejecución agéntica por bloques".
> Adoptada el 2026-07-27.

El agente ejecuta los prompts del plan de desarrollo **de forma autónoma y secuencial,
por bloques**, sin pedir confirmación entre prompts. La interacción humana se concentra
en tres momentos: el arranque del bloque, las decisiones de criterio, y el cierre del
bloque con sus pruebas manuales.

---

## 1. Qué es un bloque

Un bloque es el grupo de prompts numerados que `planificacion/PROJECT_STATE.md` presenta como una fila
de la tabla de planes activos. Ejemplos reales:

| Bloque | Prompts |
|---|---|
| Fase 11 — Autoinstalación | 11.1 → 11.3 |
| Bloque SEC — Endurecimiento de seguridad | SEC.1 → SEC.7 |
| Bloque ING.0 — Ingesta de corpus curado | ING.0.1 → ING.0.2 |
| Bloque RAG — Refuerzo del retrieval | RAG.1 → RAG.14 |
| Bloque CAL — Deuda de calidad | CAL.1 → CAL.5 |

**El bloque es la unidad de interacción.** Una vez arrancado, el agente no informa hasta
cerrarlo (salvo criterios de parada del §3).

Cuando un bloque es muy largo (RAG tiene 14 prompts), el agente puede proponer al
arrancar partirlo en tandas coherentes — p. ej. `RAG.1→RAG.6` (dataset + retrieval) y
`RAG.7→RAG.14` — para que las pruebas manuales lleguen antes. La decisión es del usuario;
si no dice nada, se ejecuta el bloque completo.

### Cómo se arranca

El usuario escribe algo como *"ejecuta el bloque SEC"* o *"continúa con el bloque en curso"*.
El agente entonces:

1. Lee `planificacion/PROJECT_STATE.md`, localiza el cursor y el bloque.
2. Lee **verbatim** los prompts del bloque en el plan correspondiente
   (`planificacion/Plan_TDD_Fase1.md`, `planificacion/Plan_TDD_Fase2.md`, ...).
3. Comprueba el **modelo sugerido** de cada prompt del bloque. Si alguno sugiere un modelo
   más capaz que el de la sesión, lo dice **una sola vez, antes de empezar**, y espera
   decisión. No vuelve a interrumpir por este motivo dentro del bloque.
4. Comprueba los prerrequisitos externos del bloque (BD arrancada, corpus entregado,
   credenciales). Si falta alguno, para antes de empezar.
5. Ejecuta el bucle del §2 sobre cada prompt, en orden.

---

## 2. Bucle por prompt (interno, sin interacción)

Para cada prompt del bloque, en este orden:

1. **Leer el prompt verbatim** del plan. No reinterpretar el alcance ni añadir features
   no pedidas.
2. **RED** — escribir los tests enumerados en el prompt y verificar que fallan por la
   razón correcta (no por error de import o de fixture).
3. **GREEN** — implementación mínima que los pone en verde.
4. **REFACTOR** — limpieza manteniendo el verde.
5. **Verificaciones de cierre** (todas las que apliquen al prompt):
   - Suite completa del ámbito tocado en verde (`pytest`, `vitest`, `tsc -b`).
   - Migración Alembic **aplicada** (`uv run alembic upgrade <rev>` + `alembic current`).
   - Contrato regenerado si cambió la API (`export_openapi` + `npm run generate:api`).
   - Retirada del legacy según el checklist de `AGENTS.md` (`_legacy_nicegui/` o borrado)
     y `grep -r` de referencias a cero.
   - Verificación en navegador si el prompt toca UI (§4).
6. **Actualizar `planificacion/PROJECT_STATE.md`**: marcar el paso ✅, mover el cursor, añadir fila al
   historial reciente.
7. **Commit** — un commit Conventional por prompt, con el identificador del prompt en el
   asunto (p. ej. `feat(sec): SEC.2 aislamiento multi-tenant por organizacion_id`).
   Sin `Co-Authored-By`. **Sin push.** El commit por prompt es lo que hace reversible un
   bloque largo: si el prompt 5 rompe el 3, hay un punto exacto al que volver.
8. **Siguiente prompt**, sin informar.

Los fallos **preexistentes** ajenos al prompt (ver `planificacion/PROJECT_STATE.md` y la memoria de
gaps del suite) no bloquean el avance: se anotan y se sigue.

---

## 3. Criterios de parada (cuándo SÍ interrumpir a mitad de bloque)

El agente rompe la autonomía **solo** por estas causas:

1. **Operación de riesgo.** Operación de sistema operativo, borrado fuera de
   `C:\Users\fabra\Documents\`, o pérdida irreversible de datos/historial. Lo detecta
   automáticamente la guarda (§6) y produce un prompt de permiso; el agente no lo fuerza.
2. **Decisión de criterio.** Ambigüedad del plan que llevaría a productos distintos,
   elección de arquitectura que el plan no cierra, o alcance que excede el bloque. Se
   plantea con `AskUserQuestion`, con opciones y recomendación.
3. **Fallo persistente.** Un RED que no llega a GREEN tras intentos razonables, o una
   suite en rojo por causa no atribuible al prompt. El agente **para y reporta con el
   output real**; no marca el prompt como cerrado ni sigue adelante.
4. **Prerrequisito externo ausente.** BD apagada, Docker Desktop cerrado, corpus no
   entregado, credencial o clave que falta.

**No** son causa de parada:

- **Desviaciones entre el plan y el código real.** El agente aplica la interpretación más
  fiel al espíritu del prompt, sin inventar infraestructura que no existe ni añadir
  features no pedidas, lo registra como *"Desviación documentada"* en la fila de historial
  de `planificacion/PROJECT_STATE.md`, y sigue. Todas las desviaciones se resumen en el informe de cierre.
- Fallos de test preexistentes ya inventariados.
- Dudas de estilo, nombres o estructura interna resolubles con las reglas de `AGENTS.md`.

---

## 4. Verificación de UI: navegador primero, humano al final

### 4.1 Lo que verifica el agente con Chrome

Cuando un prompt toca frontend, el agente **verifica él mismo en el navegador** con la
extensión de Chrome (`mcp__claude-in-chrome__*`), dentro del bloque y sin preguntar:

1. `tabs_context_mcp` para ver el estado del navegador; `tabs_create_mcp` para una pestaña
   nueva (nunca reutiliza pestañas del usuario sin que lo pida).
2. `navigate` a la URL concreta (`http://localhost:5173/...`).
3. `read_page` / `get_page_text` / `find` para comprobar que el contenido esperado está.
4. `computer` y `form_input` para interactuar (login, formularios, navegación).
5. `read_console_messages` y `read_network_requests` para detectar errores que un test
   unitario no ve (peticiones 4xx/5xx, warnings de React, claves i18n sin traducir).
6. `gif_creator` cuando el flujo tiene varios pasos y conviene dejar evidencia revisable.

Reglas duras:

- **No provocar `alert`/`confirm`/`prompt`** del navegador: bloquean la extensión.
- Si el navegador falla o no responde tras 2-3 intentos, no insistir: anotarlo como
  pendiente de verificación humana y seguir con el resto del bloque.
- La verificación en navegador **no sustituye** los tests de Vitest ni los de a11y: los
  complementa.

### 4.2 Lo que se reserva al humano

Se deja para el final del bloque, y **solo** lo imprescindible:

- SSO SAML real contra el IdP institucional y cualquier flujo con credenciales reales.
- Integración con sistemas externos no simulables (G400, ENI, APIs UJI).
- Juicio subjetivo: identidad visual, tipografía, tono del texto institucional.
- Accesibilidad con lector de pantalla real.
- Cualquier cosa que implique datos personales reales.

### 4.3 El `.bat` es por bloque, no por prompt

- **Un solo archivo** por bloque: `pruebas_manuales_bloque<NOMBRE>.bat`
  (p. ej. `pruebas_manuales_bloqueSEC.bat`).
- Contiene **solo** los pasos del §4.2. Todo lo que el agente ya verificó en navegador
  **no se repite** en el `.bat`; se menciona como ya verificado en el informe.
- Si el bloque es exclusivamente backend, **no se genera `.bat`**.
- La regla de codificación sigue vigente: ANSI cp1252 sin BOM, escrito con
  `[System.IO.File]::WriteAllText(..., [System.Text.Encoding]::GetEncoding(1252))`,
  primeros bytes `40 65 63 68`.
- **Estructura mínima**: `@echo off` y `chcp 65001 > nul` al inicio, `cd /d "%~dp0.."` justo
  después —así las rutas relativas funcionan aunque el guion viva en un subdirectorio—, bloques
  `echo` por sección, `pause` entre pasos, y al final `echo PRUEBAS COMPLETADAS` con su `pause`.
- **Solo lo que no puede automatizarse**: el `curl` de comprobación, el `alembic upgrade head` si
  hay migración, y los pasos en la interfaz. **No levanta Docker ni el servidor** —son pasos
  previos manuales— aunque sí puede comprobar que responden.

---

## 5. Gestión del stack local

El agente **puede**, sin preguntar:

- `docker compose up -d` (o servicios concretos) y `docker compose down` (sin `-v`).
- Arrancar el backend (`uvicorn`) y el frontend (`npm run dev`) en segundo plano, y
  pararlos al terminar.
- Aplicar migraciones y sembrar datos de desarrollo.

El agente **no puede** sin autorización (la guarda lo intercepta):

- `docker compose down -v`, `docker volume rm`, `docker system prune`.
- `alembic downgrade base`, `DROP DATABASE`, `TRUNCATE`.

Si Docker Desktop no está arrancado, el agente **para y lo pide** — no intenta arrancarlo
él (es una operación de sistema).

---

## 6. Barreras de seguridad (configuración)

| Capa | Fichero | Qué hace |
|---|---|---|
| Guarda de riesgo | `.claude/hooks/guard_operaciones_riesgo.ps1` | Hook `PreToolUse` + `PermissionRequest`. Autoaprueba el trabajo de desarrollo y eleva al humano las tres familias de riesgo. |
| Tests de la guarda | `.claude/hooks/test_guard_operaciones_riesgo.py` | 50 casos que fijan el contrato de la guarda. Ejecutar tras cualquier cambio del `.ps1`. |
| Reglas declarativas | `.claude/settings.json` | `allow` del bucle de desarrollo, `deny` de lo catastrófico, `ask` de lo administrativo. Versionado. |
| Enganche de la guarda | `.claude/settings.local.json` | Registra los dos hooks con rutas absolutas de esta máquina. No versionado. |

Las tres familias que exigen autorización humana:

- **A. Sistema operativo** — particiones, arranque, servicios, registro, cuentas locales,
  firewall, tareas programadas, ACLs, apagado/reinicio, elevación, instalación de
  software, ejecución de código descargado.
- **B. Borrado fuera de las raíces permitidas** — solo se autoborra dentro de
  `C:\Users\fabra\Documents\` y del directorio temporal. Cubre rutas absolutas, rutas
  estilo Unix (`/etc`, `/c/...`) y rutas relativas que escapan con `..`.
- **C. Pérdida irreversible de datos o historial** — `git push --force`,
  `git filter-branch`, `git clean -xdf`, prune/rm de volúmenes Docker, `DROP DATABASE`,
  `TRUNCATE`, `alembic downgrade base`.

**Al cambiar la guarda**, ejecutar sus tests:

```
.venv/Scripts/python.exe .claude/hooks/test_guard_operaciones_riesgo.py
```

Para desactivar la autonomía temporalmente: `/hooks` y deshabilitar los dos hooks, o
`git revert` del commit que introdujo `.claude/settings.json`.

---

## 7. Informe de cierre de bloque

Al cerrar el bloque, el agente entrega **un solo mensaje** con:

1. **Prompts cerrados** — identificador, una línea cada uno, y el commit.
2. **Tests** — cifras reales por suite (backend, frontend, a11y, contract) y cualquier
   rojo preexistente que siga ahí.
3. **Migraciones** — revisiones aplicadas y `alembic current`.
4. **Verificado en navegador** — qué flujos comprobó el agente y con qué evidencia
   (texto encontrado, consola limpia, GIF).
5. **Desviaciones documentadas** — qué se apartó del plan y por qué.
6. **Pendiente** — lo que quedó fuera y el motivo.
7. **Pruebas manuales** — el bloque de instrucciones del `.bat`, con el formato de
   `AGENTS.md` (Antes de empezar / Ejecuta el archivo / Pasos en la interfaz / Qué debes
   ver / Casos límite / Para terminar).
8. **La especificación** — una línea: qué cambió en `../docs/ESPECIFICACIONES.md`, o **por qué no
   cambió nada**. Un bloque puede no tocarla legítimamente —DOM no cambió ninguna garantía, cambió
   dónde se sirven las cosas— pero decirlo es lo que impide saltárselo en silencio. La regla y sus
   cinco disparadores están en `AGENTS.md` → «Seguimiento del estado del proyecto»; el aviso
   importante es que **la madurez la mueve el despliegue, no el cierre del bloque**.

Después del informe, el agente **espera**: el siguiente bloque no arranca solo.

### 7.1 Instrucciones para el usuario

Tras generar el `.bat`, el informe lleva un bloque con instrucciones sencillas, **sin jerga
técnica**, con este formato. Vivía en `AGENTS.md`, que a su vez apuntaba aquí para el
protocolo: la plantilla se usa al cerrar el bloque, así que su sitio es esta sección.

```
## Pruebas manuales — Bloque <NOMBRE>

### Ya verificado por el agente en navegador
- <flujo comprobado + evidencia: URL, texto encontrado, consola limpia>

### Antes de empezar
1. Abre Docker Desktop y asegúrate de que está en marcha (icono verde en la barra de tareas).
2. <paso concreto adicional, p. ej. "Abre una terminal y ejecuta: docker compose up -d">
3. <si el bloque incluye migración: "Ejecuta en una terminal: cd server; uv run alembic upgrade head">

### Ejecuta el archivo
- Haz doble clic en `pruebas_manuales_bloque<NOMBRE>.bat` (está en la carpeta <ruta relativa>).
- El script irá mostrando los pasos; pulsa cualquier tecla para avanzar entre ellos.

### Pasos en la interfaz
1. <acción concreta en el frontend: URL exacta, qué hacer, qué debe pasar>
2. <siguiente acción>

### Qué debes ver
- <resultado visual o de comportamiento esperado, con URL, texto o dato concreto>

### Casos límite
- [ ] <escenario edge case + resultado esperado>

### Para terminar
- <cómo detener los servicios si es necesario>
```

Las instrucciones deben ser **accionables y específicas**: rutas reales, valores de ejemplo, resultados esperados. No sirve "comprobar que funciona".

