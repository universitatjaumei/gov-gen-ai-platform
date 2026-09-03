## Bloque PLAT — La administración de la plataforma, separada de la de Chatbots

> **Planificado el 2026-08-22**, a propuesta del usuario: «el apartado organizaciones aparece en el
> módulo Chatbots, pero en realidad se refiere a todos los módulos, y puede ocurrir lo mismo con los
> proveedores, los tiers por modelo, etc.». Medido contra el código, no es solo una cuestión de dónde
> cae un menú: **el backend y el frontend ya se contradicen** sobre a qué módulo pertenece esta
> configuración.
>
> | Hallazgo | Evidencia |
> |---|---|
> | El módulo `plataforma` existe en el catálogo y **no abre ninguna pantalla** | `MODULOS_INICIALES` lo declara; `AppLayout.tsx` tiene tres secciones y su comentario dice que «Plataforma» era un `PlaceholderPage` y se retiró |
> | Los modelos LLM se declaran de `plataforma` en el backend y de `chatbots` en el frontend | `hub_llm_configs_router.py:32` → `require_module("plataforma")`; `App.tsx` monta `llm-configs` bajo `<RutaDeModulo modulo="chatbots">` |
> | Consecuencia hoy: **el menú promete lo que la API niega** | con `chatbots` y sin `plataforma`, el tab «Modelos LLM» se ve y responde 403. Al revés, `plataforma` no da acceso a nada |
> | `tier` es transversal, no de Chatbots | lo consumen `redaccion` (copiloto, scripts, borradores, workspaces), `curation` (spider, crawler, reconocimiento) y `agents_hub`. `HubLLMConfig` **no tiene `organizacion_id`**: es global |
> | La pantalla de Organizaciones mezcla **tres** ámbitos | `OrganizacionRead` devuelve identidad (`name`, `partner_id`, `is_active`), tema (`theme_config`) y **una docena de `default_*` de RAG** (`default_retrieval_mode`, `default_chunk_size`, `default_reranker_enabled`…) |
> | Lo que parece la pantalla de tema es un callejón sin salida | `OrganizacionesPage` tiene un `<textarea>` «Configuración de tema (JSON)» que escribe `HubOrganizacion.theme_config`, y **nadie lo lee**: la cascada resuelve desde las filas de `hub_themes` |
> | Tres pantallas sobre los mismos dos recursos | `LLMConfigsPage` (configs LLM), `PromptsPage` (plantillas + prompt de sistema) y `AIBrainPage`, que importa **las dos cosas** sin añadir recurso propio |
> | No hay interfaz para conceder módulos, y no se puede construir aquí | las concesiones son filas de `hub_module_grants` puestas a mano; su `subject_id` es un `uuid5` del claim del token y **no hay tabla de usuarios única** que enumerar. Va al **Bloque IDE** |
> | La ruta `/hub/reports` choca con el módulo Informes | `ReportsPage` es la **revisión de interacciones** de chatbots; la etiqueta ya dice «Revisión», la ruta y el componente no |
>
> **El criterio no hay que inventarlo: ya está en la arquitectura.** `Deploy: cloud` es configuración
> de la plataforma; `Deploy: edge` es operación de un módulo. `hub_llm_configs`, `hub_organizaciones`
> y `hub_themes` son los tres `cloud`. Lo que este bloque hace es que la interfaz diga lo mismo que
> el contrato.
>
> **PLAT.1 va primero y no se puede saltar.** Añadir `require_module("plataforma")` a los routers que
> hoy no lo declaran deja fuera a todo el que no tenga esa concesión, y hoy no la tiene nadie salvo
> los superadmin, que no la necesitan. Sin la migración de concesiones, un admin no-superadmin pierde
> de golpe los modelos LLM y las organizaciones.

### Prompt PLAT.1 (RED/GREEN) — Nadie pierde acceso al partir el módulo

**Modelo sugerido**: **Sonnet** — alcance cerrado: una migración de datos y sus tests.

