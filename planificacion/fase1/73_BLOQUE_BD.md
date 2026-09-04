## Bloque BD — Una sola fuente para el esquema de la base de datos

> Nacido el 2026-09-04 de una pregunta del usuario al cerrar el bloque NIC: si la retirada del
> NiceGUI dejaba tablas colgando. La respuesta corta —«no, usaba SQLite»— era media respuesta.

**Dos prompts.** BD.1 ya está ejecutado y se documenta aquí para que el bloque tenga su historia
completa; BD.2 es el que arranca con este fichero.

---

### Prompt BD.1 (RED/GREEN) — Retirar las tablas que no pertenecen a ningún modelo ✅

**Modelo sugerido**: Opus — hay que medir en dos bases y decidir qué es verdad.

```
# PROMPT BD.1 (RED/GREEN) — Las 36 tablas sin dueño
# Deploy: edge y cloud (es una migración; en producción es un no-op)

## Por que
Censado `govgenai`: 88 tablas, 51 declaradas por los tres metadatos, **36 sin dueño** y todas
vacias. Son el residuo del lado servidor de AutomatIA. Quien lea el esquema no las distingue de
las vivas (`report_templates` al lado de `hub_report_templates`), y el repositorio se va a abrir.

## Que hacer
1. Censo con la aplicacion ENTERA importada (importar modulos a mano deja fuera `redaccion`).
2. Comprobar lo que un censo por metadatos no ve: SQL crudo y FK desde tablas vivas.
3. Censar produccion en solo lectura ANTES de escribir la migracion.
4. Migracion con `DROP TABLE IF EXISTS`, sin `CASCADE`, hijas antes que madres, `downgrade` no-op.

## Criterio de done
- [x] Guardarrail que censa la base contra los metadatos, y se salta si no hay BD
- [x] Produccion medida: 51 tablas, cero huerfanas
- [x] Aplicada en desarrollo: 88 -> 52, datos vivos intactos
```

**Ejecutado el 2026-09-04**, commit `a44e7f2`. Detalle en `HISTORIAL.md` y en la docstring de la
migración `5c2e9f4a1b76`.

---

### Prompt BD.2 (RED/GREEN) — Alembic como única fuente del esquema, y CI que lo demuestre ✅

**Modelo sugerido**: Opus — toca el arranque de la aplicación y decide qué es verdad en tres
columnas donde modelo y migración se contradicen.

