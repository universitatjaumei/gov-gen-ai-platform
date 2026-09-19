# Guía de uso: qué hace cada quien con la plataforma

> **Clase: referencia viva.** Escrita el 2026-09-19. Describe cómo se usa la plataforma **ya
> instalada y arrancada**: qué hace un superadministrador el primer día, y cómo se llega desde
> ahí a un asistente publicado, un informe aprobado o un portal curado.
>
> **Esto no es la instalación.** Para levantarla en local, «Arrancar en local» del `README` de la
> raíz. Para el despliegue del prototipo,
> [`DESPLIEGUE_PROTOTIPO_GCP.md`](DESPLIEGUE_PROTOTIPO_GCP.md).
>
> **Esto tampoco es la especificación.** Aquí está el recorrido; lo que el sistema **garantiza**,
> capacidad por capacidad, está en [`ESPECIFICACIONES.md`](ESPECIFICACIONES.md).

---

## 1. Lo primero: quién puede hacer qué

Dos cosas distintas deciden si alguien ve una pantalla, y confundirlas es la causa más habitual
de «tengo el rol y no me deja»:

- **El rol** dice qué clase de persona eres.
- **El módulo concedido** dice a qué partes de la instalación entras. Es una **unidad de
  licencia**: una organización puede tener contratados Chatbots e Informes y no Curación.

| Rol | Qué le corresponde |
|---|---|
| `superadmin` | La plataforma entera: organizaciones, proveedores y modelos de LLM, módulos, tokens. Entra en todos los módulos **sin concesión explícita** —si dependiera de una fila, una instalación recién creada dejaría a su administrador encerrado fuera—. |
| `admin` | Crea y configura los asistentes, informes y portales de **sus** organizaciones. |
| `informer` | Supervisa y valida lo que responde la IA. |
| `user` | Usa los asistentes y trabaja los informes. |

Los seis módulos: `chatbots`, `curacion`, `informes`, `personas`, `registro`, `plataforma`.

`personas` está separado de `plataforma` a propósito: administrar a la gente de tu organización
no es administrar la plataforma, y meterlo ahí obligaba a dar los modelos de LLM y los tokens
para poder dar lo primero. Con `registro` pasa lo mismo.

**Al entrar, la aplicación aterriza en el primer módulo concedido**, no en una pantalla fija.
Quien sólo hace informes entra en informes.

---

## 2. El primer día: lo que hace el superadministrador

La instalación recién sembrada trae **una organización de ejemplo, un chatbot de ejemplo y sus
prompts de bienvenida** en castellano, catalán e inglés. Sirve para comprobar que todo responde;
no sirve como punto de partida de nada real.

### 2.1 Dar de alta la organización

`/plataforma/organizaciones`. Una organización es el eje sobre el que se acota todo lo demás: un
asistente, un portal curado o un informe pertenecen siempre a una.

Si la instalación va a servir a varias —el caso de una diputación con sus municipios—, se crean
todas aquí. **No se ven entre ellas**, y eso no es una opción de configuración: es cómo está
construido el acceso a datos ([`MULTITENENCIA.md`](MULTITENENCIA.md)).

### 2.2 Conectar un proveedor de modelos

`/plataforma/modelos`. Dos pasos que conviene no mezclar:

1. **La credencial del proveedor.** Se guarda **por referencia, no por valor**: lo que se declara
   es *dónde* está el secreto —el nombre de una variable de entorno, o las credenciales por
   defecto de la nube—, nunca el secreto en sí. Así un volcado de la base de datos deja de ser
   sensible.
2. **Las configuraciones de modelo**, que son las que usa el sistema. Cada una declara su
   **propósito** y su **nivel**.

**El nivel es un papel, no un modelo.** Dos niveles pueden apuntar al mismo modelo; lo que cambia
es para qué se usa. Qué actividad consume cada nivel:
[`NIVELES_DE_MODELO.md`](NIVELES_DE_MODELO.md).

Hay un propósito aparte, `embedding`, que decide con qué se vectoriza el corpus. Sin ninguna fila
de ese propósito, el sistema usa el modelo local. **Cambiarlo no es inocuo**: el corpus ya
indexado quedaría en un espacio vectorial distinto del de las preguntas, y eso no da error, da
respuestas malas. Por eso hay un guardarraíl que lo impide y obliga a reindexar a propósito.

