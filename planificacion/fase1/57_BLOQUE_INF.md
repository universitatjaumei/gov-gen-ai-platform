## Bloque INF — El módulo de informes, utilizable de punta a punta

> **Planificado el 2026-08-20**, a partir de las pruebas humanas del usuario sobre los dos caminos del
> módulo: generar un informe con IA desde cero, y ejecutar un informe de seguimiento desde plantilla.
> **Ninguno de los dos llegó al final.** Trece observaciones, y las dos que importan no son de estilo:
> son la razón por la que el usuario se quedó sin ninguna acción que pulsar.
>
> **Bloqueo A — el fichero nunca se subió, y nada lo dijo.** En el log no hay una sola petición de
> subida: tras crear el workspace hay dos `POST .../run` a secas. `WorkspacePage.tsx` tiene **dos
> caminos que lanzan la generación y uno se salta los datos**: el submit del formulario del contrato
> (líneas 85-100) sube y luego ejecuta; el botón azul destacado (líneas 137-147) ejecuta sin subir
> nada. De ahí sale toda la cascada: `Required input slot missing: 'datos'` → `No artifact found for
> block 't_matricula'` → las dos tablas sin datos → los dos bloques de IA que se apoyan en ellas en
> `Error (recuperable)`. Comprobado en la base de datos: **la plantilla no tiene ningún defecto**
> —pide un slot `datos` de tipo `markdown` y sus bloques de IA anclan bien a su tabla—. El fallo es
> de la pantalla.
>
> **Bloqueo B — la pantalla y el servidor no se ponen de acuerdo sobre qué es «pendiente»**, y esto
> es un defecto de contrato. `preview_builder.py:37-49` considera pendiente todo bloque de IA que no
> esté en `{approved, locked}`; `AIBlockReviewPanel.tsx` considera pendiente solo el que está en
> `needs_review`. Un bloque de IA que **falló** no está en ninguno de los dos conjuntos: cae en el
> hueco. Resultado exacto de lo observado: el panel de revisión —que sí se estaba renderizando,
> `ai_review_panel_enabled = True` en la plantilla real— anunciaba «Todos los apartados aprobados —
> listo para ensamblar», mientras la vista previa y la exportación devolvían 409 por esos mismos
> bloques. No es que el usuario no encontrara dónde validar: lo tenía delante diciéndole que no había
> nada que validar. **El frontend está calculando el estado en vez de recibirlo**, que es lo que
> prohíbe la regla maestra nº2 de `CLAUDE.md`.
>
> **Una regresión respecto al legacy, señalada por el usuario.** `propose` recibe **solo**
> `body.prompt_nl`: ninguna muestra de datos. El legacy sí la mandaba —`etl_factory.py:146-200`
> componía el prompt con `columns`, `dtypes`, `row_count` y `df.head(3)`, y **anonimizaba la muestra
> antes de enviarla** (línea 152)—. Pedirle a un modelo la estructura de un informe sobre un CSV cuyas
> columnas no ha visto es pedirle que adivine, y adivinó: ancló la valoración al bloque `TABLE` en vez
> de al `DETERMINISTIC_DATA`, que es justo lo que el validador rechaza.
>
> **Y el prompt induce el error que el validador castiga.** `llm_spec_service.py:85` describe
> `data_block_refs` como «the table or tables this passage is about». Para el modelo, la «tabla» es el
> bloque `TABLE`. El validador exige un bloque que produzca datos. El texto del prompt es la causa,
> no el modelo.
>
> **Decisión de alcance tomada por el usuario el 2026-08-20**: el control de acceso se resuelve **por
> módulos concedidos, no con un rol nuevo**. Hoy no hay ninguno: `App.tsx:92` mete todas las rutas
> bajo un `PrivateRoute` que solo comprueba que hay sesión, no existe un solo `role ===` en la capa de
> navegación, y los routers de `redaccion` usan `get_current_user` a secas. Es decir: cualquier
> trabajador con cuenta puede hoy listar y editar los chatbots institucionales y la configuración de
> LLM. Con el módulo de informes abierto a toda la universidad, eso deja de ser una asimetría teórica.
> El rol `informer` **no sirve** para esto: su contrato es «supervisa y valida respuestas de la IA»
> —control de calidad de chatbots—, no autoría de informes.

### Prompt INF.1 (RED/GREEN) — Un solo camino para generar el informe

