## Bloque AIS — Aislamiento del núcleo y saneamiento previo al piloto (Subfase 1.B, PENDIENTE)

> **Contexto**: hallazgos de calidad y de aislamiento núcleo/configuración de
> `docs/VALORACION_PROYECTO.md` §2 y §5 (auditoría del 2026-08-24). No son bloqueantes de
> seguridad como SEC.9, pero sí conviene cerrarlos antes del piloto: uno de ellos (la paleta del
> panel) **bloquea de facto** que otra administración use el principal tal cual, que es el modelo
> de gobernanza que declaran `README.md` y `CONTRIBUTING.md`. Va **después de SEC.9 y antes de
> Deploy**. Lo genuinamente post-piloto queda anotado al final del bloque, no se ejecuta aquí.

---

### Prompt AIS.1 (RED/GREEN) — La paleta del panel a la cascada de temas [BLOQUEANTE OSS]

**Modelo sugerido**: **Opus** — hay que unificar dos sistemas de theming disjuntos sin romper el
panel ni el widget; decisión de qué tokens quedan estructurales y cuáles pasan a dato.

**Objetivo**: `frontend/src/index.css` define, con el comentario literal «UJI brand», los tokens
`--primary`/`--sidebar`/`--accent`/`--chart-*` que consumen todas las utilidades del panel, y la
cascada de temas (`hub_themes`, que escribe `--color-*`) **no los alcanza** por el mapeo
`@theme inline`. Un ayuntamiento que despliegue el principal tiene el panel con los colores de la
UJI y sin pantalla para cambiarlos. El proyecto ya ganó esta batalla para el logotipo (lo sacó del
bundle con `marcaNoViajaEnElRepo.test.ts`); falta el mismo movimiento para los colores.

```
# PROMPT AIS.1 (RED/GREEN) — un solo sistema de theming, marca fuera del código
# Deploy: n/a (frontend)

## Cambios
- Unificar los dos namespaces: que las utilidades del panel resuelvan contra los tokens que
  escribe injectThemeCSS (o que la cascada escriba los --* del panel). Los valores de index.css
  pasan a una paleta NEUTRA por defecto; la marca institucional se resuelve por hub_themes.
- Test hermano de marcaNoViajaEnElRepo.test.ts que prohíba comentarios/valores de marca
  institucional ("UJI", "brand", hex corporativos) en los tokens de index.css.

## Tests (RED primero)
# should_not_hardcode_institutional_brand_in_index_css
# should_apply_panel_palette_from_the_theme_cascade

## Cierre
- [ ] Verificación en navegador: cambiar el tema de una organización cambia el cromo del panel.
```

---

### Prompt AIS.2 (RED/GREEN) — Material de fork fuera del principal [ALTO OSS]

**Modelo sugerido**: **Sonnet** — retirada mecánica + dos entradas de catálogo; patrón conocido.

**Objetivo**: sacar del principal lo específico de una institución (§5.2 de la auditoría): la
credencial de desarrollo con el correo del autor, los prompts de sistema no sobreescribibles con
presunción institucional, y los selectores de spider hardcodeados.

```
# PROMPT AIS.2 (RED/GREEN) — DEV_ADMIN_EMAIL por entorno, prompts al catálogo, selectores a dato
# Deploy: shared

## Cambios
- seeds.py:35: DEV_ADMIN_EMAIL = os.getenv("DEV_ADMIN_EMAIL", "admin@example.local").
- Corregir docstrings de seguridad falsos: seeds.py:12 ("login no verifica pwd", falso desde
  SEC.1), main.py:3-6 (routers automation/telemetry "pendientes de registrar", borrados en 6e78b35).
- redactor_de_bloques.py:19: los dos prompts (_SISTEMA, PROMPT_VALORACION_DE_TENDENCIA,
  PROMPT_RESUMEN_DE_RESULTADOS) al catálogo ActividadLLM, sobreescribibles vía hub_activity_prompts
  como el resto. Quitar "una universidad pública" del camino de un ayuntamiento.
- spider_factory.py:9 y normativa_spider.py: retirar "uji" del frozenset (sus selectores son un
  duplicado exacto de "boe"); los selectores de portal pasan a dato (hub_web_sites), no a un dict
  de módulo. procedimientos_spider.py (procedimientos.uji.es) es material de fork: retirar del
  principal o marcarlo como plantilla vacía configurable.

## Tests (RED primero)
# should_read_dev_admin_email_from_env
# should_resolve_institutional_report_prompts_from_activity_catalog
# should_not_name_an_institution_in_the_spider_frozenset

## Cierre
- [ ] grep de "uji"/"Jaume"/dominio institucional en server/app (fuera de comentarios de
      procedencia y fixtures) = 0.
```

---

### Prompt AIS.3 (RED/GREEN) — El núcleo no importa de los módulos ni de los routers [ALTO — arquitectura]

