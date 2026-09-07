## Bloque REPO — Sustituir el repositorio de GitHub por uno sin objetos huérfanos

> **Planificado el 2026-08-21.** No es un bloque de código: es una operación sobre GitHub que ejecuta
> el usuario. Está aquí, versionado, porque el guion detallado vivía en `_local/`, que es una carpeta
> ignorada y de usar y tirar — y esto no puede perderse con ella.
>
> **Va después del Bloque NIC, a propósito.** No tiene sentido montar el repositorio definitivo y acto
> seguido meterle la retirada de 500 ficheros de legacy.

### Prompt REPO.1 (manual del usuario) — El cambio de repositorio

**Modelo sugerido**: — (no es un prompt de agente)

```
# PROMPT REPO.1 — Lo hace el usuario
# Deploy: n/a

## Por que
El 2026-08-21 se reescribio el historial para sacar `logs/` —45 volcados `llm_anonymized_input_*.txt`
con datos de usuarios reales— y se forzo el push. Los commits viejos quedaron **inalcanzables pero no
borrados**: GitHub los sirve por URL de SHA hasta que recoge basura, sin plazo garantizado.

Hacerlo **antes de que exista el primer fork**: un fork conserva los objetos del original. Y
tambien antes de TRANSFERIR: una transferencia se lleva el almacen de objetos completo.

**Comprobado el 2026-09-07: la exposicion sigue viva, 17 dias despues de la reescritura.** El
commit huerfano `dc4904e0c763` todavia sirve `logs/` con 46 ficheros por la API. GitHub no ha
recogido basura y no promete cuando.

## A donde va el nuevo (decision del 2026-09-07)
El orden acordado con el usuario es **limpiar, transferir y abrir despues**. Eso abre una variante
mejor que la de los pasos de abajo, si hay permiso para crear repositorios en la organizacion:

  A) Crear el limpio en `ModestoFabra` (los pasos tal como estan) y transferirlo despues.
  B) Crear el limpio DIRECTAMENTE en `universitatjaumei` y no transferir nada.

**B es estrictamente mejor y es la recomendada**: el repositorio de la organizacion **nace
limpio**, asi que los 46 volcados no entran nunca en el almacen de objetos de la universidad, ni
un minuto; y se ahorra un paso entero con su ventana de riesgo.

Su unico coste es que el nombre pasa a `universitatjaumei/gov-gen-ai-platform`, y **la
autenticacion del despliegue esta anclada al nombre en DOS sitios**, los dos en GCP:
  - condicion del proveedor:  assertion.repository=='ModestoFabra/gov-gen-ai-platform'
  - enlace de la cuenta:      principalSet://.../attribute.repository/ModestoFabra/gov-gen-ai-platform
Con A el nombre acaba siendo el mismo y WIF sobrevive solo; con B hay que tocarlos, y se hace
**aditivo primero, sin ventana de rotura**: ampliar la condicion a los dos nombres con `||`,
anadir el segundo principalSet, subir, verificar un despliegue real, y solo entonces retirar el
viejo. No hay que tocar codigo: `deploy.yml` lee el proveedor de una variable y el nombre del
recurso no cambia.

## Lo que se pierde (inventariado el 2026-08-21, REVISADO el 2026-09-07)
Issues, PRs, releases, tags, webhooks: 0 de todo. Secretos de Actions: ninguno, el CI no usa.
Proteccion de rama: no hay. Forks, estrellas, watchers: 0.

**Y las 12 VARIABLES de Actions, que el inventario original no podia ver.** Se escribio el
2026-08-21 y el despliegue no empezo a funcionar hasta el 2026-08-31: hoy `deploy.yml` lee
`vars.GCP_WIF_PROVIDER`, `vars.GCP_DEPLOY_SA`, `vars.GOVGENAI_HOST` y nueve mas. Un repositorio
nuevo nace VACIO de variables, y con eso vacio la autenticacion falla de un modo que **no se
parece a su causa** (el proveedor llega como cadena vacia). Recrearlas es un paso, no un detalle:
  gh variable list                      # en el viejo, ANTES de borrarlo: apuntar los 12 pares
  gh variable set NOMBRE --body VALOR   # en el nuevo, uno por uno
Ninguna es secreta —son identificadores y rutas, lo dice el propio `deploy.yml`— asi que se
pueden leer y copiar sin ceremonia.

**Solo se pierden de verdad la fecha de creacion (2026-04-22) y el historial de ejecuciones de
Actions.**

## Los pasos
1. Copia de seguridad fuera del portatil: `git bundle create ../respaldo.bundle --all`, y
   `git bundle verify` ejecutado desde dentro del repositorio.
2. Renombrar el viejo, que es instantaneo y no destructivo:
   gh repo rename gov-gen-ai-platform-anterior --repo ModestoFabra/gov-gen-ai-platform
3. Crear el nuevo ya con el nombre bueno y VACIO (sin README, sin .gitignore, sin licencia: si
   GitHub crea un commit inicial, el push choca):
   gh repo create ModestoFabra/gov-gen-ai-platform --private
4. Subir **LAS DOS RAMAS**, fijando la URL para no depender de la redireccion del renombrado:
   git remote set-url origin git@github.com:ModestoFabra/gov-gen-ai-platform.git
   git push -u origin main
   git push -u origin desarrollo
   La rama `desarrollo` nacio el 2026-09-02, despues de escribirse este plan, y es DONDE VIVE EL
   TRABAJO: subir solo `main` dejaria fuera todo lo no desplegado. Comprobar que estan las dos:
   gh api repos/.../branches --jq '.[].name'
5. Verificar CON EL ANTERIOR TODAVIA EN PIE. Si algo falla, se para y no se ha perdido nada:
   - las dos puntas coinciden: git rev-parse main / desarrollo contra
     gh api repos/.../commits/{main,desarrollo} --jq .sha
     (si coinciden esta todo: git no puede subir un commit sin sus ancestros);
   - gh api repos/.../commits/dc4904e0c763  da 404  <- EL QUE IMPORTA, ver abajo;
   - gh api repos/.../contents/logs  da 404;
   - las 12 variables estan: gh variable list | wc -l
   - CI en verde: un commit firmado (git commit -s) y los dos workflows pasan.

   Sobre que SHA comprobar: la version anterior de este paso miraba
   `82f475b6c6d382e1586e7cc0319a9a0917fb3475`, y **ese no demuestra nada**. Medido el 2026-09-07
   caminando la cadena de huerfanos en GitHub: el arbol de `82f475b` NO tiene `logs/` —es la punta
   posterior al borrado y anterior a la reescritura—, asi que su `contents/logs` da 404 aunque la
   exposicion siga viva. El primer ancestro que SI sirve los volcados es **`dc4904e0c763`**
   (2026-08-21 06:20:35), con **46 ficheros**, y por debajo `152c3d2f3f2e` con otros 46. Comprobar
   `82f475b` era medir lo que no era, que es el fallo de instrumento habitual de esta casa.
6. Borrar el anterior:
   gh auth refresh -h github.com -s delete_repo   (el token no trae ese permiso por defecto)
   gh repo delete ModestoFabra/gov-gen-ai-platform-anterior --yes

## Despues
- **Abrir es el ULTIMO paso**, y va despues de transferir: limpiar -> transferir -> abrir.
  Settings -> Danger Zone -> Change visibility -> Public. Y ojo: una vez en la organizacion, esa
  decision **deja de ser solo del mantenedor**.
- Cualquier otro clon en otra maquina conserva los volcados. No hacer pull: borrarlo y clonar.
- El nombre corto NO cambia: sigue siendo `gov-gen-ai-platform`. Lo que cambia con la variante B
  es el dueno, y con el los dos anclajes de WIF.
- **Poner proteccion de rama en `main`**, que hoy no tiene ninguna siendo el disparador del
  despliegue. Es el momento: el repositorio se recrea de cero.
```