**Modelo sugerido**: **Opus** — decide la forma de la pantalla principal del módulo.

```
# PROMPT INF.1 (RED/GREEN) — Un solo camino para generar
# Deploy: edge (frontend/src/redaccion/, routers/redaccion/)

## Por que
`WorkspacePage.tsx` ofrece dos disparadores de la generacion y **uno se salta la subida de datos**:
el submit del formulario del contrato (lineas 85-100) sube los ficheros y luego lanza `run`; el boton
azul destacado (lineas 137-147) lanza `run` sin subir nada. En la prueba humana el usuario pulso el
azul, que es el que parece principal, y el informe se ejecuto sin datos.

Lo que vino despues no fue un error, fue silencio: el `run` devolvio 202, la pantalla no dijo nada, y
el diagnostico quedo en tres warnings que solo se ven volviendo atras con el navegador. Un boton que
lanza un trabajo condenado a fallar y no lo advierte es peor que un boton roto.

## Que hacer
1. **Un solo disparador.** Retirar el boton que ejecuta sin subir. El submit del formulario del
   contrato pasa a ser la unica via: sube lo que el contrato pida y encadena el `run`.
2. **Los slots obligatorios se validan antes de lanzar nada**, en el propio campo y con el texto del
   contrato (`input_contract.required_slots`), no despues en una lista de warnings. El zod de
   `ReportUIContractRenderer` hoy solo valida `manual_fields`: tiene que cubrir tambien los
   `dropzones` requeridos.
3. **Reejecutar un informe ya ejecutado sigue siendo posible** —es el caso normal cuando se corrige
   un dato— pero reusando lo ya subido, no ignorandolo: si los slots estan satisfechos, el boton
   dice que va a reejecutar con los ficheros que ya hay.
4. Mientras el `run` esta en marcha, la pantalla lo dice donde se pulso. Ya hay `refetchInterval`
   sobre `drafting`/`extracting` (lineas 62-65): falta que se vea.

## Tests (RED primero)
- RED backend: `POST /workspaces/{id}/run` con un slot requerido sin satisfacer responde 422 con el
  `slot_id` que falta, en vez de aceptar 202 y fallar dentro. Hoy acepta.
- RED frontend: la pantalla no permite enviar si un dropzone requerido esta vacio, y nombra el slot.
- RED frontend: no existe ningun control que invoque `run` sin pasar por la subida (el test falla si
  alguien lo reintroduce).

## Criterio de done
- [ ] Un solo camino para generar, verificado en navegador con el caso real del usuario
- [ ] Un slot obligatorio vacio se dice antes de lanzar, en el campo
- [ ] La reejecucion reusa lo subido
- [ ] `grep` a cero de cualquier llamada a `run` fuera del submit del contrato
```

---

### Prompt INF.2 (RED/GREEN) — El servidor dice qué se puede hacer con cada bloque

**Modelo sugerido**: **Opus** — cambia el contrato y toca la máquina de estados.

