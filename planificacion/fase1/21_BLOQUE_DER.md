## Bloque DER — Deriva entre copias del corpus (PENDIENTE, sustituye al descartado COR)

> **Origen**: decisión de descartar COR (ver arriba). Se conserva la duplicación por chatbot
> —porque conserva la libertad de elegir modelo de embedding por asistente— y se ataca **lo
> único que esa duplicación cuesta de verdad**: que dos copias de la misma norma diverjan
> porque alguien recargó un asistente y no el otro.
>
> ### La clave de identidad es `canonical_url`, no `content_hash`
>
> Importante, porque cambia el diseño respecto a como se planteó la petición. `content_hash`
> igual significa **contenido idéntico**; dos copias que han derivado tienen hashes
> **distintos**, así que agrupar por hash es justo lo que **no** encuentra la deriva. Lo que
> identifica «la misma norma en dos asistentes» es `canonical_url`.
>
> De ahí sale, además, que la detección **no dependa del momento de la actualización**: un
> chequeo continuo sobre `(organización, canonical_url)` encuentra la deriva aunque se haya
> producido hace tres meses por un camino que nadie previó. Avisar solo al actualizar
> protegería únicamente del descuido que ya se sospecha.
>
> **Lo de los documentos nuevos, confirmado**: no hay nada que comparar, así que no hay aviso
> posible. Lo que sí lo evita es cargarlos de una vez a los dos asistentes — que es DER.1.

---

### Prompt DER.1 (RED/GREEN) — Una carga, varios chatbots ✅ HECHO el 2026-08-11

> **Resultado**: 8 tests en `test_corpus_load_multi_chatbot.py`. Dos decisiones que el prompt
> no cerraba y se tomaron al implementarlo:
>
> - **Todas las comprobaciones van antes de la primera carga**, no una por una justo antes de
>   cada asistente. Incluida la guarda de espacio vectorial de FIX.4: descubrir con el primero
>   ya cargado que el segundo tiene el corpus en otro espacio deja una pasada que no se puede
>   repetir limpia.
> - **Se confirma por asistente, no al final.** La reconciliación es incremental, así que
>   conservar lo que sí funcionó hace que repetir la pasada solo rehaga lo que falta; tirarlo
>   todo por un fallo en el último obligaría a re-embeber corpus ya embebido, que es la parte
>   cara. El código de salida es no-cero igualmente.
>
> **Fuera de alcance, deliberado**: `corpus/sync.py` sigue con un solo chatbot. Su fuente es el
> servicio MCP de publicación y su caso de uso es otro; hacerlo repetible ahí sería una
> funcionalidad no pedida.

**Modelo sugerido**: **Sonnet** — el reconciliador ya hace el trabajo; esto es recorrerlo.

```
# PROMPT DER.1 (RED/GREEN) — Cargar el mismo corpus en dos asistentes en una pasada
# Deploy: edge

- `--chatbot-id` pasa a ser **repetible**: `--chatbot-id A --chatbot-id B`.
- Los `.md` se leen, se parsean y se validan contra el vocabulario **una sola vez**; lo que
  se repite es la reconciliación por chatbot, que es lo único que depende del destino.
- **Todos los chatbots deben ser de la misma organización.** Si no, se aborta antes de
  escribir nada: cargar corpus curado de una administración en otra es el error que no se
  puede permitir que ocurra a medias.
- El informe final es **por chatbot**, no agregado: «12 nuevos, 3 actualizados» sin decir en
  cuál no sirve para nada.
- Si un chatbot falla a mitad, se dice cuál y **no se da por buena la pasada entera**.
- Las recetas de embedding pueden diferir entre los chatbots y eso es correcto: cada uno
  embebe con el suyo. Se anota en el informe cuál usó cada uno.

## Tests (RED primero)
# should_parse_the_source_once_for_several_chatbots
# should_report_results_per_chatbot
# should_refuse_chatbots_from_different_organizations
# should_not_mark_the_run_successful_when_one_chatbot_fails
```

---

### Prompt DER.2 (RED/GREEN) — Avisar cuando una norma vive en varios asistentes ✅ HECHO el 2026-08-11

