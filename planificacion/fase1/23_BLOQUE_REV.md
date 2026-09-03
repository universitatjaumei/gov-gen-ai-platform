## Bloque REV (continuación) — REV.11 a REV.13 (PENDIENTE)

Los tres salen del segundo repaso del usuario (2026-08-23), después de cerrar REV.1–REV.10.
Los tres tienen alcance cerrado y no dependen entre sí.

### Prompt REV.11 (RED/GREEN) — Organizaciones vive bajo Chatbots y su router dice que es de Plataforma

**Modelo sugerido**: **Sonnet** — es el movimiento de PLAT.2 otra vez, con el criterio ya fijado.

**Objetivo**: `hub_organizaciones_router` protege crear, editar y borrar con
`require_module("plataforma")`, y sólo los endpoints de valores por defecto con `chatbots` (así
lo dejó PLAT.5 a propósito). Pero la **pantalla** vive en `/hub/organizaciones`, bajo
`HubLayout`, que exige el módulo `chatbots`.

La consecuencia es un fallo, no una incomodidad: **quien tenga `plataforma` y no `chatbots` no
puede llegar a la pantalla que su propio módulo protege**. Es literalmente el caso de «Modelos
LLM» que arregló PLAT.2, que se quedó sin mover porque entonces nadie miró esta pantalla.

Y el argumento de fondo lo dio el usuario: la organización **sirve al resto de los módulos**, así
que darla de alta es una operación general y no del módulo de asistentes.

```
# PROMPT REV.11 — La organización no es del módulo Chatbots
# Deploy: cloud

## RED
- `test_should_reach_organisations_with_only_the_platform_module`: con `plataforma` y sin
  `chatbots`, la ruta resuelve y la pantalla pinta.
- `test_should_not_keep_the_old_route`: `/hub/organizaciones` ya no resuelve. **Sin
  redirección**, que AGENTS.md prohíbe los shims y el panel es interno.
- `test_should_keep_the_listing_readable_for_the_chatbots_module`: el `GET` de la lista sigue
  siendo accesible con `chatbots`, porque lo consumen el selector de `ChatbotsPage`, el de
  valores por defecto y el de la cabecera (REV.10). Esto ya lo fija PLAT.5; el test se repite
  aquí porque mover la pantalla es justo la ocasión de romperlo sin querer.

## GREEN
- La ruta pasa a `/plataforma/organizaciones` y la entrada, de `HUB_SUBNAV` a
  `PLATAFORMA_SUBNAV`.
- Las claves i18n se mueven con ella; si alguna queda sin consumidor, la caza `CAL.4`.

## Cierre
- [ ] Verificado en navegador con las dos combinaciones de módulos
- [ ] `grep -r "hub/organizaciones"` a cero fuera del historial
```

### Prompt REV.12 (RED/GREEN) — Un superadministrador no ve el tema de la organización que está mirando

**Modelo sugerido**: **Sonnet** — una regla, un endpoint, y la pieza que falta ya existe.

**Objetivo**: el usuario configuró el logotipo y los colores de la UJI y **no los veía**, y
preguntó si tenía que reiniciar. No: `GET /hub/themes/resolved` funde el nivel de organización
**sólo cuando quien pregunta pertenece a una sola**, y en un superadministrador la lista vacía
significa «todas», así que responde con la marca de plataforma. Está escrito en el docstring y
es una decisión razonada — con varias organizaciones no hay forma de saber cuál es «su casa».

Lo que ha cambiado es que **ahora sí la hay**: REV.10 puso una organización elegida en la
cabecera. El endpoint puede respetarla.

```
# PROMPT REV.12 — La marca que se ve es la de la organización que se está mirando
# Deploy: cloud

## RED
- `test_should_resolve_the_theme_of_the_organisation_asked_for`: con `?organizacion=<id>`, un
  superadministrador recibe la cascada plataforma → esa organización.
- `test_should_refuse_an_organisation_the_caller_cannot_see`: un admin que pide otra
  organización recibe 403, **no** la marca de plataforma. Devolver algo distinto de lo pedido
  esconde el fallo de permisos.
- `test_should_keep_answering_the_platform_mark_without_the_parameter`: sin parámetro, el
  comportamiento de hoy, que es lo que consume el widget y el panel de quien no elige.

## GREEN
- Parámetro opcional en `/hub/themes/resolved`, validado con `assert_org_access`.
- `useMarca` y `useColoresDelPanel` (REV.9) lo pasan desde `useOrganizacionElegida` (REV.10).
- La pantalla de identidad visual dice, en el nivel «Organización», que lo que se está
  editando es lo que verá quien pertenezca a ella — y el superadministrador, si la elige
  arriba.

## Cierre
- [ ] Verificado en navegador: elegir UJI en la cabecera y ver su logotipo en el panel
```

### Prompt REV.13 (RED/GREEN) — Los prompts, en un sitio desde el que se vean todos

**Modelo sugerido**: **Opus** — hay que unir dos modelos distintos sin fingir que son el mismo.

**Objetivo**: hay dos pantallas y el usuario pregunta, con razón, por qué. La respuesta es que
son **dos modelos distintos**, no el mismo dato en dos sitios:

| Pantalla | Tabla | Ámbito |
|---|---|---|
| Chatbots → «Prompts del sistema» | `HubPromptTemplate` | Cuelga de **un chatbot** (`chatbot_id` NOT NULL), por idioma y versionado |
| Plataforma → «Prompts de actividad» | `HubActivityPrompt` | `activity` **único global**, sin organización ni chatbot |

Que en Plataforma sólo salgan los de Informes es correcto hoy: el catálogo tiene cuatro
actividades y las cuatro son de ese módulo (REV.7 les puso el módulo encima). Los prompts de
chatbot no están ahí porque **no son actividades**.

Lo que pidió el usuario es la segunda opción que se le ofreció: **una pantalla desde la que se
consulten, filtren y editen todos**.

```
# PROMPT REV.13 — Todos los prompts, con su ámbito a la vista
# Deploy: cloud

## RED
- `test_should_list_both_kinds_with_their_scope`: la pantalla de plataforma lista actividades
  Y plantillas de chatbot, cada una diciendo de qué es (plataforma / asistente «X»).
- `test_should_filter_by_scope_and_by_chatbot`: el filtro de REV.7 gana el eje de ámbito.
- `test_should_edit_a_chatbot_template_from_here`: editar arrastra el `chatbot_id`, que es lo
  que hace que la plantilla exista. **Este es el test que importa**: sin él, la pantalla
  unificada sería un listado bonito que no deja tocar la mitad de lo que enseña.
- `test_should_not_offer_a_language_for_an_activity`: una actividad no tiene idioma y una
  plantilla sí. Unir las dos vistas no puede significar inventarle campos a una de ellas.

## GREEN
- Un endpoint de sólo lectura que agrega los dos orígenes con un `ambito` explícito; **la
  edición sigue yendo a su router**, que es donde vive la regla de cada uno.
- La pantalla de Chatbots se queda como atajo (misma pantalla, filtro fijado a ese chatbot).

## Cierre
- [ ] Verificado en navegador editando una plantilla de chatbot desde Plataforma
```

---
