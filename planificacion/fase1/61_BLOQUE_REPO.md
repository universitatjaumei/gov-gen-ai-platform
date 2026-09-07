## Bloque REPO — Sustituir el repositorio de GitHub por uno sin objetos huérfanos

> **Estado (2026-09-07): 4 prompts, uno hecho.** REPO.3 ✅ (el triaje de `docs/`). Pendientes:
> **REPO.1** (crear el limpio en `universitatjaumei` — variante B elegida), **REPO.2** (los otros
> dos repositorios) y **REPO.4** (retirar los anclajes al dueño anterior, nuevo con la variante B).
> El orden es **REPO.1 → REPO.4 → REPO.2**, y REPO.1 y REPO.2 los ejecuta el usuario.

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

## A donde va el nuevo — ELEGIDA LA VARIANTE B (decision del usuario, 2026-09-07)
El orden acordado es **limpiar, mover y abrir despues**. Habia dos formas:

  A) Crear el limpio en `ModestoFabra` y TRANSFERIRLO despues.
  B) Crear el limpio DIRECTAMENTE en `universitatjaumei`. **ELEGIDA.**

**Y conviene decirlo con precision porque el nombre enga_a: con B NO HAY TRANSFERENCIA.** No se
usa la operacion «Transfer» de GitHub en ningun momento. Se crea un repositorio nuevo en la
organizacion y se le empuja el historial limpio; el viejo se borra al final. Eso es exactamente lo
que hace que nazca limpio: **una transferencia se lleva el almacen de objetos completo**, asi que
con A los 46 volcados entrarian en la organizacion de la universidad y solo desaparecerian al
borrar el original. Con B no entran nunca, ni un minuto.

Se ahorra ademas un paso entero con su ventana de riesgo.

**Requisito de B**: permiso para crear repositorios en `universitatjaumei`. Si no lo hay, se cae a
A, que sigue documentada en el historial de git de este fichero.

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

## Los pasos (variante B: el nuevo nace en la organizacion)
0. PRERREQUISITOS que no se averiguan desde fuera, y que van ANTES de tocar nada. Son las tres
   preguntas a UADTI: rol con el que se incorpora el mantenedor y **quien aprueba la creacion**,
   **permisos base para miembros** de la organizacion (decide quien ve el repositorio mientras
   siga privado), y **plan** de la organizacion (si no es Enterprise, los rulesets sobre repos
   privados pueden no estar disponibles).
0.bis. **`.git/info/exclude` NO VIAJA, y hoy protege tres ficheros que no deben publicarse.**
   Descubierto el 2026-09-07, al ponerse roja en CI una comprobacion que en local pasaba. Esa
   lista es **por clon**: no esta versionada, no va en el bundle y **el clon nuevo no la tendra**.
   Hoy contiene:
     docs/convocatoria_tecnologo_A2_TecLab.md
     docs/EU_GOVERNANCE_CONCEPT_NOTE.md
     docs/EU_GOVERNANCE_TOPICS.md
   Como el repositorio **se va a abrir**, el riesgo es concreto: en el clon nuevo un `git add -A`
   los mete, y acaban en un repositorio publico una convocatoria de plaza y dos notas de
   proyecto europeo. Antes de empujar hay que decidir por cada uno: **`.gitignore`** si nunca
   deben entrar (lo expresa para todos los clones y sí viaja), o sacarlos de `docs/` a `_local/`,
   que ya esta ignorada. **Dejarlo en `.git/info/exclude` no es una opcion en el clon nuevo**,
   porque nadie se acordara de recrearlo.
   Nota aparte: `git ls-files` es lo unico que dice la verdad sobre que hay en el arbol; el disco
   del mantenedor tiene mas cosas. El guardarrail de REPO.3 se arreglo para preguntar a git.
1. Copia de seguridad fuera del portatil: `git bundle create ../respaldo.bundle --all`, y
   `git bundle verify` ejecutado desde dentro del repositorio.
   HECHO el 2026-09-07: `Documents/respaldo-gov-gen-ai-platform-2026-09-07.bundle`, 11,1 MB,
   «complete history», con `main`, `desarrollo` y HEAD. **Falta sacarlo del portatil.**
