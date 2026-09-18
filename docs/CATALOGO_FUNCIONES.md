# El catálogo de funciones

Una **función** es código determinista con su contrato declarado, versionado, y compartido dentro
de la plataforma. Sirve para que una extracción de datos —contar las filas de un fichero de
gastos, leer los importes de un PDF de facturas, calcular un indicador— se escriba **una vez** y
la usen todas las plantillas de informe que la necesiten.

Antes del bloque FUN, el código aprobado de un script se **copiaba incrustado** en el bloque de
cada plantilla. Dos plantillas que necesitaran la misma extracción eran dos propuestas, dos
aprobaciones y dos copias; y un error en un script usado por N plantillas se arreglaba N veces. El
catálogo existe para que eso no vuelva a pasar: la plantilla **referencia** `función@versión`.

Este documento está escrito para tres lectores distintos, y cada sección dice para quién es.

---

## 1. Qué es una función, campo a campo

Una función tiene dos partes: la **función** (identidad estable) y sus **versiones** (el código y
el contrato concretos, inmutables una vez registradas).

### La función

| Campo | Qué es |
|---|---|
| `nombre` | Cómo se llama. Es lo que se ve en el catálogo. |
| `descripcion` | Para qué sirve, en una línea. |
| `organizacion_id` | La organización autora. **Nulo significa «de la plataforma»**. |
| `origen` | `autoservicio` (el código vive en el catálogo) o `paquete` (vive en el repositorio de un equipo). |
| `entry_point` | Solo en `paquete`: `distribución:nombre`. |
| `publicada_en` | Cuándo se promovió a nivel de plataforma. Nulo si no lo está. |
| `valoracion_promocion` | La valoración escrita de quien la promovió. |
| `nivel` | **Derivado, no guardado.** 2 si es de una organización y sin publicar; 3 si está publicada, es de paquete o no tiene organización. |

`nivel` es derivado a propósito: una columna sería un tercer sitio donde vive el mismo hecho y
podría discrepar de los otros dos — el defecto que MT.4 le quitó a `is_global`.

### La versión

| Campo | Qué es |
|---|---|
| `version` | El ordinal en el catálogo: 1, 2, 3… |
| `code` | El código Python, en `autoservicio`. **Nulo en `paquete`**: una copia divergiría del `pip install`. |
| `code_sha256` | El hash del código (o de la fuente del `run` en un paquete). Es lo que permite decir meses después si lo que corrió era esto. |
| `version_paquete` | Solo en `paquete`: la versión semver instalada. |
| `contrato_entrada` | El `ContratoFuncion`: slots de fichero, parámetros y la declaración responsable. |
| `contrato_salida` | Siempre `ExtractionResult`. No se inventa un segundo esquema, porque dos esquemas divergen. |
| `audit_result_json` | Lo que vio el auditor, **incluidos los avisos que no bloquearon**: es lo que la revisión posterior tiene que poder leer. |
| `estado` | `draft` · `registrada` · `suspendida` · `retirada` · `no_instalada`. |
| `autoria` | `ia` o `persona`. **No es una puerta**: nada se ramifica por este campo. Consta porque la revisión posterior quiere verlo. |

### La declaración responsable (forma parte del contrato)

| Campo | Qué es |
|---|---|
| `finalidad` | Para qué sirve la función. **Obligatoria**: sin ella el contrato ni se construye. |
| `categorias_datos` | Qué clases de datos trata. Vocabulario **abierto**, y **el mismo que el registro de actividad de REG**: con dos vocabularios, el catálogo y el registro no se cruzarían en una auditoría. |
| `declarada_por` | Quién declara. Una declaración responsable sin responsable no es una declaración. |
| `declarada_en` | Cuándo. |

El código `sin_declarar` existe en el vocabulario, y significa exactamente eso. Las funciones que
la migración de FUN.3 sacó de plantillas vivas lo llevan: no se inventó una categoría por ellas.

---

## 2. El ciclo de una versión

```
draft ──► registrada ──► suspendida ──► registrada
                    └──► retirada          (terminal)
                    └──► no_instalada      (solo paquete; lo decide `pip`)
```

**Registrar es compartir, y es automático.** Para que una versión quede `registrada` hacen falta
tres cosas, y ninguna es que una persona dé el visto bueno:

1. la **declaración responsable** completa,
2. la **auditoría** sin hallazgos críticos,
3. la **prueba en sandbox** superada.

