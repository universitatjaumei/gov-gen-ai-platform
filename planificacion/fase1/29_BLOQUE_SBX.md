## Bloque SBX — Seguridad de la Información: Sandbox aislado de ejecución de scripts (Subfase 1.B → 1.C, PENDIENTE)

**Objetivo del bloque**: introducir una **frontera de aislamiento por contenedor** para todo código que el sistema ejecuta como resultado de propuestas LLM o de scripts metaprogramados (extracción admin, charts matplotlib, fallback ETL). La auditoría AST (`ScriptSecurityAuditor`, 9R.5.4) y los límites de recursos en proceso son **una primera capa, no la última**: la dinamicidad de Python (getattr, manipulación de `__builtins__`, decoradores, bytecode) deja huecos que la auditoría estática no cubre. Este bloque añade una capa que el script no puede saltar aunque escape del intérprete: un **microservicio evaluador** independiente (`script-sandbox`) en red dedicada sin acceso a base de datos, almacenamiento ni internet, con cgroups/seccomp del propio Docker. El patrón es defensible ante una comisión de seguridad pública porque encaja con el estándar de microservicios (no requiere acceso al socket de Docker del host) y se traduce 1:1 a Cloud Run en GCP.

**Justificación de la ubicación (antes de Fase 11)**:
- Fase 11.2 reescribe `docker-compose.prod.yml` para distribución como software libre. SBX debe haber dejado allí el servicio `script-sandbox` antes de que 11.2 fije el formato.
- Es prerrequisito de auditoría pre-despliegue por la comisión de Seguridad de la Información.
- No bloquea el resto de Fase 1: los tests existentes pasan con la implementación in-process actual; SBX los reorienta a la frontera de red sin cambiar los contratos de los pipelines.

**Decisión Arquitectónica (2026-05-17)**: opción "Microservicio Evaluador" frente a "Docker-out-of-Docker (DooD)". Razones:
1. No requiere montar `/var/run/docker.sock` en el contenedor de la API — eliminamos el principal punto de fricción con infosec en entornos gubernamentales.
2. Funciona en Cloud Run (la opción DooD no — Cloud Run no expone socket de Docker).
3. Encaja con el modelo edge: en despliegues on-premise del cliente, dos contenedores en red privada se auditan trivialmente.
4. Cloud Run corre sobre gVisor por defecto: el sandbox hereda aislamiento de kernel sin configurar nada.

**Capas de defensa resultantes (defensa en profundidad)**:

1. `ScriptSecurityAuditor` (AST) — primera barrera en la API.
2. Re-auditoría defensiva dentro del propio sandbox (segunda barrera, antes de exec).
3. Red dedicada `sandbox-net` — sin DNS hacia `postgres`, `minio`, ni salida a internet.
4. Contenedor sin privilegios: `read_only: true`, `cap_drop: ALL`, `no-new-privileges`, usuario `65534:65534`.
5. Subproceso efímero por petición dentro del sandbox — sin contaminación de memoria entre ejecuciones, `kill` explícito en `finally`.
6. Límites de recursos del propio Docker (`cpus`, `memory`, `tmpfs` con tamaño máximo).
7. En GCP: gVisor (heredado automáticamente).

**Lo que NO incluye este bloque**:
- Migración del sandbox a gVisor explícito on-premise (queda en backlog post-MVP, solo se documenta cómo aplicar `runsc` si el cliente lo requiere).
- Auditoría dinámica del comportamiento del script en tiempo de ejecución (tracing de syscalls). El aislamiento por contenedor + sin red + sin privilegios cubre el modelo de amenazas del MVP.
- Ejecución distribuida o paralelización del sandbox (un único contenedor con un worker pool basta para el volumen previsto).

**Reglas duras del bloque SBX**:
- El microservicio `script-sandbox` **es edge** (vive en el cliente, ejecuta sobre datos del cliente).
- El sandbox **no importa nada** del módulo `redaccion` ni de `agents_hub`. Es un servicio autocontenido con su propio `Dockerfile` y `pyproject.toml` mínimo. Solo comparte el contrato HTTP.
- El cliente HTTP (`SandboxClient`) vive en `server/app/core/sandbox_client.py` (compartido, no edge ni cloud — capa de infraestructura). Análogo a `StorageService`.
- La auditoría AST se duplica intencionalmente: la API audita antes de enviar, el sandbox audita antes de ejecutar. **No** es deuda técnica; es defensa en profundidad. Si el contenedor recibe código no auditado (por bug en la API), no lo ejecuta.
- El sandbox **no persiste** nada entre peticiones. Cada `/execute` arranca un subproceso hijo limpio que muere al terminar.