```
# PROMPT PLAT.1 (RED/GREEN) — Conceder `plataforma` a quien hoy administra
# Deploy: cloud

## Por que
Este bloque va a exigir el modulo `plataforma` en los routers de configuracion. Hoy la unica
pantalla que lo exige (`hub_llm_configs`) esta montada bajo el modulo `chatbots`, asi que quien
administra la plataforma lo hace con la concesion de `chatbots` y **nadie tiene `plataforma`**
salvo los superadmin, que no necesitan concesion.

Si la frontera se aplica antes de repartir la concesion, todo admin no-superadmin se queda sin
modelos LLM y sin organizaciones de un dia para otro, y el sintoma llega como un 403 sin
explicacion.

## Que hacer
1. Migracion Alembic de **datos**: para cada sujeto con concesion de `chatbots`, crear la
   concesion de `plataforma` si no existe. Idempotente: se puede reejecutar.
2. `downgrade` que retire exactamente las filas que creo, y solo esas. No borrar concesiones de
   `plataforma` preexistentes.
3. Comprobar que `plataforma` esta en el catalogo y `vigente`; si la instalacion es vieja y no lo
   tiene, sembrarlo (`MODULOS_INICIALES` es semilla, no definicion).
4. Aplicar la migracion y dejar el `alembic current` en el informe.

## Tests (RED primero)
- RED: un sujeto con `chatbots` y sin `plataforma` acaba con las dos concesiones.
- RED: un sujeto que ya tenia `plataforma` no acaba con la fila duplicada.
- RED: un sujeto sin `chatbots` sigue sin `plataforma`.
- RED: reejecutar la migracion no cambia nada (idempotencia).
- RED: `modulos_del_usuario` devuelve `plataforma` para ese sujeto despues de la migracion.

## Criterio de done
- [ ] Migracion aplicada, `alembic current` en el informe
- [ ] `downgrade` probado: deja la base como estaba
- [ ] Ningun sujeto pierde un modulo que tuviera
```

### Prompt PLAT.2 (RED/GREEN) — La cuarta sección del menú, con lo que ya es transversal

**Modelo sugerido**: **Sonnet** — mover pantallas que no cambian, con las rutas enumeradas.

```
# PROMPT PLAT.2 (RED/GREEN) — Seccion «Plataforma», y dentro lo que nunca fue de Chatbots
# Deploy: cloud

## Por que
`AppLayout` tiene tres secciones y el catalogo tiene cuatro modulos. La cuarta se retiro porque
llevaba a un `PlaceholderPage`, y desde entonces `plataforma` es un modulo que se puede conceder
y no abre nada. Tres pantallas que ya existen no son de Chatbots y estan dentro de Chatbots.

## Que hacer
1. Cuarta entrada en `NAV_SECTIONS` de `AppLayout`: `plataforma` → `/plataforma`. El menu se
   sigue generando iterando los modulos concedidos (INF.7); no hay `role ===` que anadir.
2. `PlataformaLayout` con su subnavegacion, hermano de `HubLayout` y `CurationLayout`.
3. Montar `/plataforma` con `<RutaDeModulo modulo="plataforma">` y mover **tal cual**, sin
   cambiar su contenido:
   - `/hub/llm-configs`      → `/plataforma/modelos`
   - `/hub/activity-prompts` → `/plataforma/prompts-actividad`
   - `/hub/access-tokens`    → `/plataforma/tokens`
4. Quitar esos tres de `HUB_SUBNAV` y sus rutas de `/hub`.
5. Anadir `['plataforma', '/plataforma']` a `RUTA_DEL_MODULO` (`useModulos.ts`), para que quien
   solo tenga ese modulo aterrice ahi en vez de en `/sin-acceso`.
6. Claves i18n nuevas en `ca`/`es`/`en`. Ningun literal en la interfaz.
7. **Sin redirecciones desde las rutas viejas**: el panel es interno y anterior al primer
   despliegue, y `AGENTS.md` prohibe los shims de compatibilidad. Decirlo en el commit.

## Tests (RED primero)
- RED: con `plataforma` concedido, el menu principal muestra la seccion; sin el, no.
- RED: con `plataforma` y sin `chatbots`, `/plataforma/modelos` se puede abrir. Hoy es imposible.
- RED: con `chatbots` y sin `plataforma`, `/plataforma` esta cortado por `RutaDeModulo`.
- RED: quien solo tiene `plataforma` aterriza en `/plataforma`, no en `/sin-acceso`.
- RED: `/hub/llm-configs` ya no resuelve.

## Criterio de done
- [ ] Las tres pantallas se abren en su ruta nueva, verificado en navegador
- [ ] Suite de frontend verde con `--no-file-parallelism`
- [ ] Cero literales sin i18n en la seccion nueva
```

### Prompt PLAT.3 (RED/GREEN) — Organizaciones deja de ser tres pantallas en una

**Modelo sugerido**: **Opus** — decide qué campo pertenece a qué ámbito y parte un DTO que consumen
varias pantallas.

