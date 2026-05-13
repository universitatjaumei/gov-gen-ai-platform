# Índice de Documentación de AutomatIA

Bienvenido a la documentación completa de AutomatIA. Esta guía te ayudará a encontrar la información que necesitas según tu rol y necesidades.

## 🎯 Navegación por Rol

### 👤 Usuario Final
Si eres usuario final de AutomatIA en tu organización:

1. **Primeros pasos**: [Guía de Inicio Rápido](quick_start.md)
2. **Uso diario**: [Manual de Usuario - Client Node](functional/user_manual_client.md)
3. **Transformación de datos**: [Guía de Usuario ETL](ETL_USER_GUIDE.md)
4. **Automatización de procesos**: [Configuración de Flujos](functional/flows_configuration.md)
5. **Problemas comunes**: [Resolución de Problemas](troubleshooting.md)

### 🤝 Partner/Integrador
Si eres un Partner que gestiona clientes de AutomatIA:

1. **Administración**: [Guía de Administración para Partners](functional/partner_admin_guide.md)
2. **Panel de control**: [Manual de Administración](MANUAL_ADMIN.md)
3. **Instalación**: [Guía de Despliegue](deployment_guide.md)
4. **Soporte técnico**: [Resolución de Problemas](troubleshooting.md)

### 💻 Desarrollador
Si estás desarrollando o extendiendo AutomatIA:

1. **Arquitectura**: [Arquitectura Detallada](technical/architecture_detailed.md)
2. **Módulos de generación**: [Factory Modules](technical/factory_modules.md)
3. **Seguridad**: [Modelo de Seguridad](technical/security_model.md)
4. **Base de datos**: [Esquema de BD](technical/database_schema.md)
5. **Motor de ejecución**: [Runtime Engine](technical/runtime_engine.md)
6. **API interna**: [Documentación API](INTERNAL_API.md)
7. **Nuevas características**: [Features V4.0](technical/new_features_v4.md)

## 📚 Documentación por Categoría

### Documentación Funcional

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| [Manual de Usuario - Client Node](functional/user_manual_client.md) | Guía completa de uso diario de la aplicación cliente | Usuario Final |
| [Guía de Usuario ETL](ETL_USER_GUIDE.md) | Transformación de datos con lenguaje natural | Usuario Final |
| [Configuración de Flujos](functional/flows_configuration.md) | Creación y gestión de workflows automatizados | Usuario Final |
| [Guía de Administración para Partners](functional/partner_admin_guide.md) | Gestión de organizaciones y licencias | Partner |
| [Manual de Administración](MANUAL_ADMIN.md) | Panel de administración del servidor | Partner/Admin |

### Documentación Técnica

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| [Arquitectura Detallada](technical/architecture_detailed.md) | Diseño del sistema, componentes y comunicación | Desarrollador |
| [Factory Modules](technical/factory_modules.md) | Módulos de generación de código (PDF, ETL, RPA, Graphics, Reports) | Desarrollador |
| [Modelo de Seguridad](technical/security_model.md) | Anonimización, sandbox, políticas de seguridad | Desarrollador |
| [Esquema de Base de Datos](technical/database_schema.md) | Tablas y relaciones de BD cliente y servidor | Desarrollador |
| [Runtime Engine](technical/runtime_engine.md) | Motor de ejecución y orquestación de flujos | Desarrollador |
| [API Reference](technical/api_reference.md) | Endpoints y comunicación Brain-Client | Desarrollador |
| [Features V4.0](technical/new_features_v4.md) | Nuevas características de la versión 4.0 | Desarrollador |

### Documentación Operacional

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| [Guía de Inicio Rápido](quick_start.md) | Instalación y primeros pasos en 5 minutos | Todos |
| [Guía de Despliegue](deployment_guide.md) | Instalación completa y configuración | Partner/DevOps |
| [Resolución de Problemas](troubleshooting.md) | Soluciones a problemas comunes | Todos |
| [API Interna](INTERNAL_API.md) | Comunicación entre componentes del sistema | Desarrollador |

## 🔍 Búsqueda Rápida por Tema

