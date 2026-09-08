# Bloque DEP — Las dependencias vulnerables, y la puerta que las vigile

> Nacido el 2026-09-08 de la **primera ejecución** del job `supply-chain` de `ci.yml`
> (run `34214582147`). El job se añadió para preparar la auditoría de seguridad independiente
> que la OIATI pide antes de la explotación, y su primera medida dice que hay trabajo.

**Siete prompts.** El orden no es arbitrario: DEP.1 quita masa antes de subir nada, porque
subir una versión de algo que la aplicación no necesita es pagar dos veces.

---

## Lo medido, que es de donde sale todo lo demás

Sobre el lock del 2026-09-08, con `pip-audit` y `npm audit`:

| Árbol | Paquetes | Con aviso |
|---|---:|---:|
| `server` | 241 | **32** |
| `mcp_server` | 36 | **4** |
| `frontend` (producción) | — | **21**, de los cuales **13 altos** |

**Casi todos son transitivos**, y eso cambia el arreglo: no se edita `pyproject.toml`, se hace
`uv lock --upgrade-package <nombre>` y se comprueba que el padre lo admite. Donde el padre pone
techo, hay que subir al padre.

**Y el mapa de padres dice algo que no se veía:**

```
authlib          <- browser-use                     (7 avisos)
mcp              <- browser-use                     (3 avisos)
python-multipart <- mcp                             (6 avisos)  ← y la aplicación LO NECESITA
datasets         <- automatia-server, ragas         (1 aviso)
diskcache        <- ragas                           (1 aviso, SIN corrección)
langchain        <- ragas                           (1 aviso)
ragas            <- automatia-server                (1 aviso, SIN corrección)
pypdf            <- browser-use, camelot-py         (30 avisos)
lxml             <- python-docx, python3-saml, xmlsec
starlette        <- fastapi, mcp, sse-starlette
pyjwt            <- automatia-server, mcp
```

`browser-use` y `ragas` **ya están escritos como opcionales en el código** —los dos importan
dentro de un `try/except ImportError` y degradan a propósito: `agent_service.py` deja `Agent =
None` y `rag_metrics.py` cae a una métrica léxica— **y están declarados como obligatorios en el
manifiesto**. Entre los dos arrastran unos 19 de los 32 avisos del servidor, incluidos **los dos
únicos que no tienen versión corregida**.

**Corrección a lo que se dijo el mismo día**: `authlib` se citó como «la pieza de SAML/OIDC». No
lo es. El SAML es `python3-saml` + `xmlsec` + `lxml`; `authlib` entra por `browser-use` y se va
con él.

---

### Prompt DEP.1 (RED/GREEN) — Declarar lo que se usa y soltar lo que no

**Modelo sugerido**: Opus — hay una dependencia que hoy está por accidente y quitarla mal deja
la subida de ficheros rota en producción sin fallar al arrancar.