---

### Prompt SBX.1 (RED/GREEN) — Microservicio `script-sandbox`: FastAPI + subprocess efímero

**Modelo sugerido**: **Opus** — el prompt concentra decisiones de diseño embebidas: contrato HTTP (3 endpoints con semánticas distintas: extracción JSON vs. chart bytes vs. ETL CSV), estrategia de aislamiento del subproceso hijo (fork + kill explícito en `finally`, no confiar en `subprocess.run(timeout=)`), serialización de `options` complejas, re-auditoría AST defensiva sin importar del módulo `redaccion`.

```markdown
# PROMPT SBX.1 (RED/GREEN) — Microservicio script-sandbox

Objetivo: crear un servicio FastAPI autocontenido `services/script_sandbox/` que ejecuta scripts Python aprobados en un subproceso efímero, devolviendo resultados estructurados. Este servicio sustituye los `subprocess.run([sys.executable, ...])` que hoy viven dentro del proceso del API (admin_script_pipeline, chart_renderer, etl_service).

Deploy: edge (forma parte del despliegue del cliente).

## Estructura del nuevo paquete

```
services/script_sandbox/
├── pyproject.toml          # uv-managed; deps mínimas (fastapi, pydantic, pandas, matplotlib, seaborn, numpy, openpyxl, pdfplumber)
├── Dockerfile              # python:3.12-slim, usuario no-root, sin pip-cache
├── sandbox/
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── auditor.py          # COPIA SIMPLIFICADA de ScriptSecurityAuditor — re-auditoría defensiva
│   ├── runner.py           # ejecuta subproceso hijo + kill explícito
│   ├── wrappers.py         # build_extraction_wrapper, build_chart_wrapper, build_etl_wrapper
│   └── contracts.py        # Pydantic: ExecuteExtractionRequest/Response, ExecuteChartRequest, ExecuteETLRequest
└── tests/
    ├── test_health.py
    ├── test_execute_extraction.py
    ├── test_execute_chart.py
    ├── test_execute_etl.py
    ├── test_auditor_defense.py
    └── test_runner_kills_runaway.py
```

## Contrato HTTP

### `GET /health` → `{"status":"healthy"}`

### `POST /execute-extraction`
Request:
```json
{
  "code": "<script Python>",
  "file_path": "/tmp/sandbox/abc.xlsx",   # ruta dentro del tmpfs del sandbox; el caller debe haberlo escrito antes
  "raw_text": "...",
  "options": {"sheet": "Hoja1"},
  "timeout_seconds": 30
}
```
Response 200:
```json
{
  "result": {
    "tables": [...],
    "metrics": [...],
    "free_text": null
  },
  "stdout_truncated": false
}
```
Response 4xx/5xx:
- 422 SCRIPT_AUDIT_FAILED (`{"code":"SCRIPT_AUDIT_FAILED","findings":[...]}`)
- 422 SCRIPT_EMPTY
- 504 SCRIPT_TIMEOUT
- 500 SCRIPT_EXECUTION_ERROR (con `stderr_truncated` en el body, capado a 500 chars)

### `POST /execute-chart`
Request:
```json
{
  "code": "<script matplotlib>",
  "data_csv": "<contenido CSV completo>",
  "output_format": "png",
  "timeout_seconds": 30
}
```
Response 200: `Content-Type: image/png` (o image/svg+xml) con los bytes.
Response 4xx/5xx: mismos códigos que extraction (audit, empty, timeout, execution).

### `POST /execute-etl`
Request:
```json
{
  "code": "<script con def transform(df)>",
  "data_csv": "<CSV de entrada>",
  "timeout_seconds": 30
}
```
Response 200: `Content-Type: text/csv` con el CSV transformado.
Response 4xx/5xx: idéntico patrón.

## Estrategia de subproceso (runner.py)

REGLA DURA: **no usar `subprocess.run(timeout=)` solo**. Implementar `Popen` + timeout manual con `kill` explícito en `finally`:

```python
def run_subprocess(args: list[str], timeout: int) -> SubprocessResult:
    proc = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return SubprocessResult(returncode=proc.returncode, stdout=stdout, stderr=stderr)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.communicate(timeout=2)  # drena los pipes tras kill para evitar zombies
        except subprocess.TimeoutExpired:
            pass
        raise TimeoutError()