**Modelo sugerido**: **Opus** — decidir la dirección de dependencias y refactorizar los 18
imports invertidos; incluye la decisión sobre `modules/automation/`.

**Objetivo**: `CONTRIBUTING.md` regula que un módulo no importe de otro módulo, pero la dirección
inversa no está regulada ni testada, y `core/` importa de `modules/` en 18 sitios, dos de ellos de
`routers/` (`modulos_service.py:32`, `saml/identity_service.py:131`), lo que invierte la jerarquía.
`core/` es la capa que un fork más querrá no tocar. Además hay dos cruces entre módulos
(`curation→agents_hub`, `curation→redaccion`).

```
# PROMPT AIS.3 (RED/GREEN) — test de dirección de imports + decisión sobre modules/automation
# Deploy: n/a (arquitectura)

## Cambios
- Test que prohíbe que core/ importe de modules/ y de routers/, y que un módulo importe de otro
  (o declarar agents_hub como segunda capa base y regularlo explícitamente, con la razón escrita).
- Refactor de los dos imports core->routers (mover user_to_uuid / normalizar_correo a core).
- DECISIÓN modules/automation: 1.401 LOC sin un solo consumidor (era el destino de AIBrainService).
  Cablear si Informes lo va a usar, o borrar (Caso B). No dejarlo en el árbol activo sin tests.

## Tests (RED primero) — tests/infra/test_import_direction.py
# should_forbid_core_importing_from_modules
# should_forbid_core_importing_from_routers
# should_forbid_module_to_module_imports (con la lista de excepciones declarada)

## Cierre
- [ ] modules/automation cableado con test, o borrado con grep a cero.
```

---

### Prompt AIS.4 (RED/GREEN) — El panel de anonimización llama sin token (401) [MEDIO — bug]

**Modelo sugerido**: **Sonnet** — un cambio de import; el cliente Orval correcto ya existe.

**Objetivo**: `frontend/src/redaccion/hooks/useAnonymizationApi.ts:22` es un módulo API a mano cuyo
`fetchJson` **no manda `Authorization`**, contra tres endpoints que exigen auth+módulo (todos
devuelven 401). El cliente Orval con los mismos tres nombres ya está generado; el bug es invisible
a los tests porque el hook está mockeado y al guardarraíl porque busca quién *construye*
`Authorization` y el fallo es no construirla.

```
# PROMPT AIS.4 (RED/GREEN) — anonimización: consumir el hook Orval, no el manual
# Deploy: n/a (frontend)

## Cambios
- WorkspaceAnonymizationPanel.tsx:8-11: importar useGetAnonymizationSummary /
  usePatchAnonymizationMode / useReAnalyzeAnonymization de
  generated/redaccion-anonymization en vez de ../hooks/useAnonymizationApi.
- Borrar useAnonymizationApi.ts (isla manual, Caso B).
- Ampliar contractFirstApi.test.ts para cazar módulos manuales que NO construyen Authorization
  (el hueco por el que este pasó).

## Tests (RED primero)
# should_send_authorization_on_anonymization_calls
# should_not_keep_a_manual_api_module_in_redaccion

## Cierre
- [ ] grep de fetch crudo en frontend/src (fuera de las exenciones del widget) = las 4 legítimas.
```

---

### Prompt AIS.5 (RED/GREEN) — La anonimización, política heredable y con evidencia del tratamiento [MEDIO]

**Modelo sugerido**: **Opus** — toca la cascada de ámbito y el contrato de un modo con
consecuencias jurídicas; la decisión de alcance ya está tomada, lo que queda es no dejar una
promesa más ancha que lo que se cumple.

> **Decisión del usuario (2026-08-24), que reorienta este prompt**: el piloto **no trata datos de
> ciudadanos**, y la anonimización **no debe ser obligatoria sino configurable** — depende del
> contrato con el proveedor LLM y del tipo de datos. **No se implementa bóveda cifrada antes del
> piloto.** La persistencia cifrada del mapa sigue siendo F2.A.4 (Vault Edge), post-piloto.

**Estado real, verificado al planificar (corrige la formulación inicial de la auditoría)**: la
anonimización **ya es política y no obligación**. `AnonymizationMode`
(`anonymization/run_context.py:55-69`) tiene cuatro valores —`off`, `detect_only`, `replace`,
`replace_with_disposition_7` (enmascara DNI/NIE/pasaporte de forma irreversible, conforme a la
Disposición Adicional 7ª de la LOPDGDD)— y es una columna por informe
(`redaccion/database/models.py:206`) con `replace` por defecto. Lo que la auditoría encontró es más
estrecho: **`REPLACE` promete en su propio docstring «revierte el output» y el mapa no sobrevive al
proceso** (`service.py:231-237`, no-op). Dentro de una ejecución funciona; entre sesiones no. Así
que el defecto no es que falte anonimización: es que la promesa es más ancha que el cumplimiento, y
no queda evidencia de qué tratamiento se aplicó.

