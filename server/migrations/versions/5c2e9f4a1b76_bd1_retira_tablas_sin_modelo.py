"""BD.1 — retira las 36 tablas que no pertenecen a ningún modelo

Revision ID: 5c2e9f4a1b76
Revises: 4b1d8e29c7f3
Create Date: 2026-09-04

Son el residuo del lado servidor de AutomatIA —el «Brain»—, y aparecieron al censar `govgenai`
después de retirar el NiceGUI: 88 tablas en la base, 51 declaradas por los tres metadatos
(`SQLModel`, `HubConfigBase`, `HubOperationalBase`), **36 sin dueño y todas con cero filas**.

**Por qué existen.** El arranque llama a `init_server_db()`, que hace
`SQLModel.metadata.create_all`, y el *lifespan* hace lo mismo con las dos bases del Hub.
`create_all` crea lo declarado y **nunca borra lo que dejó de estarlo**; Alembic no se enteró
porque no las creó él —ninguna de las 36 aparece en ninguna de las 89 migraciones anteriores—. Así
que cada vez que un bloque retiró un modelo, su tabla se quedó.

**Por qué se retiran, si son 900 KiB.** No por el espacio. Porque quien lea el esquema no las
distingue de las vivas: `report_templates` está al lado de `hub_report_templates` y
`script_library` al lado del mundo de scripts que sí funciona. El repositorio se va a abrir, y una
tabla muerta con nombre creíble es una trampa.

**Lo que se comprobó antes de escribir esto:**

1. Ninguna la declara ningún modelo, con **la aplicación entera importada** — no una lista de
   módulos a mano, que dejaba fuera `redaccion` y hacía aparecer `hub_report_templates`, con 23
   filas, como huérfana.
2. Ninguna se lee por **SQL crudo**, que era el hueco del censo por metadatos: se buscó
   `FROM|JOIN|INTO|UPDATE|TABLE <nombre>` en `server/app`, `server/migrations`, `mcp_server`,
   `shared`, `scripts`, `frontend/src` y `services`. Cero.
3. Ninguna la nombra ninguna migración anterior.
4. Las 36 tienen **cero filas** en desarrollo.

**Y producción, medida antes de escribir esto: no tiene ninguna de las 36.** Censadas sus tablas
en solo lectura por SSH a la VM y `SELECT` sobre `information_schema` a través del contenedor
`migrate`: **51 tablas, exactamente las declaradas, cero huérfanas**. Cuadra con el mecanismo — se
desplegó por primera vez el 2026-08-31, cuando esos modelos ya no existían, así que `create_all`
nunca tuvo qué crear allí.

Eso cambia para qué sirve esta migración, y conviene decirlo: **en producción es un no-op**. Lo
que arregla es que **desarrollo y producción habían divergido** —88 tablas contra 51— y nada lo
decía. Cierra la divergencia y deja un guardarraíl que la vuelve visible si reaparece.

**Dos decisiones de forma, y las dos son por seguridad:**

* **`DROP TABLE IF EXISTS`** y no `op.drop_table`, que falla si la tabla no está. Es lo que hace
  que la misma revisión valga en desarrollo, donde borra 36, y en producción, donde no borra
  ninguna. Sin esto, aplicarla en producción reventaría en la primera.
* **Sin `CASCADE`**, y esto ya se cobró la apuesta. El primer `upgrade` **falló**:
  `flowregistry` tiene dos dependientes (`flow_step`, `trigger_subscriptions`) y PostgreSQL se
  negó a borrarla. Con `CASCADE` habría borrado los dependientes en silencio — y si alguno hubiera
  sido una tabla viva no inventariada, se habría enterado nadie. Falló, se leyó el error y se midió
  el grafo, que es lo que hace un fallo ruidoso mejor que un éxito silencioso. El DDL es
  transaccional, así que aquel intento no dejó nada a medias.

  Medido después sobre el catálogo: **6 FK entre las 36**, con cuatro tablas hija, y —lo que de
  verdad importaba— **cero FK desde una tabla viva hacia una huérfana**. Nada vivo dependía de
  ellas, que es la condición para poder borrarlas.
* **`downgrade()` no las recrea**, y eso es deliberado, no pereza. Recrearlas exigiría inventar su
  esquema —los modelos ya no existen, así que no hay de dónde copiarlo— y lo que saldría sería una
  tabla con el nombre correcto y las columnas equivocadas: peor que no tenerla. Si alguna hiciera
  falta, vuelve con su modelo y su propia migración. El pasado está en el historial de git.
"""