```

Cada `/execute-*` escribe el wrapper a un fichero temporal en `/tmp/sandbox/`, ejecuta `python` con ese fichero, captura stdout y borra el fichero en `finally`. NUNCA reutiliza el intérprete: cada petición arranca un proceso hijo nuevo. Esto garantiza que ninguna variable, módulo cargado o estado global persiste entre ejecuciones, sin necesidad de reciclar el contenedor.

## Wrappers (wrappers.py)

- `build_extraction_wrapper(code, file_path, raw_text, options)` — análogo al actual `_build_wrapper` de `admin_script_pipeline.py`, imprime `json.dumps(result, default=str)` al stdout.
- `build_chart_wrapper(code, csv_path, out_path, output_format)` — análogo al actual `_WRAPPER_TEMPLATE` de `chart_renderer.py`, llama `plt.savefig(out_path)`.
- `build_etl_wrapper(code, in_csv_path, out_csv_path)` — exec del código (que define `transform(df)`), `transform(df).to_csv(out_csv_path, index=False)`.

Todos los wrappers usan `repr()` para serializar valores en lugar de embebed JSON, para evitar problemas con `True/False/None`.

## Auditor.py — copia defensiva

CRÍTICO: NO importar `ScriptSecurityAuditor` desde `server.app.modules.redaccion`. El sandbox es autocontenido. Copiar la implementación en `sandbox/auditor.py` con su propia `WHITELIST_MODULES`. Si la lista blanca diverge con el tiempo, es porque el sandbox necesita ser MÁS estricto que la API (es la segunda barrera). Documentar esta duplicación en `docs/SANDBOX_SECURITY.md` (creado en SBX.4).

Todos los endpoints invocan `auditor.audit(code)` antes de construir el wrapper. Si `not audit.approved` → 422 SCRIPT_AUDIT_FAILED.

## Tests (RED → GREEN)

Tests in-process con `fastapi.testclient.TestClient` (sin necesidad de levantar Docker en CI):

- test_health_returns_ok
- test_execute_extraction_runs_pandas_script
- test_execute_extraction_returns_422_for_eval_call
- test_execute_extraction_returns_504_on_timeout
- test_execute_extraction_returns_500_with_stderr_truncated_on_runtime_error
- test_execute_extraction_empty_code_returns_422
- test_execute_chart_returns_png_bytes_for_valid_script
- test_execute_chart_returns_422_for_subprocess_import
- test_execute_etl_returns_csv_for_valid_transform
- test_execute_etl_returns_422_when_transform_undefined
- test_auditor_blocks_forbidden_import_even_if_caller_pre_audited (defensa en profundidad: el cliente puede haberse equivocado y el sandbox NO debe ejecutar)
- test_runner_kills_runaway_subprocess_after_timeout (lanza un script con `while True: pass` con timeout=1; verifica que el proceso hijo está muerto tras la excepción — usar `proc.poll() is not None`)
- test_each_execute_starts_fresh_subprocess (ejecuta 2 scripts que escriben a variables globales con el mismo nombre; el segundo no ve el estado del primero)

Mínimo 13 tests RED → GREEN.

## Dockerfile (parte de este prompt; el wiring del compose llega en SBX.4)

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 65534 --no-create-home --shell /usr/sbin/nologin sandboxuser \
    || true  # nobody puede existir ya

WORKDIR /srv/sandbox
COPY pyproject.toml ./
COPY uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY sandbox/ ./sandbox/

USER 65534:65534
EXPOSE 5000
CMD ["uv", "run", "uvicorn", "sandbox.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

## Criterio de done

- 13 tests verdes en `services/script_sandbox/tests/`.
- `docker build -f services/script_sandbox/Dockerfile services/script_sandbox` produce imagen sin warnings.
- El `health` endpoint responde 200.
- El runner mata efectivamente subprocesos colgados (test_runner_kills_runaway lo verifica).
- El auditor del sandbox bloquea código que la API podría haber dejado pasar por error (test_auditor_blocks_forbidden_import_even_if_caller_pre_audited).

## Lo que NO se hace aquí

- No se modifica todavía ningún código de `server/app/`. Los pipelines del API siguen ejecutando in-process. Eso llega en SBX.3.
- No se añade el servicio al `docker-compose.yml`. Eso llega en SBX.4.
- No hay autenticación entre la API y el sandbox: el aislamiento es por red dedicada (sandbox-net). Si en el futuro se necesitase mTLS, se añadirá como capa extra; queda fuera del MVP.
```