### Instalación y Configuración
- [Guía de Inicio Rápido](quick_start.md) - Instalación en 5 minutos
- [Guía de Despliegue](deployment_guide.md) - Instalación completa
- Configuración de variables de entorno → [Deployment Guide: Sección 3](deployment_guide.md#3-configuración-de-variables-de-entorno-env)

### Extracción de Documentos
- Guía de usuario → [Manual de Usuario: Sección 2](functional/user_manual_client.md#2-automatizaciones-de-documentos-extracción)
- Arquitectura técnica → [Factory Modules: PDFFactory](technical/factory_modules.md#a-pdffactory-pdf_factorypy)

### Transformación de Datos (ETL)
- Guía completa → [Guía de Usuario ETL](ETL_USER_GUIDE.md)
- Arquitectura técnica → [Factory Modules: ETLFactory](technical/factory_modules.md#b-etlscriptfactory-etl_factorypy)

### Automatización Web (RPA)
- Guía de usuario → [Manual de Usuario: Sección 3](functional/user_manual_client.md#3-automatización-de-procesos-rpa)
- Arquitectura técnica → [Factory Modules: NavigationFactory](technical/factory_modules.md#c-navigationfactory-navigation_factorypy)

### Generación de Gráficos e Informes
- Documentación técnica → [Features V4.0: Graphics & Reports](technical/new_features_v4.md)

### Flujos de Trabajo
- Configuración → [Configuración de Flujos](functional/flows_configuration.md)
- Motor de ejecución → [Runtime Engine: WorkflowEngine](technical/runtime_engine.md#2-orquestación-de-flujos-flowengine)

### Seguridad y Privacidad
- Modelo completo → [Modelo de Seguridad](technical/security_model.md)
- Anonimización → [Modelo de Seguridad: Anonymizer](technical/security_model.md#1-módulo-anonymizer-privacidad-rgpd)
- Sandbox → [Modelo de Seguridad: Sandbox](technical/security_model.md#2-sandbox-de-ejecución-seguridad-del-runtime)

### Conectores (Watchers)
- Email, carpetas, web, API → [Manual de Usuario: Sección 4](functional/user_manual_client.md#4-conectores-connections)

### Administración
- Panel de Partners → [Guía de Administración para Partners](functional/partner_admin_guide.md)
- Panel de Superadmin → [Manual de Administración](MANUAL_ADMIN.md)

### Troubleshooting
- Problemas comunes → [Resolución de Problemas](troubleshooting.md)

## 📖 Documentos Adicionales en la Raíz

Además de la documentación en `docs/`, existen documentos técnicos en la raíz del proyecto:

- `ARCHITECTURE.md` - Documento maestro de arquitectura (versión extendida)
- `ROADMAP_DEVELOPMENT.md` - Roadmap de desarrollo del proyecto
- `PROMPTS_MAESTROS.md` - Prompts de sistema para generación de IA

## 🆕 Novedades de la Versión 4.0

La versión 4.0 introduce importantes mejoras:

- **GraphicsFactory**: Generación automática de gráficos con matplotlib/seaborn
- **ReportFactory**: Creación de informes PDF profesionales con ReportLab
- **ClarificationService**: Sistema de preguntas previas a la generación
- **ScreenshotGuard**: Control de privacidad visual para RPA
- **ValidationLoopManager**: Ciclo de validación con feedback del usuario
- **APIWatcher**: Consumo de APIs REST como fuente de datos

Consulta [Features V4.0](technical/new_features_v4.md) para más detalles.

## 💡 Sugerencias de Lectura

### Para empezar desde cero
1. [Guía de Inicio Rápido](quick_start.md)
2. [Manual de Usuario - Client Node](functional/user_manual_client.md)
3. [Guía de Usuario ETL](ETL_USER_GUIDE.md)

### Para entender la arquitectura
1. [Arquitectura Detallada](technical/architecture_detailed.md)
2. [Modelo de Seguridad](technical/security_model.md)
3. [Factory Modules](technical/factory_modules.md)

### Para administrar el sistema
1. [Guía de Despliegue](deployment_guide.md)
2. [Manual de Administración](MANUAL_ADMIN.md)
3. [Resolución de Problemas](troubleshooting.md)

---

¿No encuentras lo que buscas? Consulta el [archivo de troubleshooting](troubleshooting.md) o contacta con tu Partner de soporte.
