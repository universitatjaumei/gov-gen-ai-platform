## Bloque FUN — Catálogo de funciones deterministas: de scripts copiados a funciones versionadas y compartidas (PENDIENTE, planificado el 2026-09-01)

> **Posición**: FUN.1–FUN.5 no dependen del despliegue. FUN.6 (consumo externo) va **después del
> Bloque REG**, cuyo registro de actividad y patrón de scopes consume.
>
> **Restricción de diseño transversal**: el catálogo se diseña como pieza **compartida** — hoy lo
> consumen los informes; en Fase 3 lo consumen las fases de expediente. La restricción simétrica
> quedó escrita en `Plan_TDD_Fase3.md` (las acciones de fase referencian `plantilla@versión` y
> `función@versión`, nunca código incrustado). Nada en FUN puede asumir «informe» en sus
> contratos ni nombres.
>
> **Revisado el 2026-09-02 — doble origen.** La segunda observación de desarrollo («gestionar
> ese código dentro de la herramienta es reinventar la rueda: tiene que estar en manos de quien lo
> define, versionado, testeado y mantenido contra una API declarada») acierta **para el autor
> desarrollador** y no ve **al autor informador**, que no tiene repositorio ni despliegue. La
> respuesta no es elegir: el catálogo es un **registro de referencias `función@versión` con dos
> orígenes** (autoservicio y empaquetado, detalle abajo). Lo que centraliza la plataforma no es
> el código, es la **revisión, el manifiesto de ejecución, la trazabilidad y el contrato**: git
> versiona código; la plataforma versiona decisiones y ejecuciones.
>
> **Revisado el 2026-09-02, segunda vez — el catálogo como canal del nivel 2 de la Instrucció
> 02/2026.** El usuario aclaró para qué está pensado el catálogo: **no para desarrolladores
> profesionales, sino para gobernar el desarrollo ciudadano** que regula la *Instrucció 02/2026
> del Delegat per a l'Estratègia Digital i la IA* (marc de *citizen development* governat i
> prevenció del *Shadow IT*; copia en `_local/`). La Instrucció fija tres niveles: **nivel 1**, uso
> personal, libre y **fuera de la plataforma** (macros, scripts locales, Colab); **nivel 2**,
> compartición dentro del servicio, con *declaración responsable y registro, uso inmediato y
> revisión posterior o por muestreo, nunca aprobación previa bloqueante*; **nivel 3**, alcance
> superior al servicio, que pasa a desarrollo corporativo. **La plataforma entra en el nivel 2:
> registrar una función en el catálogo ES el acto de declararla y compartirla** por «los canales
> que indique la UADTI». Consecuencias, aplicadas abajo: (1) dentro de la plataforma solo hay dos
> niveles, organización y plataforma; (2) registrar = declaración responsable + auditoría AST +
> sandbox, **automáticos**, y uso inmediato en la organización; la aprobación humana previa deja
> de ser la puerta del nivel 2 y queda para el paso a nivel 3; (3) aparece la **revisión
> posterior** con muestreo, correcciones y **suspensión**; (4) el registro acepta **código escrito
> fuera** (el caso mayoritario de la Instrucción: un script que ya funcionaba en el equipo de la
> persona referente), no solo el propuesto por la IA; (5) el auditor AST **es la caja de
> herramientas** de la Instrucción, y sus reglas deben coincidir con las Guías Operativas
> Técnicas de la UADTI. Los dos orígenes encajan en la matriz de la Instrucción sin forzarla:
> autoservicio es desarrollo ciudadano; empaquetado es desarrollo corporativo (nivel 3).
> Correspondencia artículo a artículo en `docs/EVOLUCIO_I_ASPECTES_PENDENTS.md` §Qüestió 4.

**Origen**: conversación del 2026-09-01 sobre la observación de desarrollo («generador contra
framework», ver `docs/EVOLUCIO_I_ASPECTES_PENDENTS.md` §Cuestión 4). Releída sobre los
scripts deterministas, la crítica **acierta en un punto**: los nodos del grafo se comparten por
construcción, pero **el código de un script aprobado se incrusta copiado en el bloque de cada
plantilla** (`scripts_router.py:555-560`: `options={"code": ..., "approved": True}`; documentado
en `contracts/blocks.py:41-44`). Dos plantillas que necesitan la misma extracción son dos
propuestas, dos aprobaciones y dos copias; un bug en un script usado por N plantillas se arregla
N veces. `HubScriptProposal` es una cola de aprobación con `target_template_id`, no un catálogo.

**Qué construye el bloque**: una entidad `HubFuncion` versionada con contrato de entrada/salida
declarado; los bloques referencian `funcion_id@versión` en vez de incrustar código; una función
puede **promocionarse a plataforma** (nivel 3) con valoración del superadmin y entonces cualquier
organización la referencia (caso motor: la explotación de un ERP común que varias organizaciones
comparten); y consumo externo por API. La cadena de seguridad existente **no se relaja, se
reordena**: auditoría AST (`ScriptSecurityAuditor`) + sandbox (`SandboxClient`) siguen siendo
obligatorios y automáticos **antes del registro**; la aprobación humana previa deja de ser la
puerta del nivel 2 (la Instrucció la prohíbe como condición para compartir) y se convierte en
**revisión posterior** con muestreo y suspensión, y en **valoración previa** solo para el paso a
plataforma. Lo que cambia es dónde vive el código registrado, cómo se le llega, y cuándo entra la
persona.