---

### Prompt SBX.2 (RED/GREEN) — `SandboxClient`: cliente HTTP en el API

**Modelo sugerido**: **Sonnet** — patrón cliente HTTP estándar con httpx; el contrato ya está fijado en SBX.1; las decisiones abiertas son pocas (retry policy, timeouts, manejo de excepciones).

```markdown
# PROMPT SBX.2 (RED/GREEN) — SandboxClient (httpx)

Objetivo: introducir un cliente HTTP en el API que hable con el microservicio `script-sandbox` definido en SBX.1. Este cliente sustituirá las llamadas `subprocess.run([sys.executable, ...])` que hoy viven dentro de `admin_script_pipeline.py`, `chart_renderer.py` y `etl_service.py`. En SBX.2 SOLO se crea el cliente y sus tests; la sustitución real llega en SBX.3.

Deploy: shared (el cliente vive en `server/app/core/`, lo usan módulos edge — análogo a `StorageService`).

## Estructura

```
server/app/core/sandbox_client.py
server/tests/core/test_sandbox_client.py
```

## Settings

Añadir a `server/app/core/settings.py`:
- `SANDBOX_BASE_URL: str = "http://script-sandbox:5000"` (override `SANDBOX_BASE_URL` en env).
- `SANDBOX_TIMEOUT_SECONDS_DEFAULT: int = 30`.
- `SANDBOX_CONNECT_TIMEOUT_SECONDS: float = 5.0` (timeout de conexión, distinto del timeout de ejecución del script).
- `SANDBOX_MAX_RETRIES_ON_CONNECT_ERROR: int = 1` (no se reintenta en error funcional del script).

## Contrato (Protocol)

```python
from typing import Protocol

class SandboxClient(Protocol):
    async def execute_extraction_script(
        self,
        *,
        code: str,
        file_path: str | None,
        raw_text: str | None,
        options: dict[str, Any],
        timeout_seconds: int | None = None,
    ) -> ExtractionResult:
        """Devuelve ExtractionResult (mismo tipo que pipelines/contracts.py).
        Si el sandbox responde 422 SCRIPT_AUDIT_FAILED → ExtractionResult con warning SCRIPT_SECURITY_VIOLATION.
        Si responde 504 → warning SCRIPT_TIMEOUT.
        Si responde 500 → warning SCRIPT_EXECUTION_ERROR con stderr truncado.
        Si error de red tras los reintentos → SandboxUnavailableError (excepción, NO warning — el caller decide).
        """

    async def execute_chart_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        output_format: Literal["png", "svg"] = "png",
        timeout_seconds: int | None = None,
    ) -> bytes:
        """Devuelve bytes de la imagen. Si el sandbox falla → ChartRenderError (la excepción existente en chart_renderer.py)."""

    async def execute_etl_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        timeout_seconds: int | None = None,
    ) -> str:
        """Devuelve el CSV transformado como string. Si el sandbox falla → ValueError con mensaje del sandbox."""