### Prompt REPO.2 (manual del usuario) — Los otros dos repositorios

**Modelo sugerido**: — (no es un prompt de agente)

```
# PROMPT REPO.2 — Lo hace el usuario
# Deploy: n/a

ModestoFabra/cgm-remote-monitor — fork publico de nightscout/cgm-remote-monitor. Comprobado el
2026-08-21: 1 commit por delante (un merge traido del original) y 902 por detras, SIN TRABAJO PROPIO,
sin actividad desde 2020. Borrar sin mas; no afecta al proyecto original.

ModestoFabra/GenGov — privado, es el predecesor de este repositorio y contiene 44
llm_anonymized_input_*.txt, la misma exposicion. El archivo local ya existe y no hay que clonar nada:
la carpeta Documents\AutomatIA ES un clon suyo, al dia (HEAD e5be141 = la punta en GitHub), 305
commits, una rama, sin tags. Borrarlo de GitHub no pierde historia.

Antes de borrarlo, limpiar los volcados en ese clon —para poder reclonar si algo sale mal—:
rm -f logs/*.txt  y  git filter-repo --path logs --invert-paths --force
Y guardar un bundle en un disco externo si la historia de enero-marzo importa: sera la unica copia.
```


### Prompt REPO.3 (RED/GREEN) — El triaje editorial de `docs/`

