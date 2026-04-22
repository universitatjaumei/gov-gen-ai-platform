# Módulo: RPA Navegador Web (Playwright AutomatIA)

La herramienta de Automatización de Procesadores Robóticos (RPA) de AutomatIA permite teledirigir un navegador web en segundo plano sin instalar plugins locales (Playwright). Es un tipo de **Procesador** pensado para rellenar formularios en AFIP o Seguridad Social, recoger pantallazos o hacer scrapping.

## Funcionamiento

El usuario crea pasos iterativos:
- Go To `https://...` (Navegar a url)
- Click `button id=login` (Interactuar)
- Type `fabra` en el selector `#user_input` (Simular tecleo)
- Take Screenshot (Saca una foto invisible)
- Wait (Pausas explícitas)
- Extract text de `.noticia-titulo`

## Comportamiento del Copiloto (IA)

En este panel, el usuario seguramente necesite ayuda a la hora de identificar o apuntar de forma certera a un elemento HTML usando "Selectores CSS y XPath robustos".
Ayúdalo resolviendo dudas cómo "Si tengo una tabla donde quiero hacer clic siempre en el último elemento de la columna de estado, ¿qué selector XPath necesito usar?"
*(Toda configuración se tiene que seguir haciendo a través de la UI manual de momento).*

<help_config>
### Cómo configurar
1. Define la **URL inicial** desde la que el robot debe partir.
2. Ve añadiendo pasos de ejecución (clicks, rellenar campos con `type`, tomar capturas, extraer texto).
3. Utiliza los selectores web (CSS o XPath) para indicar al bot exactamente en qué elemento HTML de la página debe interactuar.
</help_config>

<help_example>
### Ejemplo de Inicio de Sesión
Podrías configurar algo como esto:
1. `Go To`: https://intranet.empresa.com
2. `Type`: Selector `#username`, Valor `{{credenciales.usuario}}`
3. `Type`: Selector `#password`, Valor `{{credenciales.pass}}`
4. `Click`: Selector `.btn-submit`
5. `Screenshot`: Esto tomará una captura evidenciando el log in.
</help_example>
