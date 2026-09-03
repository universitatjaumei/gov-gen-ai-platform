## Bloque TST — Fiabilidad de la suite de tests

> **Contexto**: deuda encontrada al ejecutar los bloques ING.0 y RAG.1, con los síntomas medidos abajo. No bloquea ninguna funcionalidad, pero **hace poco fiable la verificación**: de aquí en adelante cada cierre de bloque afirma «suite verde», y hoy esa afirmación necesita un asterisco.
>
> **Posición en el orden (recomendada): antes de RAG.2.** Quedan 39 prompts y todos se cierran comparando la suite; arreglar esto primero hace verificable el resto. Tres prompts cortos (**TST.3 añadido el 2026-07-30**, al cerrar TST.1/TST.2, para llevar a cero los 12 rojos preexistentes que quedaban).
>
> **Lo que ya está arreglado y da contexto** (no hay que repetirlo): la fixture de `integration/` que hacía `drop_all` sobre la BD de desarrollo (commit `79dbbf3`), y el `Windows fatal exception: access violation` por cargar torch después de asyncpg, resuelto importando `langchain_text_splitters` al principio de `tests/modules/agents_hub/conftest.py`. **No reordenar ese import.**

---

### Prompt TST.1 (RED/GREEN) — Aislamiento entre tests: el `event_loop` de sesión

**Modelo sugerido**: **Sonnet** — cambio pequeño con verificación amplia; el diagnóstico viene dado.

> **RESUELTO (2026-07-30) — la hipótesis de abajo resultó FALSA.** Se retiró el override y
> los 10 fallos persistieron. La causa real, encontrada con hooks de evento a nivel de la
> clase `Engine` (el `echo` está cableado a `False` en `connection.py`, así que la traza
> por logging no era viable directamente): `test_hub_sites_router.py` asignaba
> `WebSiteRepo.create = AsyncMock(return_value=site)` **sobre la clase, sin restaurar** —
> desde ese test, `create` no ejecutaba SQL y devolvía siempre el mismo objeto desanclado,
> y los tests posteriores reventaban con FK contra un sitio fantasma. La pista decisiva:
> `session.refresh()` tenía éxito sobre una fila que "no existía" — imposible salvo que
> `create` entero fuera un mock. Arreglo: `monkeypatch.setattr` en los dos puntos +
> guardarraíl de escaneo estático (`tests/infra/test_suite_hygiene.py`) + la higiene del
> `event_loop` (que sí se hizo, como limpieza) + **CI pasa a una sola invocación de
> pytest**, porque en dos procesos separados esta clase de fallo es invisible. Detalle en
> `PROJECT_STATE.md` 2026-07-30.

```
# PROMPT TST.1 (RED/GREEN) — Los 10 fallos de test_site_model.py en ejecución conjunta
# Deploy: n/a (infraestructura de tests)

## Síntoma medido
`tests/modules/agents_hub/integration/test_site_model.py` da **10 fallos en ejecución
conjunta** con `unit/` y **pasa en solitario**:

    solo test_site_model.py                        → 15 passed
    los tres ficheros de BD juntos                 → 24 passed
    integration/ completo                          → 90 passed
    unit/ + integration/                           → 10 failed, 584 passed

Los 10: TestWebSiteRepo (2), TestCrawledPageRepo (5), TestCorpusSelectionRepo (2),
TestHubDocumentCrawledPageFK (1). El error es un **IntegrityError de FK sobre
hub_crawled_pages.site_id**: el INSERT del sitio y el de la página acaban en transacciones
distintas, así que cuando se inserta la página el sitio todavía no existe para ella.

Descartados como causa: `test_hub_document.py` y `test_ingestion_storage.py` (se ejecutaron
junto a test_site_model.py y dan 34 passed).

## Hipótesis principal, y por qué
`server/tests/conftest.py` sobreescribe la fixture `event_loop` con `scope="session"`:

    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

Con pytest-asyncio 1.3 ese override está **deprecado** y produce exactamente esta clase de
síntoma: fixtures async y tests corriendo en loops distintos, conexiones asyncpg mezcladas
entre tests y trabajo que acaba en transacciones que no son la que el test cree. El propio
`tests/modules/agents_hub/e2e/conftest.py` ya lo documenta: «todos los fixtures de BD tienen
scope="function" para evitar conflictos de event loop entre pytest-asyncio y httpx».

## Trabajo
- **Retirar el override** de `event_loop` del conftest raíz.
- Declarar la política en configuración, no en una fixture:
  `asyncio_default_fixture_loop_scope = "function"` en `[tool.pytest.ini_options]` de
  `server/pyproject.toml` (hoy sale `=None` en la cabecera de pytest, con su warning).
- **Si la hipótesis no se confirma**, bisecar `unit/` por mitades hasta aislar el fichero
  que interfiere y arreglar la causa real. NO cerrar el prompt con los 10 fallos
  reetiquetados como «preexistentes»: eso es lo que ha pasado hasta ahora.
- Segunda sospecha si la primera falla: el motor global cacheado de
  `agents_hub/database/connection.py:get_engine()`, que apunta a `DATABASE_URL` y sobrevive
  entre tests.

## Tests (RED primero)
# should_pass_site_model_suite_together_with_unit_tests   (el que hoy falla: 10 → 0)
# should_not_override_event_loop_fixture_anywhere         (scan de los conftest)
# should_declare_asyncio_fixture_loop_scope_in_config     (lee pyproject)

## Criterio de done
- [ ] `pytest tests/modules/agents_hub/unit tests/modules/agents_hub/integration` → **0 failed**
- [ ] Sin fallos nuevos: `unit`+`integration`+`evaluation`+`public_graphs`+`infra` y
      `tests/modules/agents_hub/e2e` (adjuntar las cifras de antes y después)
- [ ] Cero warnings de pytest-asyncio sobre `event_loop` en la salida
- [ ] Los 3 `test_brain_*` de `tests/test_imports.py` siguen siendo el único fallo
      inventariado (módulo `modules/brain` inexistente), o se retiran si ya no aplican
```