```
# PROMPT BD.2 (RED/GREEN) — Una sola fuente para el esquema
# Deploy: edge y cloud (arranque, CI y una migracion)

## Por que
El esquema lo gobiernan DOS mecanismos a la vez: Alembic en el despliegue y la creacion
automatica desde el metadato (`init_server_db()` y `_init_hub_db()`) en cada arranque. La
segunda hace lo declarado y nunca borra lo que dejo de estarlo: asi aparecieron las 36 tablas
de BD.1, y asi volveran a aparecer cada vez que se retire un modelo.

Medido antes de escribir esto:
- Aplicada la cadena de Alembic a una base vacia, produce EXACTAMENTE las 51 tablas
  declaradas. El `create_all` del arranque no aporta ninguna. Quitarlo no cuesta cobertura.
- `alembic check` —compara modelos con base y falla si divergen— existe y HOY FALLA: tres
  columnas son `nullable=True` en la migracion que las creo y `NOT NULL` en el modelo
  (`Mapped[datetime]` sin `nullable=` explicito):
    hub_content_findings.created_at          (u2d3e4f5g6h7, 9Q.1)
    hub_provider_credentials.created_at      (q7j8k9l0m1n2, MT.2)
    hub_provider_credentials.updated_at      (q7j8k9l0m1n2, MT.2)
  Las tres tienen `default` en Python, asi que en la practica nunca son nulas: 292 filas en
  desarrollo y 292 en produccion, CERO NULL en las dos. La verdad es el modelo.
- Ya estaban anotadas y aplazadas dos veces (docstrings de REG.1 `28d7fafbf4af` y USR.1
  `a6d9893f743a`): «quedan anotados aqui para que alguien los mire a proposito». Este es ese
  alguien.
- SQLAlchemy avisa de un ciclo de FK `hub_llm_configs <-> hub_organizaciones`
  (`HubLLMConfig.organizacion_id` y `HubOrganizacion.rewrite_llm_config_id`), «may raise an
  error in a future release».

## Que hacer
1. RED primero (ver abajo).
2. Migracion: backfill y `SET NOT NULL` en las tres columnas. El backfill es lo que USR.1
   pedia para que un `upgrade` no reviente en una base ajena con filas nulas:
   `created_at = COALESCE(created_at, detected_at)` en hallazgos (tienen `detected_at` NOT
   NULL), `now()` en credenciales. `downgrade` vuelve a `nullable=True`.
3. Quitar `init_server_db()` y `_init_hub_db()` del arranque Y del codigo (borra, no comentes).
   Las semillas se quedan: son llamadas aparte.
4. `db.py`: la docstring dice que el esquema lo gobierna SOLO Alembic y por que.
5. CI: antes de la suite, `alembic upgrade head` sobre la base del servicio y luego
   `alembic check`. Es la mitad que importa: un modelo cambiado sin su migracion pone el check
   en rojo en el mismo push, no en la base de alguien meses despues.
6. El ciclo de FK: `use_alter=True` en la FK anulable (`rewrite_llm_config_id`), que es la que
   SQLAlchemy puede crear despues de las tablas. Comprobar que `alembic check` no lo ve como
   cambio (es metadato de creacion, no de esquema).
7. Tests que nombran lo que se retira: `test_el_fallo_de_arranque_se_puede_leer.py` (parchea
   `init_server_db` para simular un arranque que falla: que parchee el primer paso que quede),
   `test_imports.py`, `test_no_legacy_shims.py` (su ejemplo de alias), y el segundo test de
   BD.1, que exigia que `create_all` siguiera en `db.py`: se invierte, como NIC.3 hizo con los
   guardarrailes de la cuarentena.
8. `AGENTS.md` §Migraciones y `docs/ESPECIFICACIONES.md` §4: invariante nuevo, «el esquema lo
   define Alembic; la aplicacion no crea tablas», con donde se hace cumplir.

## Tests (RED primero)
- RED: `main.py` no llama a nada que cree esquema; `db.py` no contiene `create_all`.
- RED: `.github/workflows/ci.yml` tiene un paso `alembic check` DESPUES de `alembic upgrade`.
- RED: sobre una base desechable con la cadena aplicada, `alembic check` sale limpio (es lo
  que CI hara, ejecutado en local para no descubrirlo en el push).
- RED: las tres columnas son NOT NULL en la base migrada.

## Criterio de done
- [x] `grep create_all` a cero en `server/app/` (los tests conservan el suyo: bases desechables)
- [x] `alembic check` limpio en local; en CI, en el primer push tras el commit
- [x] Migraciones aplicadas en desarrollo; produccion comprobada en solo lectura antes (0 NULL)
- [x] Suite completa verde desde Git Bash; `test_el_fallo_de_arranque` sigue probando lo suyo
```

**Ejecutado el 2026-09-04.** Desviación documentada: el prompt preveía tres derivas y el
guardarraíl encontró diez —las siete de más, sólo en producción—. Detalle en `HISTORIAL.md` y en
las docstrings de `7d4e2f1a9b3c` y `8f5a3c2d1e07`.

> **Orden y dependencias.** BD.1 antes que BD.2 (BD.2 invierte un test de BD.1). BD.2 no depende
> de ningún otro bloque y puede ir a `main` con lo que haya: en producción la migración sólo
> endurece tres columnas que ya no tienen nulos, y el arranque deja de hacer algo que allí no
> hacía nada.