```
# PROMPT INF.2 (RED/GREEN) — Acciones permitidas por bloque
# Deploy: edge (modules/redaccion/, routers/redaccion/, frontend/src/redaccion/)

## Por que
El servidor y la pantalla usan **dos definiciones distintas de «pendiente»** y un bloque cae en el
hueco entre las dos:

    preview_builder.py:37-49   pendiente = bloque de IA cuyo status NO esta en {approved, locked}
    AIBlockReviewPanel.tsx     pendientes = blocks.filter(b => b.status === 'needs_review')

Un bloque de IA que **fallo** no esta `approved` ni esta `needs_review`. Consecuencia medida en la
prueba humana: el panel anuncio «Todos los apartados aprobados — listo para ensamblar» mientras la
vista previa y la exportacion devolvian 409 por esos dos bloques, y **no habia ningun boton que
pulsar** porque el panel solo pinta acciones para `needs_review`. El usuario se quedo sin salida.

La causa de fondo es que el frontend **calcula** el estado. La regla maestra nº2 de `CLAUDE.md` dice
que eso lo decide el servidor y el cliente itera lo que reciba. Aqui aplica igual que en expedientes.

## Que hacer
1. `BlockStateOut` gana **`acciones_permitidas: list[str]`**, calculado en el servidor a partir de
   `kind`, `status`, `failure_kind` y el rol de quien pregunta. Un bloque de IA en error ofrece
   `retry` y `edit`; uno en `needs_review` ofrece `approve`, `reject`, `regenerate`, `edit`; uno
   `approved` no ofrece nada o `reopen`. Un `DETERMINISTIC_DATA` sin datos ofrece `retry`.
2. `AIBlockReviewPanel` **deja de filtrar por `needs_review`**: pinta los bloques que traigan
   acciones e itera `acciones_permitidas` para generar los botones. El test falla si el componente
   vuelve a comparar `status` con un literal.
3. **Un bloque en error deja de ser terminal para el informe**: se puede reintentar o escribir a
   mano, que es lo que desbloquea el caso del usuario.
4. Regenerar el contrato con Orval y usar los tipos generados, sin interfaces a mano.
5. **Anomalia a resolver en este prompt**: el workspace de la prueba quedo en BD como
   `status = assembled` con dos bloques de IA sin aprobar. Averiguar si el ensamblado se alcanza sin
   pasar el gate —agujero en la maquina de estados— o si `assembled` lo escribio otra cosa —etiqueta
   que miente—. Lo que sea, con su test.

## Tests (RED primero)
- RED: un bloque de IA en error trae `retry` y `edit` en `acciones_permitidas`; hoy no existe el campo.
- RED: quien no tiene permiso de aprobar recibe la lista sin `approve` (mismo patron que expedientes).
- RED frontend: con un bloque en error, el panel ofrece boton; hoy anuncia «todo aprobado».
- RED: el ensamblado no se alcanza con bloques de IA sin aprobar.

## Criterio de done
- [ ] Ningun `status ===` decidiendo acciones en el frontend (`grep` a cero)
- [ ] El caso real del usuario se desbloquea, verificado en navegador
- [ ] La incoherencia de `assembled` resuelta y con test
- [ ] Contrato regenerado
```

---

### Prompt INF.3 (RED/GREEN) — El 409 se explica y ofrece salida

**Modelo sugerido**: **Sonnet** — alcance cerrado, el dato ya viaja.

```
# PROMPT INF.3 (RED/GREEN) — Un 409 que dice que hacer
# Deploy: edge (frontend/src/redaccion/)

## Por que
«Exportar a Word no hace nada.» Hace: pide el DOCX, recibe 409 y **se calla**. El `catch` de
`WorkspacePage.exportar()` guarda el mensaje en `errorDeSubida`, que se pinta **dentro de la seccion
del contrato** (lineas 130-132): si esa seccion no esta visible, el error no se pinta en ningun
sitio. Un fallo silencioso es indistinguible de un boton muerto.

Y la vista previa si explica el 409, pero en un callejon: `App.tsx:126-127` la monta **fuera del
layout**, a proposito, como vista de impresion. Sin navegacion no hay vuelta, y el usuario tuvo que
descubrir que se sale con el boton atras del navegador.

El servidor ya manda lo necesario: el `detail` del 409 trae `pending_block_ids`.

## Que hacer
1. Los errores de la pantalla se pintan en un sitio **siempre visible**, no dentro de una seccion
   condicional. Uno por operacion, con el texto de lo que ha pasado.
2. Un 409 de vista previa o exportacion se traduce a lenguaje de quien pide un informe y convierte
   `pending_block_ids` en **enlaces al bloque** que hay que atender.
3. La vista previa gana una vuelta explicita al informe. Sigue sin menu —es vista de impresion— pero
   una vista sin salida no es una vista de impresion, es una trampa.

## Tests (RED primero)
- RED: con la exportacion devolviendo 409, la pantalla muestra el motivo y un enlace por bloque
  pendiente. Hoy no muestra nada.
- RED: la vista previa ofrece un control de vuelta al informe.

## Criterio de done
- [ ] Ninguna operacion falla en silencio, verificado en navegador provocando el 409
- [ ] Los bloques pendientes son alcanzables desde el mensaje
- [ ] Se sale de la vista previa sin el boton atras del navegador
```

---

### Prompt INF.4 (RED/GREEN + recuperación de legacy) — La propuesta ve la estructura de los datos

**Modelo sugerido**: **Opus** — recupera un diseño del legacy y cruza la frontera de anonimización.