---

### Prompt TST.2 (RED/GREEN) — Ningún test escribe en la BD de desarrollo

**Modelo sugerido**: **Sonnet** — reutiliza la fixture desechable ya existente; el trabajo es cablear y poner el guardarraíl.

```
# PROMPT TST.2 (RED/GREEN) — La suite e2e deja residuos en la BD del desarrollador
# Deploy: n/a (infraestructura de tests)

## Síntoma medido
En la BD de desarrollo hay **12 chatbots residuales** de ejecuciones de test:
8 `E2E Bot <uuid>` (organización «E2E Test Client») y 4 `Pipeline Test <uuid>`
(«Pipeline Test Client»). `tests/modules/agents_hub/e2e/conftest.py` lo dice en su
docstring: «Por defecto usan la misma BD de desarrollo (govgenai)», y su fixture
`db_engine` crea las tablas del hub ahí.

Es la misma familia que la fixture destructiva ya arreglada: un test que escribe en la BD
del desarrollador ensucia el entorno y, cuando además la limpia, se lo lleva por delante.

## Trabajo
- `e2e/conftest.py` pasa a usar la **BD desechable por test** de
  `tests/modules/agents_hub/conftest.py` (fixture `db_url` / `db_session`), en lugar de
  `os.getenv("DATABASE_URL")`. Si algún test e2e necesita el `app` de FastAPI apuntando a
  esa BD, sobreescribir la dependencia de sesión, no el entorno global.
- **Limpieza de los residuos actuales**: comando o paso documentado que borre las
  organizaciones `E2E Test Client` y `Pipeline Test Client` con sus chatbots en cascada.
  Que **reporte lo que borra** y no lo haga en silencio: es la BD del usuario.
- **Guardarraíl**, que es lo que evita la recaída:
  ningún fichero de `tests/` puede (a) llamar a `metadata.drop_all`, ni (b) crear tablas
  sobre una URL que venga de `DATABASE_URL` sin pasar por la fixture desechable.

## Tests (RED primero)
# should_have_no_test_fixture_calling_drop_all              (scan de tests/)
# should_have_no_test_creating_tables_on_the_dev_database   (scan de tests/)
# should_run_e2e_against_a_disposable_database              (la BD del test no es la de DATABASE_URL)
# should_leave_no_rows_in_the_dev_database_after_e2e        (recuento antes/después)

## Criterio de done
- [ ] `tests/modules/agents_hub/e2e` verde contra BD desechable
- [ ] Recuento de `hub_chatbots` en la BD de desarrollo **idéntico antes y después** de
      ejecutar la suite completa (adjuntar los dos números)
- [ ] Los 12 residuos retirados, con el recuento de lo borrado en el cierre
- [ ] Sin BD `test_hub_*` huérfanas tras la ejecución (la fixture las borra en su finally)
```

---

### Prompt TST.3 (GREEN) — Cero fallos preexistentes: se acaban los asteriscos

**Modelo sugerido**: **Sonnet** — dos arreglos mecánicos y un guardarraíl; ninguna decisión de diseño abierta.

```
# PROMPT TST.3 (GREEN) — Retirar los últimos fallos que se venían filtrando
# Deploy: n/a (infraestructura de tests)

## Síntoma medido (tras TST.1 y TST.2)
Con el aislamiento ya arreglado, la suite completa sigue arrastrando 12 resultados rojos
que llevan meses «inventariados» y que hay que recordar filtrar en cada cierre de bloque:

- **3 failed** en `tests/test_imports.py`: `test_brain_llm_gateway_import`,
  `test_brain_extraction_strategies_import`, `test_brain_cortex_import`.
  `ModuleNotFoundError: No module named 'server.app.modules.brain'`. El módulo `brain`
  fue retirado; son tests-smoke de un import que ya no existe.
- **9 errors** de colección en `tests/unit/test_admin_models.py` (3) y
  `tests/unit/test_prompt2_db_api.py` (6): `ModuleNotFoundError: No module named
  'aiosqlite'`. Ambos usan `sqlite+aiosqlite:///:memory:` pero `aiosqlite` no está
  declarado ni en `pyproject.toml` ni en `uv.lock`.

