# Personalización CSS del widget — Qué necesitas facilitar

**Gov Gen AI Platform · Widget de chatbot público**

---

## Estado actual del widget

El widget actual usa **estilos inline mínimos** para garantizar que funciona en cualquier
entorno sin conflictos con el CSS del portal anfitrión. Las únicas variables CSS expuestas
son las de las píldoras de fuentes y la posición de la burbuja flotante.

Para que el widget se integre visualmente con la identidad de la institución, se necesita
una hoja de estilo externa que redefina esas variables y añada las propias del layout.

---

## Qué necesitas facilitarme

### 1. Paleta de colores de la institución

| Elemento | Lo que necesito | Ejemplo |
|---|---|---|
| Color primario (botones, acciones) | Hex o RGB | `#005ea2` |
| Color primario hover | Hex | `#004f87` |
| Color de fondo de la ventana del chat | Hex | `#ffffff` |
| Color de fondo del header | Hex | `#005ea2` |
| Color del texto del header | Hex | `#ffffff` |
| Color de fondo de la burbuja flotante (botón 💬) | Hex | `#005ea2` |
| Color de fondo de mensajes del **usuario** | Hex | `#dbeafe` |
| Color del texto de mensajes del usuario | Hex | `#1e3a5f` |
| Color de fondo de mensajes del **asistente** | Hex | `#f1f5f9` |
| Color del texto de mensajes del asistente | Hex | `#1e293b` |
| Color de fondo de la barra de aviso (traducción) | Hex | `#fef3c7` |
| Color del texto del aviso de traducción | Hex | `#92400e` |
| Color activo de las estrellas de valoración | Hex | `#f59e0b` |

### 2. Tipografía

| Elemento | Lo que necesito | Ejemplo |
|---|---|---|
| Familia de fuentes | Nombre CSS o URL Google Fonts | `'Inter', sans-serif` |
| Tamaño base de texto | px o rem | `14px` |
| Tamaño del texto del placeholder | px o rem | `13px` |
| Peso del texto del asistente | normal / bold | `normal` |

### 3. Dimensiones del widget

| Elemento | Lo que necesito | Ejemplo |
|---|---|---|
| Ancho del panel de chat | px o % | `380px` |
| Alto del panel de chat | px o vh | `540px` |
| Radio de borde del panel | px | `12px` |
| Radio de borde de las burbujas de mensaje | px | `8px` |
| Posición inferior de la burbuja flotante | rem o px | `1.5rem` |
| Posición derecha de la burbuja flotante | rem o px | `1.5rem` |

### 4. Logotipo o icono de cabecera (opcional)

- Archivo SVG o PNG del logotipo institucional (máx. 120 × 40 px recomendado).
- O simplemente el nombre corto que aparecerá en el header del chat ("Asistente UJI", "InfoBot", etc.).

### 5. Textos de la interfaz (i18n)

El widget usa ficheros de traducción `i18next`. Si quieres personalizar los textos
(en lugar de los genéricos en español), necesito:

| Clave | Texto por defecto | Tu texto |
|---|---|---|
| `chat.placeholder` | "Escribe tu pregunta…" | |
| `chat.send` | "Enviar" | |
| `chat.widget_open` | "Abrir asistente" | |
| `chat.widget_close` | "Cerrar asistente" | |
| `chat.widget_loading` | "Cargando respuesta…" | |
| `chat.sources` | "Fuentes" | |
| `chat.feedback_rate` | "Valora esta respuesta" | |
| `chat.feedback_stars` | "estrellas" | |
| Nombre del asistente en el header | "Asistente" | |

### 6. Idiomas activos

- [ ] Español (`es`) — siempre
- [ ] Valenciano/Catalán (`val`)
- [ ] Inglés (`en`)
- [ ] Otro: ___________

---

## Resultado: lo que generaré con esa información

Con los datos anteriores generaré:

1. **Un archivo CSS** (`widget-theme-<institucion>.css`) con todas las variables CSS
   definidas y las clases de los elementos principales del widget:

   ```css
   :root {
     /* Colores */
     --widget-primary:          #005ea2;
     --widget-primary-hover:    #004f87;
     --widget-bg:               #ffffff;
     --widget-header-bg:        #005ea2;
     --widget-header-fg:        #ffffff;
     /* Mensajes */
     --msg-user-bg:             #dbeafe;
     --msg-user-fg:             #1e3a5f;
     --msg-assistant-bg:        #f1f5f9;
     --msg-assistant-fg:        #1e293b;
     /* Fuentes */
     --source-pill-bg:          #e0f2fe;
     --source-pill-fg:          #0369a1;
     --source-pill-border:      #7dd3fc;
     /* Layout */
     --widget-width:            380px;
     --widget-height:           540px;
     --widget-border-radius:    12px;
     --widget-bottom:           1.5rem;
     --widget-right:            1.5rem;
     /* Tipografía */
     --widget-font:             'Inter', sans-serif;
     --widget-font-size:        14px;
   }
   ```

2. **Los ficheros de traducción i18n** actualizados con los textos de la institución.

3. **Una página HTML de demostración** con el widget integrado y estilizado,
   lista para validar visualmente antes del despliegue en el portal real.

---

## Lo que NO necesitas proporcionar

- Código React ni JavaScript. El widget ya existe y funciona.
- Diseño de la arquitectura del chat (ya está implementada).
- Lógica de negocio. Solo los valores de diseño visual listados arriba.

---

## Preguntas frecuentes

**¿Puedo usar los colores del logo institucional directamente?**
Sí. Si me facilitas el logo en SVG, puedo extraer la paleta automáticamente.

**¿El widget puede adaptarse a modo oscuro?**
Sí, con una segunda hoja `@media (prefers-color-scheme: dark)` que redefine las
variables. Indícame si lo necesitas.

**¿El widget puede estar en una posición diferente (esquina izquierda, centrado)?**
Sí, con `--widget-bottom`, `--widget-right` y `--widget-left`. Indícame la
posición deseada.

**¿Puede el widget ocupar toda la pantalla en móvil?**
Sí, con media queries. Es parte del tema. Dime si el portal tiene tráfico móvil
relevante y lo incluyo en la plantilla.

**¿Puede embeberse en un iframe en lugar de directamente?**
Sí. En ese caso el HTML de prueba del apéndice de la guía E2E es la plantilla
del iframe. Solo necesito las dimensiones del iframe en el portal anfitrión.
