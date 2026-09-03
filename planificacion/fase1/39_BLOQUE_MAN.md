## Bloque MAN — Validación manual de la plataforma completa

**Añadido el 2026-08-03 a petición del usuario.** Hasta ahora las pruebas manuales se han hecho
**por bloque**, y han dejado **10 ficheros `.bat` sueltos** en la raíz. Ese modelo se ha quedado
corto por dos motivos:

1. **Varios de esos `.bat` han caducado sin que nadie lo note.** ROL renombró Partner→Admin y
   Client→Organización, CAL.2 retiró el panel de fuentes web, y CAL.3/CAL.4 rehicieron la
   pantalla de documentos y sus etiquetas. Un guion que dice «pulsa *Fuentes web*» ya no se
   puede seguir, pero sigue ahí, y quien lo ejecute concluirá que la aplicación está rota.
2. **Nadie ha probado nunca la plataforma de una pieza.** Cada campaña validó su bloque contra
   el estado de ese día; los caminos que cruzan módulos —Hub → Redacción → Automatización, o
   una organización con dos chatbots y temas distintos— no los ha recorrido nadie entero.

**Regla que no cambia** (CLAUDE.md §Verificación de UI): lo que el agente puede comprobar en
navegador **no entra** en estos guiones. Lo humano es lo irreducible: credenciales e IdP reales,
sistemas externos no simulables, juicio subjetivo de identidad visual, lector de pantalla real y
cualquier cosa con datos personales de verdad.

**Superficie a cubrir**: `server/app/modules/{agents_hub,automation,redaccion}`, el frontend
(`admin`, `redaccion`, `widget`, `themes`), el servidor MCP, el `client_app` como agente de
ejecución local, y los dos modos de despliegue (`DEPLOY_MODE=cloud|edge`).

---

### Prompt MAN.1 — Inventario, poda y matriz de lo irreducible

**Modelo sugerido**: **Sonnet** — trabajo de recorrido y criterio acotado, sin código nuevo.

```
# PROMPT MAN.1 — Qué exige humano, y qué de lo escrito ya no vale

## Acción
- Revisar los 10 pruebas_manuales_*.bat de la raíz contra el código de HOY. Para cada uno:
  vigente / caducado / parcialmente caducado, con el motivo concreto (qué prompt lo
  invalidó). Los caducados se BORRAN — el historial de git guarda lo que decían.
- Construir docs/PRUEBAS_MANUALES.md: matriz por módulo con, en cada fila, qué se prueba,
  por qué NO puede hacerlo el agente en navegador, y quién puede ejecutarlo (cualquiera /
  alguien con credenciales institucionales / alguien con lector de pantalla / diseño).
- Marcar explícitamente lo que NO va a la matriz por estar ya cubierto en navegador o por
  tests, para que no se repita por inercia.

## Cierre
- [ ] Cada .bat de la raíz o está justificado como vigente o ha desaparecido
- [ ] La matriz cubre agents_hub, automation, redaccion, widget, themes, MCP y client_app
- [ ] Cada fila dice por qué es irreducible; si no se sabe decir, no es irreducible
```

---

### Prompt MAN.2 — Campaña funcional en local (pre-deploy)

**Modelo sugerido**: **Sonnet** — redacción de guiones sobre la matriz de MAN.1.

```
# PROMPT MAN.2 — Recorrido completo de la plataforma sin GCP

## Acción
- Un pruebas_manuales_plataforma.bat maestro que encadene las áreas de la matriz y permita
  ejecutar sólo una (parámetro o menú): levantar, comprobar con curl que responde, y guiar.
- Guiones de los caminos que CRUZAN módulos, que son los que nadie ha recorrido enteros:
    · organización nueva -> dos chatbots -> temas distintos -> widget de cada uno
    · corpus ingerido -> consulta -> cita -> feedback -> el hueco aparece en curación
    · plantilla de redacción -> borrador LLM -> anonimización -> exportación
    · script propuesto -> sandbox -> aprobación -> ejecución en el agente local
- Cada paso con URL exacta, dato de ejemplo y resultado esperado. «Comprobar que
  funciona» no es un paso.

## Cierre
- [ ] El .bat en ANSI (cp1252) sin BOM — se escribe con WriteAllText, ver CLAUDE.md
- [ ] Primeros bytes 0x40 0x65 0x63 0x68 verificados
- [ ] Ejecutado de principio a fin por el usuario, con los fallos anotados como prompts
```