Con eso, la versión es usable de inmediato. La revisión humana viene **después** (§4).

**Una versión registrada es inmutable.** Corregir es publicar otra. Sin esto, «arreglar una vez»
sería «cambiar en silencio informes ya aprobados». Los únicos campos que una versión registrada
admite son los de otra persona y otro momento: los de la revisión y los de la suspensión.

**El anclaje es exacto en autoservicio.** Una plantilla anclada a `función@1` ejecuta la versión 1
para siempre; publicar la 2 **no cambia ninguna plantilla**. Adoptar la 2 es una decisión de quien
mantiene la plantilla.

**En paquete el anclaje es por mayor**, que es lo que compra el semver: una plantilla anclada al
ordinal que trajo 1.2.0 sigue ejecutando cuando se instala 1.3.0, y un mayor distinto **falla en
alto** nombrando los dos. Lo que no se aproxima es el manifiesto: anota la versión instalada
**exacta** con su hash.

**Retirar es terminal.** `suspendida` vuelve; `retirada` no. Y una versión retirada o desinstalada
**no se borra**: hay manifiestos de informe que la citan por id, y un manifiesto que apunta a una
fila inexistente no se puede auditar.

**Un bloque anclado a algo que no se puede ejecutar falla en alto**, con el nombre de la función y,
si está suspendida, **el motivo**. Nunca queda vacío en silencio.

---

## 3. Quién puede qué

El servidor calcula `acciones_permitidas` y la pantalla **itera** esa lista; no decide. Si una
acción aparece, su endpoint no responde 403, porque la autorización se lee de la misma función que
llena el DTO.

| | Autora | Admin de la organización | Superadmin | Otra organización |
|---|---|---|---|---|
| Anclar una versión (`adoptar_version`) | sí | sí | sí | solo si está publicada |
| Publicar una versión nueva (`versionar`) | sí | sí | sí | no |
| Revisar (`revisar`) | **no** | sí | sí | no |
| Suspender (`suspender`) | **no** | sí | sí | no |
| Reactivar (`reactivar`) | **no** | sí | sí | no |
| Retirar (`retirar`) | sí | sí | sí | no |
| Solicitar la promoción | — | sí | — | no |
| Promover a plataforma | no | no | **sí** | no |

Dos reparticiones que no se mezclan:

* **Suspender es de quien revisa; retirar es de quien escribe.** La autora no puede reactivar lo
  que otra persona suspendió: si pudiera, suspender no sería una decisión, sería una sugerencia.
* **Revisar es de otra persona.** La autora de una función no aparece como revisora de su propia
  versión.

Y una función de **paquete** no ofrece `versionar` ni `promover`: se versiona con `pip` y ya es de
plataforma. Sí ofrece `retirar`, porque la plataforma tiene que poder vetar una instalada sin
esperar a que alguien la desinstale.

---

## 4. Correspondencia con la Instrucció 02/2026

Esta sección es para quien tenga que dar por bueno el diseño: la UADTI y la OIATI.

La Instrucció de desarrollo ciudadano *governat* define tres niveles según el alcance, y el
catálogo los implementa así:

| Instrucció | En el catálogo |
|---|---|
| **Nivel 1** — uso personal | Fuera de la plataforma. Un script que alguien usa en su equipo no pasa por aquí, y no tiene que hacerlo. |
| **Nivel 2** — compartir dentro del servicio | **Registrar una función en una organización.** Filtro automático (declaración + auditoría + sandbox), uso inmediato, **sin aprobación humana previa**, y revisión posterior. |
| **Nivel 3** — alcance superior al servicio | **Promoción a plataforma** (con valoración escrita del superadministrador) o **origen paquete** (lo instala quien opera el despliegue). |

### Lo que el nivel 2 exige, y dónde está

* **§8.2, declaración responsable**: es parte del contrato (`finalidad`, `categorias_datos`,
  `declarada_por`). Sin ella la versión no se registra.
* **§8.3, filtro automático**: auditoría AST sin hallazgos críticos + prueba en sandbox. Los
  avisos **no bloquean** —eso sería aprobación previa por la puerta de atrás— pero constan.
* **§8.4, revisión posterior**: cola de revisión con **muestreo aleatorio**, y cuatro resultados
  posibles: `conforme`, `correcciones`, `reclasificada`, `suspendida`. **«Aprobada» no es uno de
  ellos, y no lo es a propósito**: en el nivel 2 no hay nada que aprobar.