> **Resultado**: 19 tests backend + 4 vitest. Tres cosas que aparecieron al ejecutarlo:
>
> - **El detector vive en `agents_hub`, no en `curation`.** Escribirlo en `curation/` violaba
>   la frontera de CUR.1 y lo cazó `test_frontera_curacion.py`. El criterio correcto ya estaba
>   escrito en esa guarda para `gap_detector`: su sujeto es un chatbot y su señal nace del
>   corpus del asistente, no de auditar páginas — es algo que el asistente **emite** hacia la
>   curación.
> - **`severity` crítica cuando las copias no coinciden en `estat_vigencia`.** No estaba en el
>   prompt y es el peor caso real: no es que una respuesta esté desactualizada, es que dos
>   asistentes de la misma casa contestan lo contrario sobre si una norma sigue en vigor.
> - **Cuando no se puede saber cuál es la vigente** —mismas fechas, distinto contenido— se
>   avisa a todos con `indeterminat: true` en vez de elegir una: el aviso llevaría implícita
>   una afirmación falsa.
>
> Y dos guardarraíles ajenos que saltaron y se atendieron en vez de rodearse: CAL.3 (la página
> de documentos pasó de 300 líneas → el diálogo y el borrado salen a
> `DeleteDocumentDialog` + `useBorradoDeDocumento`) y CAL.4 (las formas plurales de i18next no
> aparecen literales en el código → la guarda de claves muertas aprende a buscar la clave base).

**Modelo sugerido**: **Sonnet** — se apoya en la maquinaria de hallazgos de curación que ya
existe; sin decisiones abiertas.

```
# PROMPT DER.2 (RED/GREEN) — Que borrar o actualizar una copia no deje las otras a medias
# Deploy: edge

## Detección continua (lo que de verdad encuentra la deriva)
- Hallazgo nuevo `copia_divergent`, junto a `revisio_vencuda` (SYNC.2), en la maquinaria de
  curación: dentro de una organización, **mismo `canonical_url` con `content_hash` distinto**
  en dos o más chatbots. Dice en cuáles y con qué fecha de carga cada uno, para que se vea
  cuál es la vieja.
- No se resuelve solo ni borra nada: propone recargar, que es DER.1.

## Avisos en el momento de la operación
- **Al borrar un documento**: si su `canonical_url` está en más chatbots de la organización,
  la respuesta lo dice y ofrece borrarlo en todos (`?en_todos_los_chatbots=true`). **Sin ese
  parámetro se borra solo el suyo** — un borrado en cascada implícito sobre corpus normativo
  no puede ser el comportamiento por defecto.
- **Al actualizar un documento** cuya `canonical_url` está en más chatbots: la respuesta
  avisa de cuáles quedan con la versión anterior. No se propagan cambios automáticamente:
  cada asistente puede tener su receta y su calendario, y propagar en silencio es cómo se
  reembebe un corpus sin que nadie lo haya pedido.

## Frontend
- El aviso se ve **antes** de confirmar el borrado, con el número y los nombres.
- El hallazgo `copia_divergent` aparece en la pantalla de hallazgos como los demás.
- i18n es/ca/en.

## Tests (RED primero)
# should_flag_the_same_norm_with_different_content_across_chatbots
# should_not_flag_identical_copies
# should_warn_how_many_chatbots_hold_the_document_before_deleting
# should_delete_only_in_this_chatbot_by_default
# should_delete_in_all_chatbots_when_explicitly_asked
# should_warn_which_chatbots_keep_the_previous_version_after_an_update
# should_scope_all_of_this_to_the_organization        (gate SEC.8.1)
```

---

### Prompt DER.3a ✅ HECHO el 2026-08-11 — Qué necesitamos de la publicación: metadatos y opciones de notificación

> **Entregable**: `docs/REQUISITOS_PUBLICACION_PLATAFORMA.md`. Dos cosas que aparecieron al
> escribirlo y mejoran el prompt original:
>
> - **Los campos se parten en dos tablas siguiendo los dos hitos que el contrato ya
>   distingue** (§«Dos hitos, no uno»): lo que no depende de la validación de Secretaría
>   General va primero y se puede acordar ya; lo que sí depende va después. Eso convierte el
>   documento en algo accionable —dice qué construir primero— en vez de una lista plana.
> - **Se añade la señal de cambio del contenido** como requisito propio, con la regla de que
>   debe cambiar con el texto y **no** con las etiquetas. Sin decirlo, cada revisión de
>   vocabulario obligaría a reprocesar el corpus entero.
>
> Las tres reglas duras que rechazan el paquete se verificaron contra el código antes de
> prometerlas a otra unidad (`manifest.py:136-141`, `metadata_filter.py:73`), no contra el
> contrato solo.

**Modelo sugerido**: **Opus** — es un documento que va a una reunión con otra unidad y del que
sale una decisión difícil de revertir; el criterio pesa más que el código (aquí no hay código).

