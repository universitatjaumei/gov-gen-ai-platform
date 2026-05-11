# Guía de pruebas E2E manuales — Chatbots Públicos

**Gov Gen AI Platform · Módulo 9B**

> Esta guía cubre los escenarios que **no se verifican automáticamente** en la suite de tests:
> comportamiento visual del widget, streaming en navegador real, integración end-to-end
> con base de datos y LLM reales.

---

## Requisitos previos

Antes de empezar, asegúrate de tener:

1. **Docker Desktop** en marcha (icono verde en la barra de tareas).
2. Servicios arrancados:
   ```
   docker compose up -d
   ```
3. Base de datos migrada:
   ```
   cd server
   uv run alembic upgrade head
   ```
4. Al menos un chatbot creado con documentos ingestados (ver sección A).
5. La API respondiendo:
   ```
   curl http://localhost:8000/health
   ```

---

## Sección A — Gestión de chatbots (panel admin)

### A.1 Crear un chatbot mínimo

1. Abre `http://localhost:5173/admin/chatbots`.
2. Haz clic en **Nuevo chatbot**.
3. Rellena:
   - Nombre: `Test RAG`
   - Cliente: (selecciona el cliente de desarrollo)
   - Modo de retrieval: `Vectorial RAG`
   - Modelo LLM: (selecciona el disponible)
4. Guarda.

**Qué debes ver:**
- El chatbot aparece en la lista con estado activo.
- No hay errores en consola del navegador.

### A.2 Editar configuración del grafo

1. Haz clic en el chatbot `Test RAG` → editar.
2. Cambia `quality_threshold` a `0.4` y `min_retrieval_results` a `1`.
3. Guarda.

**Qué debes ver:** Los valores persisten al reabrir el formulario.

### A.3 Cambiar modo de retrieval

1. Edita el chatbot → cambia a `Contexto largo`.
2. Guarda.
3. Vuelve a editarlo.

**Qué debes ver:** El modo seleccionado es `MD_LONG_CONTEXT`.

### A.4 Ver estadísticas de corpus

1. En la lista de chatbots, abre las estadísticas del chatbot (icono o botón `Corpus`).

**Qué debes ver:**
- Número de documentos, chunks y tokens estimados.
- Recomendación de modo de retrieval basada en el tamaño del corpus.
- Si no hay documentos: estadísticas a cero, sin error.

### A.5 Chatbot tipo router

1. Crea un chatbot `Router Test` con tipo `router`.
2. Asígna como hijo el chatbot `Test RAG`.
3. Comprueba que aparece en la lista de hijos.
4. Elimina el hijo.

**Qué debes ver:**
- El chatbot router muestra su lista de hijos.
- Añadir y quitar hijos funciona sin recarga completa.

### A.6 Eliminar chatbot

1. Elimina el chatbot `Router Test`.
2. Confirma el diálogo.

**Qué debes ver:** Desaparece de la lista. No hay chatbots huérfanos.

---

## Sección B — Ingestión de documentos

### B.1 Subida de PDF

1. Ve a `http://localhost:5173/admin/documents`.
2. Selecciona el chatbot `Test RAG`.
3. Sube un PDF de prueba (mínimo 2 páginas con texto).

**Qué debes ver:**
- Barra de progreso o indicador de ingestión.
- El documento aparece en la lista con estado `processed`.
- El número de chunks > 0 en estadísticas de corpus.

### B.2 Reingestión / regeneración de chunks

1. Desde la página de chatbots, pulsa **Regenerar chunks** en `Test RAG`.

**Qué debes ver:**
- Mensaje de confirmación.
- Los chunks se regeneran (el número puede variar si se cambiaron parámetros).

### B.3 Ingestión por URL (si hay fuentes configuradas)

1. Configura una fuente de ingestión con una URL pública estable.
2. Fuerza la ingestión manual (o espera al siguiente ciclo del scheduler).

**Qué debes ver:** El documento aparece con `source_kind = web`.

---

## Sección C — Widget de chat (escenarios principales)