**Los dos orígenes de una función** (decidido el 2026-09-02):

| | Origen **autoservicio** | Origen **empaquetado** |
|---|---|---|
| Nivel de la Instrucció 02/2026 | **Nivel 2**, desarrollo ciudadano compartido en el servicio (y nivel 3 si se promociona) | **Nivel 3**, desarrollo corporativo |
| Autor | La persona referente de desarrollo ciudadano del servicio (*power user*): trae un script que ya usaba en su equipo, o lo construye con la IA dentro de la plataforma | Un equipo de desarrollo (UADTI), en su propio repositorio, con su CI y su versionado |
| Dónde vive el código | En el catálogo (`HubFuncionVersion.code`) | En un paquete Python instalado en el despliegue, descubierto por *entry point* `govgenai.funciones` |
| Cómo entra | **Registro** = declaración responsable + auditoría AST + prueba en sandbox, automáticos → **uso inmediato** en la organización → revisión posterior o por muestreo | `pip install` por quien opera; la plataforma lo registra al arrancar y valida su contrato |
| Dónde corre | Sandbox | En el proceso del servidor: la confianza está en quien lo instala, igual que en un plugin |
| Versionado | Ordinal del catálogo; versión registrada inmutable | Semver del paquete; el catálogo registra cada versión instalada con `code_sha256` de su fuente |
| Anclaje de una plantilla | Por versión exacta, **por construcción**: publicar v2 no toca nada anclado a v1 | Por **mayor** de semver, **por contrato**: una versión instalada del mismo mayor se acepta; un mayor distinto falla en alto |
| Ámbito | Nace en su organización (nivel 2); paso a plataforma (nivel 3) con valoración del superadmin | Plataforma desde el principio: lo instala quien opera el despliegue, no una organización |
| Quién revisa | El administrador de la organización y el superadmin, **después** y por muestreo; pueden pedir correcciones, reclasificar o suspender | Quien instala responde; el superadmin puede retirar una instalada |

Lo que **no cambia entre orígenes**, y es exactamente lo que justifica que el catálogo exista
aunque el código viva fuera: el contrato de entrada/salida (mismo esquema, mismo validador, mismo
formulario SDUI derivado), la referencia `función@versión` desde plantillas, fases de expediente
y API, la entrada validada antes de ejecutar, el `RunManifest` con la versión exacta y el hash
de lo que corrió, el rastro en el registro de actividad, el inventario de quién usa qué, y la
frontera de organización. Una función empaquetada hereda todo eso el día que se instala.

**Reglas duras del bloque FUN**:

- **El anclaje de versión es la clave de bóveda.** Una plantilla referencia una versión concreta;
  publicar una versión nueva NO cambia ninguna plantilla existente. Sin esto, «arreglar una vez»
  sería «cambiar en silencio informes ya aprobados» y el RunManifest dejaría de ser reproducible.
- **Una versión registrada es inmutable**: corregir es publicar otra versión. El código de una
  versión registrada no se edita jamás (misma razón que el log de auditoría).
- **Se comparte código y contrato, nunca datos**: ni ficheros, ni resultados, ni datos de prueba
  cruzan organizaciones.
- **Control proporcional al alcance, como manda la Instrucció (§2 y §5).** Registrar una versión
  exige **siempre y automáticamente** declaración responsable (finalidad y categorías de datos),
  auditoría AST sin hallazgos críticos y prueba en sandbox superada; con eso la versión queda
  **registrada y usable de inmediato** por las plantillas de su organización. **No hay aprobación
  humana previa en el nivel 2**: la persona entra después, en la revisión posterior o por
  muestreo, que puede pedir correcciones, reclasificar o **suspender**. La aprobación previa
  humana queda **solo** para el paso a plataforma (nivel 3), que exige valoración del superadmin
  con motivo escrito. Un hallazgo AST crítico bloquea el registro en cualquier nivel: la
  automatización filtra, la persona gobierna.
- **El registro acepta código escrito fuera.** La Instrucció parte de que la persona referente ya
  construyó la solución en su equipo (nivel 1); el formulario de registro admite pegar o subir
  ese código además de proponerlo con la IA, y los dos caminos pasan por la misma auditoría, el
  mismo sandbox y la misma declaración. Ninguna rama «si lo escribió la IA».
- **El auditor AST es la caja de herramientas de la Instrucció (regla 1).** Sus reglas (módulos
  permitidos, prohibiciones, rutas) se documentan como tales en `docs/CATALOGO_FUNCIONES.md` y se
  contrastan con las Guías Operativas Técnicas de la UADTI; si divergen, cada subida de nivel 1 a
  2 sería una reescritura, que es justo lo que empuja al *Shadow IT*. Mantener esas reglas es
  mantener la caja de herramientas, y ese papel es de la UADTI.
