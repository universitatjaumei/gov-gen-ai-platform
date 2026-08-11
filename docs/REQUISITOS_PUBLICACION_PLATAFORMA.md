# Qué necesita el asistente normativo del sistema de publicación

> **Para**: la unidad de desarrollo de la UJI.
> **De**: el proyecto del asistente normativo (Gov Gen AI Platform).
> **Fecha**: 2026-08-11. **Estado**: propuesta para acordar, no especificación cerrada.

Hoy el corpus del asistente se prepara y se carga **a mano**: alguien cura los documentos, los
convierte a un formato acordado y ejecuta una orden de carga. Funciona para arrancar y no
funciona a medio plazo: en cuanto las normas se publiquen con regularidad, mantener el
asistente al día dejará de ser sostenible manualmente.

Este documento dice **qué información necesitamos de cada norma** y **de qué formas podemos
enterarnos de que hay algo nuevo**, para que elijáis la que mejor encaje con lo que ya tenéis.
No hace falta decidirlo todo hoy; la parte 1 se puede acordar antes que la parte 2.

---

## Parte 1 — Qué necesitamos saber de cada norma

Esto no es una lista de deseos: cada campo hace un trabajo concreto, y la tercera columna dice
**qué se rompe si falta o llega mal**. Si un campo no os cuadra, esa columna es la que hay que
discutir — puede que el trabajo se pueda hacer de otra manera.

### 1.1 Lo imprescindible para que el asistente cargue y cite bien

Con esto el corpus se carga, el asistente responde citando el enlace correcto y respeta quién
puede ver cada cosa. **No depende de que Secretaría General valide el vocabulario de materias**,
así que se puede acordar y construir ya.

| Campo | Qué es | ¿Obligatorio? | Qué se rompe si falta o llega mal |
|---|---|---|---|
| `id_publicacio` | Identificador de la norma en vuestro sistema | **Sí** | Sin él no se puede saber si una norma es nueva o es una versión de otra ya cargada. Ver §1.4 |
| `title` | Título oficial | **Sí** | El asistente cita «documento sin título» ante un ciudadano |
| `url_oficial` | Enlace a la publicación oficial | **Sí** | La respuesta no se puede verificar. Una cita sin enlace obliga a creerse al asistente, que es justo lo que no queremos |
| `language` | Idioma del documento (`ca`, `es`…) | **Sí** | Se mezclan versiones lingüísticas y el asistente puede contestar en un idioma citando el texto del otro |
| `content_class` | Qué clase de documento es: norma, preguntas frecuentes, u otro | **Sí** | Un documento orientativo se citaría con la autoridad de una norma |
| `revisat_per` / `revisat_el` | Quién validó el documento y cuándo | **Sí para normas** | Sin firma no se sabe si una norma ha pasado por revisión humana. La carga **rechaza el paquete** |
| `nivell_acces` | Público, interno o restringido | **Sí** | Un documento interno podría acabar respondiendo a un ciudadano anónimo |
| `us_assistents` | Si la norma puede usarse en asistentes: `si`, `restringit` o `no` | **Sí** | Ver §1.4: es una prohibición, no una preferencia |
| `motiu_exclusio` | Por qué se excluye | **Sí si `us_assistents: no`** | Excluir sin motivo convierte una decisión en un silencio que nadie puede auditar. La carga **rechaza el paquete** |
| `estat_vigencia` | Vigente, derogada, modificada… | **Sí** | El peor fallo posible: citar como vigente una norma derogada |
| `rang` | Rango normativo | Sí | Sin él el asistente no puede decir qué norma prevalece cuando dos dicen cosas distintas |
| `canonica` / `versio_idiomatica_de` | Si es la versión principal o la traducción de otra | Sí si hay versiones | Sin esto, la versión catalana y la castellana se cuentan como dos normas distintas y se citan por duplicado |
| `data_revisio_prevista` | Cuándo toca volver a revisarla | Recomendado | Sin ella, una norma que nadie toca envejece en silencio. Con ella, el sistema avisa solo |