```

## Implementaciones

- `HttpSandboxClient` — usa `httpx.AsyncClient` con timeouts diferenciados (connect/read), `retry` solo en `httpx.ConnectError` y `httpx.ReadTimeout` a nivel de conexión (NO sobre `ReadTimeout` que ocurra después de empezar a recibir — eso indica timeout funcional del script).
- `LocalSandboxClient` — ejecuta in-process el mismo wrapper que el sandbox HTTP. Útil para tests E2E del API sin levantar el contenedor sandbox. Implementación: importa los wrappers desde una versión local (puede copiar minimamente del código de SBX.1 o invocar a `subprocess.run` como hacían los pipelines antes). Marcar `LocalSandboxClient` con docstring que aclare que es SOLO para tests y desarrollo sin Docker.

`get_sandbox_client()` como FastAPI dependency (factory que decide según `settings.SANDBOX_MODE` con valores `http` (default en producción) y `local` (default en tests si la env var `TESTING=1`)).

## Tests (RED → GREEN)

Usar `respx` (mock de httpx) o `httpx.MockTransport`:

- test_http_client_execute_extraction_serializes_and_parses_response
- test_http_client_execute_extraction_returns_warning_when_sandbox_returns_422_audit
- test_http_client_execute_extraction_returns_warning_when_sandbox_returns_504
- test_http_client_execute_extraction_returns_warning_when_sandbox_returns_500
- test_http_client_execute_extraction_raises_SandboxUnavailableError_on_connect_error
- test_http_client_execute_extraction_retries_once_on_connect_error
- test_http_client_execute_chart_returns_bytes
- test_http_client_execute_chart_raises_ChartRenderError_on_422
- test_http_client_execute_etl_returns_csv_string
- test_local_client_execute_extraction_matches_http_client_behavior (mismo input → mismo `ExtractionResult` que con sandbox HTTP mockeado)
- test_get_sandbox_client_returns_http_in_production
- test_get_sandbox_client_returns_local_when_testing_env_set

Mínimo 12 tests RED → GREEN.

## Criterio de done

- 12 tests verdes en `server/tests/core/test_sandbox_client.py`.
- `httpx` y `respx` añadidos a `server/pyproject.toml` (si no están).
- `SANDBOX_*` settings documentados en `server/app/core/settings.py` y `.env.example`.
- Ningún código de `pipelines/`, `services/charts/` ni `services/transformation/` toca al cliente todavía: ese refactor llega en SBX.3.

## Lo que NO se hace aquí

- No se cablea el cliente en los pipelines existentes (SBX.3).
- No se modifica el `docker-compose.yml` (SBX.4).
```

---

### Prompt SBX.3 (RED/GREEN) — Refactor de pipelines existentes a `SandboxClient`

**Modelo sugerido**: **Sonnet** — refactor mecánico guiado por tests existentes; el contrato del `SandboxClient` está fijado en SBX.2 y el comportamiento esperado en cada caller no cambia.

```markdown
# PROMPT SBX.3 (RED/GREEN) — Cablear SandboxClient en pipelines, charts y ETL

Objetivo: sustituir las 4 ejecuciones de subprocess in-process existentes por llamadas al `SandboxClient` de SBX.2. Ningún test funcional preexistente debe romperse (los warnings y bytes generados siguen siendo equivalentes). El comportamiento observable del API se mantiene; lo que cambia es la frontera donde se ejecuta el código.

Deploy: edge (los 4 ficheros tocados ya estaban en módulos edge).

## Ficheros a modificar

### 1. `server/app/modules/redaccion/pipelines/admin_script_pipeline.py`

- Eliminar la importación de `subprocess`, `sys`, `tempfile`, `os`.
- `extract()` pasa a `async def extract_async()` (la versión síncrona se elimina — el único caller es `scripts_router.test_proposal`, ya async).
- `_execute_in_sandbox()` se reemplaza por:
  ```python
  return await self._client.execute_extraction_script(
      code=code,
      file_path=file_path_or_None,
      raw_text=raw_text,
      options=inp.options,
      timeout_seconds=timeout,
  )
  ```
- El re-audit AST defensivo en `extract_async` SE MANTIENE en la API (defensa en profundidad: el sandbox también lo hace).
- Constructor pasa a recibir `SandboxClient` (inyección obligatoria).
- Borrar las funciones `_build_wrapper` y `_dict_to_result` (ahora las hace el sandbox).
- Sustituir `_AUDITOR = ScriptSecurityAuditor()` por inyección del auditor también (o mantenerlo como singleton de módulo, está bien por ahora).

### 2. `server/app/modules/redaccion/services/charts/chart_renderer.py`

- `render_chart_from_script()` pasa a `async def`.
- Sustituye `subprocess.run` + tempdir por:
  ```python
  csv_bytes = io.StringIO(); df.to_csv(csv_bytes, index=False)
  return await sandbox_client.execute_chart_script(
      code=code,
      dataframe_csv=csv_bytes.getvalue(),
      output_format=output_format,
      timeout_seconds=timeout,
  )
  ```
- Si el cliente lanza `ChartRenderError`, propagar (ya es el mismo tipo de excepción).
- Constructor o función receive `sandbox_client` (Depends o explícito).

### 3. `server/app/modules/redaccion/services/transformation/etl_service.py`

- `_execute_fallback_script()` deja de ser staticmethod, recibe el cliente.
- En lugar de `exec(...)`:
  ```python
  csv_in = df.to_csv(index=False)
  csv_out = await self._sandbox_client.execute_etl_script(
      code=code,
      dataframe_csv=csv_in,
  )
  return pd.read_csv(io.StringIO(csv_out))
  ```
- El comentario `# si emergen requisitos de aislamiento más fuertes, migrar a un subprocess sandbox análogo al ChartRenderer` se elimina (resuelto).
- Cuando se llama a `_execute_fallback_script` desde `run()`, pasa a `await`.