### 2.3 Conceder módulos

`/plataforma/modulos`. Sin concesión no hay acceso, para cualquier rol que no sea
`superadmin`. Es aquí donde se decide qué tiene contratado cada organización.

### 2.4 Dar de alta a las personas

`/personas`. Alta manual, con contraseña local, mientras el SSO institucional no esté conectado.
Cuando lo esté, las personas llegan del IdP y esta pantalla pasa a ser el sitio donde se revisa
lo que el IdP declara.

Se puede crear, editar, cambiar la contraseña y dar de baja. La pantalla no deja quedarse sin
ningún superadministrador activo: es la comprobación que evita cerrar la puerta desde dentro.

### 2.5 Identidad visual y tokens

`/plataforma/identidad-visual` aplica la cascada **Plataforma → Organización → Chatbot**: lo que
se fija arriba se hereda abajo, y cada nivel puede cambiar **campos sueltos** sin repetir la
configuración entera. Un valor vacío y un valor sin poner significan cosas distintas: sin poner
es «hereda», vacío es «lo quiero vacío».

`/plataforma/tokens` emite **tokens de acceso personal** revocables, con *scopes*. Son lo que
consumen las integraciones máquina, incluido el servidor MCP
([`MCP_SERVER.md`](MCP_SERVER.md)). No son la credencial del widget público, que es otra cosa
(§3.5).

---

## 3. Chatbots: de cero a un asistente publicado

Módulo `chatbots`, rutas bajo `/hub`.

### 3.1 Crear el asistente

`/hub/chatbots`. Lo que hay que decidir al crearlo: a qué organización pertenece, qué
configuración de modelo usa, su *system prompt*, y su **modo de recuperación**.

Dos modos en uso:

- **`RAG`** — búsqueda híbrida (vectorial + texto completo) sobre los fragmentos del corpus. Es
  el modo por defecto y el adecuado para un corpus grande.
- **`MD_AGENT_SELECTOR`** — el modelo lee documentos enteros con *tools*. Sirve cuando el corpus
  es pequeño y la granularidad de documento importa más que la de fragmento.

Los perfiles de grafo público y qué hace cada uno: [`GRAPH_PROFILES.md`](GRAPH_PROFILES.md).

`/hub/valores-por-defecto` fija lo que heredan los asistentes nuevos, para no repetir la misma
configuración en cada uno.

### 3.2 Cargar el corpus

`/hub/documents`. **Al corpus sólo entra Markdown conforme al contrato**
([`CONTRATO_MD_CORPUS.md`](CONTRATO_MD_CORPUS.md)). Un PDF devuelve **415** y dice a dónde ir.

No es una limitación técnica sino la frontera del diseño: lo que sale de convertir un PDF no
tiene *front-matter*, ni anclas de artículo, ni estado de vigencia, o sea que es contenido que el
asistente no puede citar como norma, entrando por la misma puerta que el corpus curado y
quedando indistinguible de él. La conversión vive en el pipeline de curación (§5), que es donde
está el OCR y donde se declara lo que se ha transcrito automáticamente.

Cada documento declara su procedencia —URL de origen, idioma, vigencia— y eso es lo que permite
que la respuesta cite el artículo exacto y avise cuando una norma ha sido desplazada.

Si hay que cargar el vocabulario de ámbitos y submaterias:
[`CARGA_VOCABULARIO.md`](CARGA_VOCABULARIO.md). Si hay que reingerir todo:
[`RUNBOOK_REINGESTA.md`](RUNBOOK_REINGESTA.md).

### 3.3 Ajustar los prompts

`/hub/prompts`. Las plantillas cuelgan del chatbot, están versionadas y van por idioma.

### 3.4 Probarlo antes de enseñarlo

Dos pantallas, y hacen cosas distintas:

- `/hub/test-scenarios` — escenarios de prueba guardados: preguntas con lo que debería
  contestarse. Sirven para ver si un cambio de configuración mejora o empeora, en vez de
  juzgarlo por una pregunta suelta.
- `/hub/revision` — revisión de las interacciones reales, con su valoración. Es donde se ve qué
  está contestando de verdad.