- **Suspender es de quien revisa; retirar es de quien escribe.** Una versión suspendida no se
  ejecuta: el bloque que la referencia falla en alto con el motivo de la suspensión. Retirar (por
  el autor) y suspender (por el revisor) son dos estados distintos, porque responden a dos
  responsabilidades distintas de la matriz de roles de la Instrucció (§9).
- **La entrada se valida contra el contrato ANTES de llegar al sandbox**: el fallo de un ERP que
  cambia de formato tiene que ser «la entrada no cumple el contrato», no un traceback de pandas.
- **Un solo contrato, un solo validador, para los dos orígenes.** Una función empaquetada declara
  su contrato con el mismo esquema que una de autoservicio y pasa por el mismo validador; si el
  contrato es incoherente, el arranque falla en alto nombrando el paquete, no se registra a
  medias. Dos esquemas de contrato divergen; uno solo es lo que hace que el formulario, la API
  y el expediente traten igual a las dos.
- **El origen empaquetado no pasa por el sandbox y eso se dice, no se disimula**: su código corre
  en el proceso del servidor y la confianza se desplaza a quien lo instala, exactamente como en
  un plugin de despliegue. Por eso nace con ámbito de plataforma y por eso su alta no es un
  formulario sino un `pip install`. Lo que la plataforma sí verifica de él es el contrato, el
  mayor de semver al resolver, y el hash de su fuente en cada ejecución.
- **La garantía de anclaje cambia de naturaleza con el origen, y el manifiesto no.** En
  autoservicio el anclaje es por construcción (versión exacta e inmutable). En empaquetado es
  por contrato (semver: mismo mayor, compatible), porque un despliegue no puede tener dos
  versiones del mismo paquete instaladas. En ambos, el `RunManifest` registra la versión
  **exacta** y el `code_sha256` de lo que corrió: la reproducibilidad como registro se conserva
  siempre; como garantía de re-ejecución idéntica, solo en autoservicio, y el manifiesto lo deja
  ver.

---

### Prompt FUN.1 (RED/GREEN) — La entidad `HubFuncion` y sus versiones

**Modelo sugerido**: **Sonnet** — modelo + migración con las decisiones ya tomadas aquí.

**Objetivo**: tablas `hub_funciones` y `hub_funcion_versiones`, con ámbito declarado, migración
aplicada e inventario de multitenencia actualizado.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.1 (RED/GREEN) — hub_funciones + hub_funcion_versiones

## Modelos (junto a los modelos de redaccion, que es la casa física hasta que Fase 3
## aporte el segundo consumidor — misma regla que la anonimización en REG)
- HubFuncion: id UUID pk, nombre str(120), descripcion Text, organizacion_id UUID FK
  NULLABLE (nulo = plataforma, semántica heredable establecida), publicada_en timestamptz
  nullable, publicada_por nullable, creada_por nullable (nulo en origen paquete),
  origen (StrEnum: autoservicio|paquete — es estructura, no vocabulario), entry_point
  str(200) nullable (solo paquete: «distribucion:nombre», UNIQUE cuando no es nulo),
  created_at/updated_at. __ambito__ = "heredable".
- HubFuncionVersion: id UUID pk, funcion_id FK ondelete CASCADE, version int (ordinal del
  catálogo, en ambos orígenes), code Text NULLABLE (nulo en paquete: el código no vive
  aquí), version_paquete str(32) nullable (semver, solo paquete), contrato_entrada JSONB,
  contrato_salida JSONB, audit_result_json JSONB nullable (nulo en paquete: no hay
  auditoría AST), code_sha256 str(64) (en paquete, hash de la fuente de la función
  instalada), estado (draft|registrada|suspendida|retirada|no_instalada — el último solo
  en paquete), UNIQUE(funcion_id, version). __ambito__ = "derivada".
- Declaración responsable (Instrucció §6 regla 3 y §8.2), en la versión: finalidad Text
  NOT NULL en autoservicio, categorias_datos JSONB (list[str], el MISMO vocabulario que
  ActividadIAEvent.categorias_datos de REG.1 — un solo vocabulario de categorías de datos
  en la plataforma; si REG.1 aún no existe, se define aquí y REG lo reutiliza),
  declarada_por, declarada_en. En paquete la declaración la trae el descriptor (FUN.5).
- Revisión posterior (Instrucció §8.4), en la versión: revisada_por nullable, revisada_en
  nullable, revision_resultado nullable (StrEnum: conforme|correcciones|reclasificada|
  suspendida — estructura, no vocabulario), revision_nota Text nullable. Suspensión:
  suspendida_por, suspendida_en, motivo_suspension Text (obligatorio al suspender).
- Promoción (nivel 3): en HubFuncion, promocion_solicitada_por/_en nullable (la pide el
  admin de la organización con motivo), publicada_en/publicada_por (la resuelve el
  superadmin) y valoracion_promocion Text (obligatoria al promover).
- Nivel derivado, no columna: nivel 2 = organizacion_id no nulo y publicada_en nulo;
  nivel 3 = publicada_en no nulo o origen paquete. Se expone en el DTO.