### 4. `server/app/routers/redaccion/scripts_router.py`

- `_SANDBOX = AdminScriptExtractionPipeline()` desaparece.
- En `test_proposal`:
  ```python
  pipeline = AdminScriptExtractionPipeline(client=Depends(get_sandbox_client))
  extraction = await pipeline.extract_async(inp)
  ```
  o equivalente con inyección por endpoint.

### 5. `server/app/modules/redaccion/blocks/handlers.py`

- Los handlers que invocaban a `ChartRenderer` o ETL fallback ahora hacen `await`. Si alguno era síncrono, propagar a async.

### 6. `server/app/modules/redaccion/graph/nodes/data_transformation_node.py`

- Si invoca `etl_service.run()`, ya era async; no cambia. Verificar que sigue cuadrando.

## Tests a adaptar

Tests existentes que mockeaban `subprocess.run` o tocaban el wrapper interno deben mockear ahora el `SandboxClient`:

- `tests/modules/redaccion/test_admin_script_pipeline*.py` — usar `LocalSandboxClient` o mock de `SandboxClient`. Eliminar referencias a `subprocess`, `tempfile`.
- `tests/modules/redaccion/test_chart_renderer*.py` — idem.
- `tests/modules/redaccion/test_etl_service*.py` — idem en los tests del fallback.
- `tests/routers/redaccion/test_scripts_router*.py` — `_SANDBOX` desaparece; mockear `get_sandbox_client` con `app.dependency_overrides`.

Tests nuevos:
- test_admin_script_pipeline_uses_sandbox_client_and_propagates_warnings (verifica que cuando el cliente devuelve un `ExtractionResult` con `SCRIPT_TIMEOUT`, el pipeline lo devuelve idéntico)
- test_admin_script_pipeline_re_audits_before_calling_client (verifica que un script con `eval()` NUNCA llega al cliente)
- test_chart_renderer_uses_sandbox_client_and_returns_bytes
- test_etl_service_fallback_uses_sandbox_client
- test_scripts_router_test_proposal_uses_async_pipeline (smoke: hace `app.dependency_overrides` para inyectar `LocalSandboxClient`)

## Criterio de done

- 0 ocurrencias de `subprocess.run` ni `subprocess.Popen` en `server/app/modules/redaccion/`. (`grep -r "subprocess" server/app/modules/redaccion/` debe estar limpio).
- 0 ocurrencias de `exec(` en `server/app/modules/redaccion/`. (la auditoría busca exactamente esto en otros sitios; aquí debe quedar SOLO en `script_auditor.py` como string a detectar).
- Toda la suite de redacción pasa (425+/425+ tests verdes, sin regresiones respecto al estado pre-SBX).
- Los tests nuevos (5) verdes.

## Lo que NO se hace aquí

- No se levanta el sandbox real: los tests usan `LocalSandboxClient`. El levantado HTTP se prueba manualmente al cerrar SBX.4 con `docker compose up script-sandbox`.
- No se cambia el `docker-compose.yml` (SBX.4).
```

---

### Prompt SBX.4 (RED/GREEN) — Hardening Docker + documentación de seguridad

**Modelo sugerido**: **Sonnet** — configuración Docker + docs; las decisiones técnicas ya están en SBX.1-3, este prompt aterriza el wiring y el modelo de amenazas.

```markdown
# PROMPT SBX.4 (RED/GREEN) — docker-compose con red aislada + docs de seguridad

Objetivo: incorporar el servicio `script-sandbox` a los dos docker-compose (dev y prod) con hardening completo, dejar la red `sandbox-net` aislada de los datos del cliente (postgres, minio) e internet, y documentar el modelo de amenazas en `docs/SANDBOX_SECURITY.md`.