2. Apuntar las 12 variables del viejo, que en el nuevo no estan:
   gh variable list --repo ModestoFabra/gov-gen-ai-platform
   NO se renombra el viejo. En B se queda como esta y sirviendo hasta el paso 7: es la red.
3. Crear el nuevo en la ORGANIZACION, VACIO (sin README, sin .gitignore, sin licencia: si GitHub
   crea un commit inicial, el push choca):
   gh repo create universitatjaumei/gov-gen-ai-platform --private
4. AMPLIAR LA AUTENTICACION A LOS DOS NOMBRES, antes de empujar. Aditivo, sin ventana de rotura:
   gh variable list -> copiar los 12 pares al nuevo (gh variable set ... --repo universitatjaumei/...)
   gcloud iam workload-identity-pools providers update-oidc modestofabra-gov-gen-ai-platform \
     --project=uji-teclab --location=global --workload-identity-pool=github \
     --attribute-condition="assertion.repository=='ModestoFabra/gov-gen-ai-platform' || assertion.repository=='universitatjaumei/gov-gen-ai-platform'"
   gcloud iam service-accounts add-iam-policy-binding govgenai-deploy@uji-teclab.iam.gserviceaccount.com \
     --project=uji-teclab --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/618806480921/locations/global/workloadIdentityPools/github/attribute.repository/universitatjaumei/gov-gen-ai-platform"
   Los dos anclajes estan medidos el 2026-09-07 y son los dos sitios que llevan el nombre. El
   codigo NO se toca: `deploy.yml` lee el proveedor de una variable y el nombre del recurso no
   cambia.
5. Subir **LAS DOS RAMAS** al nuevo:
   git remote set-url origin git@github.com:universitatjaumei/gov-gen-ai-platform.git
   git push -u origin main
   git push -u origin desarrollo
   La rama `desarrollo` nacio el 2026-09-02, despues de escribirse este plan, y es DONDE VIVE EL
   TRABAJO: subir solo `main` dejaria fuera todo lo no desplegado. Comprobar que estan las dos:
   gh api repos/.../branches --jq '.[].name'
6. Verificar CON EL ANTERIOR TODAVIA EN PIE. Si algo falla, se para y no se ha perdido nada:
   - las dos puntas coinciden: git rev-parse main / desarrollo contra
     gh api repos/.../commits/{main,desarrollo} --jq .sha
     (si coinciden esta todo: git no puede subir un commit sin sus ancestros);
   - gh api repos/.../commits/dc4904e0c763  da 404  <- EL QUE IMPORTA, ver abajo;
   - gh api repos/.../contents/logs  da 404;
   - las 12 variables estan: gh variable list --repo universitatjaumei/... | wc -l
   - CI en verde: un commit firmado (git commit -s) y los dos workflows pasan.
   - **UN DESPLIEGUE REAL desde el nuevo**, que es lo unico que demuestra que WIF acepta el
     nombre nuevo. Sin esto no se puede seguir: llevar `desarrollo` a `main` en el nuevo y ver
     `deploy.yml` en verde hasta el paso de salud.

   Sobre que SHA comprobar: la version anterior de este paso miraba
   `82f475b6c6d382e1586e7cc0319a9a0917fb3475`, y **ese no demuestra nada**. Medido el 2026-09-07
   caminando la cadena de huerfanos en GitHub: el arbol de `82f475b` NO tiene `logs/` —es la punta
   posterior al borrado y anterior a la reescritura—, asi que su `contents/logs` da 404 aunque la
   exposicion siga viva. El primer ancestro que SI sirve los volcados es **`dc4904e0c763`**
   (2026-08-21 06:20:35), con **46 ficheros**, y por debajo `152c3d2f3f2e` con otros 46. Comprobar
   `82f475b` era medir lo que no era, que es el fallo de instrumento habitual de esta casa.
7. Borrar el viejo. **Aqui es donde mueren los 46 volcados**, y no antes: hasta este punto la
   exposicion sigue viva y el viejo es la red por si algo del paso 6 falla.
   gh auth refresh -h github.com -s delete_repo   (el token no trae ese permiso por defecto)
   gh repo delete ModestoFabra/gov-gen-ai-platform --yes
