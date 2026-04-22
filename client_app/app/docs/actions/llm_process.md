# Módulo: LLM Processing (Procesamiento de Lenguaje Genérico)

Este **Procesador** permite a los usuarios incrustar Modelos de Lenguaje (LLMs locales o remotos que funcionen a través de APIs compatibles o frameworks on-premises) en medio de los flujos automáticos (Workflows) de AutomatIA para que procesen un texto que ha venido de pasos anteriores.

## Casos de Uso del LLM Processor
- **Clasificador (Triage)**: Recibir un correo o incidencia (`{{email_watcher.body}}`) y determinar si pertenece al departamento "Técnico" o de "Ventas".
- **Resumen**: Obtener textos largos escaneados de PDFs o noticias del WebWatcher y devolver un "bullet point list" de la noticia resumida a 140 caracteres.
- **Detector de sentimiento**: Revisar reseñas y catalogarlas como Positivas o Negativas (etiquetado).

## Funcionamiento Manual

El usuario dispone de una gran caja de configuración que le solicita rellenar la instrucción de sistema ("Eres un analista experto en recursos humanos") y el Prompt a enviar con las variables inyectadas (ej. "Resume el siguiente texto en 5 líneas. Extrae la esencia \n\n {{extraction_resultados.texto_puro}}"). También debe indicar cuantas variables de Output desea mapear.

## Comportamiento del Copiloto (IA)

Aquí brillas. Como IA, tu misión es ayudar al usuario del software a escribir un "Prompt Perfecto y robusto" para el propio nodo LLM que el usuario incorporará a su automatización de producción.
Un usuario preguntará: "¿Cómo monto un prompt para que el LLM del proceso no alucine (invente cosas) al intentar clasificar facturas en tres categorias?".
Sugiérele que utilice técnicas del tipo "Few-Shot Prompting" proporcionándole una plantilla de ejemplo de ese prompt exacto.
*(Aviso: Puedes preparar sugerencias de prompt y botones para inyectarlo en la caja de texto temporal del usuario desde tu servicio utilizando la UI pero NO puedes auto-completar el panel lateral izquierdo)*

<help_config>
### Cómo configurar
1. **Datos de Entrada**: Conecta al nodo el texto o variable que deseas que analice la Inteligencia Artificial.
2. **Sistema (Rol)**: Opcionalmente, dale un rol al LLM (ej. "Eres un traductor experto a inglés").
3. **Instrucción (Prompt)**: Escribe exactamente qué debe hacer (ej. "Resume en 3 líneas el siguiente texto: `{{texto_entrada}}`").
4. **Salida**: Escoge si esperas un texto libre, un JSON estructurado o una clasificación específica.
</help_config>

<help_example>
### Ejemplo de Resumidor de Emails
Si tienes un flujo que lee correos, puedes pasar el asunto y cuerpo al LLM Process con el prompt:
`Extrae la queja principal de este email y categorízala como [URGENTE, NORMAL, BAJA]: {{email.body}}`

El NLP te devolverá en su variable de salida únicamente la categoría detectada, que luego puedes usar en un nodo de condición IF/THEN para avisar al soporte o ignorarlo.
</help_example>
