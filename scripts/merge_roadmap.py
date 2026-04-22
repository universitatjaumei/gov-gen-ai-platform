"""
Script to merge MODIFICACION_INCREMENTAL_ROADMAP_DEVELOPMENT.md into ROADMAP_DEVELOPMENT.md
Handles encoding issues robustly.
"""

def read_file_robust(filepath):
    """Read file trying multiple encodings."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            print(f"✅ Successfully read {filepath} with {encoding} encoding")
            return content
        except Exception as e:
            print(f"❌ Failed to read with {encoding}: {e}")
            continue
    
    raise Exception(f"Could not read {filepath} with any encoding")

def write_file_utf8(filepath, content):
    """Write file with UTF-8 encoding."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    # Read both files
    print("Reading ROADMAP_DEVELOPMENT.md...")
    main_roadmap = read_file_robust('ROADMAP_DEVELOPMENT.md')
    
    print("Reading MODIFICACION_INCREMENTAL_ROADMAP_DEVELOPMENT.md...")
    incremental = read_file_robust('MODIFICACION_INCREMENTAL_ROADMAP_DEVELOPMENT.md')
    
    # Create new sections to add
    print("Creating new sections...")
    
    new_sections = """

---

## NUEVAS FASES INTEGRADAS

### Fase 3.5: GUI Cliente

**Objetivo:** Completar la interfaz de usuario del cliente con las páginas pendientes.

**Prompts:**
- PROMPT 18B: Dashboard UI (GUI-02)
- PROMPT 21A: Validation Loop UI
- PROMPT 21B: Additional UI components

**Tiempo estimado:** 2-3 días

**Estado:** ⏳ Pendiente

---

### Fase 3.9: Autenticación Partners y Administrador (RBAC)

**Contexto del Problema:**
- El modelo de datos está incompleto para autenticación
- `PartnerAccount` no tiene campos de autenticación (`password_hash`, `auth_provider_id`)
- No hay sistema de autenticación para el superadministrador
- Las rutas `/partner/*` y `/admin/*` necesitan protección

**⚠️ Riesgo Identificado:**
Sin esta capa, no hay forma segura de exponer las rutas `/partner/*` (que contendrán datos sensibles de facturación y clientes) en la Fase 4.

#### 📋 PROMPT 23A (REVISADO): Universal Auth & Roles (RBAC)

**🎯 Objetivo:** Implementar un sistema de autenticación centralizado en el Servidor (Brain) que soporte roles (SUPERADMIN, PARTNER) y proteja las rutas de administración (`/admin` y `/partner`).

**📁 Archivos a Modificar/Crear:**
- `server/app/database/models.py` (Añadir campos auth y seed de Admin)
- `server/app/services/auth_service.py` (Lógica de login y roles)
- `server/app/ui/login_page.py` (Interfaz unificada)
- `server/app/middleware/auth_middleware.py` (Guardia de rutas)
- `server/database/seeds.py` (Crear el usuario Superadmin por defecto)

**💻 Instrucciones Técnicas:**

**Modelo PartnerAccount:**
- Añadir `password_hash: str`
- Añadir `role: str` (Enum: SUPERADMIN, PARTNER). Default: PARTNER

**Seeds:**
Crear una cuenta "Vendor/Superadmin" por defecto si no existe:
- Email: `admin@automatia.ai`
- Password: `admin_secret_reset_me` (Hasheada)
- Role: `SUPERADMIN`
- PartnerID: `000000` (ID reservado del sistema)

**Middleware (NiceGUI):**
- Interceptar navegación
- Si la ruta empieza por `/admin`: Verificar token válido Y `role == SUPERADMIN`
- Si la ruta empieza por `/partner`: Verificar token válido Y (`role == PARTNER` O `role == SUPERADMIN`)
- Si falla: Redirigir a `/login`

**Tiempo estimado:** 1.5 días

**Estado:** ⏳ Pendiente

---

### Fase 4.4: Pruebas en Local contra PostgreSQL

**Contexto del Problema:**
- Desarrollo en SQLite vs Producción en PostgreSQL
- Necesidad de validar compatibilidad antes del deployment

**Estrategia Híbrida de Desarrollo:**
- Tests unitarios: SQLite (rápido, en memoria)
- Tests de integración: PostgreSQL (realista)

**📁 Archivos a Crear:**
- `docker-compose.dev.yml` - PostgreSQL local para desarrollo
- `scripts/manage_dev_db.py` - Gestión de BD de desarrollo
- `scripts/validate_postgres.py` - Validación de compatibilidad

**Flujo de Trabajo:**
1. Desarrollo diario: `pytest` (SQLite, rápido)
2. Pre-commit: `TEST_WITH_POSTGRES=true pytest` (PostgreSQL, completo)
3. CI/CD: Siempre PostgreSQL

**Criterios de Éxito:**
- [ ] Todos los tests pasan en SQLite
- [ ] Todos los tests pasan en PostgreSQL
- [ ] No hay diferencias de comportamiento entre ambos

**Tiempo estimado:** 1 día

**Estado:** ⏳ Pendiente

---

### Fase 4.5: Infraestructura Servidor (Docker + PostgreSQL)

**Contexto:**
Movemos la "Generación de Instaladores" a una futura Fase 6 (Go-to-Market) y redefinimos la Fase 5 como "Infraestructura Servidor".

**Objetivo:** Preparar el servidor (Brain) para deployment en producción con Docker y PostgreSQL.

#### 📋 PROMPT 27: Dockerización del Brain (Server)

**🎯 Objetivo:** Crear la imagen Docker optimizada para el servidor (Brain).

**📁 Archivos a Crear:**
- `server/Dockerfile`
- `server/.dockerignore`
- `server/entrypoint.sh`

**💻 Instrucciones:**
- **Base Image:** `python:3.11-slim-bookworm`
- **Dependencias:** curl, git, librerías para Playwright
- **Gestor:** Instalar `uv`
- **Entrypoint:** Migraciones DB + `uvicorn server.app.main:app --host 0.0.0.0`

---

#### 📋 PROMPT 28: Migración a PostgreSQL (Async)

**🎯 Objetivo:** Reemplazar SQLite por PostgreSQL con `asyncpg`.

**📁 Archivos a Modificar:**
- `server/app/database/db.py`
- `server/app/config.py`

**💻 Instrucciones:**
- **Dependencias:** Añadir `asyncpg` y `psycopg2-binary`
- **Lógica Condicional:**
  - Si `DATABASE_URL` empieza por `sqlite`: usar `sqlite+aiosqlite`
  - Si empieza por `postgresql`: usar `postgresql+asyncpg`

---

#### 📋 PROMPT 29: Orquestación (Docker Compose)

**🎯 Objetivo:** Levantar el entorno completo con un solo comando.

**📁 Archivos a Crear:**
- `docker-compose.yml`
- `.env.example`

**Servicios:**
- **db:** `postgres:15-alpine` con volumen persistente
- **brain:** Build del servidor, depends_on db, expone puerto 8000

**Tiempo estimado:** 2 días

**Estado:** ⏳ Pendiente

---

#### 📋 NUEVA TAREA: Migración MailWatcher a Servicio del Sistema (Opción 2)

**Objetivo:** Migrar el MailWatcher de servicio integrado (Opción 1) a servicio independiente del sistema operativo (Systemd/Windows Service).

**Tareas:**
- [ ] Crear `scripts/mail_watcher_daemon.py` (daemon standalone)
- [ ] Crear archivo Systemd service (`automatia-mail-watcher.service`) para Linux
- [ ] Crear script de instalación Windows Service (usando nssm)
- [ ] Actualizar UI para control de servicio del sistema
- [ ] Documentar instalación y configuración
- [ ] Migrar configuración existente de Opción 1 a Opción 2

**Tiempo estimado:** 1-2 días

**Beneficios:**
- ✅ Servicio totalmente independiente de la aplicación web
- ✅ Auto-start con el sistema operativo
- ✅ Auto-restart ante fallos
- ✅ Monitorización con herramientas del sistema
- ✅ Logs centralizados

**Referencia:** Ver `implementation_plan.md` (GUI-05) - Opción 2

**Estado:** ⏳ Pendiente

---

## Resultado de las Nuevas Fases

Con estas fases integradas, el roadmap queda mucho más sólido para una Beta real:

**Servidor:**
- Desplegable en cualquier VPS
- Capaz de aguantar múltiples usuarios concurrentes
- Autenticación y roles implementados
- PostgreSQL para producción

**Cliente:**
- Los betatesters descargan el código (o un zip simple)
- Ejecutan `uv sync`
- Configuran la URL de tu servidor Docker en su `/config`

---

"""
    
    # Merge documents
    print("Merging documents...")
    merged_content = main_roadmap + new_sections
    
    # Write merged content
    print("Writing merged ROADMAP_DEVELOPMENT.md...")
    write_file_utf8('ROADMAP_DEVELOPMENT.md', merged_content)
    
    # Backup incremental file
    print("Creating backup of MODIFICACION_INCREMENTAL...")
    write_file_utf8('MODIFICACION_INCREMENTAL_ROADMAP_DEVELOPMENT.md.backup', incremental)
    
    print("\n✅ Merge completed successfully!")
    print(f"   - Main ROADMAP updated with new phases (3.5, 3.9, 4.4, 4.5)")
    print(f"   - Backup created: MODIFICACION_INCREMENTAL_ROADMAP_DEVELOPMENT.md.backup")
    print(f"   - You can now delete MODIFICACION_INCREMENTAL_ROADMAP_DEVELOPMENT.md if desired")

if __name__ == "__main__":
    main()
