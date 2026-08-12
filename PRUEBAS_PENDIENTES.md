# Pruebas manuales pendientes

> Escrito el 2026-08-12 como traspaso de sesión. Documento autocontenido: no hace falta
> la conversación previa para ejecutarlo.
>
> Contexto de fondo y matriz por módulo: `docs/PRUEBAS_MANUALES.md`.

---

## 0. Antes de nada: hay un commit sin subir

```
8c15e95  chore(man): retirar el .bat de 9CBis.11 y corregir el camino de temas del maestro
```

El árbol de trabajo está limpio. El commit anterior (`537f611`, el fix de lint que ponía
CI en rojo) **ya está subido**. Para subir el que queda:

```powershell
git push
```

---

## 1. Requisitos previos (comunes a todo)

1. **Docker Desktop** arrancado (icono verde en la barra de tareas).
2. **Base de datos** levantada:
   ```powershell
   docker compose up -d db
   ```
3. **Migraciones al día**, desde `server\`:
   ```powershell
   cd C:\Users\fabra\Documents\AI_agents_hub\server
   uv run alembic upgrade head
   ```
4. **Backend** (desde la raíz; tarda ~80 s en arrancar, es normal):
   ```powershell
   cd C:\Users\fabra\Documents\AI_agents_hub
   uv run --project server uvicorn server.app.main:app --port 8000
   ```
5. **Frontend** (en otra terminal, desde `frontend\`):
   ```powershell
   cd C:\Users\fabra\Documents\AI_agents_hub\frontend
   npm run dev
   ```
6. **Sesión iniciada** en http://localhost:5173/login como `fabra@uji.es` (SuperAdmin).

Atajo: `arranque.bat` (doble clic, opción 1) levanta backend y frontend en dos ventanas.
No levanta Docker ni la BD: los pasos 1–3 son tuyos.

---

## 2. Qué ejecutar, en este orden

Los cuatro `.bat` están en la raíz del proyecto. Se ejecutan con doble clic y van
pidiendo una tecla entre pasos.

### 2.1 — `pruebas_manuales_bloqueREV.bat` — **prioridad alta**

**Por qué**: REV.1 es el código más reciente con interfaz y **nadie lo ha verificado a
mano todavía**. Añade el veredicto de quien revisa sobre conversaciones reales.

**Qué comprueba**: la cola de pendientes y el veredicto en http://localhost:5173/hub/reports,
con nota obligatoria cuando el veredicto es «mal».

### 2.2 — `pruebas_manuales_plataforma.bat` — **prioridad alta**

**Por qué**: es el guion maestro de MAN.2 y **el criterio de cierre que falta** de ese
bloque. Cruza varios módulos en cada camino.

Tiene menú, o le pasas el número como parámetro:

| Opción | Camino |
|---|---|
| `0` | Solo smoke check de servicios — **empieza por aquí** |
| `1` | Organización → dos chatbots → temas → widget |
| `2` | Corpus → consulta → cita → feedback → hueco |
| `3` | Plantilla de redacción → borrador → anonimización → exportación |
| `4` | Script propuesto → sandbox → aprobación → agente local |

**Dos avisos sobre este guion, ya corregidos dentro del propio `.bat`:**

- **CAMINO 1** decía que el widget no aplica ningún tema. **Era falso desde el
  2026-08-10**: el hallazgo #3 de MAN.2 lo arregló y SEC.8.6 movió los temas a la base de
  datos. Si lo hubieras ejecutado con la versión anterior habrías dado por bueno un
  defecto que ya no existe. Ahora lleva los `curl` reales de crear tema, aplicarlo y
  emitir la credencial de sitio.
- **No hay pantalla de temas** en el panel de administración (queda para un prompt
  propio), así que crear y aplicar un tema va por API. Los `curl` exactos están dentro
  del CAMINO 1(c).

- **CAMINO 2**: al corpus **ya no se sube un PDF**, solo Markdown del contrato (cambio de
  EXT.1). Un PDF da 415 con un mensaje que lo explica; probar eso también vale.

### 2.3 — `pruebas_manuales_bloqueSEC.bat`

**Por qué**: el bloque SEC sigue marcado «pendientes las pruebas manuales» en
`PROJECT_STATE.md`.

**Qué comprueba**: contabilidad de tokens y cuotas, login del admin, temas cerrados sin
sesión, aislamiento entre organizaciones.

### 2.4 — `pruebas_manuales_bloqueRAG.bat`

**Por qué**: quedó bloqueado en su día por el defecto FIX.1 (el modelo de un chatbot no
se podía cambiar), que **ya está arreglado**.

**Qué comprueba**: escenarios de prueba en http://localhost:5173/hub/test-scenarios y los
huecos de corpus en http://localhost:5173/curation/findings.

---

## 3. Opcional: solo si quieres reprobar la instalación desde cero

`pruebas_manuales_bloqueFASE11.bat` — verifica la instalación «one-click» completa.

**Cuidado**: ocupa los puertos **80 y 443** y exige parar antes la BD de desarrollo
(`docker compose -f docker-compose.yml down`). No lo lances si estás a media prueba de
los anteriores.

Comprobado que D.4.0 no lo invalida: el `Dockerfile` hace `uv sync --frozen --no-dev`
sin el extra `local-models`, y este guion no toca ingesta.

---

## 4. Vigentes, pero no hace falta repetirlos ahora

Cubren código antiguo ya verificado y sin cambios desde su prompt:

- `pruebas_manuales_promptAUTH_4.bat` — login, tokens de acceso, SSO opcional.
- `pruebas_manuales_promptFIX1.bat` — selector de modelo y escenarios de prueba.
- `pruebas_manuales_promptROL_2.bat` — renombrado Partner→Admin, Client→Organización.
- `pruebas_manuales_promptSBX_4.bat` — aislamiento Docker del sandbox. SEC.8.3 lo
  refuerza, no lo invalida.

---

## 5. Qué se hizo en la sesión anterior (para no repetirlo)

### Arreglado el rojo de CI (commit `537f611`, ya subido)

`ruff check app/` fallaba con cinco F401 (imports sin usar). Comprobado endpoint por
endpoint que **ninguno tapaba una guarda de autenticación perdida** antes de borrar:

| Fichero | Import | Por qué sobraba |
|---|---|---|
| `server/app/api/v1/hub_chat.py` | `get_current_user`, `require_scopes` | El endpoint sigue protegido por `require_scopes_allowing_widget("chat:test")`. La mención en el docstring es prosa. |
| `server/app/routers/hub_themes_router.py` | `get_current_user` | Los 7 endpoints llevan su `Depends`; `/presets` es público a propósito. |
| `server/app/routers/hub_ingestion_router.py` | `HubChatbot` (línea 394) | Import local sobrante desde que `_chatbot_autorizado()` devuelve el chatbot. |
| `server/app/modules/agents_hub/ingestion/watcher.py` | `tempfile` | Arrastre del paso por fichero temporal ya retirado. |

Verificado: `ruff check app/` limpio, y **319 tests pasan** en
`server/tests -k "chat or ingest or watcher or theme"`, más 13 en
`test_hub_themes.py` + `test_imports.py`.

### Poda de los `.bat` (commit `8c15e95`, **sin subir**)

Verificados los 11 `.bat` de la raíz contra el código actual, porque el inventario de
MAN.1 era del 2026-08-09 y desde entonces entraron SEC.8, EXT, FAQ, D.4.0, REV.1 y DER.

**Borrado 1**: `pruebas_manuales_prompt9CBis11.bat`. Inejecutable desde SEC.8.5 — su
banco de pruebas `frontend/widget.html` autentica con `data-token` (un JWT de rol admin
incrustado y caducado) y el widget **ya no lee ese atributo**: ahora manda `X-Widget-Key`
desde `data-widget-key`. Sumado al `chatbot_id` de fixture inexistente, daba 401 siempre.
Está en el historial de git, recuperable.

**Corregido 1**: `pruebas_manuales_plataforma.bat` (el CAMINO 1 descrito arriba). De paso
se arreglaron dos defectos propios del guion: dos `^` de continuación de línea que
habrían fundido varios `echo` en uno, y un `&&` que no funciona en PowerShell. Ejecutado
en seco (`plataforma.bat 1`) y verificado que renderiza bien.

**`docs/PRUEBAS_MANUALES.md`** puesto al día: su inventario daba 9CBis.11 por vigente y
arrastraba dos avisos de «bloqueado de raíz» por los hallazgos #2 y #3 que el propio
documento ya declaraba resueltos más arriba.

---

## 6. Dos huecos abiertos (no son pruebas, son trabajo)

1. **El bloque DER no tiene `.bat`.** DER.1 («una carga, varios chatbots») y DER.2 (aviso
   de deriva entre copias de la misma norma) cambiaron el comportamiento de
   http://localhost:5173/hub/documents, y ningún guion cubre eso. Si quieres verificarlo
   a mano en esta ronda, es la pantalla de documentos: cargar una norma y comprobar que
   se puede asociar a varios chatbots, y que borrarla avisa de en cuántos más está.

2. **`frontend/widget.html` necesita arreglo de código.** Sigue con el `chatbot_id` de
   fixture (`9d6eed7d…`, «E2E Bot») y el `data-token` muerto. No es documentación: es un
   fichero que hay que actualizar para que use `data-widget-key`. Pendiente de decidir.

---

## 7. Nota sobre la codificación de los `.bat`

Comprobados los 10 `.bat` de la raíz: **ninguno tiene BOM y ninguno tiene bytes
no-ASCII**, así que la página de códigos que declaran (`chcp 1252` o `chcp 65001`) es
indiferente y ninguno debería mostrar símbolos raros. Si ves caracteres extraños al
ejecutarlos, el problema está en la consola, no en los ficheros.

Si algún día editas un `.bat`, **no lo guardes con el editor en UTF-8 con BOM**: CMD
interpreta los primeros bytes como parte del primer comando (`echo` pasa a leerse `ho`).
Escríbelos desde PowerShell con codificación 1252:

```powershell
[System.IO.File]::WriteAllText('ruta\absoluta\archivo.bat', $contenido,
    [System.Text.Encoding]::GetEncoding(1252))
```
