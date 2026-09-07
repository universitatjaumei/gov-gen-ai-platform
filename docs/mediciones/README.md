# Mediciones

**Instantáneas fechadas. No se mantienen.** Cada fichero recoge lo que se midió un día concreto,
con qué lote y qué salió. Ninguno se actualiza después: cuando hay una medición nueva se añade
otro fichero con su propia fecha, y el anterior se queda como estaba.

Eso es deliberado. Una medición reescrita deja de poder auditarse a sí misma, y la comparación
entre dos fechas —que suele ser lo interesante— exige que la primera siga diciendo lo que decía.

> ⚠️ **Esto no describe el sistema de hoy.** Para lo vigente:
> [`../ESPECIFICACIONES.md`](../ESPECIFICACIONES.md) —qué garantiza la plataforma— y
> [`../DECISIONES.md`](../DECISIONES.md) —qué se decidió y si sigue en pie—. Una configuración
> citada aquí puede haber cambiado, y de hecho **varias han cambiado**.

## Qué hay

| Fecha | Medición | Qué dijo |
|---|---|---|
| 2026-08-25 | [Qué valor darle a `retrieval_top_k`](2026-08-25_MEDICION_RETRIEVAL_TOP_K.html) | La anchura de la recuperación, medida en vez de supuesta |
| 2026-08-25 | [Redacta mejor con menos documentos](2026-08-25_CALIDAD_RESPUESTA_TOP_K.html) | Más contexto no da mejor respuesta: pasado cierto punto, resta |
| 2026-08-25 | [Por qué el asistente no contesta](2026-08-25_DIAGNOSTICO_POR_QUE_NO_CONTESTA.html) | Y por qué no es la anchura, que era la hipótesis de partida |
| 2026-08-25 | [Al asistente de Gerencia lo calla el umbral](2026-08-25_GERENCIA_TOP_K_Y_UMBRAL.html) | El mismo diagnóstico en el otro asistente, con otra causa. Incluye por qué el flujo agéntico contesta a todo |
| 2026-08-27 | [Granularidad del contexto](2026-08-27_EXPERIMENTO_GRANULARIDAD_CONTEXTO.html) | Cuánto contexto inyectar — y **qué puede decidir un lote de 25**, que es la pregunta que casi nunca se hace |
| 2026-08-27 | [Cierre del bloque HIB](2026-08-27_BLOQUE_HIB_CIERRE.html) | Lo que hacía falta medir para abrir el piloto, y qué dijo al medirlo |
| 2026-08-27 | [Gerencia al cerrar HIB](2026-08-27_GERENCIA_CIERRE_BLOQUE_HIB.html) | El re-troceado, el reranker y la lectura incómoda del resultado |
| 2026-08-28 | [Configuración de apertura](2026-08-28_CONFIGURACION_APERTURA_PILOTO.html) | Con qué abre el piloto, y **qué medición decidió cada valor** |

## Cómo leerlas

**El instrumento miente antes que el sistema.** Varias de estas mediciones existen porque una
cifra extrema resultó ser un artefacto del medidor y no un hallazgo: un 0, un 1.000 exacto, una
comparación que se invierte al cambiar el orden. Cuando una tabla de aquí sorprenda, la primera
hipótesis razonable es que mida otra cosa.

**Y los tamaños de lote son pequeños a propósito.** Con 25 consultas no se sostiene un porcentaje;
lo que sí se sostiene es un hallazgo cualitativo —«esto no es la anchura», «con menos documentos
redacta mejor»— y ése es el nivel al que están escritas las conclusiones. Donde una medición no
daba para decidir, lo dice.

## Convención

`AAAA-MM-DD_NOMBRE.html`, con la fecha de la medición. La carpeta se ordena sola y una ronda nueva
nunca compite por el nombre con la anterior. Un guardarraíl comprueba que no queden `.html`
sueltos en `docs/`, para que la siguiente caiga aquí sin que nadie tenga que acordarse.