```
# PROMPT INF.4 (RED/GREEN) — La IA propone sobre datos que ha visto
# Deploy: edge (modules/redaccion/services/, routers/redaccion/, frontend)

## Por que
`propose` recibe **solo** `body.prompt_nl` (`llm_drafts_router.py:128`). Ninguna muestra de datos.
El usuario pidio un informe sobre un CSV de saldos describiendo las columnas **a mano en el prompt**,
y el modelo tuvo que adivinar el resto. Adivino mal.

El legacy no lo hacia asi. `etl_factory.py:146-200` preparaba el contexto del fichero y lo metia en
el prompt:

    'columns': list(df.columns),
    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
    'sample_rows': df.head(3).to_dict(orient='records'),
    'row_count': len(df)

Y **anonimizaba la muestra antes de enviarla** (linea 152: `ctx.anonymize(sample_rows)`). Es el
diseno correcto y se perdio en la migracion. Lo senalo el usuario, no se dedujo del codigo.

## Que hacer
1. `propose` acepta un **fichero de muestra opcional**. Si viene, el servicio compone el contexto
   como el legacy: nombres de columna, tipos inferidos, numero de filas y las tres primeras filas.
2. **La muestra se anonimiza antes de salir hacia el modelo.** Por la frontera edge-cloud de
   `CLAUDE.md`, eso pasa en el servicio edge: `model_factory` recibe datos ya anonimizados y no
   anonimiza. Reusar `WorkspaceAnonymization`, que ya existe en el modulo.
3. Sin fichero, el comportamiento no cambia: el modelo propone desde el texto. No se convierte en
   obligatorio lo que hoy funciona.
4. En la pantalla, ofrecer la muestra **antes** de escribir el prompt, diciendo para que sirve: que
   sin ella el modelo no conoce las columnas.
5. El prompt del sistema declara explicitamente que las columnas listadas son **las que existen** y
   que no debe inventar otras.

## Tests (RED primero)
- RED: `propose` con un CSV adjunto incluye columnas, tipos y tres filas en el prompt; hoy no acepta
  fichero.
- RED: los valores de la muestra salen anonimizados hacia el modelo (mock con `spec=`, que es la
  leccion de `project_external_client_mock_spec`).
- RED: `propose` sin fichero sigue funcionando igual.
- RED e2e con el caso real de tesoreria: la propuesta resultante pasa el validador.

## Criterio de done
- [ ] El caso del usuario (CSV de saldos, agrupado por ano y mes) produce una propuesta valida
- [ ] Ningun valor sin anonimizar sale hacia el LLM
- [ ] Sin fichero, nada cambia
- [ ] Contrato regenerado
```

---

### Prompt INF.5 (RED/GREEN) — El prompt deja de inducir el error que el validador castiga

**Modelo sugerido**: **Sonnet** — cambio localizado con test sobre el texto.

```
# PROMPT INF.5 (RED/GREEN) — Que `data_block_refs` se entienda
# Deploy: edge (modules/redaccion/services/llm_spec_service.py)

## Por que
Los dos errores rojos que dejaron al usuario sin poder aprobar:

    blocks[b6].data_block_refs: AI_SUMMARY block 'b6' valora 'b4', que no produce datos ('TABLE')
    blocks[b6].data_block_refs: AI_SUMMARY block 'b6' valora 'b5', que no produce datos ('CHART')

El validador tiene razon (`draft_validator.py:94-104`): una valoracion debe apoyarse en el bloque que
**produce** los datos, no en el que los dibuja. Pero el prompt describe el campo como «the table or
tables this passage is about» (`llm_spec_service.py:85`), y para el modelo la «tabla» del informe es
el bloque `TABLE`. **El texto del prompt causa el error.** No es un fallo del modelo.

## Que hacer
1. Reescribir la descripcion de `data_block_refs`: es el id de un bloque `DETERMINISTIC_DATA` o
   `DATA_TRANSFORM`, **nunca** el de un `TABLE` ni un `CHART`, con una frase que diga por que —el
   `TABLE` es una presentacion, los datos estan antes—.
2. Anadir un ejemplo minimo correcto en el prompt: bloque de datos, tabla que lo pinta, valoracion
   que apunta **al de datos**.
3. Mismo repaso al resto de campos que el validador comprueba y el prompt describe en prosa
   ambigua: `data_block_ref` de TABLE/CHART y `config.source_block_ref` de DATA_TRANSFORM. Si el
   validador lo exige, el prompt lo dice con el nombre del kind.

## Tests (RED primero)
- RED: el texto del prompt nombra `DETERMINISTIC_DATA`/`DATA_TRANSFORM` y excluye TABLE/CHART para
  `data_block_refs`.
- RED e2e con un doble del LLM que devuelve la propuesta del caso real: pasa el validador.

## Criterio de done
- [ ] Una propuesta con tabla, grafico y valoracion valida a la primera
- [ ] Verificado con el prompt literal del usuario sobre tesoreria
```