Deploy: edge (afecta a la topología de despliegue cliente).

## Cambios en docker-compose.yml (dev)

Añadir el servicio:
```yaml
  script-sandbox:
    build:
      context: ./services/script_sandbox
      dockerfile: Dockerfile
    container_name: govgenai_script_sandbox
    networks:
      - sandbox-net
    read_only: true
    tmpfs:
      - /tmp/sandbox:size=128M,mode=0700,uid=65534,gid=65534
    cap_drop: ["ALL"]
    security_opt:
      - no-new-privileges:true
    user: "65534:65534"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped
```

Si el servicio `app` (FastAPI principal) ya existe en el compose dev, conectarlo también a `sandbox-net` (manteniendo su red default existente). Si NO existe (el dev hoy sólo levanta dependencias y el API se ejecuta con `uv run uvicorn` en host), añadir un comentario:
```yaml
# El API ejecutándose en host accede al sandbox via http://localhost:5001 si se mapea el puerto;
# alternativamente, ejecutar el API también en contenedor y conectarlo a sandbox-net.
```
Y exponer el puerto 5000 del sandbox como 5001 en host para desarrollo local sin contenedor del API:
```yaml
    ports:
      - "127.0.0.1:5001:5000"   # SOLO en dev; en prod NO se publica
```

Definir la red:
```yaml
networks:
  sandbox-net:
    driver: bridge
    internal: false  # en dev, false para permitir build/pull; ver nota en prod
```

## Cambios en docker-compose.prod.yml (prod)

Añadir el servicio sin `ports:` (no se expone fuera del host):
```yaml
  script-sandbox:
    # ... mismas opciones que en dev ...
    networks:
      - sandbox-net
    # NO ports — solo accesible desde la red sandbox-net
```

Conectar `app` a las dos redes:
```yaml
  app:
    # ... existente ...
    networks:
      - default
      - sandbox-net
    environment:
      # ... existente ...
      SANDBOX_BASE_URL: http://script-sandbox:5000
```

Definir la red como `internal: true` en prod (sin egress fuera del bridge):
```yaml
networks:
  sandbox-net:
    driver: bridge
    internal: true   # PROD: sin egress a internet, solo intercomunicación entre containers conectados
```

## Verificación manual de aislamiento (parte del criterio de done)

Tras `docker compose -f docker-compose.prod.yml up -d script-sandbox app`, ejecutar:
```bash
# 1. El sandbox NO debe poder resolver postgres
docker compose exec script-sandbox python -c "import socket; print(socket.gethostbyname('postgres'))"
# Debe fallar con: socket.gaierror

# 2. El sandbox NO debe poder salir a internet
docker compose exec script-sandbox python -c "import urllib.request; urllib.request.urlopen('https://www.google.com', timeout=3).read()"
# Debe fallar con: URLError / timeout

# 3. El API SÍ debe poder hablar con el sandbox
docker compose exec app curl -s http://script-sandbox:5000/health
# Debe responder: {"status":"healthy"}

# 4. El sandbox NO debe poder hablar al API (no necesita iniciar conexiones salientes)
docker compose exec script-sandbox python -c "import urllib.request; urllib.request.urlopen('http://app:8000/health', timeout=3).read()"
# Debe fallar (network unreachable o connection refused, depende del driver)
```

Estos 4 checks se documentan como pasos manuales en `pruebas_manuales_promptSBX_4.bat` (requiere UI/interacción con Docker, justifica .bat según CLAUDE.md sección "Pruebas manuales").

## `docs/SANDBOX_SECURITY.md`

Crear con secciones:

1. **Modelo de amenazas**
   - Adversario: usuario autenticado de la plataforma (proposer) que intenta exfiltrar datos del cliente, escalar privilegios o denegar servicio.
   - Activos protegidos: base de datos del cliente (postgres), almacenamiento (minio/gcs), red interna del cliente, otros tenants.
   - Asunciones: el atacante puede escribir cualquier código Python; la auditoría AST puede ser bypassable.

