## Bloque NIC — La retirada del legacy NiceGUI, con inventario antes de borrar

> **Planificado el 2026-08-21**, al revisar el repositorio para abrirlo. La regla de `CLAUDE.md` dice
> que `client_app/` debe contener **sólo** el agente de ejecución local (RPA, folder watcher) y que
> todo lo demás es legacy pendiente de migrar. Medido hoy, no es así:
>
> | | |
> |---|---|
> | Ficheros versionados en `client_app/` | **505** |
> | De ellos, importan NiceGUI | **96** (87 en `app/ui`) |
> | El agente de ejecución local | `app/core/rpa_executor.py`, `app/modules/rpa/`, `app/modules/watchers/` (folder, email, web, api) |
> | Ficheros en `_legacy_nicegui/` | 52 (29 de `client_app`, 22 de `server`, 1 `main.py`) |
>
> **Nada en producción depende de `client_app/`.** Las diez menciones en `server/` son comentarios de
> procedencia («Migrado desde `client_app/app/modules/privacy/anonymizer.py`»). Hay **un solo import
> real**, y está en un test: `shared/tests/test_security_unification.py:44`. No aparece en
> `docker-compose`, ni en el `Dockerfile`, ni en CI.
>
> **Y la UI NiceGUI existe hoy en cuatro sitios**: la carpeta `Documents\AutomatIA`, el bundle de
> GenGov, `client_app/app/ui` y `_legacy_nicegui/`. Conservarla dos veces dentro del repositorio que
> se va a abrir no se sostiene cuando hay dos copias verificadas fuera.
>
> **Por qué esto es un bloque y no una limpieza.** Borrar 87 ficheros a ojo es exactamente cómo se
> pierde una funcionalidad sin enterarse: `app/ui` no es sólo pantallas, arrastra servicios que quizá
> no tengan equivalente todavía en `server/app/modules/automation/`. El primer prompt no borra nada:
> cruza.

### Prompt NIC.1 (análisis) — El inventario: qué está cubierto y qué no

**Modelo sugerido**: **Opus** — decide qué se considera «cubierto», que es la decisión de todo el bloque.

```
# PROMPT NIC.1 (analisis) — Cruzar client_app/app contra lo que ya existe
# Deploy: n/a (documento)

## Por que
La regla de retirada de legacy exige que nada se borre antes de estar cubierto. Nadie ha hecho el
cruce, asi que hoy no se sabe que de `client_app/app/ui` y `app/services` tiene equivalente en
`server/app/modules/automation/` + `frontend/src/automation/` y que no.

## Que hacer
1. Para cada pantalla de `client_app/app/ui` y cada servicio de `client_app/app/services`, localizar
   su equivalente actual (endpoint, servicio, componente) o declarar que no existe.
2. Escribir `docs/INVENTARIO_RETIRADA_LEGACY.md` con una fila por fichero y una de estas cuatro
   etiquetas: **cubierto** (hay equivalente verificado), **parcial** (existe pero le falta algo
   concreto, y decir que), **no cubierto** (no hay nada), **no aplica** (era andamiaje).
3. No mover ni borrar nada. Este prompt solo mira.
4. En el informe de cierre, decir cuantos ficheros caen en cada etiqueta.

## Tests (RED primero)
- RED: un test de infra comprueba que `docs/INVENTARIO_RETIRADA_LEGACY.md` existe y tiene una fila
  por cada fichero de `client_app/app/ui` y `client_app/app/services` (se compara contra
  `git ls-files`). Asi el inventario no puede quedarse a medias sin que se note.

## Criterio de done
- [ ] Cada fichero de `app/ui` y `app/services` tiene etiqueta y justificacion
- [ ] Las etiquetas «cubierto» citan el equivalente concreto, no «esta en automation»
- [ ] Cero ficheros movidos o borrados en este prompt
```

### Prompt NIC.2 (RED/GREEN) — Lo cubierto se va a la cuarentena

**Modelo sugerido**: **Sonnet** — alcance cerrado por el inventario de NIC.1.

```
# PROMPT NIC.2 (RED/GREEN) — Mover a _legacy_nicegui lo que ya esta cubierto
# Deploy: n/a (retirada)

## Por que
`CLAUDE.md`, Caso A: el codigo NiceGUI migrado se mueve a `_legacy_nicegui/` manteniendo la ruta
relativa, y el borrado definitivo lo hace el usuario al cerrar la Fase 1. Lo etiquetado «cubierto»
en NIC.1 ya cumple la condicion y hoy sigue en su sitio original.

## Que hacer
1. Mover a `_legacy_nicegui/` todo lo etiquetado **cubierto**, manteniendo la ruta relativa.
2. Lo etiquetado **no aplica** se borra directamente (Caso B): era andamiaje, el historial de git
   guarda el pasado.
3. `grep -r` a cero de imports activos hacia lo movido, antes de cerrar el prompt.
4. Arreglar el unico import real que queda: `shared/tests/test_security_unification.py:44` importa
   `client_app.app.services.sandbox_service`. O apunta al equivalente, o el test se retira con su
   razon escrita.

## Tests (RED primero)
- RED: ningun fichero fuera de `_legacy_nicegui/` importa lo movido.
- RED: `client_app/` no contiene ya ningun fichero etiquetado «cubierto».
- La suite entera despues, desde Git Bash.

## Criterio de done
- [ ] `grep -r` a cero de imports hacia lo movido
- [ ] Suite completa verde
- [ ] Lo etiquetado «parcial» y «no cubierto» sigue intacto y en su sitio
```