---

### Prompt INF.6 (RED/GREEN) — Una propuesta inválida se arregla sin empezar de cero

**Modelo sugerido**: **Opus** — decide cómo se corrige una propuesta.

```
# PROMPT INF.6 (RED/GREEN) — Corregir la propuesta, no rehacerla
# Deploy: edge (frontend/src/redaccion/pages/LLMDraftPreviewPage.tsx)

## Por que
Con la propuesta invalida, «Aprobar y crear» queda deshabilitado (exige `ok=true`) y **la unica
salida es volver a escribir el prompt entero**. El usuario se quedo ahi: dos lineas rojas con
`blocks[b6].data_block_refs` y ningun sitio donde tocar.

INF.5 hace que el error ocurra mucho menos. Este prompt hace que, cuando ocurra, se pueda arreglar.

## Que hacer
1. Los errores del validador se muestran **junto al bloque culpable**, no en una lista suelta arriba,
   y en lenguaje de quien pide un informe: «esta valoracion apunta al grafico; tiene que apuntar a
   los datos que el grafico dibuja».
2. Donde el arreglo es mecanico —cambiar la referencia al bloque de datos correcto— ofrecerlo como
   una accion. Donde no lo es, dejar editar el campo.
3. Revalidar sin volver a llamar al modelo: `validate` ya existe y es barato.
4. El progreso de la generacion, que hoy es solo el boton deshabilitado con el texto `t('loading')`
   (`LLMDraftPreviewPage.tsx:81`): decir que se esta consultando al modelo y que tarda. Una espera de
   treinta segundos sin senal se lee como una pantalla colgada, y asi la leyo el usuario.
5. Retirar los strings incrustados de esta pantalla: 'Generar propuesta' (linea 81) y 'Aprobar y
   crear' (linea 158) violan la regla de i18n.

## Tests (RED primero)
- RED: un error del validador se renderiza junto a su bloque y con texto traducido.
- RED: corregir la referencia y revalidar habilita el boton sin llamar a `propose`.
- RED: mientras propone, la pantalla anuncia que esta trabajando.

## Criterio de done
- [ ] De propuesta invalida a plantilla creada sin reescribir el prompt, verificado en navegador
- [ ] Ningun string incrustado en la pantalla (`grep`)
```

---

### Prompt INF.7 (RED/GREEN + migración) — Acceso por módulos concedidos

**Modelo sugerido**: **Opus** — modelo de datos, migración y frontera de autorización.

```
# PROMPT INF.7 (RED/GREEN) — Modulos concedidos por usuario
# Deploy: cloud (core/auth, routers) + frontend

## Por que
Hoy no hay control de acceso por funcion. `App.tsx:92` mete **todas** las rutas bajo un
`PrivateRoute` que solo comprueba que hay sesion; no existe un solo `role ===` en la capa de
navegacion; `App.tsx:94` aterriza a todo el mundo en `/hub/chatbots`; y los routers de `redaccion`
usan `get_current_user` a secas. Es decir: cualquier trabajador con cuenta puede listar y editar los
chatbots institucionales y la configuracion de LLM.

Mientras la aplicacion la usaban administradores, era una asimetria teorica. Con el modulo de
informes abierto a toda la organizacion —el colectivo objetivo es «todo el que necesita hacer
informes»— deja de serlo.

**Por modulos, no por rol nuevo** (decision del usuario, 2026-08-20). Un rol `redactor` es mas barato
hoy y explota en cuanto alguien necesite informes y curacion pero no chatbots. Y el rol `informer`
que ya existe **no sirve**: su contrato es «supervisa y valida respuestas de la IA», que es control
de calidad de chatbots.

## Que hacer
1. Concesion de modulos por usuario, en tabla versionada y **no como Enum de Python ni
   `CheckConstraint`** —misma regla que el vocabulario del corpus: los modulos son dato—. Los modulos
   de hoy: `chatbots`, `curacion`, `informes`, `plataforma`.
2. **El servidor dice que modulos hay**, en `/auth/me`. El menu y las rutas se **generan iterando esa
   lista**; el frontend no decide nada. Mismo patron que `acciones_permitidas`.
3. Los routers exigen el modulo, no solo sesion: una dependencia `require_module("chatbots")` sobre
   los de chatbots y plataforma, `require_module("informes")` sobre los de `redaccion`. Sin modulo,
   403.
4. El aterrizaje deja de ser `/hub/chatbots` fijo: se cae al primer modulo concedido. Un usuario solo
   de informes entra en informes.
5. Migracion con los datos actuales: los `superadmin` y `admin` existentes reciben todos los modulos,
   para no romper a nadie. Aplicarla al terminar (`uv run alembic upgrade <rev>`) y mostrar
   `alembic current`.

## Tests (RED primero)
- RED: `/auth/me` devuelve los modulos concedidos; hoy no existe el campo.
- RED: un usuario solo con `informes` recibe 403 en los endpoints de chatbots y de LLM configs.
- RED frontend: el menu se construye desde la lista y no muestra chatbots sin el modulo.
- RED frontend: el test falla si alguna ruta se pinta sin consultar los modulos.
- RED: un `admin` existente conserva todo tras la migracion.

## Criterio de done
- [ ] Un usuario solo de informes no ve ni alcanza chatbots, verificado en navegador con dos sesiones
- [ ] Migracion aplicada y `alembic current` mostrado
- [ ] Los modulos son dato, no Enum (`grep` a cero de un Enum de modulos)
- [ ] Contrato regenerado
```