> **Origen**: el usuario, el 2026-08-11: la forma de publicar y notificar no está definida y
> hay que acordarla con la unidad de desarrollo, así que conviene llevarles **la relación de
> metadatos y un abanico de alternativas de notificación** para que elijan la que les encaje.
>
> **Va separado de DER.3 y NO está bloqueado, a propósito.** Meterlo dentro de DER.3 lo dejaría
> en circular: este entregable es justamente **lo que desbloquea DER.3**. Sale antes de la
> reunión; DER.3 se escribe después, con la opción ya elegida.

```
# PROMPT DER.3a (ENTREGABLE) — docs/REQUISITOS_PUBLICACION_PLATAFORMA.md
# Deploy: n/a (documento)

## Audiencia
La unidad de desarrollo de la UJI. Gente que no conoce este codebase: nada de nombres de
clase, de tabla ni de prompt. Se habla de normas, documentos y avisos.

## Parte 1 — Metadatos que la plataforma necesita por documento
Se derivan de `docs/CONTRATO_MD_CORPUS.md`, que ya es la fuente de verdad; **este documento
no inventa un vocabulario nuevo**, lo traduce a lo que hay que emitir. Por cada campo:
que significa, si es obligatorio, y **que se rompe si falta o llega mal**. Esa tercera
columna es la que hace que se respete; sin ella, «obligatorio» es una opinion.

Como minimo: `id_publicacio`, `title`, `url_oficial`, `language`, `estat_vigencia`,
`ambit_principal`, `submateries`, `content_class`, `us_assistents`, `nivell_acces`, y el
hash o la fecha de modificacion que permita saber que ha cambiado sin traerse el cuerpo.

Dos cosas que hay que decir explicitamente, porque son las que se olvidan:
- **`us_assistents` es una prohibicion, no una preferencia** cuando vale 'no'.
- **El identificador tiene que ser estable entre versiones de la misma norma.** Sin eso no
  se puede distinguir «norma nueva» de «norma modificada», y la ingesta duplica.

## Parte 2 — Alternativas de notificacion, con su coste para ELLOS
Cuatro, y para cada una: que tiene que construir la unidad de desarrollo, que construimos
nosotros, que pasa si se cae una parte, y si permite saber que se ha retirado una norma
(que es lo que habilita la poda del censo, y no todas lo permiten).

  A. **Sondeo de un indice** — publican un listado consultable; la plataforma pregunta cada
     N horas. Lo mas simple para ellos, y **es censo**, asi que habilita la poda. Latencia
     de horas, que para normativa es irrelevante.
  B. **Webhook** — nos avisan al publicar. Inmediato y barato en reposo, pero **no es
     censo** (un aviso perdido no se recupera solo) y obliga a autenticacion y reintentos.
  C. **Cola de mensajes** (Pub/Sub) — como B pero con reintentos y sin perder avisos.
     Mas infraestructura para ellos.
  D. **Deposito de ficheros** (bucket) — dejan los `.md` conformes al contrato en una
     carpeta. Es censo, es lo mas parecido a lo que hacemos hoy a mano, y encaja con que el
     pipeline de conversion viva fuera (`DECISION_EXTRACCION_Y_DESPLIEGUE.md`).

**Recomendacion explicita, no un menu neutro**: A o D, porque son censo y la poda es lo que
mantiene el corpus honesto cuando una norma se deroga. B y C sirven como *complemento* para
bajar la latencia, nunca como unica via. Un documento que presenta cuatro opciones sin
mojarse traslada la decision a quien tiene menos informacion para tomarla.

## Parte 3 — Lo que NO les pedimos
Que digan que chatbots consumen cada norma. Explicar por que en dos frases —los
identificadores son internos y esa relacion cambia mucho mas que la norma— para que la
pregunta no vuelva en la reunion siguiente.
```

---

### Prompt DER.3 (BLOQUEADO — requiere que el pipeline de publicación esté definido) — Cada asistente declara qué porción del corpus consume

**Modelo sugerido**: **Opus** — decide dónde vive el mapa documento→chatbots, y esa decisión
es difícil de deshacer una vez que el servicio de publicación empiece a emitir.