```
# PROMPT DEP.1 (RED/GREEN) — python-multipart declarado; browser-use y ragas a extras
# Deploy: edge y cloud (manifiesto y lock; sin migracion)

## Por que
Dos cosas que la medicion del 2026-09-08 destapo, y la primera es un defecto latente:

1. `python-multipart` NO esta declarado en ningun sitio. Llega por
   `browser-use -> mcp -> python-multipart`. Y la aplicacion lo necesita: `UploadFile` y
   `Form(` aparecen 22 veces en 7 ficheros (ingestion, uploads, workspaces, scripts,
   llm_drafts, hub_ingestion, hub_themes). FastAPI no falla al importar por esto: falla al
   ATENDER la peticion. O sea que el sintoma seria un 500 en la subida de un PDF en
   produccion, y no un arranque en rojo.

2. `browser-use` y `ragas` estan declarados como obligatorios y escritos como opcionales.
   `agent_service.py` los envuelve en try/except y deja `Agent = None`; `rag_metrics.py`
   pone `_RAGAS_AVAILABLE = False` y cae a solapamiento lexico, y su propia docstring dice
   que la evaluacion es «a mano o de noche, jamas bloqueando un PR». `datasets` esta
   declarado directo y solo lo usa `rag_metrics`.

Entre los dos arrastran authlib (7), mcp (3), python-multipart (6), datasets (1), diskcache
(1) , langchain (1) y ragas (1). Diskcache y ragas son DOS DE LOS TRES avisos sin version
corregida que hay en todo el arbol: no se pueden arreglar subiendo, solo dejando de traerlos.

## Que hacer
1. RED primero (ver abajo).
2. `python-multipart` pasa a dependencia declarada de `server/pyproject.toml`, con la version
   ya corregida. Es lo unico que ENTRA en este prompt.
3. `browser-use`, `ragas` y `datasets` salen del conjunto por defecto a extras:
   `[project.optional-dependencies]`, `agente-navegador` y `evaluacion`. No se borra codigo:
   los dos try/except ya existen y son la razon de que esto se pueda hacer.
4. `uv lock` en el mismo commit, y comprobar con `uv lock --check` (no con `uv sync`, que
   relockea y por eso siempre pasa).
5. Medir otra vez con el mismo comando del job y escribir el antes/despues en el informe.

## RED
- Un test que falle si algun modulo que usa `UploadFile`/`Form` depende de que otro paquete
  traiga `python-multipart`: se comprueba que esta declarado en el manifiesto, no que este
  instalado. Instalado esta hoy, y ese es justo el problema.
- Un test que importe `create_app()` con `browser_use` y `ragas` ausentes del `sys.modules`
  (monkeypatch del import) y compruebe que la aplicacion se construye y que
  `_RAGAS_AVAILABLE` es False sin reventar.
- Un test que compruebe que `Dockerfile` y `docker-compose.vm.yml` NO instalan los extras
  nuevos: si el despliegue los instala igualmente, el ejercicio no ha servido de nada.

## Criterio de done
- [ ] `python-multipart` declarado, con la subida de un fichero verificada de punta a punta
- [ ] Los tres paquetes fuera del conjunto por defecto, con `uv lock --check` limpio
- [ ] `pip-audit` medido de nuevo: se dice cuantos avisos caen y cuales quedan
- [ ] La evaluacion RAGAS sigue pudiendo ejecutarse con `--extra evaluacion`, y se documenta
      donde (`docs/` o el README del modulo de evaluacion)
```

---

### Prompt DEP.2 (RED/GREEN) — Las subidas que no cruzan un mayor

**Modelo sugerido**: Sonnet — es mecánico y lo que decide es la suite.

```
# PROMPT DEP.2 (RED/GREEN) — Subir lo que sube sin romper contrato
# Deploy: edge y cloud (solo lock)

## Por que
Despues de DEP.1 quedan los avisos de paquetes que se arreglan dentro de su version mayor.
Se hacen JUNTOS y en un solo commit porque separarlos en catorce commits no compra ninguna
reversibilidad util: si la suite se pone roja, lo que se quiere saber es cual, y eso lo dice
la suite, no el historial.

Candidatos con correccion dentro del mayor (verificar la lista contra la medicion del dia,
que habra cambiado):
  aiohttp 3.13.3 -> 3.14.3      urllib3 2.6.3 -> 2.7.0       requests 2.32.5 -> 2.33.0
  idna 3.11 -> 3.15             click 8.3.1 -> 8.3.3         pygments 2.19.2 -> 2.20.0
  mako 1.3.11 -> 1.3.12         orjson 3.11.5 -> 3.11.6      soupsieve 2.8.1 -> 2.8.4
  python-dotenv 1.2.1 -> 1.2.2  pyasn1 0.6.2 -> 0.6.4        httplib2 0.31.1 -> 0.32.0
  pillow 12.1.0 -> 12.3.0       lxml 6.0.2 -> 6.1.0          pyjwt 2.10.1 -> 2.13.0
  cryptography 46.0.3 -> 46.0.7 setuptools 81.0.0 -> 83.0.0

## Que hacer
1. `uv lock --upgrade-package <nombre>` uno a uno, NO `uv lock --upgrade` entero: lo segundo
   mueve tambien lo que no tiene ningun aviso y convierte el diff en algo que nadie revisa.
2. Suite completa desde Git Bash. `lxml` y `cryptography` tocan el camino de SAML
   (`python3-saml`, `xmlsec`): sus tests son los que hay que mirar primero si algo cae.
3. `pyjwt` toca la firma de los tokens de sesion: `tests/api/test_auth_login.py` y el gate de
   control de acceso son la prueba de fuego.
4. Lo que no pueda subir por un techo de su padre se ANOTA con el padre que lo impide, y pasa
   al prompt que corresponda. No se fuerza con `--upgrade-package` a una version que el
   resolutor rechace.

## Criterio de done
- [ ] Suite completa en verde, medida y con la cifra dicha
- [ ] `uv lock --check` limpio
- [ ] Lista escrita de lo que NO subio y por que padre
```

---

### Prompt DEP.3 (RED/GREEN) — El camino HTTP: starlette y fastapi

**Modelo sugerido**: Opus — es un cambio de mayor en el núcleo del servidor.

```
# PROMPT DEP.3 (RED/GREEN) — starlette 0.50 -> 1.x
# Deploy: edge y cloud (solo lock, salvo que fastapi obligue a tocar codigo)

## Por que
`starlette` 0.50.0 tiene siete avisos y la correccion mas alta pide 1.3.1. Es un cambio de
version MAYOR y `starlette` no se sube solo: lo trae `fastapi` (declarado `>=0.111.0`),
`sse-starlette` y `mcp`. Si el techo lo pone `fastapi`, hay que subir `fastapi` y entonces
esto deja de ser una subida de lock.

Va en prompt propio porque es lo que puede romper el contrato OpenAPI, y ese contrato es la
unica fuente de verdad del frontend: si cambia, `npm run generate:api` produce otro cliente y
el job `contract` de CI se pone rojo. Es exactamente el aviso que se quiere, y por eso este
prompt no puede ir mezclado con quince subidas menores.

## Que hacer
1. Averiguar quien pone el techo antes de tocar nada: `uv tree --package starlette`.
2. Subir `starlette`, y `fastapi` si hace falta, con su `uv lock`.
3. Regenerar el contrato (`uv run python export_openapi.py`) y DIFERENCIARLO contra el
   anterior. Un contrato que cambia sin que se haya tocado ningun router es el hallazgo.
4. Si el contrato cambia: regenerar el cliente con Orval y pasar `tsc -p tsconfig.app.json`,
   que es el que CI usa y el que incluye los tests.

## Criterio de done
- [ ] Suite completa, job `contract` conceptualmente reproducido en local
- [ ] Diff del contrato OpenAPI revisado y explicado, o vacio
- [ ] Verificacion en navegador del panel y del widget: middlewares y streaming son lo que
      un cambio de mayor de starlette rompe sin que ningun test unitario lo note
```

---

### Prompt DEP.4 (RED/GREEN) — pypdf y el camino del PDF

**Modelo sugerido**: Opus — treinta avisos, versión mayor, y toca la extracción del corpus.

```
# PROMPT DEP.4 (RED/GREEN) — pypdf 5.9 -> 6.x
# Deploy: edge (extraccion de documentos)

## Por que
`pypdf` acumula **30 avisos**, mas que ningun otro paquete del arbol, y la correccion mas alta
pide 6.16.1 desde 5.9.0. Importa mas que el numero: pypdf parsea PDF que vienen de fuera, que
es la superficie que un atacante elige. Despues de DEP.1 su unico padre es `camelot-py`.

## Que hacer
1. Comprobar si `camelot-py` admite pypdf 6.x. Si pone techo, la decision es de criterio y
   sube al usuario: subir camelot, sustituirlo, o aceptar el aviso con fecha.
2. La extraccion tiene contrato (`docs/CONTRATO_MD_CORPUS.md`) y el corpus real esta a mano.
   La comprobacion que vale no es «la suite pasa»: es que la extraccion produzca EL MISMO
   texto sobre una muestra de PDF reales antes y despues. Un cambio de mayor en un parser
   cambia el texto en silencio, y eso reindexaria el corpus sin que nadie lo pidiera.
3. Medir la muestra y decir el tamano. Si el texto cambia, decir en cuantos documentos y en
   que.

## Criterio de done
- [ ] Comparacion antes/despues sobre PDF reales, con el numero de documentos dicho
- [ ] Suite de `redaccion` y de ingesta en verde
- [ ] Si algo cambia en el texto extraido, esta escrito que cambia y por que es aceptable
```

---

### Prompt DEP.5 (RED/GREEN) — El servidor MCP, que tiene su propio lock

**Modelo sugerido**: Sonnet — cuatro paquetes y una suite pequeña.

```
# PROMPT DEP.5 (RED/GREEN) — Los cuatro avisos de mcp_server
# Deploy: shared (el servidor MCP)

## Por que
`mcp_server` tiene lock propio y hasta el arreglo del 2026-09-08 NO SE AUDITABA: los dos
`pip-audit` iban encadenados y el shell abortaba el paso al primero. Su primera medida:
36 paquetes, 4 con aviso.

  cryptography 48.0.1 -> 50.0.0 (5 avisos)   mcp 1.27.2 -> 1.28.1
  pydantic-settings 2.14.1 -> 2.14.2         starlette 1.3.0 -> 1.3.1

Dato util: este arbol va MAS ADELANTADO que el del servidor (cryptography 48 contra 46,
starlette 1.3 contra 0.50). El que esta atrasado es `server`, y conviene no leerlo al reves.

## Que hacer
1. `uv lock --upgrade-package` en `mcp_server/`, los cuatro.
2. Suite de `mcp_server` (`uv run --directory mcp_server --extra dev pytest tests`).
3. El MCP remoto se comprueba contra el servidor desplegado, y REG.4 dejo el guion: dos
   clientes concurrentes, porque con uno la implementacion mala pasa.

## Criterio de done
- [ ] Suite de mcp_server en verde
- [ ] `uv lock --check` limpio en ese proyecto
- [ ] Handshake del MCP remoto verificado con dos clientes a la vez
```

---

### Prompt DEP.6 (RED/GREEN) — El frontend, y si «producción» quiere decir producción

**Modelo sugerido**: Sonnet — salvo que la primera comprobación destape lo que se sospecha.

```
# PROMPT DEP.6 (RED/GREEN) — 21 avisos, 13 altos
# Deploy: cloud y edge (el paquete que sirve el navegador)

## Por que
`npm audit --omit=dev` da 21 avisos en el arbol de PRODUCCION, 13 de severidad alta, y todos
con arreglo disponible. Ninguno es dependencia directa.

Pero la lista tiene algo raro y hay que mirarlo antes de arreglar nada: `esbuild`,
`@babel/core` y `browserslist` son herramientas de construccion, y con `--omit=dev` no
deberian aparecer. O algo de `dependencies` deberia estar en `devDependencies`, o hay un
paquete de produccion que se los trae. Lo primero cambia el numero de verdad; lo segundo, no.

El que mas importa por lo que hace es `dompurify`: es el saneador de HTML, y donde se pinta
la respuesta del modelo.

## Que hacer
1. Averiguar por que aparecen las herramientas de construccion (`npm ls <paquete>`), y si es
   una mala clasificacion, corregirla. Esa correccion va PRIMERO y sola.
2. `npm audit fix` sin `--force`. Lo que solo se arregle con `--force` se anota y se decide
   uno a uno: `--force` sube mayores en silencio.
3. `npm ci`, `tsc -p tsconfig.app.json --noEmit`, `npm test` y `npm run test:a11y`. Los
   cuatro, que son los que CI ejecuta.
4. Verificacion en navegador del chat: `dompurify` es el sitio donde una regresion no la ve
   ningun test unitario y si la ve una respuesta con formato.

## Criterio de done
- [ ] El reparto dependencies/devDependencies dice la verdad, o esta explicado por que
- [ ] Los 13 altos en cero, o los que queden con su razon escrita
- [ ] Las cuatro comprobaciones de CI en verde y el chat verificado en navegador
```

---

### Prompt DEP.7 (RED/GREEN) — Encender la puerta

**Modelo sugerido**: Opus — es una decisión de política, y mal puesta se desactiva sola.

```
# PROMPT DEP.7 (RED/GREEN) — De informar a bloquear
# Deploy: no aplica (integracion continua)

## Por que
El job `supply-chain` nacio informando y no bloqueando, y con una razon escrita: sobre 408
dependencias transitivas apareceria un aviso sin version corregida, y un guardarrail rojo por
algo que quien lo lee no puede arreglar acaba desactivado. El plan que se escribio entonces
era «primero medir, y con la medida encima de la mesa, fijar el umbral». DEP.1 a DEP.6 son esa
medida. Este prompt cierra el ciclo, y sin el, el bloque deja el arbol limpio hoy y sucio
dentro de tres meses.

## Que hacer
1. Un fichero de avisos aceptados —no una lista de exclusiones sin mas— donde cada entrada
   lleve: el identificador, POR QUE se acepta, quien lo acepto y una FECHA DE CADUCIDAD.
   Un aviso aceptado sin fecha es un aviso olvidado.
2. Un test que falle cuando una entrada de ese fichero caduque. Es la pieza que hace que la
   lista no crezca sola: sin ella, aceptar es gratis y para siempre.
3. `pip-audit` y `npm audit` pasan a BLOQUEAR por encima del umbral que se acuerde. Propuesta
   para discutir, no para aplicar sin decidir: bloquear en `high` y `critical`, informar por
   debajo.
4. Quitar `continue-on-error` solo de lo que pase a bloquear, y ACTUALIZAR
   `test_cadena_de_suministro_mira_de_verdad.py`, que hoy afirma lo contrario: su test
   `test_los_dos_proyectos_se_auditan_aunque_el_primero_encuentre_algo` fija el diseno
   antiguo y tiene que decir el nuevo.

## Criterio de done
- [ ] Fichero de avisos aceptados con motivo, responsable y caducidad
- [ ] Test que se pone rojo cuando una aceptacion caduca, con su caso negativo comprobado
- [ ] El guardarrail del job actualizado, y sus mutaciones vueltas a comprobar
- [ ] Una ejecucion real en `desarrollo` que demuestre que bloquea cuando debe
```

---

## Lo que este bloque NO hace

- **No toca la rotación de `JWT_SECRET_KEY`.** Es una operación de despliegue, no de código, y
  no depende de ninguno de estos prompts.
- **No persigue los avisos sin corrección publicada.** Después de DEP.1 debería quedar uno solo
  (`pyjwt` PYSEC-2025-183); su sitio es el fichero de aceptados de DEP.7, con fecha.
- **No sube dependencias que no tienen ningún aviso.** `uv lock --upgrade` entero mueve el
  árbol completo y convierte el diff en algo que nadie revisa.
