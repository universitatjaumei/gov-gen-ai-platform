## Bloque ROL — Renombrado de nomenclatura institucional (Subfase 1.B, PENDIENTE)

> **Contexto**: `docs/Arquitectura.md` §5 y `PLAN_DESARROLLO.md` dan por aplicado el renombrado de roles, pero el código sigue con la nomenclatura antigua. Este bloque lo aplica. Es más barato ahora que tras la Fase 3 (Expedientes introduce `responsable_rol` por todo el módulo).

**Mapa de renombrado (fuente de verdad para ambos prompts):**

| Antiguo (código actual) | Nuevo | Naturaleza | Tabla / campo afectado |
|---|---|---|---|
| `AdminAccount` (admin global) | `SuperAdminAccount` | Cuenta | tabla `admin_accounts` → `superadmin_accounts` |
| rol `admin` (global) | rol `superadmin` | Rol | claim `role` en JWT |
| `PartnerAccount` | `AdminAccount` | Cuenta | tabla `partner_accounts` → `admin_accounts` |
| rol `partner` | rol `admin` | Rol | claim `role` en JWT |
| `HubClient` | `HubOrganizacion` | Entidad de datos | tabla `hub_clients` → `hub_organizaciones` |
| columna/parámetro `client_id` | `organizacion_id` | FK | en `HubChatbot`, temas, ingestión, etc. |
| usuario final | rol `user` | Rol | sin cambios de tabla |

> ⚠️ **Trampa**: `AdminAccount` se **reutiliza** para una entidad distinta (el ex-`PartnerAccount`). La migración debe renombrar tablas preservando datos (`ALTER TABLE ... RENAME`), **nunca** drop+create. Ejecutar los renombrados en el orden correcto para no colisionar (`admin_accounts` → `superadmin_accounts` **antes** de `partner_accounts` → `admin_accounts`).

---

### Prompt ROL.1 (RED/GREEN) — Refactor de modelos, migración y dependencias de seguridad

**Modelo sugerido**: **Opus** — refactor transversal (>800 LOC afectadas en modelos, deps, routers, tests), reutilización peligrosa del nombre `AdminAccount` y migración de datos que debe preservar filas y FKs.

**Objetivo**: Aplicar el mapa de renombrado en el backend (modelos ORM, migración Alembic con preservación de datos, dependencias de seguridad y todas las queries/imports afectados) sin perder datos ni romper tests.

```
# PROMPT ROL.1 (RED/GREEN) — Renombrado institucional en el backend
# Deploy: cloud (cuentas/roles) + shared (deps de auth)

## Alcance (aplicar el "Mapa de renombrado" del Bloque ROL)
- database/models.py: AdminAccount→SuperAdminAccount, PartnerAccount→AdminAccount.
  Añadir NADA de lógica nueva aquí (la contraseña del ex-partner es SEC.1).
- modules/agents_hub/database/config_models.py: HubClient→HubOrganizacion; todas las
  columnas y relaciones `client_id`→`organizacion_id`. Mantener HubConfigBase.
- core/auth/models.py: el enum/Literal de roles pasa a superadmin | admin | user.
- api/deps.py + core/auth: require_admin (global) → require_superadmin;
  crear require_admin nuevo (=ex require_partner o el gate de partner); actualizar
  require_scopes / techos de rol de PAT (core/auth/pat/scopes.py: admin→superadmin,
  partner→admin en la tabla de techos).
- routers/auth_router.py: login_admin→login_superadmin (path /auth/superadmin/login),
  login_partner→login_admin (path /auth/admin/login). Mantener el bug de contraseña
  TAL CUAL (lo arregla SEC.1); aquí solo se renombra.
- Reemplazar TODA referencia a client_id/HubClient/partner/PartnerAccount en:
  hub_chatbots_router, hub_themes_router, hub_feedback, hub_chat, seeds.py, y
  cualquier servicio que los importe (grep exhaustivo).

## Migración Alembic (preservando datos; NO drop+create)
- op.rename_table('admin_accounts','superadmin_accounts')
- op.rename_table('partner_accounts','admin_accounts')     # tras el anterior
- op.rename_table('hub_clients','hub_organizaciones')
- op.alter_column(... 'client_id', new_column_name='organizacion_id') en cada tabla con esa FK
- Data migration de roles: UPDATE de la columna role en tokens/cuentas si se persiste
  ('admin'→'superadmin', 'partner'→'admin'). Los JWT en vuelo caducan solos (60 min).
- Reaplicar constraints/índices renombrados. Aplicar con `uv run alembic upgrade head`.

## Tests (RED primero) — tests/core/ + tests/api/
# test_role_rename.py
# should_expose_superadmin_admin_user_roles_only            (el Literal no acepta 'partner')
# should_superadmin_login_verify_password_like_before        (regresión del login global)
# should_require_superadmin_dependency_rejects_admin_role
# should_require_admin_dependency_accepts_admin_and_superadmin
# test_migration_rename.py
# should_rename_tables_preserving_rows                       (seed → upgrade → filas intactas)
# should_rename_client_id_to_organizacion_id_on_chatbots
# should_have_zero_references_to_old_names                   (grep: 'PartnerAccount'|'HubClient'|"role == 'partner'" = 0 en server/app, excl. migración)

## Criterios de cierre (obligatorio)
- [ ] `grep -rn "PartnerAccount\|HubClient\|'partner'\|\bclient_id\b" server/app` = 0 (excl. la migración y comentarios de mapeo)
- [ ] `uv run alembic upgrade head` + `alembic current` en head; datos preservados
- [ ] OpenAPI reexportado (cambian paths de login y esquemas) + Orval pendiente para ROL.2
- [ ] Suite backend en verde
```

---

### Prompt ROL.2 (RED/GREEN) — Frontend: tipos Orval, rutas, i18n y checks de rol

**Modelo sugerido**: **Sonnet** — alcance cerrado; la fuente de verdad (OpenAPI) ya cambió en ROL.1, solo hay que propagar.

**Objetivo**: Propagar el renombrado al frontend regenerando Orval y actualizando rutas, checks de rol e i18n. Sin lógica de negocio nueva.

```
# PROMPT ROL.2 (RED/GREEN) — Renombrado institucional en el frontend

## Regenerar contrato
- Reexportar openapi.json (ya hecho en ROL.1) → `npm run orval` → tipos/hooks nuevos
  (SuperAdminAccount, AdminAccount, HubOrganizacion, organizacion_id).

## Cambios
- shared/auth: el AuthContext y las rutas protegidas usan roles superadmin|admin|user.
  Reemplazar cualquier comparación con 'partner'/'admin-global'.
- Renombrar pantallas/labels: "Clientes"→"Organizaciones" (ClientsPage→OrganizacionesPage),
  "Partners"→"Admins" donde aparezca. Rutas /clients→/organizaciones.
- i18n: renombrar claves y textos es/ca/en (client→organizacion, partner→admin). Sin strings sueltos.

## Tests Vitest (RED primero) — mínimo 5
# should_render_organizaciones_page_from_generated_types
# should_route_superadmin_to_platform_section
# should_route_admin_to_org_scoped_section
# should_hide_platform_admin_from_user_role
# should_use_i18n_keys_not_hardcoded_role_labels

## Pruebas manuales (CLAUDE.md — requiere navegador)
- .bat prompt ROL_2: login como cada rol y verificar navegación y etiquetas.
```

---