### 1.2 Lo que hace falta para orientar la búsqueda por materia

Esto **sí depende** de que Secretaría General valide el vocabulario, así que puede ir después.
Sin ello el asistente funciona; lo que no puede es acotar la búsqueda por materia, y responde
peor en corpus grandes.

| Campo | Qué es |
|---|---|
| `ambit_principal` | Ámbito principal al que pertenece la norma |
| `ambits_secundaris` | Otros ámbitos que también la tocan |
| `submateries` | Materias concretas, del vocabulario acordado |
| `submateries_internes` | Materias de uso interno, no publicables |
| `resum_router` | Un resumen que diga **objeto + a quién se aplica + qué resuelve** |
| `preguntes_tipus` | Preguntas típicas que esta norma responde |
| `termes_bilingues` | Pares de términos equivalentes (p. ej. *despesa* / *gasto*) |

> **Aviso sobre `resum_router`**: no es el resumen del buscador del portal. Aquel está escrito
> para que una persona decida si abre el documento; este, para que el sistema decida si la
> norma es candidata a responder una pregunta. Reutilizar uno como el otro degrada la búsqueda
> sin que se note.

Pasar de 1.1 a 1.2 **no obliga a recargar nada pesado**: se reetiqueta y se vuelve a enviar, y
por cómo funciona nuestra detección de cambios (§1.3) eso no dispara reprocesado del texto.

### 1.3 Cómo sabremos que algo ha cambiado

Necesitamos, por cada norma, **una señal de cambio del contenido**: idealmente un hash del
texto; si no, una fecha de última modificación.

Esto os ahorra trabajo a vosotros y a nosotros: con esa señal solo hace falta enviar el texto
completo de lo que ha cambiado. Y hay un detalle que conviene fijar desde el principio:

> **La señal debe cambiar cuando cambia el texto de la norma, y NO cuando cambian sus
> etiquetas.** Si reetiquetar una norma altera el hash, cada revisión de vocabulario nos
> obligaría a reprocesar el corpus entero. Por nuestra parte ya está resuelto: calculamos el
> hash sobre el cuerpo del documento, ignorando los metadatos y el tipo de salto de línea.

### 1.4 Dos cosas que conviene decir en voz alta

Son las dos que, por experiencia, se dan por supuestas y luego fallan.

**`us_assistents: no` es una prohibición.** No significa «poco relevante» ni «de momento no».
Significa que esa norma no puede entrar en el índice del asistente bajo ninguna configuración.
Nuestro sistema la excluye siempre, y por eso exige que se diga el motivo.

**El identificador tiene que ser estable entre versiones de la misma norma.** Si al modificar
una norma cambia su identificador, para nosotros es una norma nueva: acabaríamos con la versión
vieja y la nueva conviviendo en el índice y el asistente citando las dos. Si en vuestro sistema
el identificador cambia por diseño, hace falta **otro campo** que diga «esto es una versión
de aquello».

---

## Parte 2 — Cómo nos enteramos de que hay algo nuevo

Cuatro formas posibles. Para cada una: qué tendríais que construir vosotros, qué construimos
nosotros, qué pasa si algo se cae, y una propiedad que resulta decisiva y explico justo debajo.

> **Qué es un «censo» y por qué decide.** Una norma puede desaparecer del corpus por dos
> motivos muy distintos: porque se ha retirado, o porque el aviso no llegó. Solo se puede
> distinguir si en algún momento recibimos **la lista completa** de lo que hay publicado —un
> censo—. Sin censo, el asistente no puede retirar nada por su cuenta sin arriesgarse a borrar
> normas vigentes, y el corpus se va llenando de normas que ya no existen. Es la diferencia
> entre un corpus que se mantiene solo y uno que hay que auditar a mano cada cierto tiempo.

### A. Sondeo de un índice publicado

Publicáis un listado consultable de las normas vigentes, con sus metadatos y su señal de
cambio; nosotros preguntamos cada N horas y nos traemos solo lo que ha cambiado.