**Lo que más cuesta afinar no es que recupere, es que calle.** Está medido: los escenarios bien
anotados recuperan la norma correcta, y el hueco es declinar cuando no hay fundamento. Subir el
umbral de calidad no lo arregla. Si el asistente contesta cosas que no debería, el camino es la
revisión humana de respuestas, no el número.

### 3.5 Publicarlo

`/hub/chatbots`, en el propio asistente, se emite una **credencial de sitio** para el widget. Es
distinta de un token personal: **aparece en el HTML de quien publique la página**, y eso es el
diseño, no un descuido —por eso sólo abre chatbots públicos anónimos y nada más—.

Dos consecuencias prácticas: **una credencial por sitio** (si la misma está en dos, revocar por
abuso de uno apaga el otro), y **la que uses en local acaba dentro del HTML generado**, así que
emite una nueva para publicar y revoca la de pruebas.

El fragmento a pegar, los atributos y cómo se revoca:
[`WIDGET_INCRUSTACION.md`](WIDGET_INCRUSTACION.md). Plantilla de estilos y página de
demostración: [`chatbots-publicos/`](chatbots-publicos/).

### 3.6 Mantenerlo vivo

`/hub/vigencia` es la cola de documentos cuya vigencia toca comprobar. Se puede **tachar**: queda
constancia de que una persona lo revisó y cuándo. Una cola que no se puede tachar deja de
mirarse.

---

## 4. Informes: de una plantilla a un documento aprobado

Módulo `informes`, rutas bajo `/redaccion`. El contrato completo está en
[`REDACCION_CONTRACT_FIRST.md`](REDACCION_CONTRACT_FIRST.md); el caso guía que originó las dos
reglas duras del módulo, en [`CASO_INFORME_SEGUIMIENTO.md`](CASO_INFORME_SEGUIMIENTO.md).

### 4.1 La plantilla

`/redaccion/builder`. Una plantilla define los bloques del informe: texto, tablas, gráficos,
transformaciones de datos. Está **versionada**, y un informe se crea siempre a partir de una
versión concreta: así un cambio de plantilla no altera retroactivamente lo ya redactado.

### 4.2 El informe

`/redaccion/wizard` lista las plantillas disponibles y crea un **espacio de trabajo** a partir de
la que elijas; de ahí se entra en `/redaccion/workspaces/{id}`, que es donde se trabaja: se
suben los documentos de origen, se ejecutan los bloques y se revisa lo que sale.

La regla que ordena todo el módulo: **los números los produce código determinista; lo que escribe
el modelo es la valoración**, y va sujeta a aprobación humana antes de exportar. Un dato de un
informe institucional no sale de un modelo de lenguaje.

`/redaccion/workspaces/{id}/preview` es la vista de impresión, sin navegación.

### 4.3 Cuando hace falta calcular algo que no está

Tres caminos, en este orden:

1. **El catálogo de funciones** — `/redaccion/funciones`. Funciones deterministas, versionadas y
   compartidas entre organizaciones. Antes de escribir código, mirar si ya existe.
   [`CATALOGO_FUNCIONES.md`](CATALOGO_FUNCIONES.md).
2. **Proponer una función o un script** — `/redaccion/scripts/wizard`. El código se **audita
   automáticamente** (auditoría estática graduada: aceptable, advertencia, crítico, con número de
   línea) y se prueba en un **sandbox sin red**. El filtro es automático, no una aprobación
   previa de nadie.
3. **La revisión posterior** — `/redaccion/funciones/revision` y
   `/redaccion/scripts/review`. Es donde entra la persona: puede pedir correcciones,
   reclasificar o suspender una función ya publicada.

Por qué la persona entra **después** y no antes: la Instrucció 02/2026 prohíbe la aprobación
previa como condición para compartir dentro del servicio. La única aprobación previa que queda es
el paso al nivel 3. El aislamiento del sandbox, capa por capa:
[`SANDBOX_SECURITY.md`](SANDBOX_SECURITY.md).

### 4.4 Datos personales

La anonimización es **selectiva y por políticas**, no automática en todo. En informes y espacios
de trabajo hay NER reversible: se anonimiza antes de que el texto llegue al modelo y se
restituye después. El chatbot público no la lleva porque no recibe datos personales por diseño.

---

## 5. Curación: del portal al corpus

