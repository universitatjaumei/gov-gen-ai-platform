## Bloque LEG — Retirada del legacy de prompts de AutomatIA

> **Planificado el 2026-08-18**, a partir de una pregunta del usuario sobre unos logs de arranque.
> No es limpieza estética: esta vía **escribe en la base de datos en cada arranque del servidor** y
> es lo que colisiona con la suite de tests cuando ambos corren a la vez. Da dos síntomas ya
> observados —arranques fallidos en desarrollo y un test inestable— con una sola causa.
>
> **Qué es.** Ocho prompts de la época de AutomatIA (generador de scripts, clarificación por tipo
> de tarea —custom / ETL / RPA / extracción—, procesado con LLM, naming semántico, orquestador de
> flujos, metaprogramación) sembrados en cada arranque en dos tablas legacy,
> `ExtractionServiceConfig` y `SystemPrompt`.
>
> **Por qué se puede retirar.** El único consumidor de esas tablas es
> `server/app/services/knowledge_orchestrator_service.py`, que **no lo importa nadie**: cero
> referencias en `server/` y **0 % de cobertura** (68 líneas, 68 sin ejecutar). Los prompts vivos
> son otros dos sistemas que no se tocan: `HubPromptTemplate` (por asistente) y
> `HubActivityPrompt` (por actividad de plataforma).
>
> **Fronteras que no se cruzan.** `AutomationLibrary` **se queda**: la importa el orquestador
> huérfano, pero también `library_router`, que está vivo en `main.py`. Y `models.py` tiene
> diecinueve clases: se retiran **dos**, no el fichero.

### Prompt LEG.1 (análisis) — Qué se salva de los ocho prompts antes de borrarlos

**Modelo sugerido**: **Opus** — es un juicio de contenido: decidir si un texto escrito para el
legacy dice mejor lo que el actual dice peor.

```
# PROMPT LEG.1 (analisis) — Comparar antes de borrar

## Por que
Es la leccion de PRO.1 y de PRO.4: el legacy de AutomatIA tenia decisiones mejores que las del
codigo nuevo -la auditoria graduada de tres niveles, las diez operaciones de limpieza-, y se
descubrieron al leerlo, no al planificarlo. Borrar 580 lineas de prompts sin leerlas es tirar
trabajo que puede estar mejor redactado que el equivalente actual.

## Que hacer
1. Leer los ocho prompts de `server/app/database/seeds_prompts.py`.
2. Emparejar cada uno con su equivalente vivo, si lo tiene:
   - generador de scripts        -> actividad `propuesta_de_script`
   - clarificacion (4 variantes) -> no hay equivalente: el modulo de Informes no pregunta antes
   - procesado con LLM           -> nodos de redaccion
   - naming semantico            -> operaciones de limpieza del ETL (`normalize_text`, `rename`)
   - orquestador de flujos       -> sin equivalente (es de automatizaciones, fase futura)
   - metaprogramacion            -> sin equivalente
3. Escribir `docs/COMPARATIVA_PROMPTS_LEGACY.md`: por cada prompt, si su texto aporta algo que el
   actual no diga, y si aporta, portar el fragmento a la actividad correspondiente.
4. Lo que no tenga equivalente y describa una capacidad futura -clarificacion previa, orquestacion
   de flujos- se **cita en el documento** para que el bloque de automatizaciones lo encuentre, y
   no se conserva como codigo muerto.

## Criterio de done
- [ ] Los ocho prompts leidos y emparejados
- [ ] `docs/COMPARATIVA_PROMPTS_LEGACY.md` escrito
- [ ] Lo que mejora el texto actual, portado y con su test
- [ ] Ninguna decision de borrado tomada sin haber leido el texto
```

### Prompt LEG.2 (RED/GREEN) — El arranque deja de escribir en la base de datos

**Modelo sugerido**: **Sonnet** — alcance cerrado.

```
# PROMPT LEG.2 (RED/GREEN) — Cortar la siembra del arranque
# Deploy: cloud (app/database/)

## Por que
`seed_all` llama a `seed_system_prompts`, `seed_v12_system_prompts` y `seed_prompt_tiers` en cada
arranque. Son las lineas `[SEED] Iniciando poblado de SystemPrompt...` del log. Escribir en la
base de datos al arrancar es lo que choca con la suite: el servidor siembra mientras los tests
reinicializan, y salta cualquiera de los dos.

## Que hacer
1. RED: un test comprueba que el arranque **no** escribe en `extraction_service_config` ni en
   `system_prompt`. Debe fallar ahora.
2. GREEN: retirar las tres llamadas de `seed_all` y el fichero `seeds_prompts.py` entero (580
   lineas), mas el uso de `ExtractionServiceConfig` que queda en `seeds.py`.
3. Comprobar que el arranque sigue completo: `init_server_db`, hub, jobs zombis, seeds que si
   valen, cache de modelos, precios y planificador de calidad.

## Criterio de done
- [ ] El arranque no toca las dos tablas legacy
- [ ] `seeds_prompts.py` eliminado y sin referencias (`grep -r` a cero)
- [ ] La aplicacion arranca (comprobado, no supuesto)
```