> **Origen**: pregunta del usuario el 2026-08-11. «Cuando definamos el pipeline de publicación,
> el mantenimiento será automatizado. ¿No deberíamos prever que en el momento de publicación se
> indique el número de chatbots que consumen la norma, para sincronizar la ingesta?»
>
> **La necesidad es real; el sitio propuesto, no.** Poner el mapa documento→chatbots en la
> publicación invierte la autoridad por tres motivos:
>
> 1. **El servicio de publicación no conoce los chatbots**, ni debe: sus identificadores son
>    internos de la plataforma. Publicar es un acto de transparencia sobre una norma, no una
>    decisión sobre la configuración de un asistente.
> 2. **No es una propiedad de la norma.** Que el asistente de Gerencia la consuma lo decide
>    quien configura ese asistente, y cambia mucho más a menudo que la norma.
> 3. **Viola CLAUDE.md §5**: si el mapa vive en el documento publicado, añadir un tercer
>    asistente obliga a **volver a publicar documentos**. Reclasificar debe costar un `UPDATE`.
>    Es el mismo mecanismo por el que una taxonomía deja de revisarse, aplicado a otra cosa.
>
> **El reparto correcto ya está en el contrato del `.md`**: la publicación aporta *propiedades
> de la norma* —`ambit_principal`, `submateries`, `nivell_acces` y `us_assistents`
> (`si|restringit|no`)—. Nótese que `us_assistents` **ya es** la señal de publicación sobre
> consumo por asistentes, y está bien acotada: dice «¿es apropiada para asistentes?», no «¿para
> cuáles?». Esa frontera no se cruza.
>
> **Y el patrón de este lado ya existe, para la otra fuente automatizada.**
> `HubCorpusSelection` (`operational_models.py:131`) es una selección N:M chatbot→sitio con
> `rule_type`, `rule_value` y `auto_ingest_new`: el rastreo web ya resuelve «cuando aparezca
> contenido nuevo, quién lo consume», declarativamente y del lado de la plataforma. Esto es lo
> mismo con otra fuente, y **si se implementa reinventando el mecanismo, está mal**.
>
> **Por qué está BLOQUEADO y no pendiente**: el pipeline de publicación no está definido.
> Escribir suscripciones contra un servicio cuya forma aún no se conoce es especular, que es lo
> que este proyecto no hace. **Nada de DER.1 lo cierra**: `--chatbot-id` imperativo y
> suscripciones declarativas conviven sin estorbarse, igual que hoy conviven la subida manual y
> el rastreo automático.
>
> **Disparador**: cuando la unidad de desarrollo responda al entregable de **DER.3a** y quede
> elegida la vía de notificación. DER.3a es el paso previo y **no está bloqueado**.

```
# PROMPT DER.3 (BLOQUEADO) — La suscripcion vive en la plataforma, no en la publicacion
# Deploy: edge

## Modelo — mismo patron que HubCorpusSelection, otra fuente
- Suscripcion chatbot -> corpus publicado, con una regla sobre los metadatos que el
  contrato YA define. Nada de listas de identificadores de documento: una regla sobre
  `ambit_principal` / `submateries` / `rang` sobrevive a que se publiquen normas nuevas,
  y una lista no.
- `auto_ingest_new`, como en el rastreo: publicar algo que casa con la regla lo ingiere
  solo; sin el interruptor, se propone y decide una persona.
- **`us_assistents: 'no'` manda sobre cualquier regla.** Es la unica señal de la
  publicacion sobre este eje y es una prohibicion, no una preferencia.

## Sincronizacion
- `corpus/sync.py` deja de recibir `--chatbot-id` y resuelve los destinos de las
  suscripciones. Ahi si es repetible por naturaleza, y por eso DER.1 no lo toco.
- Cada chatbot embebe con su modelo, igual que en DER.1: la guarda de espacio vectorial
  corre por chatbot antes de escribir.
- El informe es por chatbot. Una sincronizacion automatica que resume en una linea es
  una sincronizacion que nadie audita.

## Lo que NO se hace
- **No se añade al `.md` ni al payload de publicacion ningun campo con chatbots**, ni un
  recuento. Si aparece la tentacion otra vez, releer los tres motivos de arriba.
- No se propaga automaticamente a asistentes sin suscripcion: no tener regla significa
  no querer el documento, no «querer todo».

## Tests (RED primero)
# should_resolve_destinations_from_subscriptions_not_from_arguments
# should_ingest_a_newly_published_norm_into_every_matching_chatbot
# should_never_ingest_a_norm_marked_us_assistents_no
# should_only_propose_when_auto_ingest_is_off
# should_report_per_chatbot
# should_scope_subscriptions_to_the_organization        (gate SEC.8.1)
```

---