Módulo `curacion`, rutas bajo `/curation`. Es **previa** al asistente y vale por sí sola: el
entregable principal es el informe de auditoría del portal, tenga o no un chatbot detrás.

| Pantalla | Qué se hace |
|---|---|
| `/curation/sites` | Dar de alta el portal y sus **apartados**, que son parametrizables y tienen cadencia propia |
| `/curation/audit` | Lanzar y seguir el rastreo |
| `/curation/findings` | Los hallazgos: contenido caducado, contradictorio, insuficiente, con revisión vencida |
| `/curation/publish` | Decidir qué se publica y qué entra al corpus |

**No hay ingesta automática de web a corpus**, y es deliberado: una página nueva es una señal
para quien cura, no un disparador. Quien decide qué entra es una persona.

El rastreo es cortés por construcción —pausa por *host*, `robots.txt` leído una vez por hora— y
el servidor **sólo pide direcciones de la red pública**, comprobado en cada salto y también a
través de redirecciones.

Recorrido completo y real: [`CASO_CURACION_ESCOLA_DOCTORAT.md`](CASO_CURACION_ESCOLA_DOCTORAT.md).
Con varias organizaciones: [`CURACION_MULTIORGANIZACION.md`](CURACION_MULTIORGANIZACION.md).
Los apartados dinámicos y su ciclo de vida: [`SECCIONES_DINAMICAS.md`](SECCIONES_DINAMICAS.md).
Cómo probarlo sin salir a internet:
[`../pruebas_manuales/`](../pruebas_manuales/) y el guion del bloque de curación.

---

## 6. Registro de actividad IA

Módulo `registro`, ruta `/registro`. No es para las respuestas de esta plataforma —ésas se
registran solas— sino para que **otras herramientas de la institución declaren que han usado IA**
y quede constancia en un sitio único.

Se registran **metadatos, no *payloads***: qué sistema, qué categoría de actividad, cuándo, con
qué modelo y con qué supervisión. El catálogo de categorías se anuncia, no se impone.
[`REGISTRO_ACTIVIDAD_IA.md`](REGISTRO_ACTIVIDAD_IA.md).

Junto a él hay **verificaciones como servicio**: comprobar citas, vigencia o auditoría estática
de código desde una aplicación de fuera, por API y con *scope* propio. El inventario de qué
comprueba y registra la plataforma, y qué de ello es accesible desde fuera:
[`GOVERNANCA_PER_API.md`](GOVERNANCA_PER_API.md).

---

## 7. Lo que la plataforma no hace, y conviene saber antes

- **No ejecuta nada en la máquina de quien la usa.** No hay agente de escritorio, ni vigilancia
  de carpetas, correo o web, ni programador de flujos locales. La automatización de procesos y el
  gestor de expedientes están previstos y **no tienen código**.
- **No convierte documentos para el corpus.** Eso es el pipeline de curación, y lo que llega al
  corpus es su salida.
- **No decide por una persona.** Ni qué entra al corpus, ni si una valoración es correcta, ni si
  una función sigue sirviendo.
- **No gobierna la IA de la institución.** El inventario de casos de uso, el registro de sistemas
  y la asignación de responsabilidades se gestionan fuera. Dónde acaba su alcance, y por qué esa
  separación es deliberada: [`MARCO_GOBERNANZA_IA.md`](MARCO_GOBERNANZA_IA.md).

La lista completa y razonada está en `ESPECIFICACIONES.md` §10.

---

## 8. Dónde seguir leyendo

| Si quieres | Lee |
|---|---|
| Saber qué garantiza el sistema y dónde se hace cumplir | [`ESPECIFICACIONES.md`](ESPECIFICACIONES.md) |
| Entender cómo está construido y por qué | [`Arquitectura.md`](Arquitectura.md) |
| Presentar el proyecto a alguien de fuera | [`PRESENTACION_PROYECTO.md`](PRESENTACION_PROYECTO.md) |
| Depurar por qué un asistente contestó lo que contestó | [`DEPURAR_CONTEXTO_RAG.md`](DEPURAR_CONTEXTO_RAG.md) |
| Saber qué se prueba a mano y qué no | [`PRUEBAS_MANUALES.md`](PRUEBAS_MANUALES.md) |
| Contribuir código | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