- Invariante de coherencia por origen, en la capa de servicio: autoservicio exige code,
  finalidad y declarada_por y prohíbe version_paquete; paquete exige version_paquete y
  entry_point y prohíbe code.
- Sin relationship() cross-base, como siempre.

## Guarda de inmutabilidad (capa de servicio)
- Una versión en estado registrada (o suspendida, o retirada) no admite cambio de code ni
  de contratos ni de declaración: el servicio lo rechaza. Corregir = crear versión nueva.
  Sí admite cambios de estado (registrada -> suspendida -> registrada; registrada ->
  retirada) y de los campos de revisión, que son de otra persona y de otro momento.

## Migración
- Alembic autogenerate + revisión; aplicar con uv run alembic upgrade <rev>.

## Tests (mínimo 6) — tests/modules/redaccion/test_fun1_catalogo.py
- __ambito__ declarado en ambas (el guardarraíl de MT.1 lo exige).
- UNIQUE(funcion_id, version).
- La guarda: editar code de una versión registrada falla; crear v2 funciona; cambiar el
  estado a suspendida con motivo funciona; suspender sin motivo falla.
- Round-trip de contratos JSONB y de la declaración responsable.
- Acotación de listado: una organización ve las suyas + las publicadas (organizacion_id
  nulo o publicada_en no nulo); nunca las no publicadas de otra.
- code_sha256 se calcula al escribir y coincide con el código.
- La invariante por origen: autoservicio sin code falla; autoservicio sin finalidad falla;
  paquete con code falla; paquete sin version_paquete falla.
- El nivel derivado: organización sin publicar -> 2; publicada -> 3; paquete -> 3.
```

**Verificación**: suite del directorio + higiene verdes; `alembic current` con la revisión;
`docs/MULTITENENCIA.md` actualizado con las dos tablas (su test lo exige).

---

### Prompt FUN.2 (RED/GREEN) — El contrato de entrada/salida, declarado y validado

**Modelo sugerido**: **Opus** — es LA decisión de diseño del bloque: qué declara una función y
dónde se valida.

**Objetivo**: formalizar el contrato hoy implícito («asigna `result: dict`») como dato declarado
de cada versión, validado en dos puntos: al registrar y antes de ejecutar.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.2 (RED/GREEN) — contrato E/S de una función

## Contrato de entrada
- Slots de fichero (kind: excel|pdf|markdown|text, obligatorio u opcional) + parámetros
  tipados. Los parámetros reutilizan la FORMA de UIFieldDescriptor (contracts/ui.py): el
  SDUI pinta el formulario desde el contrato, gratis y sin campos hardcodeados en React
  (regla maestra 1).

## Contrato de salida
- ExtractionResult existente (tables/metrics/free_text). NO inventar un segundo esquema
  de salida: el que hay es el que consumen los nodos, y dos esquemas divergen.

## El contrato es el mismo objeto para los dos orígenes
- Un modelo Pydantic ContratoFuncion (entrada + salida) que se serializa a los JSONB de
  FUN.1 y que es TAMBIÉN lo que declara una función empaquetada (FUN.5) en su descriptor.
  Un solo validador; ninguna rama «si es paquete». El test de FUN.5 que registra un
  paquete con contrato incoherente reutiliza este validador sin tocarlo.

## La declaración responsable forma parte del contrato
- ContratoFuncion lleva también la declaración (finalidad, categorias_datos) — es lo que la
  Instrucció exige registrar antes de compartir (§8.2) y lo que la revisión posterior lee.
  El mismo objeto sirve para el descriptor de un paquete (FUN.5): una función corporativa
  también declara finalidad y categorías. Vocabulario de categorías compartido con REG.

## Validación en dos puntos
1. Al registrar una versión: el contrato es coherente (slots con kind válido, parámetros
   con tipo conocido, declaración completa) o la versión no se crea.
2. Antes de ejecutar: la entrada cumple el contrato ANTES de invocar el sandbox. El error
   es tipado y legible («falta el slot datos», «el parámetro umbral no es numérico») —
   nunca un traceback de pandas por un ERP que cambió de formato.

## Tests (mínimo 5) — tests/modules/redaccion/test_fun2_contrato.py
- Contrato incoherente rechazado al registrar, con el motivo.
- Entrada que no cumple -> error tipado SIN invocar el sandbox (espía sobre el cliente).
- Entrada válida -> llega al sandbox con las variables del protocolo actual
  (file_path/raw_text/options), que no cambia.
- Los descriptores del formulario SDUI se derivan del contrato (test de que salen del
  JSON, no de literales).
- Salida que no valida como ExtractionResult -> warning de error, no excepción opaca.
```

**Verificación**: suite del directorio + higiene verdes.

---

### Prompt FUN.3 (RED/GREEN) — Referencia en vez de copia, con migración de las plantillas

**Modelo sugerido**: **Opus** — migración de datos vivos + retirada del camino viejo; es el
prompt que convierte la crítica de desarrollo en falsa también aquí.