* **La prohibición de la aprobación previa como condición para compartir** se hace cierta con un
  test que pide la misma versión a las dos superficies: aparece en la cola como `sin_revisar`
  **y** el resolutor la ejecuta, a la vez.
* **§9, reparto de responsabilidades**: suspender es de quien revisa, retirar de quien escribe, y
  revisar es siempre de otra persona.

### La diferencia honesta con la regla 2 de la Instrucció

La Instrucció prevé, para el desarrollo ciudadano, que **el código se quede en el equipo de la
persona**. Aquí no ocurre eso: el código se registra en la plataforma y se ejecuta en el nodo
institucional, sobre los datos institucionales.

Es un régimen **distinto**, no una interpretación laxa, y conviene decir en qué sentido:

* A favor: el código pasa por una auditoría estática, corre en un sandbox, queda versionado con su
  hash, tiene declaración responsable, entra en una cola de revisión y deja rastro en el registro
  de actividad de IA. Nada de eso existe cuando el script vive en el portátil de alguien.
* En contra: los datos que trata son los institucionales y no una copia en un equipo personal, y
  el código lo puede usar cualquiera de la organización sin que su autora lo sepa.

**Esto necesita un «sí» explícito de la UADTI y de la OIATI**, no un silencio. La plataforma no
puede decidir por su cuenta que su régimen es equivalente al que la Instrucció describe.

---

## 5. La caja de herramientas del auditor

Para quien vaya a escribir o revisar una función de autoservicio. **Estas listas salen del
código** (`services/script_auditor.py`) y las sirve `GET /api/v1/verificaciones/codigo/reglas`; un
test comprueba que este documento no se desvía de ellas.

**Módulos permitidos** (16): `base64`, `collections`, `datetime`, `fitz`, `io`, `json`, `math`,
`matplotlib`, `numpy`, `openpyxl`, `pandas`, `pdfplumber`, `re`, `seaborn`, `typing`,
`unicodedata`.

**Capacidades denegadas** — las tres familias, y por qué cada una:

* **Salir de la máquina**: `socket`, `requests`, `httpx`, `urllib`, `http`, `ssl`. Un script de
  extracción no tiene por qué hablar con nadie, y si pudiera, podría llevarse los datos.
* **Tocar el sistema**: `os`, `sys`, `subprocess`, `shutil`, `open`, `chmod`, `remove`,
  `unlink`, `rmtree`, `popen`, `system`, `spawn`, `pty`, `tty`, `platform`, `threading`,
  `multiprocessing`, `concurrent`, `ctypes`, `cffi`.
* **Tocar la propia plataforma**: `fastapi`, `uvicorn`, `nicegui`. Un script de extracción que
  importara el servidor podría registrar rutas, leer la configuración o apagarlo — y estos tres
  están instalados en el mismo entorno, así que sin prohibirlos explícitamente el `import`
  funcionaría. (`nicegui` sigue en la lista aunque el cliente NiceGUI se retirara el 2026-09-04:
  prohibir algo que no está instalado no cuesta nada, y quitarlo sólo tendría sentido el día que
  se pueda asegurar que ningún despliegue lo tiene.)
* **Reescribirse a sí mismo**: `eval`, `exec`, `compile`, `__import__`, `importlib`, `builtins`,
  `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`, `inspect`, `ast`, `code`,
  `codeop`, `dis`, `marshal`, `pickle`, `shelve`, `gc`, `types`, `traceback`, y los atributos de
  introspección (`__class__`, `__globals__`, `__code__`, `__bases__`, `__mro__`,
  `__subclasses__`, `__builtins__`, `__dict__`, `__closure__`, `__loader__`, `__module__`).
  Sin esta familia, la lista de módulos no serviría de nada: se saltaría en una línea.
* **Rutas absolutas**: un script que escribe en `C:\...` o `/var/...` funciona en el portátil de
  quien lo escribió y no en el despliegue, donde el almacenamiento es un servicio.

**Las seis reglas y su nivel**:

| Regla | Nivel |
|---|---|
| `syntax-error` | CRITICAL |
| `forbidden-call` | CRITICAL |
| `interpreter-access` | CRITICAL |
| `absolute-path` | CRITICAL |
| `forbidden-module` | CRITICAL |
| `module-not-whitelisted` | WARNING |