> Para estos tests, embed el widget en una página HTML de prueba local.
> Plantilla mínima (ver apéndice al final de esta guía).

### C.1 Apertura y cierre del widget

1. Carga la página de prueba con el widget.
2. El widget debe abrirse automáticamente (estado inicial `open=true`).
3. Haz clic en el botón ✕.

**Qué debes ver:**
- El widget se colapsa a la burbuja flotante 💬.
- Al hacer clic en 💬 el widget se reabre con el historial conservado.

### C.2 Consulta básica

1. Escribe una pregunta relacionada con el contenido ingestado.
2. Pulsa **Enter** o el botón de envío.

**Qué debes ver:**
- El mensaje del usuario aparece en la conversación.
- Aparece un indicador de streaming ("Detectando idioma…", "Buscando en la base de conocimiento…", "Generando respuesta…").
- La respuesta del asistente se va dibujando token a token (streaming visible).
- Al completarse, el indicador de streaming desaparece.
- Debajo de la respuesta aparecen **píldoras de fuentes** con el título del documento y enlace.
- Aparecen las **estrellas de valoración** (1–5) debajo de la respuesta.

### C.3 Fuentes citadas

1. Haz clic en una píldora de fuente.

**Qué debes ver:** Abre el documento en una nueva pestaña (o 404 si la URL es de prueba).

### C.4 Pregunta sin respuesta (fallback)

1. Haz una pregunta completamente ajena al contenido ingestado (p. ej. "¿Cuál es la capital de Francia?").

**Qué debes ver:**
- El asistente responde con un mensaje de fallback (sin inventar información del corpus).
- No aparecen fuentes (o aparecen con score muy bajo).
- No se muestra warning de traducción.

### C.5 Múltiples turnos

1. Haz 3 preguntas consecutivas, esperando la respuesta de cada una antes de enviar la siguiente.

**Qué debes ver:**
- El historial de la conversación se conserva visible en el widget.
- Cada turno funciona de forma independiente (la valoración aparece tras cada respuesta del asistente).

### C.6 Envío durante streaming (botón deshabilitado)

1. Envía una pregunta.
2. Mientras el asistente está respondiendo, intenta enviar otra pregunta.

**Qué debes ver:**
- El campo de texto y el botón de envío están **deshabilitados** durante el streaming.
- No se envían mensajes duplicados.

### C.7 Enter y botón de envío

1. Escribe una pregunta y pulsa **Enter**.
2. Escribe otra y haz clic en el botón de envío.

**Qué debes ver:** Ambas formas de envío funcionan igual.

---

## Sección D — Idioma y traducción

### D.1 Consulta en el idioma del corpus

1. Si el corpus está en español, haz una pregunta en español.

**Qué debes ver:** Sin warning de traducción.

### D.2 Consulta en idioma diferente al corpus

1. Haz una pregunta en catalán si el corpus está en español.

**Qué debes ver:**
- Aparece el aviso de traducción en amarillo ("⚠️ La pregunta se detectó en catalán…").
- La respuesta puede estar en español (según la política de idioma configurada).

### D.3 Cambio de idioma vía postMessage

1. Desde la consola del navegador, ejecuta:
   ```javascript
   window.postMessage({ type: 'govgenai:setLang', lang: 'ca' }, '*')
   ```

**Qué debes ver:** El placeholder del campo de texto y los textos del widget cambian al catalán (si los textos i18n están traducidos).

---

## Sección E — Feedback

### E.1 Valoración con estrellas

1. Tras recibir una respuesta, haz clic en la estrella 4.

**Qué debes ver:**
- Las estrellas 1–4 se muestran rellenas (★), la 5 vacía (☆).
- Al recargar la página y consultar en el panel admin, la interacción tiene `feedback_score = 4`.

### E.2 Segunda valoración (no debería sobrescribir la UI)

1. Haz clic en la estrella 2 después de haber valorado con 4.

**Qué debes ver:**
- La valoración en UI cambia a 2 estrellas rellenas.
- En la BD se registra el último valor enviado.

---

## Sección F — Modos de retrieval