**Y una observación de diseño que sale de la propia decisión**: «depende del contrato con el
proveedor y del tipo de datos» **no es una decisión por informe**, que es donde vive hoy el ajuste.
El contrato con el proveedor es de la **organización**. El modo por defecto debe descender en
cascada desde la organización (heredable, con `core/ambito.py`, igual que MT.6 hizo con los
prompts) y el informe solo debe poder **restringir**, nunca ampliar.

```
# PROMPT AIS.5 (RED/GREEN) — política por organización, promesa acotada, evidencia sin mapa
# Deploy: edge

## Cambios
- Modo por defecto HEREDABLE desde la organización (organizacion_id nullable = plataforma), con
  core/ambito.py. El informe puede restringir (hacia más protección) y NO ampliar: un workspace no
  puede bajar a 'off' lo que su organización fijó en 'replace'.
- Acotar la promesa de REPLACE: el docstring y la UI dicen que la reversión es DENTRO de la
  ejecución (es lo que el flujo necesita: el output vuelve de-anonimizado en el mismo run) y que
  la re-identificación posterior NO se ofrece. Sin promesas que el código no cumple.
- Evidencia del tratamiento SIN guardar el mapa: registrar en el manifiesto/auditoría del run qué
  modo se aplicó y cuántas entidades de cada tipo se sustituyeron —CONTEOS, no valores—. Satisface
  la exigencia de evidencia de MARCO_GOBERNANZA_IA.md sin crear un almacén de secretos.
- save_state/load_state: o se retiran (no dejar no-op que finge capacidad, regla "borra, no
  comentes"), o se documentan como el punto de extensión de F2.A.4. Elegir y justificar.

## Tests (RED primero)
# should_inherit_the_anonymization_mode_from_the_organisation
# should_let_a_workspace_restrict_but_not_widen_the_inherited_mode
# should_record_treatment_counts_without_storing_pii_values
# should_not_promise_cross_session_reidentification

## Cierre
- [ ] Decisión escrita en docs/ y coherente con MARCO_GOBERNANZA_IA.md.
- [ ] Ningún valor de PII en la evidencia del run (solo tipo y conteo).
```

---

### Prompt AIS.6 (RED/GREEN) — §13 de la AGPL: enlace al fuente en panel y widget [MEDIO OSS]

**Modelo sugerido**: **Sonnet** — patrón ya en uso (`CORPUS_SITE_BASE_URL`): variable de entorno,
vacío = desactivado.

**Objetivo**: el §13 no está implementado (el README lo admite). No existe `SOURCE_URL` ni enlace
al fuente en el pie del panel ni en el widget —«el caso que se olvida», según el propio README—. La
obligación es de quien despliega una versión modificada frente a los usuarios de esa instancia, e
incluye la ciudadanía que usa el widget.

```
# PROMPT AIS.6 (RED/GREEN) — SOURCE_URL configurable, visible donde están los usuarios
# Deploy: shared (config) + frontend (panel y widget)

## Cambios
- SOURCE_URL en .env.example (vacío = desactivado), servido por el backend.
- Pie del panel y del widget público: enlace "Código fuente" a SOURCE_URL cuando está definido.
  Apunta al fork en el commit desplegado, NO al principal (por eso es config, no URL fija).

## Tests (RED primero)
# should_render_source_link_when_source_url_is_set
# should_hide_source_link_when_source_url_is_empty
# should_show_source_link_in_the_public_widget

## Cierre
- [ ] Verificado en navegador en panel y widget.
```

---

### Prompt AIS.7 (RED/GREEN) — Infraestructura de contribución [MEDIO OSS]

**Modelo sugerido**: **Sonnet** — ficheros de gobernanza; sin lógica.

**Objetivo**: faltan piezas que hacen exigible el modelo de gobernanza y que un evaluador de pliego
(ENS) espera encontrar.

```
# PROMPT AIS.7 (docs) — PR template, SECURITY, CODEOWNERS, plantillas de issue
# Deploy: n/a

## Cambios
- .github/PULL_REQUEST_TEMPLATE.md con la pregunta central: "¿por qué esto es generalizable y no
  material de fork?" (la intervención de mayor rendimiento por menor coste de la auditoría).
- SECURITY.md con canal de divulgación responsable y política de embargo (destinatario: AAPP/ENS).
- CODEOWNERS que exija revisión de mantenedor sobre core/, migrations/ y la frontera edge/cloud.
- .github/ISSUE_TEMPLATE/ con campo "fork / modo de despliegue".

## Cierre
- [ ] Los cuatro ficheros existen y CONTRIBUTING.md los referencia.
```

---