**Objetivo**: `DeterministicDataBlock` referencia `funcion_id@versión`; el **registro** (no una
aprobación) escribe en el catálogo y referencia; las plantillas existentes se migran; el código
incrustado deja de existir como camino activo; el registro acepta código escrito fuera.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.3 (RED/GREEN) — funcion_ref en DeterministicDataBlock

## Contrato del bloque (contracts/blocks.py)
- DeterministicDataBlock gana funcion_ref: {funcion_id: UUID, version: int} | None.
- options deja de llevar "code"/"approved" para admin_script: el contrato lo rechaza
  (la lección de extra="forbid" de REG.1 aplicada aquí).

## De cola de aprobación a registro (scripts_router.py, hoy líneas ~555-560)
- El flujo de propuesta (propose / test / validate-test-result) se conserva como la
  PRUEBA EN SANDBOX del registro; lo que desaparece es `approve` como puerta del nivel 2.
  Registrar una versión = declaración responsable rellenada + audit sin CRITICAL + test en
  sandbox superado -> HubFuncionVersion en estado `registrada`, referenciable de inmediato
  por las plantillas de la organización. Hallazgos WARNING no bloquean: quedan en
  audit_result_json y se muestran en la ficha para la revisión posterior (es exactamente
  «revisión posterior, no aprobación previa» de la Instrucció §5 nivel 2).
- `propose` admite además `code` aportado por la persona (pegado o subido), sin instrucción
  en lenguaje natural: es el script que ya usaba en su equipo (nivel 1). Pasa por el
  mismo auditor y el mismo sandbox; el resultado es indistinguible de uno propuesto por la
  IA salvo por un campo `autoria` (ia|persona) en la versión, que la revisión posterior
  quiere ver.
- Crea HubFuncion (o versión nueva de una existente si el autor lo indica) y escribe
  funcion_ref en el bloque. El código ya no se incrusta.
- HubScriptProposal deja de tener target_template_id como razón de ser: si tras esto no
  aporta nada que HubFuncionVersion no tenga, se retira (Caso B, borrar), con migración
  de las propuestas vivas. Decidirlo midiendo qué campos quedan huérfanos.

## El nodo (deterministic_extraction.py)
- Resuelve funcion_ref -> versión del catálogo (estado registrada) -> pasa code al
  pipeline, que no cambia. Función retirada, versión inexistente o **suspendida**: el
  bloque falla EN ALTO con mensaje que nombra la función y, si está suspendida, el motivo
  de la suspensión — nunca vacío en silencio (la lección de los perfiles sin configurar).
- La resolución se encapsula en un ResolvedorDeFuncion con un único método que devuelve
  «lo ejecutable» (código para el sandbox hoy; en FUN.5 también un callable in-process),
  para que el nodo no sepa de orígenes. En este prompt solo existe el origen
  autoservicio; FUN.5 añade el otro sin tocar el nodo.
- El RunManifest registra funcion_id, version y code_sha256 de lo que corrió (hoy no
  registra nada de esto: el código iba incrustado y no tenía identidad).

## Migración de datos (Alembic, data migration)
- Cada bloque existente con options.code se convierte en HubFuncion v1 registrada de la
  organización de su plantilla + funcion_ref, con finalidad = título del bloque y
  declarada_por = quien aprobó en su día (la aprobación antigua vale como declaración;
  revision_resultado = conforme, revisada_por = el aprobador: ya la miró una persona).
  Idempotente y con recuento antes/después.

## Retirada
- grep -r de options["code"] / "approved": True como camino activo a cero; el pipeline
  recibe el código resuelto, no lo busca en options. El endpoint `approve` como puerta
  desaparece (no se deja «por compatibilidad»).

## Tests (mínimo 10) — tests/modules/redaccion/test_fun3_referencia.py
- DOS plantillas referencian la MISMA función y ambas ejecutan (el caso del bloque).
- Registrar (declaración + AST sin CRITICAL + sandbox superado) crea la versión registrada
  y una plantilla la usa SIN ninguna aprobación humana (el test que hace cierta la
  Instrucció).
- Registrar sin declaración responsable -> 422; con hallazgo CRITICAL -> 422 con el
  hallazgo; con WARNING -> registrada, y el hallazgo consta en la ficha.
- Código aportado por la persona (sin instrucción NL) pasa por auditor y sandbox y queda
  con autoria=persona.
- Publicar v2 NO cambia una plantilla anclada a v1 (el test más importante del bloque).
- Adoptar v2 en una plantilla es un cambio explícito del bloque y ejecuta v2.
- Bloque legacy migrado ejecuta igual que antes (regresión con una plantilla real) y su
  versión consta como revisada por el aprobador antiguo.