### Prompt NIC.3 (RED/GREEN) — En `client_app/` se queda solo el agente de ejecución

**Modelo sugerido**: **Opus** — decide qué es agente y qué era interfaz de configuración del agente.

```
# PROMPT NIC.3 (RED/GREEN) — client_app queda reducido a su unica razon de existir
# Deploy: edge (client_app es el nodo de ejecucion local)

## Por que
`client_app/` existe para una cosa: ejecutar en la maquina del cliente lo que la nube no puede
—RPA, vigilancia de carpetas, correo, web—. Todo lo demas que hay ahi es interfaz NiceGUI, y la
interfaz de configuracion de esos vigilantes pertenece al frontend, no al agente.

## Que hacer
1. Dejar en `client_app/` el agente y sus tests: `app/core/rpa_executor.py`, `app/modules/rpa/`,
   `app/modules/watchers/`, la configuracion y la base de datos local que necesiten, y el cliente
   WebSocket contra el servidor si existe.
2. Lo etiquetado **parcial** o **no cubierto** en NIC.1 **no se toca aqui**: sale del bloque y se
   planifica como migracion propia. Decirlo en el informe de cierre, con la lista.
3. Actualizar `docs/Arquitectura.md` y `CLAUDE.md` con lo que `client_app/` es al terminar.

## Tests (RED primero)
- RED: un test de infra falla si aparece un import de `nicegui` dentro de `client_app/`.
- RED: los vigilantes y el ejecutor RPA siguen pasando sus tests actuales.

## Criterio de done
- [ ] Cero imports de `nicegui` en `client_app/`
- [ ] Los tests del agente de ejecucion siguen verdes
- [ ] La lista de lo «parcial» y «no cubierto» queda escrita como trabajo pendiente
```

### Prompt NIC.4 (RED/GREEN) — El entorno legacy de la raíz también se va

**Modelo sugerido**: **Sonnet** — mecánico, pero hay que medir antes de tocar.

```
# PROMPT NIC.4 (RED/GREEN) — Retirar lo que solo existia para sostener NiceGUI
# Deploy: n/a (retirada)

## Por que
Cuando NiceGUI se va, se quedan colgando cosas que solo existian por el:

- `pyproject.toml` de la raiz: su primera dependencia es `nicegui==3.4.1`, y su `uv.lock` pesa 1,3 MB.
- `tests/` de la raiz (35 ficheros): CI solo los recoge (SEC.8.7); hay que decidir si migran a
  `server/tests/` o se retiran.
- `translations.json` (158 KB) y `shared/automatia_shared/core/i18n.py`: el i18n del legacy. El
  frontend usa i18next.
- `arranque.bat`: comprobar si sigue arrancando algo que exista.

## Que hacer
1. Medir primero: quien importa cada una de esas piezas. Sin medir, no se toca.
2. Retirar lo que quede huerfano, con su razon en el commit.
3. Si el `pyproject.toml` de la raiz se queda sin funcion, retirarlo con su `uv.lock`; si mantiene el
   `[tool.pytest.ini_options]` de la suite raiz, decir explicitamente para que sirve.
4. Actualizar `README.md` (la seccion «Donde esta cada cosa») y `docs/Arquitectura.md`.

## Tests (RED primero)
- RED: un test de infra falla si `nicegui` aparece como dependencia en cualquier `pyproject.toml`.
- RED: la suite raiz sigue recogiendose en CI, o se documenta su retirada.

## Criterio de done
- [ ] `grep -ri nicegui` a cero en dependencias y configuracion
- [ ] `uv sync --locked` y la suite completa verdes desde cero
- [ ] `README.md` refleja la estructura real
```

### Prompt NIC.5 (manual del usuario) — El borrado definitivo de `_legacy_nicegui/`

**Modelo sugerido**: — (no es un prompt de agente)

```
# PROMPT NIC.5 — Lo hace el usuario, a mano
# Deploy: n/a

`CLAUDE.md` reserva este paso a la persona: `_legacy_nicegui/` es cuarentena de larga duracion y se
borra al cerrar la Fase 1 completa, una vez verificado en produccion lo migrado.

Cuando el usuario lo borre:
1. Retirar de `CLAUDE.md` la seccion del Caso A y la mencion a `_legacy_nicegui/` en el README, que
   describen un directorio que ya no existe.
2. Comprobar que `_legacy_archive/`, si aun existe, se va con el.
3. Suite completa verde y `docker compose up` despues.
```

> **Orden y dependencias.** NIC.1 es la condición de todo: sin inventario, NIC.2 y NIC.3 borran a
> ciegas. NIC.4 depende de que NiceGUI ya no esté en `client_app/`. NIC.5 es del usuario y cierra la
> Fase 1. **El Bloque REPO va después de NIC.5**, no antes.

---