---

### Prompt MAN.3 — Accesibilidad con lector real e identidad visual

**Modelo sugerido**: **Sonnet** — guion de validación; el juicio lo pone el humano.

```
# PROMPT MAN.3 — Lo que no puede juzgar ni un test ni el agente

## Acción
- Guion de recorrido con lector de pantalla REAL (NVDA/JAWS) sobre los formularios del
  panel: chatbots, organizaciones, modelos LLM, documentos y prompts. Fase 20 dejó el gate
  de axe en CI, y CAL.4 asoció 29 <label> a su campo, pero axe no oye: que el foco siga un
  orden razonable y que cada campo se anuncie con su nombre sólo lo dice una persona.
- Guion de identidad visual institucional: tipografía, color, tono del texto y del widget
  embebido en una página real de la UJI.

## Cierre
- [ ] Cada hallazgo, o prompt nuevo o descarte razonado; nada queda en «lo miramos»
```

---

### Prompt MAN.4 — Campaña contra el entorno desplegado (POST-DEPLOY)

**Modelo sugerido**: **Sonnet** — depende de que D.5 haya terminado.

```
# PROMPT MAN.4 — Lo que sólo existe en producción

## Prerrequisito
- Deploy GCP completo (D.0-D.5). Antes de eso este prompt no se puede empezar.

## Acción
- SSO SAML real contra el IdP institucional: alta de usuario nuevo, organización asignada
  desde SAML_ORGANIZACION_ID, y el caso que nunca se ha probado — un usuario del IdP que
  NO debería tener acceso.
- Sistemas externos no simulables en local (G400, ENI, APIs UJI).
- Cloud Run de verdad: cold start medido, Cloud SQL vía proxy, ficheros en GCS a través
  del StorageService.
- Modo edge contra modo cloud: que la frontera de datos aguanta donde se dijo.

## Cierre
- [ ] El cold start medido se compara con el criterio de extracción a microservicio
      (>15 s -> toca extraer embedding/Docling; ver CLAUDE.md)
- [ ] Ningún dato de cliente real sale del edge en modo edge
```

---

## Prompt suelto FIX.1 — El modelo de un chatbot no se puede cambiar (PENDIENTE)

> **Contexto**: encontrado el 2026-08-02 durante las pruebas manuales del Bloque RAG, que el
> usuario no pudo completar. Un solo síntoma —«el botón de ejecutar no hace nada»— tapaba
> cuatro fallos distintos, y ninguno era el que parecía.
>
> **Lo que estaba pasando de verdad**:
>
> 1. **`gemini-2.0-flash` está retirado.** Google devuelve `404 NOT_FOUND: "This model
>    models/gemini-2.0-flash is no longer available"`. El chatbot demo lo tenía asignado.
> 2. **El fallo era invisible.** `POST …/run` devuelve **500** cuando el modelo no responde y
>    `TestScenariosPage` lanza la mutación **sin `onError`**: el botón se comporta igual que si
>    no lo hubieras pulsado. Y en el chatbot demo el 500 ni siquiera aparecía, porque sin
>    corpus el grafo corta antes de llamar al LLM y devuelve el fallback — o sea que el modelo
>    roto quedaba tapado por un corpus vacío.
> 3. **No hay forma de cambiar el modelo.** El formulario **hardcodea**
>    `llm_config_id: DEV_LLM_ID` (y `organizacion_id: DEV_ORG_ID`), y `ChatbotUpdate` **ni
>    siquiera declara `llm_config_id`**: no es un hueco de UI, es que la API no lo permite.
>    Hubo que repuntar el chatbot por SQL.
> 4. **Marcar una configuración por defecto exige un baile de dos pasos** que la API no
>    documenta: responde 409 «ya existe una por defecto para el tier N» en vez de demotar la
>    anterior. En la BD de desarrollo habían quedado **dos configuraciones tier 1 por
>    defecto** a la vez.
>
> **El riesgo latente, que es el peor de los cuatro**: mientras el formulario hardcodee
> `llm_config_id`, **editar cualquier chatbot en la UI le reasigna el modelo en silencio**.
> El «Chatbot de Ejemplo» usa Ollama a propósito y una edición inocente lo pasaría a Gemini.
>
> **Relación con CAL.2 y con las reglas maestras**: `DEV_LLM_ID`/`DEV_ORG_ID` son exactamente
> lo que CLAUDE.md prohíbe —lógica y datos hardcodeados en React que no vienen del contrato—.
> No se espera a CAL.2 porque esto bloquea las pruebas manuales hoy.