Un fallo que se filtra a mano deja de ser información: nadie distingue el 12 esperado del
13 nuevo. Este prompt lo lleva a cero para que «suite verde» vuelva a significar algo.

## Trabajo
- **`aiosqlite` como dependencia de desarrollo**: `uv add --dev aiosqlite`. Es lo que ya
  presuponen los tests; no se cambian los tests para no usar sqlite.
- **Los 3 tests de `brain`: Caso B, borrado directo.** El módulo no existe y no hay
  migración en curso asociada; el historial de git es la fuente de verdad del pasado.
  No dejar el test comentado ni con `skip`: se borra la función.
  Comprobar antes con `grep -r` que no queda ninguna otra referencia a `modules.brain`
  en el proyecto (código, tests, docs); si queda, retirarla también.
- **Guardarraíl** en `tests/infra/test_suite_hygiene.py`: ningún test puede importar un
  módulo del proyecto que no exista. Basta con un escaneo de los `import
  server.app.modules.<x>` de `tests/` comprobando que el paquete está en disco — barato
  y detecta la próxima retirada que deje tests huérfanos.

## Tests (RED primero para el guardarraíl)
# should_not_import_nonexistent_project_modules   (scan de tests/, RED con los 3 de brain)

## Criterio de done
- [ ] `uv run pytest tests/unit tests/api tests/core tests/modules tests/infra` y los
      ficheros de `tests/` raíz: **0 failed, 0 errors** (adjuntar la cifra)
- [ ] `grep -r "modules.brain"` a cero en todo el proyecto
- [ ] `aiosqlite` en `pyproject.toml` **y** en `uv.lock`
- [ ] Actualizar la memoria de gaps preexistentes: ya no hay nada que filtrar
```

---

### Prompt TST.4 (GREEN) — Coste de la verificación: que la suite deje de frenar el desarrollo

**Modelo sugerido**: **Sonnet** — tres cambios de infraestructura medidos; ninguna decisión de diseño abierta.

> **Añadido el 2026-08-01 a petición del usuario**, al ver que ejecutar la suite completa tras
> cada prompt costaba entre 5 minutos y más de una hora según la carga de la máquina. La
> pregunta era «¿reducimos tests o los ejecutamos solo al cerrar el bloque?»; la respuesta
> medida fue que el problema no es el número de tests sino cómo se ejecutan.

```
# PROMPT TST.4 (GREEN) — Tres cambios medidos y una politica escalonada

## Lo que se midio antes de tocar nada (mismo subconjunto, tiempo que reporta pytest)
- Cobertura forzada en addopts: 21,3 s -> 12,8 s sin ella. ~40 % de toda ejecucion local.
- BD desechable por test: ~1,3 s de SETUP por test. tests/.../integration son 139 tests en
  212 s, o sea que el setup era practicamente todo el directorio.
- Cola gorda: 39 s (chat CoreGraph en modo RAG), 21 s (reconciliador), 13 s (migracion HNSW).

## Los tres cambios
1. Quitar --cov de addopts. CI ya lo pasa explicito en sus dos invocaciones, asi que la
   cobertura vigilada no baja ni un punto. En local, bajo demanda.
2. pytest-xdist con -n auto en addopts. Es seguro porque cada test de BD crea la suya con
   nombre unico, sin estado compartido que serializar.
3. BD desechable por TEMPLATE: una plantilla por sesion con el esquema creado, y cada test
   la copia con CREATE DATABASE ... TEMPLATE, que es copia de ficheros.

## La contrapartida que hay que atajar en el mismo prompt
-n auto reparte los tests entre procesos, y eso ESCONDE el estado filtrado entre tests, que
es justo lo que TST.1 unifico CI para cazar. CI se queda en -n0, con el porque escrito en el
workflow y en CLAUDE.md. En local manda la velocidad; en CI manda la deteccion.

## Politica escalonada (CLAUDE.md, seccion de ejecucion por bloques)
- Durante el prompt: solo el fichero de tests que se esta escribiendo.
- Al cerrar el prompt: los directorios que toca + tests/infra/test_suite_hygiene.py.
- Al cerrar el bloque: la suite entera, desde Git Bash.

## Criterio de done
- [ ] Suite completa verde con -n auto y cifra medida (no deducida)
- [ ] Suite verde tambien con -n0, que es el modo de CI
- [ ] Antes/despues del setup por test, medido
```

---