**Modelo sugerido**: **Opus** — decide qué se publica y qué no, y algunas instantáneas llevan
asuntos abiertos dentro.

```
# PROMPT REPO.3 (RED/GREEN) — Que instantaneas viajan al repositorio publico
# Deploy: n/a (documentacion)

## Por que
El 2026-08-22, al revisar `docs/` para abrir el repositorio, salieron tres clases de documento y
sólo una se resolvio entonces:

- **La isla AutomatIA** (17 ficheros que describian otro producto) → a cuarentena ese mismo dia.
- **Premisa caducada** (los que razonaban sobre Cloud Run) → prompt D.0.doc, antes de desplegar.
- **Ciertos pero historicos** → esto. Se dejo para aqui a proposito: no estan mal, son
  instantaneas y razonamiento, y decidir si un repositorio publico los quiere es una eleccion
  **editorial** que se toma mejor mirando al publico que va a leerlos.

Y hay un motivo mas para no haberlo hecho antes: algunos llevan **asuntos abiertos** dentro
—`VALORACION_PROYECTO.md` tenia hallazgos con decisiones marcadas como pendientes—, asi que
esto es triar, no borrar a bulto. Borrarlos sin leerlos pierde trabajo por hacer.

## Que hacer
1. Leer y clasificar, uno a uno: `VALORACION_PROYECTO.md`, `AUDITORIA_PRE_DEPLOY.md`,
   `PRUEBAS_PENDIENTES.md`, `CAMBIOS_ARQUITECTURA.md`, `CAMBIOS_PLANIFICACION.md`, los cuatro
   `COMPARATIVA_*.md`, `PLAN_CHATBOTS_E_INGESTA_LOCAL.md` y
   `DECISION_OPENWEBUI_CARCASA_CHAT.md` (una decision **descartada**, que puede seguir siendo
   util precisamente por eso).
2. **Antes de tirar nada, extraer lo que siga abierto** y llevarlo a donde vive el trabajo
   pendiente: `planificacion/PROJECT_STATE.md` o un bloque. Un hallazgo sin resolver no se
   archiva, se traslada.
3. Decidir para cada uno: se queda como instantanea fechada, se resume en el historial y se
   retira, o se va. **Razonar cada retirada en el commit**, no borrar en lote.
4. Unificar `MCP_SERVER.md` y `mcp.md`, que se solapan; el indice ya lo señala.
5. Dejar `docs/README.md` coherente con lo que quede.

## Tests (RED primero)
- RED: `docs/README.md` no enlaza ningun fichero que no exista (indice sin enlaces rotos).
- RED: ningun documento activo referencia uno retirado.

## Criterio de done
- [ ] Los doce clasificados, con la razon de cada retirada en el commit
- [ ] Cero asuntos abiertos perdidos: los que habia, trasladados y citados
- [ ] `MCP_SERVER.md` y `mcp.md` unificados
- [ ] `docs/README.md` sin enlaces rotos
```

---