from alembic import op

revision = "5c2e9f4a1b76"
down_revision = "4b1d8e29c7f3"
branch_labels = None
depends_on = None


#: Las 36, agrupadas por lo que fueron. El agrupamiento no es decorativo: es lo que permite
#: comprobar de un vistazo que no se ha colado nada vivo en la lista.
HUERFANAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "los vigilantes y el RPA del agente local",
        (
            "mailwatcherstate",
            "receivedemail",
            "webwatcherhistory",
            "rpaplaybook",
            "pendingscreenshotreview",
            "localautomation",
            "localcredentials",
        ),
    ),
    (
        "el editor de flujos del NiceGUI",
        (
            "flowregistry",
            "flow_step",
            "favoriteflow",
            "triggerconfig",
            "trigger_subscriptions",
            "wizarddraft",
            "atom_registry",
            "automatism_package",
        ),
    ),
    (
        "la extracción y el ETL de la aplicación de escritorio",
        (
            "userextractionconfig",
            "extractionlog",
            "etljobhistory",
            "validationhistory",
        ),
    ),
    (
        "scripts e informes antes de que fueran del servidor",
        (
            "customscript",
            "customscriptexecution",
            "script_library",
            "report_templates",
            "reporthistory",
            "runmanifestlog",
        ),
    ),
    (
        "administración del «Brain» que nunca llegó a usarse",
        (
            "apiendpointconfig",
            "databasecredentialconfig",
            "providerapikey",
            "securitypolicy",
            "serverconnection",
            "connection_logs",
            "tasklog",
            "enterprise_audit_log",
            "cleanuplog",
            "cleanuppolicy",
            "cleanupschedulerconfig",
        ),
    ),
)


#: Las cuatro que tienen clave ajena hacia otra huérfana, y por eso se borran **antes**.
#:
#: No es una lista de precaución: sale del grafo medido sobre el catálogo después de que el primer
#: `upgrade` fallara. Las seis FK entre las 36 son
#: `flow_step` → `flowregistry` y → `atom_registry`;
#: `trigger_subscriptions` → `flowregistry` y → `triggerconfig`;
#: `customscriptexecution` → `customscript`; y `enterprise_audit_log` → `tasklog`.
#:
#: Se ordena a mano en vez de calcular la topología en tiempo de migración a propósito: cuatro
#: nombres se leen y se comprueban, y un grafo calculado al vuelo no. Si otro entorno tuviera una
#: FK que esta lista no prevé, la migración **falla** en vez de arrastrarla — que es justo la
#: propiedad que se acaba de demostrar útil.
HIJAS: tuple[str, ...] = (
    "flow_step",
    "trigger_subscriptions",
    "customscriptexecution",
    "enterprise_audit_log",
)


def upgrade() -> None:
    todas = [tabla for _motivo, tablas in HUERFANAS for tabla in tablas]
    assert set(HIJAS) <= set(todas), "una hija no está en la lista que se borra"

    # `IF EXISTS` y no `op.drop_table`: éste falla si la tabla no está, y producción —censada, 51
    # tablas y cero huérfanas— no tiene ninguna. Sin `IF EXISTS`, la misma revisión reventaría
    # allí en la primera.
    for tabla in [*HIJAS, *(t for t in todas if t not in HIJAS)]:
        op.execute(f'DROP TABLE IF EXISTS "{tabla}"')


def downgrade() -> None:
    """No las recrea, y está explicado arriba: no hay de dónde copiar su esquema.

    Un `downgrade` que creara treinta y seis tablas con el nombre correcto y las columnas
    inventadas sería peor que este, que al menos no miente. La bajada de esta revisión es un
    no-op deliberado.
    """