2. **Capas de defensa**
   - Capa 1: `ScriptSecurityAuditor` (AST) en la API antes de aceptar la propuesta.
   - Capa 2: Workflow HITL para promoción a plantilla global (9R.5.6).
   - Capa 3: Red `sandbox-net` aislada (sin DNS hacia postgres/minio, sin egress en prod).
   - Capa 4: Contenedor sin privilegios (cap_drop ALL, no-new-privileges, usuario 65534, read_only fs).
   - Capa 5: Re-auditoría AST defensiva dentro del sandbox.
   - Capa 6: Subproceso efímero por petición (sin contaminación entre ejecuciones).
   - Capa 7: Límites de recursos del propio Docker (cpus, memory, tmpfs size).
   - Capa 8: En GCP, gVisor (heredado automáticamente por Cloud Run).

3. **Lo que NO mitiga este diseño**
   - Bugs del kernel del host (mitigado parcialmente por gVisor en GCP).
   - Side-channel attacks entre tenants (fuera de alcance MVP).
   - Inyección de prompts maliciosos al LLM que generan código bypass — mitigado por capas 1, 2, 5.

4. **Cómo auditar el aislamiento**
   - Los 4 checks de la sección "Verificación manual" anterior.
   - Comandos para inspeccionar capacidades del contenedor: `docker inspect govgenai_script_sandbox --format '{{json .HostConfig.CapDrop}}'`.

5. **Migración futura a gVisor explícito (on-premise)**
   - Pasos para configurar `runtime: runsc` si el cliente despliega sobre containerd + gVisor.
   - Queda fuera del MVP; documentado por si infosec del cliente lo requiere.

6. **Diferencias dev vs. prod**
   - Dev: `sandbox-net` no es internal; el sandbox expone 5001 en host para `uv run` local.
   - Prod: `sandbox-net` internal=true, sin ports expuestos, sandbox solo accesible desde `app`.

## Tests (RED → GREEN)

Tests automáticos:
- test_compose_dev_defines_sandbox_service (parsea YAML y verifica claves obligatorias: cap_drop, read_only, security_opt, user, network)
- test_compose_prod_sandbox_has_no_ports (sandbox sin sección `ports`)
- test_compose_prod_sandbox_net_is_internal (network internal=true)
- test_compose_prod_app_connected_to_sandbox_net
- test_sandbox_dockerfile_runs_as_non_root_user (parsea Dockerfile, verifica `USER 65534`)

5 tests verdes en `tests/infra/test_compose_sandbox.py` (nuevo).

Verificación manual (vía `.bat`):
- `pruebas_manuales_promptSBX_4.bat` cubre los 4 checks de aislamiento de red, plus el smoke E2E de `/api/v1/redaccion/scripts/{id}/test` apuntando al sandbox real.

## Criterio de done

- 5 tests automáticos verdes.
- Los 4 checks manuales de aislamiento pasan (documentados en el .bat con texto explícito de qué esperar).
- `docs/SANDBOX_SECURITY.md` existe y cubre las 6 secciones.
- `docker compose -f docker-compose.prod.yml up -d` levanta los 4 servicios (postgres, app, sandbox, minio) y el endpoint `/api/v1/redaccion/scripts/{id}/test` ejecuta scripts en el sandbox (verificable en logs).
- `.env.example` actualizado con `SANDBOX_BASE_URL=http://script-sandbox:5000` y `SANDBOX_TIMEOUT_SECONDS_DEFAULT=30`.

## Pruebas manuales — Prompt SBX.4

### Antes de empezar
1. Abre Docker Desktop.
2. En una terminal: `docker compose -f docker-compose.prod.yml build script-sandbox app`.
3. Levanta: `docker compose -f docker-compose.prod.yml up -d`.

### Ejecuta el archivo
- Doble clic en `pruebas_manuales_promptSBX_4.bat` (raíz del proyecto).

### Qué debes ver
- 4 checks de aislamiento (los 3 que deben fallar fallan; el que debe pasar pasa).
- 1 smoke E2E: crear un proposal con `POST /api/v1/redaccion/scripts/propose`, ejecutar `/test`, ver en `docker logs script-sandbox` la entrada de ejecución.

### Para terminar
- `docker compose -f docker-compose.prod.yml down`.
```

---

### Continuación tras el bloque SBX

Con SBX cerrado, el siguiente bloque del orden de ejecución es **Bloque 9Q** (Calidad de Contenido Web Ingestado). Tras 9Q viene **Fase 11** (Autoinstalación y Distribución), que reescribirá `docker-compose.prod.yml` para distribución pública. Fase 11.2 debe preservar el servicio `script-sandbox` y su red aislada — añadirlo al template público con comentarios claros.

---