Para cada test, edita el chatbot para cambiar el modo antes de hacer la consulta.

### F.1 Modo RAG

1. Configura `retrieval_mode = RAG`, `retrieval_top_k = 5`.
2. Haz una consulta específica sobre un fragmento del corpus.

**Qué debes ver:** Respuesta precisa con 1–5 fuentes citadas.

### F.2 Modo MD_LONG_CONTEXT

1. Configura `retrieval_mode = MD_LONG_CONTEXT`.
2. Haz la misma consulta.

**Qué debes ver:**
- Respuesta posiblemente más completa (contexto global).
- Las fuentes citadas corresponden a documentos completos, no fragmentos.
- El streaming puede tardar más (el LLM procesa más tokens de entrada).

### F.3 Comparativa calidad de respuesta

1. Usa la misma pregunta en ambos modos y compara la calidad de la respuesta.

**Qué anotar:**
- ¿Cuál es más precisa?
- ¿Cuál es más rápida?
- ¿Las fuentes citadas son relevantes en ambos casos?

---

## Sección G — Casos límite y errores

### G.1 Mensaje vacío

1. Haz clic en enviar con el campo de texto vacío.

**Qué debes ver:** El botón está deshabilitado. No se envía nada.

### G.2 Chatbot sin documentos

1. Crea un chatbot nuevo sin ingestar ningún documento.
2. Haz una consulta.

**Qué debes ver:**
- Respuesta de fallback (no hay evidencias).
- Sin fuentes citadas.
- Sin error en la consola.

### G.3 Timeout / error de red (simulado)

1. Para el servidor con `docker compose stop server`.
2. Intenta enviar un mensaje desde el widget.

**Qué debes ver:**
- El widget muestra un estado de error o el streaming se detiene.
- No se queda en "cargando" indefinidamente.
- El campo de texto vuelve a ser editable.

### G.4 Pregunta muy larga

1. Pega un texto de más de 2000 caracteres en el campo de texto.

**Qué debes ver:**
- El mensaje se envía (el límite del backend es 10.000 caracteres).
- O el campo rechaza el input si el frontend tiene validación.

---

## Sección H — Panel admin: revisión de interacciones

1. Ve a `http://localhost:5173/admin` → sección de feedback/revisión.
2. Verifica que aparecen las interacciones realizadas en las pruebas anteriores.
3. Comprueba que las valoraciones de estrellas se muestran correctamente.

---

## Checklist de cierre

Antes de dar por válidas las pruebas, verifica:

- [ ] CRUD de chatbots funciona sin errores
- [ ] Ingestión de al menos un PDF completa correctamente
- [ ] El widget se abre, cierra y reabre conservando historial
- [ ] Streaming funciona (tokens visibles uno a uno)
- [ ] Fuentes citadas aparecen y son clicables
- [ ] Valoración de estrellas registra en BD
- [ ] Fallback activo cuando no hay evidencias suficientes
- [ ] Warning de traducción aparece solo cuando corresponde
- [ ] El botón de envío se deshabilita durante el streaming
- [ ] Sin errores 500 en los logs del servidor durante las pruebas

---

## Apéndice — Página HTML mínima para probar el widget

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Test Widget</title>
  <style>
    /* El widget ocupa todo el contenedor */
    #govgenai-widget {
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      width: 380px;
      height: 540px;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
      overflow: hidden;
    }
  </style>
</head>
<body>
  <h1>Página de prueba del widget</h1>
  <p>El widget aparece en la esquina inferior derecha.</p>

  <div
    id="govgenai-widget"
    data-chatbot-id="REEMPLAZA-CON-UUID-DEL-CHATBOT"
    data-api-url="http://localhost:8000/api/v1"
    data-lang="es"
  ></div>

  <!-- En desarrollo, apuntar al bundle generado por Vite -->
  <script type="module" src="http://localhost:5173/src/widget/main.tsx"></script>
</body>
</html>
```

> **Nota**: en producción, sustituye el `<script>` por el bundle compilado (`widget.js`)
> y el `data-api-url` por la URL real de la API.