- **Vosotros**: un listado consultable y una forma de pedir el texto de una norma.
- **Nosotros**: ya está construido. El sistema sabe leer un conjunto de datos de índice y otro
  de contenido, y traerse solo lo que ha cambiado. Está implementado sobre un servicio MCP
  con dos conjuntos de datos: **si ya tenéis algo así, el trabajo por vuestra parte es
  exponer los campos de la parte 1**. Si preferís otro protocolo, es adaptable.
- **Si algo se cae**: no se pierde nada. El siguiente sondeo lo recoge.
- **¿Es censo?** **Sí**, si el listado es completo.
- **Latencia**: horas. Para normativa es irrelevante.

### B. Aviso al publicar (*webhook*)

Nos llamáis cuando se publica o se modifica algo.

- **Vosotros**: una llamada saliente con autenticación y reintentos.
- **Nosotros**: un punto de entrada autenticado, control de duplicados y una cola.
- **Si algo se cae**: un aviso perdido **se pierde para siempre**, salvo que reintentéis. Si
  nuestro servicio está caído esa tarde, esas normas no entran nunca.
- **¿Es censo?** **No.** No detecta retiradas.
- **Latencia**: inmediata.

### C. Cola de mensajes (Pub/Sub o equivalente)

Como B, pero con la cola encargándose de los reintentos.

- **Vosotros**: publicar en un tema. Más infraestructura que B.
- **Nosotros**: un consumidor.
- **Si algo se cae**: la cola reintenta; no se pierden avisos.
- **¿Es censo?** **No**, igual que B.
- **Latencia**: inmediata.

### D. Depósito de ficheros

Dejáis los documentos, en el formato acordado, en una carpeta o depósito compartido.

- **Vosotros**: escribir los ficheros. Es lo más parecido a lo que hoy se hace a mano.
- **Nosotros**: ya está construido; es la vía que se usa ahora mismo.
- **Si algo se cae**: no se pierde nada; el contenido está en el depósito.
- **¿Es censo?** **Sí**, si el depósito contiene todo lo vigente.
- **Latencia**: la de vuestro proceso de publicación.

### Nuestra recomendación

**A o D.** Las dos son censo, y el censo es lo que permite que el corpus se mantenga honesto
cuando una norma se deroga. Entre las dos, elegid la que os cueste menos: **A** si ya tenéis o
vais a tener un catálogo consultable; **D** si os resulta más natural depositar ficheros.

**B y C sirven como complemento, no como única vía.** Si en algún momento hace falta que un
cambio se refleje en minutos y no en horas, se añade el aviso inmediato **encima** del sondeo:
el aviso adelanta el trabajo y el sondeo garantiza que nada se queda fuera. Al revés no
funciona.

No os proponemos un menú neutro a propósito. Las cuatro son construibles; solo dos resuelven el
problema de las normas retiradas, y ese problema no se ve hasta que el asistente lleva un año
citando algo que ya no está en vigor.

---

## Parte 3 — Lo que NO os vamos a pedir

**Qué asistentes consumen cada norma.** Puede parecer natural que la publicación diga a qué
asistentes va cada documento, pero no debe: los identificadores de los asistentes son internos
de nuestra plataforma, y esa relación cambia mucho más a menudo que las normas —basta con que
se configure un asistente nuevo—. Si viviera en la publicación, cada cambio de configuración
nuestro os obligaría a volver a publicar documentos.

Vosotros nos decís **qué es cada norma**; nosotros decidimos **qué quiere cada asistente**, con
reglas sobre los campos de la parte 1.

---

## Qué necesitamos de vosotros para seguir

1. Si los campos de §1.1 os encajan, o cuáles no y por qué.
2. Si podéis dar una señal de cambio del contenido (§1.3) y de qué tipo.
3. Cuál de las cuatro vías de la parte 2 preferís.
4. Si el identificador de una norma es estable entre versiones (§1.4).

Con eso podemos especificar la integración por nuestra parte. Mientras tanto el corpus se sigue
cargando a mano, así que **nada de esto bloquea el piloto**.