- Función retirada -> fallo en alto con mensaje.
- Versión suspendida -> fallo en alto que incluye el motivo de la suspensión.
- El contrato rechaza options.code.
```

**Verificación**: suite de `tests/modules/redaccion/` + higiene verdes; migración aplicada con
recuento; un informe real generado desde una plantilla migrada, comparado con su versión previa.

---

### Prompt FUN.4 (RED/GREEN) — Revisión posterior, suspensión, paso a nivel 3 y el catálogo en el panel

**Modelo sugerido**: **Opus** — es donde la Instrucció se convierte en máquina de estados y en
acciones por rol; los contratos están cerrados pero las decisiones de quién puede qué y cuándo
tienen efectos cruzados con la tenencia.

**Objetivo**: el circuito del nivel 2 de la Instrucció (§8.4: revisión posterior, periódica o por
muestreo, que puede derivar en correcciones, reclasificación o suspensión) y el paso a nivel 3
(promoción a plataforma con valoración), con la pantalla de catálogo y la cola de revisión.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.4 (RED/GREEN) — revisión posterior + suspensión + nivel 3 + catálogo

## Backend — revisión posterior (nivel 2)
- GET /funciones/revision?estado=sin_revisar|todas&muestra=N: versiones registradas de
  la organización del principal (todas, para superadmin), con antigüedad, nº de
  plantillas que las referencian, autoría (ia|persona), hallazgos WARNING del auditor y
  la declaración. `muestra=N` devuelve N al azar entre las no revisadas: es el muestreo
  de la Instrucció, y existe para que revisar no exija leerlo todo.
- POST /funciones/{id}/versiones/{v}/revisar {resultado, nota}: sella revisada_por/_en y
  revision_resultado. `correcciones` no cambia el estado (la versión sigue usable; la
  corrección es una versión nueva del autor). `reclasificada` tampoco: anota que el
  alcance excede el nivel 2 y marca la función como candidata a promoción (nivel 3).
- POST /funciones/{id}/versiones/{v}/suspender {motivo}: estado -> suspendida; los
  bloques anclados fallan en alto con el motivo (FUN.3). POST .../reactivar vuelve a
  registrada. Suspende el admin de la organización o el superadmin; el autor NO puede
  reactivar lo que otro suspendió (dos responsabilidades, §9).
- Retirar sigue siendo del autor (y del superadmin): estado -> retirada, terminal.

## Backend — paso a nivel 3
- POST /funciones/{id}/solicitar-promocion {motivo} (admin de la organización autora).
- POST /funciones/{id}/promover {valoracion} (solo superadmin; valoracion obligatoria):
  sella publicada_en/publicada_por/valoracion_promocion. No muta código ni versiones; la
  autoría (organizacion_id) se conserva como atribución. Es la única aprobación humana
  PREVIA del bloque, y es previa porque el nivel 3 de la Instrucció lo es.
- Señal de nivel 3 en el DTO (candidata_nivel_3: bool + motivos): revision_resultado =
  reclasificada en alguna versión, o promoción solicitada. No se infiere nada más: la
  Instrucció deja la valoración a personas, y la plataforma solo la señala.
- Tenancy: la organización B puede REFERENCIAR una función publicada de A (y las de
  plataforma), nunca las no publicadas de otra; solo la autora (o plataforma) versiona.
- acciones_permitidas por rol y estado (versionar, retirar, revisar, suspender,
  reactivar, solicitar_promocion, promover, adoptar_version) las calcula el servidor y
  van en el DTO — el frontend itera, no decide (regla maestra 2). Un usuario sin permisos
  recibe la lista vacía (test obligatorio de la regla).

## Frontend (panel admin)
- Página de catálogo: lista con origen y nivel (mía · nivel 2 / de plataforma · nivel 3 /
  publicada por otra), detalle con el contrato legible (slots y parámetros), la
  declaración responsable, los hallazgos del auditor y las versiones con su estado y su
  revisión. Una versión suspendida muestra el motivo.
- Página o pestaña «Revisión posterior»: la cola con filtros y el botón de muestra
  aleatoria; acciones desde acciones_permitidas. Es la pantalla de la UADTI y del admin.
- Botones desde acciones_permitidas del DTO. i18n es/ca/en. Orval regenerado.

## Tests (mínimo 10)
- Una versión recién registrada aparece en la cola sin_revisar y es usable a la vez
  (revisar no bloquea usar).
- muestra=N devuelve N no revisadas y ninguna revisada.
- Revisar con `correcciones` no cambia el estado; con `reclasificada` marca
  candidata_nivel_3.
- Suspender sin motivo -> 422; con motivo -> suspendida y el bloque anclado falla en
  alto con ese motivo; reactivar por el autor -> 403; por el admin -> registrada.
- Solo superadmin promociona (403 al admin); promover sin valoracion -> 422.
- B referencia la publicada de A; 404/403 sobre la no publicada.
- Solo la autora versiona una función publicada.
- La promoción no cambia code_sha256 de ninguna versión.
- Usuario sin permisos -> acciones_permitidas vacía.
- Frontend: los botones se generan desde acciones_permitidas; la cola pinta desde el DTO.
```

**Verificación**: navegador — registrar una función en una organización y usarla de inmediato en
una plantilla; verla en la cola de revisión; suspenderla y ver el bloque fallar con el motivo;
reactivarla; solicitar y resolver la promoción como superadmin; referenciarla desde otra
organización; consola y red limpias.

---

### Prompt FUN.5 (RED/GREEN) — El origen empaquetado: funciones que llegan por *entry point*