---

### Prompt INF.8 (RED/GREEN) — Los controles parecen controles

**Modelo sugerido**: **Sonnet** — alcance cerrado, lista cerrada de defectos observados.

```
# PROMPT INF.8 (RED/GREEN) — Que se vea donde hay que pulsar
# Deploy: edge (frontend/src/redaccion/, shared/layout/)

## Por que
Lista de lo que el usuario no reconocio como interfaz, cada cosa con su causa:

- «Aparece esta informacion como texto sin que se sepa que Tria un fitxer es un boton»: es un
  `<input type="file">` desnudo en `DynamicUploadSlots`, con el texto que pone el navegador **en su
  propio idioma**, y el submit es un `<button type="submit">` **sin una sola clase CSS**
  (`ReportUIContractRenderer.tsx:69`).
- «El copiloto tiene cuatro tablas de las cuales 3 estan totalmente en blanco»: `DrawerHub.tsx:7-12`
  declara cuatro pestanas y la linea 55 solo pinta contenido para `copilot`. Las otras tres no
  existen.
- «El cajon lateral deberia llevar una aspa»: no hay ningun control de cierre, y `FocusLock`
  (linea 28) **atrapa el foco dentro**. Con `role="dialog" aria-modal` y sin cierre ni Escape es un
  defecto de accesibilidad, no un adorno.

## Que hacer
1. Zona de subida con aspecto de zona de subida y **su propio texto**, del contrato y traducido, en
   vez del que pone el navegador. El nombre del fichero elegido se ve.
2. El submit del contrato con estilo de accion principal.
3. El cajon gana aspa y cierre con Escape, y devuelve el foco al boton que lo abrio.
4. Las tres pestanas sin contenido **se retiran** hasta que lo tengan. Una pestana en blanco no es
   una promesa, es un fallo aparente. (Si se decide implementarlas, es otro prompt.)
5. Retirar los strings incrustados: `DrawerHub.tsx` (etiquetas de pestana y
   `aria-label="Panel de herramientas"`) y `GenericReportWizard.tsx:47` ('Crear informe').
6. **Comprobar en navegador el unico hallazgo sin confirmar del analisis**: el usuario vio el estado
   de cada bloque dos veces. Puede ser solo el `<span className="sr-only">` de
   `WorkspaceEditor.tsx:74-76` apareciendo al copiar el texto, y entonces no hay nada que arreglar.
   Mirarlo antes de tocar nada.

## Y una cosa que no es de interfaz
`arranque.bat` levanta el backend con `--host 0.0.0.0`, que lo publica en toda la red. En el log de
las pruebas se ven decenas de `GET /?${jndi:dns://MDEDiscovery...}`: es el escaner de Microsoft
Defender sondeando el puerto con payloads de log4shell. Para desarrollo debe ser `127.0.0.1`.

## Tests (RED primero)
- RED: la zona de subida expone su etiqueta traducida y el nombre del fichero elegido.
- RED: el cajon tiene control de cierre accesible y Escape lo cierra.
- RED: no se renderiza ninguna pestana sin panel.
- RED: `grep` de strings incrustados en los tres ficheros, a cero.

## Criterio de done
- [ ] Verificado en navegador: se distingue donde se sube el fichero y donde se continua
- [ ] El cajon se cierra con raton y con teclado
- [ ] `arranque.bat` en 127.0.0.1
- [ ] El posible estado duplicado, confirmado o descartado con evidencia
```

---

### Prompt INF.9 (RED/GREEN) — Plantilla o informe suelto, explicado al elegir

**Modelo sugerido**: **Sonnet** — alcance cerrado.

```
# PROMPT INF.9 (RED/GREEN) — Que se entienda que se esta creando
# Deploy: edge (frontend/src/redaccion/)

## Por que
Del usuario: «Tampoco sabe la diferencia entre workspace y plantilla. Por el principio de
determinista first deberia sugerirse plantilla por defecto si se va a repetir el informe.»

La pantalla ofrece las dos opciones como equivalentes y con vocabulario interno —«workspace»—. Y la
eleccion importa: una plantilla se reusa, se versiona y su parte determinista se ejecuta igual cada
vez; un informe suelto se tira. Es la diferencia entre pagar el LLM una vez y pagarlo cada mes.

## Que hacer
1. Nombrar las dos cosas en el idioma de quien pide un informe: «plantilla reutilizable» y «informe
   de una sola vez». Que desaparezca «workspace» de la interfaz.
2. Recomendar plantilla, con la razon dicha: si el informe se repite, la plantilla lo vuelve
   determinista y barato.
3. Que se vea que una plantilla se puede usar despues sin volver a pasar por la IA.

## Tests (RED primero)
- RED: la pantalla de propuesta nombra las dos opciones sin la palabra «workspace» y recomienda una.
- RED: `grep` de «workspace» en textos visibles de i18n, a cero.

## Criterio de done
- [ ] Verificado en navegador
- [ ] Ninguna cadena visible dice «workspace»
```

---

### Prompt INF.10 (RED/GREEN) — El copiloto sabe dónde está

**Modelo sugerido**: **Opus** — decide qué contexto recibe el modelo.

```
# PROMPT INF.10 (RED/GREEN) — Un copiloto con contexto del informe
# Deploy: edge (modules/redaccion/, routers/redaccion/copilot_router.py)

## Por que
El usuario le pregunto «No se donde aprobar los bloques» y no obtuvo respuesta. El copiloto no
recibe el estado del informe: no sabe que bloques hay, en que estado estan ni que falta.

El legacy si lo tenia. `client_app/app/core/state.py:79` dejaba anotado el motivo: los datos cargados
se publican al estado «para que el Copiloto conozca las columnas disponibles».

## Que hacer
1. El copiloto recibe el contexto del workspace: bloques, estado de cada uno, avisos abiertos y
   slots sin satisfacer. Anonimizado antes de salir, por la frontera edge-cloud.
2. Las preguntas de «donde hago X» se responden con la accion concreta de **este** informe, apoyandose
   en `acciones_permitidas` de INF.2 en vez de en una descripcion generica de la interfaz.
3. Si el contexto dice que hay bloques pendientes, decirlo sin que se pregunte.

## Tests (RED primero)
- RED: el prompt del copiloto incluye los bloques y su estado; hoy no.
- RED: los datos del informe salen anonimizados (mock con `spec=`).
- RED: con dos bloques sin aprobar, la respuesta los nombra.

## Criterio de done
- [ ] «No se donde aprobar» obtiene una respuesta util, verificado en navegador
- [ ] Ningun dato sin anonimizar sale hacia el LLM
```

---

> **Orden y dependencias.** INF.1, INF.2 e INF.3 son los que convierten «no puedo terminar» en «puedo
> terminar»: sin ellos, los demás no se pueden ni probar de punta a punta. INF.4 e INF.5 arreglan el
> camino de la IA, y INF.5 es el más barato de los dos. INF.6 depende de INF.5. INF.7 es independiente
> del resto y puede adelantarse si la apertura del módulo corre prisa. INF.8, INF.9 e INF.10 son de
> comprensión y van al final a propósito: pulir una pantalla que todavía no deja acabar el trabajo es
> pintar sobre una puerta cerrada.

---
