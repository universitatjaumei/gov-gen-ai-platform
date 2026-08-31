# Incrustar el widget en una página

> **Entregable de D.6-VM (2026-08-31)**, que recoge lo que D.1 dejó pendiente. La credencial de
> sitio la construyó SEC.8.5 (`HubWidgetKey`); esto documenta cómo se usa, cómo se revoca y
> qué es exactamente lo que viaja en el HTML.

## El fragmento

```html
<div
  id="govgenai-widget"
  data-chatbot-id="<UUID del chatbot>"
  data-widget-key="<credencial de SITIO>"
  data-api-url="https://34-175-38-129.sslip.io/api/v1"
  data-lang="es"
></div>
<script src="/widget.iife.js" defer></script>
```

| Atributo | Obligatorio | Qué hace |
|---|---|---|
| `data-chatbot-id` | **Sí** | Sin él el widget no arranca (`readConfig` devuelve `null`) |
| `data-widget-key` | Sí en una página pública | La credencial de sitio. Viaja en la cabecera `X-Widget-Key` |
| `data-api-url` | Sí si la página no está en el mismo origen que la API | Por omisión `/api/v1`, que sólo vale si comparten origen |
| `data-lang` | No | `es` por omisión |
| `data-model` | No | Sólo para el aviso del pie: lo declara la página, no el servidor |

## Lo que hay que entender de la credencial

**Es de SITIO y aparece en el HTML de quien publique la página.** Eso no es un descuido: es el
diseño. Por eso sólo abre chatbots `public_anon` y nada más — no da acceso al panel, ni a otros
chatbots, ni a datos de ninguna organización.

Dos consecuencias prácticas:

1. **Una credencial por sitio.** Si la misma clave está en dos sitios, revocar por abuso de uno
   apaga el otro.
2. **La que uses en local acaba dentro del HTML generado.** Emite una nueva para el bucket,
   genera el sitio con ella, y **revoca la de local**. Si no, publicas tu credencial de pruebas.

## Revocar y rotar

Las dos operaciones están en el panel del chatbot, y la diferencia importa:

- **Revocar** apaga la credencial ya. El widget de las páginas que la lleven deja de responder;
  las páginas siguen leyéndose, porque el asistente es un añadido y no el servicio principal.
- **Rotar** es emitir una nueva, regenerar y volver a subir el sitio con ella, y revocar la
  vieja **después** de comprobar que el sitio nuevo funciona. En ese orden: al revés hay un
  hueco en el que el widget está muerto en producción.

La clave se guarda **con hash**, así que no se puede volver a mostrar: si se pierde, se emite
otra. Es la misma razón por la que la rotación es «emitir, publicar, revocar» y no «recuperar».

## Si el widget no responde

En orden, porque el primero explica la mayoría de los casos:

1. **Origen no permitido.** La página y la API no comparten origen, así que el origen del sitio
   tiene que estar en `CORS_ALLOWED_ORIGINS`. En producción la política es cerrada, y un origen
   que falta se traduce en un *preflight* rechazado — **no** en un error visible en la página.
2. **Contenido mixto.** Si la página se sirve por HTTPS y `data-api-url` es `http://`, el
   navegador bloquea la llamada sin avisar en la interfaz. Mírala en la consola.
3. **Credencial revocada o de otro chatbot.** Responde 401/403; el widget no rompe la página.
4. **El chatbot no es `public_anon`.** La credencial de sitio no abre ningún otro tipo, a
   propósito.

**El widget nunca puede romper la lectura de la página.** Si el servidor no responde, se queda
sin abrir y la norma se sigue leyendo: es el requisito que D.6.1 pone por escrito, y la razón de
que el `<script>` vaya con `defer`.