8. ESTRECHAR la autenticacion, ya sin vuelta atras que proteger:
   gcloud ... providers update-oidc ... --attribute-condition="assertion.repository=='universitatjaumei/gov-gen-ai-platform'"
   gcloud iam service-accounts remove-iam-policy-binding ... --member="principalSet://.../attribute.repository/ModestoFabra/gov-gen-ai-platform"
   Y un despliegue mas para comprobar que sigue en verde con la condicion estrecha.

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


### Prompt REPO.4 (RED/GREEN) — Retirar los anclajes al dueño anterior

**Modelo sugerido**: **Sonnet** — es una retirada mecánica con un guardarraíl; el criterio ya está
decidido.

> **Nuevo el 2026-09-07**, al elegir la variante B. Con la variante A no hacía falta: el nombre
> acababa siendo el mismo. Con B cambia el dueño, y el repositorio se nombra a sí mismo en seis
> sitios. Va **después de REPO.1**, porque hasta que el repositorio no está en la organización el
> guardarraíl no puede estar verde.

```
# PROMPT REPO.4 (RED/GREEN) — El repositorio deja de nombrar a su dueño anterior
# Deploy: n/a

## Por que
Medido el 2026-09-07: seis sitios del arbol escriben `ModestoFabra`, y ninguno es codigo de
negocio. Cuatro son ficheros vivos que un lector nuevo consulta, y dos son documentacion:

  .github/CODEOWNERS                      14 entradas a @ModestoFabra
  server/pyproject.toml                   Repository = "https://github.com/ModestoFabra/..."
  mcp_server/pyproject.toml               idem
  CONTRIBUTING.md                         la tabla de §«Donde trabajas» nombra el principal
  docs/DESPLIEGUE_PROTOTIPO_GCP.md §177   la condicion de WIF, con el nombre viejo
  planificacion/PLAN_DESARROLLO.md        dos menciones de contexto

`deploy.yml` NO lleva el nombre: lee el proveedor de una variable. Comprobado.

## Que hacer
1. CODEOWNERS: a un equipo de la organizacion, no a una persona. Es el cambio con mas fondo del
   prompt —una persona no es un mantenedor sostenible para un repositorio institucional— asi que
   el equipo tiene que existir antes (paso 0 de REPO.1).
2. Los dos `Repository =` de los `pyproject.toml`, al nombre nuevo.
3. `CONTRIBUTING.md`: la tabla de §«Donde trabajas» pasa a nombrar el principal en la
   organizacion. **OJO con no romper lo que esa seccion dice**: la regla es que NO hay fork
   privilegiado, «incluida la universidad donde nacio». Que el principal viva en la organizacion
   de la UJI **no le da privilegio**, y el texto tiene que seguir diciendolo — si no, la
   gobernanza se lee como que la UJI dirige.
4. `docs/DESPLIEGUE_PROTOTIPO_GCP.md` §177: la condicion de WIF, con el nombre nuevo. Y el
   `principalSet`, que ese documento no menciona y deberia: son DOS anclajes, no uno.
5. `planificacion/PLAN_DESARROLLO.md`: las dos menciones de contexto.
6. NO se toca `planificacion/HISTORIAL.md` ni los planes de fase cerrados: son registro.

## Tests (RED primero)
- RED: ningun fichero vivo escribe `ModestoFabra`. El barrido excluye `HISTORIAL.md`,
  `planificacion/fase1/` y `docs/` marcados como instantanea fechada — la misma distincion
  registro/activo que ya usa `test_repo3_el_indice_de_docs_no_miente.py`.
- RED: `CODEOWNERS` no asigna a un usuario individual (`@usuario`), sino a un equipo
  (`@org/equipo`). Es lo que impide que la retirada se haga cambiando un nombre de persona por
  otro.

## Criterio de done
- [ ] Los seis sitios, al nombre nuevo, y el guardarrail verde
- [ ] CODEOWNERS a un equipo
- [ ] `CONTRIBUTING.md` sigue diciendo que no hay fork privilegiado
- [ ] `docs/DESPLIEGUE_PROTOTIPO_GCP.md` documenta LOS DOS anclajes de WIF
```

---

### Prompt REPO.3 ✅ (RED/GREEN, HECHO el 2026-09-07) — El triaje editorial de `docs/`

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