```
# PROMPT PLAT.3 (RED/GREEN) — La identidad del inquilino y los defaults de RAG no son lo mismo
# Deploy: cloud

## Por que
`OrganizacionRead` devuelve en el mismo sitio la identidad de la organizacion (`name`,
`partner_id`, `is_active`), su tema, y una docena de `default_*` que son **valores por defecto de
RAG**: perfil de grafo, modo de recuperacion, umbral de calidad, troceado, reranker, presupuesto
de contexto. Por eso la pantalla acabo bajo Chatbots: la mayoria de sus campos si son de
Chatbots. Moverla de sitio sin partirla se llevaria los defaults de RAG fuera de su modulo.

## Que hacer
1. `/plataforma/organizaciones`: alta, baja y edicion de la **identidad** del inquilino, y nada
   mas. Es lo que ve alguien que administra la plataforma y no toca chatbots.
2. `/hub/valores-por-defecto`: los `default_*`, con selector de organizacion. Es configuracion
   del modulo Chatbots aplicada a una organizacion, no identidad de la organizacion.
3. Decidir la forma del contrato y **razonarla en el commit**: dos endpoints separados, o uno con
   dos sub-objetos. Lo que no vale es que la pantalla de identidad tenga que mandar de vuelta
   doce campos de RAG que no muestra, porque cualquier omision los pisaria con el defecto.
4. Regenerar `openapi.json` y el cliente si el contrato cambia.
5. El `theme_config` **no se toca aqui**: se retira en PLAT.7, cuando exista su sustituto.

## Tests (RED primero)
- RED: guardar la identidad de una organizacion no altera ninguno de sus `default_*`.
- RED: guardar los defaults de RAG no altera su nombre ni su `partner_id`.
- RED: la pantalla de identidad no pinta ningun campo de RAG, y al contrario.
- RED: SEC.2 sigue en pie en las dos: un admin no ve ni toca organizaciones ajenas.
- RED: los `default_*` siguen heredandose como antes (los `None` significan «heredar»).

## Criterio de done
- [ ] Las dos pantallas verificadas en navegador, incluido el caso de dos organizaciones
- [ ] Ningun campo se pisa al guardar la otra mitad
- [ ] Contrato regenerado si cambio
```

### Prompt PLAT.4 (RED/GREEN) — Una sola pantalla para proveedores, modelos y tiers

**Modelo sugerido**: **Opus** — hay que decidir qué de «Cerebro IA» sobrevive y qué era duplicado.

```
# PROMPT PLAT.4 (RED/GREEN) — Retirar «Cerebro IA», que solapa con las dos pantallas de al lado
# Deploy: cloud

## Por que
`AIBrainPage` importa plantillas de prompt **y** configuraciones LLM. No tiene recurso propio:
todo lo que edita lo editan ya `PromptsPage` y `LLMConfigsPage`. Tres pantallas sobre dos
recursos es una invitacion a que dos digan cosas distintas del mismo dato.

## Que hacer
1. Leer `AIBrainPage` entera **antes** de decidir. Si aporta una vista que las otras dos no dan
   —por ejemplo, ver de un tiron que modelo resuelve cada nivel—, esa vista se conserva y se
   lleva a `/plataforma/modelos`; lo que sea duplicado se va.
2. `/plataforma/modelos` queda como la unica pantalla de proveedores, configuraciones LLM y
   niveles (tiers), con el test de conexion que ya existe.
3. Decir en la pantalla **quien consume cada nivel**: los tiers los usan Informes (copiloto,
   scripts, borradores), Curacion (rastreo, reconocimiento) y Chatbots. Quien cambia un nivel
   tiene que saber que no esta tocando solo los chatbots.
4. Retirar `AIBrainPage`, su ruta y sus claves i18n. Caso B: borrado directo, sin cuarentena.
5. `grep -r` a cero antes de cerrar.

## Tests (RED primero)
- RED: un test de infra falla si `AIBrainPage` sigue referenciada en cualquier sitio.
- RED: lo que se decidio conservar de esa pantalla funciona en su sitio nuevo.
- RED: el test de conexion del proveedor sigue verde.

## Criterio de done
- [ ] `grep -ri aibrain` a cero
- [ ] `/plataforma/modelos` verificada en navegador, incluido el test de conexion
- [ ] La pantalla dice que modulos consumen los niveles
```

### Prompt PLAT.5 (RED/GREEN) — La frontera, declarada en el backend

**Modelo sugerido**: **Sonnet** — routers enumerados, criterio ya fijado.

