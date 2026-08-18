# Decisión: no se instala navegador sin cabeza para el rastreo (RAS.4)

**Fecha**: 2026-08-18. **Estado**: decidido con la medición delante. **Se revisa** cuando un
apartado dé un sondeo distinto.

## La pregunta

Si una parte grande de un apartado se pinta con JavaScript, no hay forma de leerla sin renderizar.
La pregunta era si hace falta meter un navegador sin cabeza en el rastreador, y **no se responde
opinando**: se responde midiendo el apartado que se va a rastrear. Un navegador pesa cientos de
megabytes y el despliegue previsto es una VM pequeña —la aplicación está en ~345 MB precisamente
porque los modelos locales se hicieron opcionales—. Es la misma decisión que se tomó con `torch`.

## La medición

Sondeo del apartado de la Escuela de Doctorado de `www.uji.es`, **sin navegador**, el 2026-08-18,
con pausa de 2 s y `robots.txt` respetado:

| Medida | Valor |
|---|---|
| Páginas leídas en el sondeo | 25 (tope del sondeo; quedaban 72 en cola) |
| Páginas que necesitan renderizado | **0** |
| Señales de dinamismo encontradas | ninguna |
| Texto visible por página (mediana) | 3.982 caracteres |
| Página con menos texto | 2.177 caracteres |
| HTML por página | ~51 KB |
| `<script>` por página | ~10 |
| `<noscript>` presente | sí, en páginas llenas de texto |
| `sitemap.xml` del portal | **404: no existe** |

## La decisión

**No se implementa renderizado.** El contenido estático cubre el apartado: cada página sirve su
texto en el HTML —entre 2 KB y 4 KB por página— y ninguna necesita un navegador para leerse.
Implementarlo ahora sería infraestructura anticipada: cientos de megabytes y segundos por página
para resolver un problema que este portal no tiene.

Lo que sí queda hecho es **poder detectarlo**: el sondeo de RAS.2 vive en
`modules/curation/sondeo_dinamico.py`, se puede ejecutar sobre cualquier apartado antes de
rastrearlo, y una página ilegible sin navegador se avisa como `needs_javascript` en vez de acusarla
de estar vacía. La medición se repite; la decisión no se hereda.

## Dos cosas que la medición enseñó y no estaban previstas

**El `<noscript>` y los diez scripts son del portal, no de la página.** Una página perfectamente
estática de `www.uji.es` lleva las dos cosas. Cualquier heurística que mirara sólo eso habría
declarado dinámico el portal completo, y el informe de calidad habría salido lleno de acusaciones
falsas en la primera pasada. Por eso las señales exigen **poco texto junto a** muchos scripts, o un
contenedor de framework vacío.

**El portal no publica `sitemap.xml`.** La señal más fiable del sondeo —el hueco entre las URLs que
declara el sitemap y las que alcanza el recorrido por enlaces— **no está disponible aquí**, así que
el veredicto se apoya sólo en las señales por página. Conviene saberlo antes de fiarse del sondeo en
otro apartado del mismo portal: si un día aparece el sitemap, la señal fuerte vuelve a estar.

## Si algún día hace falta

Las condiciones están escritas para no volver a discutirlo desde cero:

1. Primero el sondeo del apartado. Si dice que no hace falta, no se hace.
2. Si hace falta: detrás del mismo protocolo de descarga que ya usa el spider, como **extra de
   instalación** (`[render]`), **desactivado por defecto** y activable **por sitio**. Ningún sitio
   renderiza por accidente.
3. La cortesía de RAS.1 se aplica igual o más: un navegador pide muchos más recursos por página.
4. Con el coste medido y escrito —tamaño de imagen, memoria, segundos por página— para que activarlo
   en producción sea una decisión con cifras.