**Modelo sugerido**: **Opus** — es la costura entre el repositorio de un tercero y el catálogo;
las decisiones de confianza y de anclaje están tomadas arriba, pero encajarlas sin duplicar el
validador ni el nodo exige criterio.

**Objetivo**: que un equipo de desarrollo mantenga funciones en su propio repositorio, con su CI
y su semver, y que la plataforma las registre, valide, referencie, ejecute y trace **igual** que
las de autoservicio. Es la respuesta a «¿qué valor añade hacerlo en la herramienta en vez de en
Claude Code?»: el código se queda donde lo escribe quien lo mantiene; la plataforma se queda con
la revisión, el manifiesto, la trazabilidad y el contrato.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.5 (RED/GREEN) — origen paquete via entry points. Deploy: edge

## El descriptor que exporta un paquete (contrato público mínimo, en app/core o en un
## paquete govgenai-sdk ligero si ya existe uno para REG; si no, aquí y se mueve después)
- FuncionEmpaquetada(nombre: str, version: str semver, contrato: ContratoFuncion (el de
  FUN.2, sin variantes, declaración responsable incluida: una función corporativa también
  declara finalidad y categorías de datos), run: Callable[[EntradaValidada],
  ExtractionResult]).
- Grupo de entry points: govgenai.funciones. Cada entry point apunta a una instancia del
  descriptor. La distribución (nombre del paquete pip) se lee de los metadatos del entry
  point y forma, con el nombre, el entry_point «distribucion:nombre» de FUN.1.

## Sincronización al arrancar (lifespan, como el resto de arranques)
- Descubrir los entry points del grupo. Para cada uno: validar el contrato con el
  validador de FUN.2 -> si es incoherente, el arranque FALLA EN ALTO nombrando el paquete
  y la función (nunca registrar a medias ni saltársela con un warning).
- Upsert de HubFuncion(origen=paquete, organizacion_id nulo, publicada_en = ahora si es
  nueva). Si la version_paquete instalada no existe aún como HubFuncionVersion: crear
  versión nueva (ordinal siguiente) con version_paquete, code nulo y code_sha256 = sha256
  de inspect.getsource(run). Las versiones anteriores de esa función que ya no están
  instaladas pasan a estado no_instalada (no se borran: hay manifiestos que las citan).
- Un entry point que desaparece (paquete desinstalado): TODAS sus versiones pasan a
  no_instalada; la función se conserva.
- Idempotente: arrancar dos veces no crea nada nuevo.

## Resolución (el ResolvedorDeFuncion de FUN.3 gana el segundo origen; el nodo no cambia)
- funcion_ref anclada a version N de una función paquete: buscar la versión instalada
  (estado registrada) de esa función. Si su version_paquete tiene el MISMO mayor que la
  anclada -> ejecutar esa (compatibilidad por contrato semver), y el RunManifest registra
  la version_paquete EXACTA y su code_sha256, no la anclada. Mayor distinto, o ninguna
  instalada -> fallo EN ALTO con mensaje que nombra función, mayor anclado y mayor
  instalado.
- La entrada se valida contra el contrato ANTES de llamar a run (mismo punto que FUN.2).
- run se ejecuta in-process, en el executor de hilos si es síncrono (regla de asincronía
  total); la salida se valida como ExtractionResult igual que la del sandbox.

## Catálogo (FUN.4) y acciones
- El DTO expone origen y, en paquete, distribución y version_paquete. acciones_permitidas
  para una función paquete NO incluye versionar ni promover (se versiona con pip y ya es
  de plataforma); sí incluye retirar (el superadmin puede vetar una instalada).

## Fixture de pruebas
- Un paquete mínimo bajo tests/fixtures/paquete_funcion_demo/ con pyproject y un entry
  point real, instalado en editable en el entorno de tests (o registrado con
  importlib.metadata simulado si instalar en la suite resulta frágil: decidirlo midiendo,
  no suponiendo; y documentar la elección).

## Tests (mínimo 8) — tests/modules/redaccion/test_fun5_paquete.py
- Arrancar con el paquete demo crea la función (origen=paquete, ámbito plataforma) y su
  versión con version_paquete y code_sha256 de la fuente.
- Contrato incoherente en el paquete -> el arranque falla nombrándolo (no hay fila).
- Idempotencia del arranque.
- Una plantilla referencia la función paquete y ejecuta; el RunManifest lleva la
  version_paquete exacta y el hash.
- Mismo mayor instalado distinto del anclado (1.2.0 anclado, 1.3.0 instalado) -> ejecuta
  1.3.0 y el manifiesto lo dice.
- Mayor distinto (1.x anclado, 2.0.0 instalado) -> fallo en alto con el mensaje.
- Paquete desinstalado -> versiones no_instalada, función conservada, bloque falla en
  alto.