`module-not-whitelisted` es **WARNING** y no CRITICAL a propósito: un módulo desconocido no es
necesariamente peligroso —puede ser útil y faltar en la lista—, así que no bloquea el registro y
sí llega a la revisión posterior, que es quien puede decidir ampliar la lista.

> **Petición explícita a la UADTI**: estas reglas se escribieron desde el análisis del riesgo de
> un script de extracción, no desde las Guías Operativas Técnicas. Hay que contrastarlas con
> ellas. Si las Guías son más estrictas en algo, manda la Guía; si son más laxas, se queda lo
> estricto y se dice por qué.

---

## 6. Llevar tu script al catálogo

Para la persona referente de un servicio que ya tiene un script que funciona.

Tu script de nivel 1 ya hace lo que tiene que hacer. Lo que el catálogo te pide es **declarar su
contrato**, que es lo que permite que otra persona lo use sin leerlo.

### Paso 1 — di qué ficheros necesita

Cada fichero es un **slot** con nombre, clase y si es obligatorio:

```python
slots=[
    {"slot_id": "gastos", "kind": "excel", "required": True,
     "label": {"es": "Fichero de gastos", "ca": "Fitxer de despeses"}}
]
```

Las clases son `excel`, `pdf`, `markdown` y `text`; el servidor manda al navegador qué extensiones
acepta cada una, así que no hay que repetirlas.

### Paso 2 — di qué parámetros acepta

```python
parametros=[
    {"slot_id": "umbral", "field_type": "number", "label": {"es": "Umbral"}, "required": False}
]
```

Un parámetro **es** un descriptor de campo de interfaz, así que el formulario sale de aquí sin
escribir nada en el frontend.

### Paso 3 — declara

```python
finalidad="Contar las filas del fichero de gastos de un servicio",
categorias_datos=["dades_pressupostaries"],
```

### Paso 4 — el protocolo del script **no cambia**

Sigues asignando `result`, y sigues recibiendo `file_path`, `raw_text` y `options`. Los parámetros
del contrato llegan dentro de `options`, que es donde tu script ya los busca. No se te pide
reescribir nada: cambiar el protocolo es lo que empuja a la gente a seguir trabajando por su
cuenta.

### Qué pasa al registrar

El auditor lee tu código sin ejecutarlo (§5), el sandbox lo ejecuta una vez con tus datos de
prueba, y si las dos cosas van bien tu función queda **registrada y usable**. Nadie tiene que
aprobártela. Después aparecerá en la cola de revisión posterior, y ahí alguien puede pedirte
correcciones, reclasificar su alcance o suspenderla si encuentra un problema — pero mientras eso
no pase, funciona.

---

## 7. Empaquetar una función

Para el primer equipo de desarrollo que mantenga funciones en su propio repositorio. El ejemplo
completo está en `server/tests/fixtures/paquete_funcion_demo/`.

### El descriptor

```python
from server.app.modules.redaccion.funciones_paquete import FuncionEmpaquetada

CONTAR_FILAS = FuncionEmpaquetada(
    nombre="contar_filas",
    version="1.2.0",          # semver de tres números, obligatorio
    contrato=CONTRATO,        # el mismo ContratoFuncion que una de autoservicio
    run=contar_filas,         # (EntradaValidada) -> ExtractionResult
)
```

El *entry point* apunta a una **instancia**, no a una factoría: así la plataforma puede validar tu
contrato antes de ejecutar una sola línea de tu paquete.

### El grupo

```toml
[project.entry-points."govgenai.funciones"]
contar_filas = "paquete_funcion_demo:CONTAR_FILAS"
```

El `entry_point` del catálogo es `distribución:nombre` — `paquete-funcion-demo:contar_filas`.

### Qué valida la plataforma al arrancar, y qué hace si falla

Descubre los *entry points*, valida cada contrato con **el mismo validador** que usa una función
de autoservicio, y **detiene el arranque** si algo no cuadra, nombrando paquete y función:

* contrato incoherente,
* versión que no es semver,
* `run` que no es invocable,
* dos *entry points* que declaran lo mismo,
* un *entry point* que no se puede importar.

Falla en alto y no «avisa y sigue» porque un servidor en pie al que le falta una función da el
síntoma mucho después, como «la plantilla referencia algo que no existe», sin ninguna pista del
paquete roto.

La sincronización es **idempotente**: arrancar dos veces no crea nada.