```
# PROMPT PLAT.5 (RED/GREEN) — `require_module("plataforma")` donde corresponde
# Deploy: cloud

## Por que
Solo `hub_llm_configs_router` declara su modulo. `hub_organizaciones_router`, `hub_themes_router`
y `pat_router` son `Deploy: cloud` y no declaran ninguno: hoy los protege solo el rol, asi que un
admin de una organizacion con el modulo de informes concedido y nada mas puede llamarlos por API
aunque no tenga pantalla. La regla de `AGENTS.md` es que el modulo se declara al registrar el
router; estos son de antes de la regla.

**Depende de PLAT.1.** Sin la migracion de concesiones, esto es una averia, no una frontera.

## Que hacer
1. Anadir `dependencies=[Depends(require_module("plataforma"))]` a `hub_organizaciones_router`,
   `hub_themes_router` y `pat_router`.
2. **Excepcion documentada en `hub_themes_router`**: `get_theme_for_chatbot` y
   `get_theme_logo` los consume el widget publico, que no tiene sesion ni modulo. Si la
   dependencia a nivel de router los rompe, sacarlos a un router propio o poner la guarda por
   endpoint, y explicar en el docstring por que esos dos no la llevan.
3. Etiquetar en el docstring de cada router el modulo, como ya se hace con `Deploy:`.
4. Revisar el resto de routers sin modulo (`library_router`, `hub_test_scenarios_router`,
   `hub_prompt_templates_router`, `hub_content_quality_router`, `hub_ingestion_router`,
   `hub_sites_router`) y **decir cual es el de cada uno**, aunque no se cambie ninguno en este
   prompt: el inventario es el entregable.

## Tests (RED primero)
- RED: sin `plataforma`, `GET /hub/organizaciones` responde 403.
- RED: con `plataforma`, responde 200.
- RED: el widget publico sigue pintando su tema y su logotipo **sin sesion**. Es el test que
  impide arreglar la frontera rompiendo la parte publica.
- RED: un superadmin entra sin concesion explicita.

## Criterio de done
- [ ] Los tres routers declaran su modulo
- [ ] El widget publico verificado en navegador, sin sesion
- [ ] Inventario de los routers sin modulo, con el modulo que les toca
```

### Prompt PLAT.6 (RED/GREEN) — La identidad visual se configura, no se escribe en JSON

**Modelo sugerido**: **Opus** — pantalla nueva sobre una cascada de tres niveles, con decisiones de
diseño embebidas.

```
# PROMPT PLAT.6 (RED/GREEN) — Colores, tipografia y logotipo, en los tres niveles
# Deploy: cloud

## Por que
La cascada visual existe y funciona —plataforma → organizacion → chatbot— y desde el 2026-08-22
lleva tambien la marca (`ThemeBranding`). Lo que no existe es donde configurarla: el logotipo se
sube por API con `curl`, y los colores solo se pueden tocar escribiendo JSON a mano en un
`<textarea>` cuyo destino, ademas, no lo lee nadie.

Una pantalla que edite solo el nivel de la organizacion no sirve: no podria fijar el defecto de
la plataforma ni la excepcion de un chatbot concreto, que son los otros dos niveles de la misma
cascada.

## Que hacer
1. `/plataforma/identidad-visual`, con **selector de nivel**: plataforma / organizacion /
   chatbot. El nivel de plataforma, reservado a superadmin, como ya hace `create_theme`.
2. Editar colores y tipografia con controles de verdad —selector de color, lista de tipografias—
   no un area de texto con JSON. Los campos salen del contrato (`ThemeColors`,
   `ThemeTypography`), iterados: si el contrato crece, la pantalla crece.
3. Subida del logotipo contra `POST /hub/themes/{id}/logo`, que ya existe. Decir en la pantalla
   los limites reales: PNG o JPEG, 1 MB, sin SVG y por que.
4. **Vista previa sobre el fondo real de la barra lateral.** Es el motivo por el que la prueba
   manual de la marca sigue necesitando a una persona: un logotipo con letras oscuras pasa todos
   los tests y se lee fatal sobre el azul del panel. Con la vista previa, deja de necesitarla.
5. Mostrar **que hereda** cada nivel de su padre y que esta pisando, campo a campo. Una cascada
   que no se ve es una cascada que se configura a ciegas.
6. Enlace desde la pantalla de identidad de la organizacion (PLAT.3) al nivel de esa
   organizacion.

## Tests (RED primero)
- RED: los campos se generan iterando el contrato; el test falla si busca un campo escrito a mano.
- RED: un admin no puede seleccionar el nivel de plataforma; un superadmin si.
- RED: al guardar solo el logotipo, los colores heredados no se copian ni se congelan.
- RED: la pantalla dice, para un campo sin definir en su nivel, de donde lo hereda.
- RED: subir un SVG o un fichero de mas de 1 MB da un error legible, no un 500 crudo.

## Criterio de done
- [ ] Los tres niveles configurables y verificados en navegador
- [ ] La vista previa refleja el cambio antes de guardar
- [ ] Accesibilidad: la puerta de axe del proyecto, verde
- [ ] Cero literales sin i18n
```

