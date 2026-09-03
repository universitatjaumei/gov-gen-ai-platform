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

Hacerlo **antes de que exista el primer fork**: un fork conserva los objetos del original.

## Lo que se pierde (inventariado el 2026-08-21)
Issues, PRs, releases, tags, webhooks: 0 de todo. Secretos de Actions: ninguno, el CI no usa.
Proteccion de rama: no hay. Forks, estrellas, watchers: 0. **Solo se pierden la fecha de creacion
(2026-04-22) y el historial de ejecuciones de Actions.**

## Los pasos
1. Copia de seguridad fuera del portatil: `git bundle create ../respaldo.bundle --all`, y
   `git bundle verify` ejecutado desde dentro del repositorio.
2. Renombrar el viejo, que es instantaneo y no destructivo:
   gh repo rename gov-gen-ai-platform-anterior --repo ModestoFabra/gov-gen-ai-platform
3. Crear el nuevo ya con el nombre bueno y VACIO (sin README, sin .gitignore, sin licencia: si
   GitHub crea un commit inicial, el push choca):
   gh repo create ModestoFabra/gov-gen-ai-platform --private
4. Subir, fijando la URL para no depender de la redireccion que deja el renombrado:
   git remote set-url origin git@github.com:ModestoFabra/gov-gen-ai-platform.git
   git push -u origin main
5. Verificar CON EL ANTERIOR TODAVIA EN PIE. Si algo falla, se para y no se ha perdido nada:
   - la punta coincide: git rev-parse HEAD  contra  gh api repos/.../commits/main --jq .sha
     (si coincide esta todo: git no puede subir un commit sin sus ancestros);
   - gh api repos/.../commits/82f475b6c6d382e1586e7cc0319a9a0917fb3475  da 404 (punta vieja);
   - gh api repos/.../contents/logs  da 404;
   - CI en verde: un commit firmado (git commit -s) y los dos workflows pasan.
6. Borrar el anterior:
   gh auth refresh -h github.com -s delete_repo   (el token no trae ese permiso por defecto)
   gh repo delete ModestoFabra/gov-gen-ai-platform-anterior --yes

## Despues
- Si se abre: Settings -> Danger Zone -> Change visibility -> Public.
- Cualquier otro clon en otra maquina conserva los volcados. No hacer pull: borrarlo y clonar.
- El nombre definitivo NO cambia: acaba llamandose gov-gen-ai-platform, igual que ahora.
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
