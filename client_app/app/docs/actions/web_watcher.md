# Módulo: Web Watcher (Monitor Web)

El módulo Web Watcher de AutomatIA funciona como un Event Trigger (Disparador de Eventos). Su objetivo es observar continuamente páginas web, feeds RSS o archivos expuestos vía web, y desencadenar un proceso automatizado (Flow) únicamente cuando detecta un cambio en el contenido supervisado.

## Funcionamiento Manual

El usuario debe configurar los siguientes parámetros obligatorios o conceptuales:
- **URL Objetivo**: La dirección de la página que se va a monitorear (Ej. `https://example.com/noticias`).
- **Intervalo de Comprobación**: Frecuencia con la que el monitor revisará si ha habido cambios (ej. cada 15 minutos, 60 minutos, 24 horas).
- **Selector CSS (Opcional)**: En lugar de analizar el HTML completo de la web (lo cual dispararía falsos positivos si cambian cosas como la fecha o un anuncio), el usuario puede colocar un selector como `.article-content` o `#precio`. Si el módulo detecta cambios solo dentro de ese elemento o selector, entonces dispara la ejecución.

## Datos Emisores (Outputs)

Cuando este módulo detecta un cambio y arranca un flujo, provee las siguientes variables (Pills) para que las consuman los procesadores siguientes:
- El evento en sí mismo (Trigger alert).
- Las diferencias detectadas (Diffs).

## Comportamiento del Copiloto (IA)

En esta pantalla, el Copiloto tiene un rol puramente consultivo. Debes ayudar al usuario a entender:
1. Cómo configurar los intervalos para no sobrecargar los servidores web (respetar políticas CORS y rate limits).
2. Qué es un selector CSS y cómo puede extraer uno usando el inspector del navegador para el sitio web que desea monitorizar.
(Nota: Este módulo NO soporta autoconfiguración ni generación vía comandos).

<help_config>
### Cómo configurar
1. **URL**: Introduce la dirección de la página web que quieres monitorizar.
2. **Selector CSS** (opcional): Te recomendamos que uses un selector de la zona específica que quieres vigilar (ej. `.precio` o `.noticias-hoy`). De lo contrario saltará con cambios técnicos invisibles de la web.
3. **Frecuencia**: Determina cada cuántos minutos u horas el robot visitará la URL para buscar cambios.
</help_config>

<help_example>
### Ejemplo de Vigilante Web
Si quieres suscribirte a una sección de noticias de una web institucional:
- URL: `https://institucion.gob/noticias`
- Selector: `.listado-titulares`
- Frecuencia: `Cada hora`

Si entre la hora 10:00 y las 11:00 publican una nueva noticia en ese recuadro, este módulo despertará al flujo automatizado pasándole la antigua y nueva versión.
</help_example>