### Prompt PLAT.7 (RED/GREEN) — Retirada del tema en JSON y de la ruta que choca con Informes

**Modelo sugerido**: **Sonnet** — mecánico, con una migración y un `grep -r`.

```
# PROMPT PLAT.7 (RED/GREEN) — Fuera la columna que nadie lee y la ruta mal llamada
# Deploy: cloud

## Por que
`HubOrganizacion.theme_config` es una columna JSONB con un `<textarea>` en la interfaz —
«Configuracion de tema (JSON)» — y **ningun lector**: la cascada resuelve desde `hub_themes`. Son
dos sitios para lo mismo, y el que esta a la vista es el que no hace nada. Con PLAT.6 ya
existiendo, se puede retirar sin dejar hueco.

Y `/hub/reports` (`ReportsPage`) es la revision de interacciones de chatbots. La etiqueta ya dice
«Revision»; la ruta y el nombre del componente chocan de frente con el modulo Informes, que es
donde alguien los va a buscar.

## Que hacer
1. Migracion Alembic que **borra** `hub_organizaciones.theme_config`, con `downgrade` que la
   recrea vacia. Comprobar antes, con una consulta, si alguna fila tiene contenido; si lo tiene,
   decirlo en el informe y **parar** antes de borrar: puede ser configuracion que alguien
   escribio creyendo que servia.
2. Quitar el campo de `OrganizacionRead`/`Create`/`Update` y el `<textarea>` de la pantalla.
   Regenerar el contrato y el cliente.
3. Renombrar la ruta `/hub/reports` → `/hub/revision` y el componente `ReportsPage` →
   `RevisionInteraccionesPage`, con su fichero de test.
4. `grep -r` a cero de `theme_config` sobre organizaciones y de `ReportsPage`.

## Tests (RED primero)
- RED: un test de infra falla si `theme_config` reaparece en el modelo de organizacion.
- RED: la migracion aplica y revierte sobre una base de datos limpia.
- RED: `/hub/reports` ya no resuelve y `/hub/revision` si.
- RED: la revision de interacciones sigue funcionando igual (sus tests actuales, renombrados).

## Criterio de done
- [ ] Migracion aplicada, `alembic current` en el informe
- [ ] `grep -r` a cero
- [ ] Contrato regenerado
```

> **Orden y dependencias.** **PLAT.1 es la condición de todo**: sin la migración de concesiones,
> PLAT.5 deja a los administradores fuera. PLAT.2 solo mueve pantallas que no cambian, así que es el
> más barato y el que ya hace utilizable el módulo `plataforma`. PLAT.3 y PLAT.4 son los dos caros y
> son independientes entre sí. PLAT.5 va después de PLAT.1 y de que las pantallas estén en su sitio,
> porque si no se prueba la frontera contra una interfaz que todavía la contradice. PLAT.6 depende de
> PLAT.3 solo para el enlace. PLAT.7 depende de PLAT.6: retirar el `theme_config` antes de tener su
> sustituto deja a la organización sin forma de configurar su tema.
>
> **Lo que este bloque NO hace, y por qué.** La pantalla de concesión de módulos salió de aquí el
> 2026-08-22, al preguntar el usuario dónde estaba prevista la gestión de usuarios: no se puede
> construir sobre lo que hay. `HubModuleGrant` dice en su propio docstring que «no hay una tabla de
> usuarios única», y su `subject_id` es un `uuid5` derivado del claim del token, así que se pueden
> **leer** las concesiones existentes pero no enumerar a quién concederlas. Eso es identidad, no
> reorganización del panel: va en el **Bloque IDE**.
>
> **PLAT.1 y PLAT.2 se ejecutan ANTES del Bloque IDE, y el resto después** (decisión del usuario,
> 2026-08-22). No es una preferencia: las pantallas de IDE.4 e IDE.5 cuelgan de `/plataforma`, que es
> la sección que crea PLAT.2, así que sin ella no tienen dónde vivir. Y PLAT.1 va delante de PLAT.2
> porque mover «Modelos LLM» a una sección en la que un admin no puede entrar le **quita** un acceso
> que hoy tiene. Ya estaban marcados como adelantables por otro motivo —arreglan solos el 403—, así
> que adelantarlos no fuerza nada.
>
> **Orden de ejecución completo**: PLAT.1 → PLAT.2 → IDE.1…IDE.5 → PLAT.3…PLAT.7 → **Deploy**.
> El bloque se queda escrito seguido, que es más fácil de leer que partido en dos.

---