### Prompt LEG.3 (RED/GREEN) — El orquestador huérfano y el test que siembra tu base de datos

**Modelo sugerido**: **Sonnet**.

```
# PROMPT LEG.3 (RED/GREEN) — Retirar el consumidor muerto y su test
# Deploy: cloud (app/services/, tests/)

## Por que
`knowledge_orchestrator_service.py` es el unico que lee las dos tablas y **no lo importa nadie**:
0 % de cobertura, 68 lineas sin ejecutar. Y `tests/test_prompts.py` usa `server_engine` -la base
de datos real del desarrollador- y siembra prompts: pasa aislado y falla en la suite paralela.

## Que hacer
1. Retirar `server/app/services/knowledge_orchestrator_service.py` (Caso B de CLAUDE.md: huerfano
   sin migracion activa, se borra; el historial de git es la fuente de verdad del pasado).
2. Retirar `server/tests/test_prompts.py`.
3. GUARDARRAIL, que es lo que impide que vuelva a pasar: un test de higiene que falle si algun
   test importa `server_engine` o escribe en la base de datos de desarrollo. Va en
   `tests/infra/test_suite_hygiene.py`, junto a los otros seis.

## Restricciones
- **`AutomationLibrary` no se toca**: la importa este orquestador, pero tambien `library_router`,
  que esta vivo.

## Criterio de done
- [ ] El servicio y el test, fuera
- [ ] Guardarrail que caza un test escribiendo en la BD del desarrollador
- [ ] Suite completa sin el flake (medida, no supuesta)
```

### Prompt LEG.4 (RED/GREEN + migración) — Borrar las dos tablas

**Modelo sugerido**: **Sonnet**.

```
# PROMPT LEG.4 (RED/GREEN) — Las dos tablas y sus dos clases
# Deploy: cloud (app/database/, migrations/)

## Por que
Las tablas vienen del esquema inicial (`8879cf0a3197_initial_schema`), asi que no desaparecen
solas: hace falta migracion. Dejarlas vacias seria peor que borrarlas, porque una tabla que existe
invita a que alguien la use.

## Que hacer
1. Retirar de `server/app/database/models.py` **las dos clases**, `ExtractionServiceConfig` y
   `SystemPrompt`. **El fichero se queda**: tiene diecinueve clases y las otras diecisiete estan
   vivas.
2. Migracion nueva que hace `drop_table` de las dos, con `downgrade` que las recrea. Aplicarla y
   mostrar `alembic current`.
3. Comprobar que `actividades_llm.py` sigue igual: su comentario dice que la clave de cada
   actividad "es el `name` de `SystemPrompt` del legacy" -se heredo la convencion de nombres a
   proposito-. Es un vinculo documental, no de ejecucion; actualizar el comentario para que no
   apunte a algo que ya no existe.

## Criterio de done
- [ ] Dos clases fuera, diecisiete intactas
- [ ] Migracion aplicada y `alembic current` en la nueva cabeza
- [ ] `grep -r` de las dos clases a cero en el arbol activo
```

### Prompt LEG.5 (retirada) — El `main.py` de la raíz, y el script que lo lanza

**Modelo sugerido**: **Sonnet**.

```
# PROMPT LEG.5 (retirada) — El lanzador de NiceGUI sale del arbol activo

## Por que
El `main.py` de la raiz son 686 lineas que importan `nicegui`, las paginas de `client_app`,
`ExtractionService` y `RPAExecutor`: es el lanzador de la aplicacion de escritorio. Sigue en el
arbol activo y **`arranque.bat` todavia lo ejecuta** (`uv run main.py`), asi que moverlo sin tocar
el script deja un arranque roto.

## Que hacer
1. Mover `main.py` a `_legacy_nicegui/main.py`, manteniendo la ruta relativa (Caso A de
   CLAUDE.md: codigo NiceGUI con migracion activa; el borrado definitivo lo hace el usuario al
   cerrar la Fase 1).
2. Limpiar de `arranque.bat` la parte que lanza la aplicacion NiceGUI. Lo que se queda es lo que
   se usa: backend y frontend.
3. `grep -r` para confirmar que nada del arbol activo lo importa ni lo invoca.

## Criterio de done
- [ ] `main.py` en cuarentena y `arranque.bat` sin referencias a el
- [ ] `arranque.bat` probado: levanta backend y frontend
- [ ] Ninguna referencia viva al modulo, comprobada con `grep -r`
```

---