- Entrada inválida -> error tipado SIN llamar a run (espía).
- acciones_permitidas de una función paquete no contiene versionar ni promover.
```

**Verificación**: suite del directorio + higiene verdes; en navegador, la función del paquete demo
aparece en el catálogo con su origen y su distribución, y una plantilla la referencia y genera.

---

### Prompt FUN.6 (RED/GREEN) — Consumo externo: `POST /api/v1/funciones/{id}/run` (tras REG)

**Modelo sugerido**: **Sonnet** — endpoint sobre patrones ya establecidos (scopes de REG.2,
sandbox de SBX).

**Objetivo**: que una aplicación externa ejecute una función del catálogo por API, con PAT,
cuota y rastro en el registro de actividad. Vale para los dos orígenes: la API no sabe de dónde
viene el código, solo del contrato.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.6 (RED/GREEN) — ejecución de funciones por API. Deploy: edge

- Scope nuevo funciones:execute en el catálogo PAT (emisible por superadmin y admin).
- POST /api/v1/funciones/{funcion_id}/run con version explícita en el cuerpo (el
  anclaje también rige fuera: sin version no se ejecuta), entrada validada contra el
  contrato (FUN.2), ejecución en sandbox con timeout y límite de tamaño de entrada,
  salida = ExtractionResult.
- La organización se deriva del dueño del PAT; solo funciones propias o publicadas, y
  solo versiones en estado registrada: una suspendida devuelve 423 con el motivo.
- Evento en el registro de actividad de REG: herramienta = cliente del PAT, finalidad =
  la declarada por la función, categorías de datos = las declaradas, referencia
  funcion_id@version + code_sha256. Sin payloads, como siempre.

## Tests (mínimo 6)
- Sin scope -> 403; con scope -> ejecuta.
- Entrada inválida -> 422 tipado sin tocar el sandbox.
- Función de otra organización no publicada -> 404.
- Versión suspendida -> 423 con el motivo, sin tocar el sandbox.
- El evento REG se escribe sin contenido de la entrada.
- Timeout del sandbox -> error controlado, no 500 opaco.
```

**Verificación**: `curl` real contra el endpoint con un PAT de prueba; el evento visible en la
lectura del registro (REG.5).

---

### Prompt FUN.7 — Verificación de punta a punta y documentación

**Modelo sugerido**: **Sonnet**.

**Objetivo**: el ciclo completo recorrido de verdad, y el contrato escrito para el siguiente
consumidor (Fase 3) y para el primer equipo que empaquete una función.

**Instrucciones al agente**:
```markdown
# PROMPT FUN.7 — cierre del bloque

## Recorrido en navegador (evidencias en el informe de cierre)
1. Registrar un script escrito fuera (pegado) con su declaración responsable: sin
   ninguna aprobación, aparece como función v1 registrada y usable.
2. Usarla en DOS plantillas distintas; generar los dos informes.
3. Verla en la cola de revisión posterior; pedir una muestra; revisarla como
   `correcciones`; suspenderla con motivo y ver el bloque fallar con ese motivo;
   reactivarla.
4. Publicar v2 con un arreglo: las dos plantillas siguen en v1 (comprobado); adoptar v2
   en una; regenerar y ver el arreglo solo ahí.
5. Solicitar la promoción como admin; promoverla como superadmin con valoración;
   referenciarla desde otra organización.
6. La función del paquete demo (FUN.5) aparece con su origen, nivel 3 y distribución; una
   plantilla la referencia y genera; el RunManifest del informe muestra version_paquete y
   hash.
7. read_console_messages y read_network_requests limpios en cada paso.

## docs/CATALOGO_FUNCIONES.md
- El contrato campo a campo (declaración responsable incluida), el ciclo de versiones
  (draft/registrada/suspendida/retirada/no_instalada, inmutabilidad, anclaje), quién
  puede qué (autora/admin/superadmin/consumidora), y el puente a Fase 3: las acciones de
  fase de expediente referencian plantilla@versión y función@versión — con el enlace a la
  restricción escrita en Plan_TDD_Fase3.md.
- Sección «Correspondencia con la Instrucció 02/2026»: nivel 2 = registro en la
  organización; nivel 3 = promoción o paquete; declaración responsable; revisión
  posterior y muestreo; suspensión; y la diferencia honesta con la regla 2 (el código va a
  los datos, al nodo institucional, no al equipo de la persona: un régimen más
  controlado pero distinto, que UADTI y OIATI deben dar por bueno explícitamente).
- Sección «Llevar tu script al catálogo» (para la persona referente): cómo envolver un
  script de nivel 1 en el contrato (slots, parámetros, ExtractionResult), qué mira el
  auditor y por qué, qué pasa en el sandbox, qué se declara.
- Sección «La caja de herramientas»: las reglas del auditor AST (módulos permitidos,
  prohibiciones) listadas desde el código (no copiadas a mano: un test comprueba que el
  documento y el auditor coinciden), con la petición explícita a la UADTI de contrastarlas
  con las Guías Operativas Técnicas.
- Sección «Empaquetar una función»: el descriptor, el grupo de entry points, qué valida
  la plataforma al arrancar, la regla del mayor de semver, qué registra el manifiesto, y
  la frontera de confianza dicha sin rodeos (corre in-process; quien instala responde).
  Es el documento que se le da al primer equipo externo, así que se escribe para él.
```

**Al cerrar el bloque**: suite completa desde Git Bash; `.bat` humano solo si queda algo
irreducible (previsiblemente nada: todo el ciclo es verificable en navegador).

---