---

### Prompt FIX.1 (RED/GREEN) — Elegir el modelo, y ver el error cuando falla

**Modelo sugerido**: **Sonnet** — cuatro arreglos acotados, todos con causa ya diagnosticada.

```
# PROMPT FIX.1 (RED/GREEN) — Que el modelo se pueda cambiar y que los fallos se vean
# Deploy: cloud (chatbots y configuración de LLM son configuración)

## 1. BACKEND — `llm_config_id` entra en ChatbotUpdate
- `ChatbotUpdate` gana `llm_config_id: uuid.UUID | None`.
- Se VALIDA que la configuración existe: 404 con mensaje, no un IntegrityError de la FK a
  mitad de la petición.
- El resto del handler ya aplica `payload` con setattr, así que no hay más que tocar.

## 2. BACKEND — marcar por defecto demota a la anterior
Hoy `is_default=True` responde 409 si ya hay otra del mismo tier. Eso convierte «quiero que
esta sea la de por defecto» en dos peticiones y un hueco: entre la una y la otra no hay
ninguna. Pasa a ser una sola operación: se demota la anterior del mismo tier y se promueve
esta, en la MISMA transacción. Vale para POST y para PATCH.
NOTA: el 409 de BORRAR una configuración en uso se queda como está — ahí sí hay que decidir
qué pasa con los chatbots que la usan, y eso no es este prompt.

## 3. FRONTEND — selector de modelo, y fuera los identificadores hardcodeados
- El formulario de chatbot lista las configuraciones (`GET /hub/llm-configs`) y deja elegir.
- Al EDITAR, el desplegable arranca en la configuración actual del chatbot, no en una
  constante. Esto es lo que cierra el riesgo de reasignar el modelo en silencio.
- `DEV_LLM_ID` y `DEV_ORG_ID` desaparecen del fichero. La organización se elige de
  `GET /hub/organizaciones` al crear; al editar no se toca (ChatbotUpdate no la admite).

## 4. FRONTEND — los errores se ven
- Ejecutar un escenario muestra el error si la mutación falla, con `role="alert"`.
- Mismo tratamiento para crear y borrar: si el backend dice que no, se dice.

## 5. FRONTEND — editar un escenario
El `PATCH` existe desde RAG.13 y no lo usa nadie. Botón de editar que reutiliza el mismo
formulario de crear, prellenado.

## TESTS (RED primero)
# backend  tests/api/test_chatbot_llm_config.py
#   should_change_the_model_of_an_existing_chatbot
#   should_reject_an_unknown_llm_config_with_404
#   should_not_touch_the_model_when_the_field_is_absent      (el riesgo de la reasignación muda)
#   should_promote_to_default_demoting_the_previous_one
#   should_leave_exactly_one_default_per_tier
# frontend src/admin/__tests__/ChatbotModelSelector.test.tsx
#   should_list_available_llm_configs_in_the_form
#   should_preselect_the_current_config_when_editing
#   should_not_send_a_hardcoded_llm_config_id
# frontend src/admin/__tests__/TestScenariosPage.test.tsx  (amplía el existente)
#   should_show_an_error_when_the_run_fails
#   should_edit_an_existing_scenario

## CRITERIO DE DONE
- [ ] `grep -rn "DEV_LLM_ID\|DEV_ORG_ID" frontend/src` = 0
- [ ] Contrato OpenAPI + Orval regenerados; `tsc` limpio
- [ ] Suite backend y frontend sin regresiones
- [ ] Verificación en navegador por el agente si la extensión lo permite; si no, se dice
- [ ] Sin migración
```

---