### La regla del mayor

Publicar **1.3.0** sobre plantillas ancladas a 1.2.0: se ejecuta 1.3.0, y el manifiesto anota
1.3.0. Publicar **2.0.0**: el bloque **falla en alto** nombrando el mayor anclado y el instalado,
porque tu contrato puede haber cambiado. Reanclar es una decisión de quien mantiene la plantilla,
después de revisar.

Desinstalar el paquete pasa todas sus versiones a `no_instalada`; la función **se conserva**.

### Qué registra el manifiesto

`funcion_id`, `nombre`, `version` (el ordinal del catálogo), `origen`, `code_sha256` y
`version_paquete` **exacta**. Es lo que permite responder «qué corrió» sobre un informe de hace
seis meses.

### La frontera de confianza, sin rodeos

**Tu `run` corre in-process, en el servidor, con los datos del cliente, y sin sandbox.** No hay
aislamiento. La confianza está en quien instala el paquete en el despliegue, exactamente como en
un plugin de pytest o de Airflow. Lo que la plataforma controla no es tu código: es quién puede
hacer `pip install`.

Lo que sí se valida siempre es **la entrada contra tu contrato antes de llamarte** y **la salida
como `ExtractionResult` después**. Por eso tu `run` no tiene que defenderse de un slot que falta.

### Una advertencia sobre la dependencia

Hoy los tres nombres que necesitas (`FuncionEmpaquetada`, `ContratoFuncion`, `ExtractionResult`)
viven en la plataforma, así que la necesitas como dependencia de desarrollo. Cuando aparezca un
segundo consumidor se moverán a un `govgenai-sdk` ligero, y no cambiará nada más: ni el grupo del
*entry point*, ni la forma del descriptor, ni el anclaje. Está dicho aquí para que no lo
descubras a mitad del primer intento.

---

## 8. Ejecutar una función por API

Para una aplicación externa. Requiere un PAT con el scope `funciones:execute` (lo puede emitir un
superadministrador o un administrador de organización).

```
POST /api/v1/funciones/{funcion_id}/run
{
  "version": 1,
  "ficheros": {"gastos": "ingestion/2026/gastos.xlsx"},
  "parametros": {"umbral": 1000}
}
```

Cuatro cosas que esta superficie **no** relaja:

* **`version` es obligatoria.** El anclaje también rige fuera: una API que ejecutara «la última»
  convertiría cada publicación en un cambio silencioso para todos sus consumidores.
* **La organización se deriva del PAT**, no del cuerpo. Solo funciones propias o publicadas.
* **Una versión suspendida devuelve `423` con el motivo**, no un 404: la función existe y tienes
  que poder distinguir «no está» de «está detenida, y por esto».
* **Los ficheros van por referencia de almacenamiento, no por contenido.** Hay un tope de tamaño
  de petición, heredado del que fijó VAS.1.

Cada ejecución deja un evento en el registro de actividad de IA con la finalidad y las categorías
**que la función declaró** —no las que diga quien llama— y la referencia `funcion:<id>@<v>#<sha>`.
**Sin payloads**, como todo el registro.

La respuesta incluye un bloque `funcion` con qué se ejecutó exactamente, para que puedas anotarlo
en tu propio registro y que los dos se puedan cruzar.

---

## 9. El puente a Fase 3

El catálogo se diseñó como pieza compartida, no solo para informes. En Fase 3, las **acciones de
fase de expediente** referencian `plantilla@versión` y `función@versión` en vez de llevar su
propio código: la restricción está escrita en `planificacion/Plan_TDD_Fase3.md`, donde se retiró
`ejecuciones_accion.codigo_ejecutado` precisamente porque duplicaba sandbox, auditoría y
aprobación.

Lo que se comparte entre módulos es **código y contrato**, nunca datos. Y la cadena
auditoría + sandbox + revisión no se relaja para el nuevo consumidor.

---

## Documentos relacionados

- `docs/ESPECIFICACIONES.md` — qué garantiza la plataforma y en qué madurez.
- `docs/REDACCION_CONTRACT_FIRST.md` — el contrato de plantillas y bloques.
- `docs/MULTITENENCIA.md` — el ámbito de cada tabla, incluidas `hub_funciones` y
  `hub_funcion_versiones`.
- `planificacion/fase1/71_BLOQUE_FUN.md` — los siete prompts con su razonamiento.