### Prompt AIS.8 (RED/GREEN) — Higiene de arranque y observabilidad [MEDIO — calidad]

**Modelo sugerido**: **Sonnet** — cambios localizados de patrón conocido.

**Objetivo**: las tres piezas de higiene baratas de la auditoría §2.3 que conviene tener antes del
piloto (las caras —code-splitting, descomponer `ChatbotsPage`— quedan post-piloto, ver abajo).

```
# PROMPT AIS.8 (RED/GREEN) — logging estructurado, to_thread, DATABASE_URL que falle
# Deploy: shared

## Cambios
- Configuración de logging de la aplicación (niveles, timestamps) en el arranque; sustituir las
  157 print() de server/app por logger. El except Exception del scheduler de calidad
  (main.py:156) deja de tragarse el fallo con un print.
- report_exporter.py:108: subprocess.run de LibreOffice envuelto en asyncio.to_thread (no bloquear
  el event loop en async def to_pdf).
- db.py:13-16 y connection.py:18-19: DATABASE_URL sin fallback con credenciales; si falta,
  RuntimeError explícito (como JWT_SECRET_KEY), no conectar a ciegas a una BD conocida.
- **Guardarraíl del extra `local-models`** (añadido el 2026-08-24, ver más abajo): un test en
  tests/infra que afirme que `server/uv.lock` fija `torch`, `torchvision` y
  `sentence-transformers`.

## Tests (RED primero)
# should_fail_loudly_when_database_url_is_absent
# should_not_block_the_event_loop_on_pdf_export
# should_configure_application_logging_at_startup
# should_pin_the_local_models_stack_in_the_server_lock

## Cierre
- [ ] grep de print( en server/app = 0 (o solo en scripts de CLI).
```

> **Por qué el guardarraíl del lock entra aquí** (decisión del usuario, 2026-08-24). Salió de una
> alarma que resultó ser falsa y dejó un hueco real. El `uv.lock` **de la raíz** apareció con 558
> líneas borradas y la lectura razonable fue «la pila de torch desapareciendo por un `uv sync` sin
> el extra» — la trampa que ya está anotada en la memoria del proyecto. Al mirarlo no era eso: ese
> lock es del proyecto `automatia`, el legado NiceGUI de la raíz, y lo que se iba era **el árbol de
> Docling** poniéndose al día con EXT.3 (`docling-core`, `rapidocr`, `opencv`, `omegaconf`… más
> `accelerate` y `torchvision`, que allí sólo eran alcanzables a través de Docling). `server/uv.lock`
> —el que copia el `Dockerfile` y usa CI— está intacto y fija los tres paquetes. **Así que revertir
> habría sido lo contrario de lo que se quería**: volver a fijar el árbol que EXT.3 retiró, en un
> fichero que además desaparece con el Bloque NIC.
>
> Lo que sí quedó al descubierto: **CI hace `uv sync --frozen` sin `--extra local-models`**, así que
> el camino de los modelos locales no se ejercita en ninguna parte. El `--frozen` del `Dockerfile`
> protege la imagen —una inconsistencia falla en voz alta—, pero la instalación local de un edge no
> tiene nada que la vigile. El test es estático (lee el lock, no instala nada) y cuesta tres líneas.

---

### Lo que este bloque NO hace (queda anotado para después del piloto)

De los 14 puntos del §6 de la auditoría, lo genuinamente post-piloto se deja aquí escrito para que
el alcance esté acotado y no aparezca de sorpresa. No se ejecuta antes del piloto porque no
bloquea y su coste-beneficio mejora con datos reales delante:

- **Code-splitting del frontend** (item 14): 0 `React.lazy` en ~31.500 líneas; todo va a un bundle
  único con ~500 KB de clientes Orval. Coste de primera carga, no de corrección. Lazy routes
  cuando el piloto muestre el peso real.
- **Descomponer `ChatbotsPage.tsx`** (1.059 LOC, item 14): el nuevo fichero monolítico del
  frontend, el perfil que tenía `DocumentsPage` antes de CAL.3. Mismo patrón, otra instancia.
- **Retirada de `client_app/`** (§2.3): 469 ficheros `.py` de peso muerto en el repo, no en el
  artefacto. Ya asignada al **Bloque NIC**, después del despliegue.
- **`create_all` en el lifespan** (§2.3): mitigado por el servicio `migrate` de
  `docker-compose.prod.yml`; el `Dockerfile` sin `alembic upgrade head` merece **un aviso en la
  guía de despliegue** (Bloque Deploy/D.6), no un cambio de código ahora.
- **MT fase 2 completa** (MT.8–MT.21): vista y permisos multiorganización. Queda tras el piloto
  por decisión ya tomada (depende de cómo quede). MT.16 se adelanta a SEC.9.7 porque es lo único
  que valida el aislamiento, que el piloto monoorganización no ejercita.

---
