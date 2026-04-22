# **Arquitectura**

# **0\. Introducción**

## **0.1. Propósito de la Aplicación**

Gen Gov es una plataforma diseñada para la automatización de procesos administrativos y empresariales mediante **metaprogramación asistida por inteligencia artificial**, generando activos deterministas como scripts, workflows y conectores.  
La aplicación se fundamenta en un principio central: **la IA genera la lógica, pero la ejecución es siempre local, auditable y soberana**, garantizando la privacidad, la trazabilidad y el control de la lógica de negocio.  
Este modelo híbrido permite acelerar la creación de automatismos sin comprometer la seguridad ni el cumplimiento normativo.  
La **IA también se utiliza como copiloto de diseño y para el mantenimiento:** La plataforma no solo genera activos al inicio, sino que supervisa la coherencia del flujo de datos en tiempo real, sugiriendo "pasos puente" y validando tipos de datos entre componentes heterogéneos. También sugiere modificaciones ante errores de ejecución.

---

## **0.2. Cumplimiento Normativo (RIA y RGPD)**

Gen Gov asegura el cumplimiento del **Registro de Información Administrativa (RIA)** y del **Reglamento General de Protección de Datos (RGPD)** mediante un diseño centrado en la privacidad y la auditabilidad:

- **Arquitectura Zero‑Knowledge**: los datos personales nunca salen del entorno local del cliente.  
- **Anonimización reversible** basada en técnicas de NER y generación sintética.  
- **Auditoría local completa**, gracias al registro RunManifest.  
- **Código generado 100% auditable y transparente**, evitando cajas negras.

---

## **0.3. Visión General de la Arquitectura**

La arquitectura de Gen Gov se basa en un modelo **Cloud \+ Edge** compuesto por:

- **The Brain**: núcleo central encargado de la generación de código, la orquestación y la gestión de modelos LLM.  
- **Client Node**: entorno local donde se ejecutan los automatismos, preservando la soberanía del dato.  
- **Factories y Blueprints**: mecanismos de metaprogramación que permiten generar, transformar y versionar automatismos de forma determinista.  
- El client node tiene también scripts deterministas. Cuando es posible, la IA genera la estructura de pasos o operaciones para ejecutar con los scripts deterministas, de modo que se ahorra consumo de tokens y se asegura el resultado de la ejecución.

Este enfoque combina la potencia generativa de la IA con los requisitos de seguridad, control y trazabilidad propios de administraciones públicas y empresas.

---

## **0.4. Público Destinatario**

Este documento está dirigido a:

- Arquitectos de software.  
- Desarrolladores del Client Node y el Brain.  
- Equipos de seguridad, auditoría y cumplimiento.  
- Partners que desarrollan verticalizaciones, Blueprints o conectores especializados.

---

## **0.5. Alcance del Documento**

Este documento describe la arquitectura técnica de AutomatIA, incluyendo:

- topología del sistema,  
- anonimización y soberanía del dato,  
- modelo de orquestación generativa,  
- factories de generación de código,  
- sandbox y mecanismos de seguridad,  
- conectores y subsistemas I/O,  
- modos monolito y split,  
- y el roadmap técnico previsto.

---

## **0.6. Modelo de Licenciamiento y Distribución**

La arquitectura de AutomatIA implementa un modelo de distribución **híbrido** diseñado para maximizar la adopción, proteger la propiedad intelectual y facilitar un ecosistema de partners sostenible.

### **Arquitectura de Licenciamiento**

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA DE PRODUCTO                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SERVIDOR (The Brain)                  │   │
│  │                      (Propietario)                       │   │
│  │                                                          │   │
│  │  • LLM Gateway Multi-Proveedor (BYOK)                   │   │
│  │  • Prompts del sistema optimizados                       │   │
│  │  • Multi-tenancy (Admin → Partner → Cliente)            │   │
│  │  • Facturación y auditoría                               │   │
│  │                                                          │   │
│  │  Licencia: Comercial (no exclusiva)                     │   │
│  │  Titular: Universidad                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ API REST                         │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    CLIENTE (Client Node)                 │   │
│  │                      (Open Source)                       │   │
│  │                                                          │   │
│  │  • UI de usuario (NiceGUI)                              │   │
│  │  • Motor de flujos y ejecución                          │   │
│  │  • Procesadores deterministas (ETL, RPA base)           │   │
│  │  • Sistema de extensiones (Custom Scripts)              │   │
│  │                                                          │   │
│  │  Licencia: Apache 2.0 / MIT                             │   │
│  │  Repositorio: Público (GitHub)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### **Distribución de Funcionalidades**

| Funcionalidad | Ubicación | Requiere Licencia Servidor |
|---------------|-----------|---------------------------|
| Extracción IA de documentos | Servidor | Sí |
| Generación de scripts con IA | Servidor | Sí |
| RPA con navegación inteligente | Servidor | Sí |
| ETL y transformaciones deterministas | Cliente | No |
| Custom Scripts (ejecución) | Cliente | No |
| Flujos deterministas | Cliente | No |
| Conectores básicos (archivos, SQL) | Cliente | No |
| Multi-tenancy y facturación | Servidor | Sí |

### **BYOK: Bring Your Own Key**

El sistema implementa un modelo de **resolución de API keys en cascada** que permite a cada cliente utilizar su propio proveedor de LLM:

```
┌─────────────────────────────────────────────────────────────────┐
│              CASCADA DE RESOLUCIÓN DE API KEYS                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. ¿Cliente tiene key propia configurada?                    │
│      └─ SÍ → Usar key del cliente (no facturable)              │
│      └─ NO ↓                                                   │
│                                                                 │
│   2. ¿Partner tiene key asignada al cliente?                   │
│      └─ SÍ → Usar key del partner (facturable al cliente)      │
│      └─ NO ↓                                                   │
│                                                                 │
│   3. ¿Servidor tiene key por defecto?                          │
│      └─ SÍ → Usar key del servidor (facturable)                │
│      └─ NO → Error: No hay proveedor LLM configurado           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Proveedores LLM Soportados:**

| Proveedor | Tipo | Datos Locales | Caso de Uso |
|-----------|------|---------------|-------------|
| Google Gemini | Cloud | No | Producción general |
| OpenRouter | Cloud (multi-modelo) | No | Flexibilidad de modelos |
| OpenAI | Cloud | No | Compatibilidad GPT |
| Azure OpenAI | Cloud privado | Configurable | Cumplimiento enterprise |
| Ollama | Local | Sí | Máxima privacidad, air-gapped |

**Beneficios del BYOK:**
- **Evaluación sin coste:** Clientes prueban con sus propias keys, partners no asumen tokens.
- **Cumplimiento normativo:** Ollama permite que datos nunca salgan de la organización.
- **Flexibilidad:** Cada cliente elige proveedor según sus necesidades y contratos existentes.

### **Modelo Comercial (Partners)**

```
┌─────────────────────────────────────────────────────────────────┐
│                   FLUJO DE INGRESOS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CLIENTE FINAL                                                  │
│       │                                                         │
│       │ Paga suscripción/consumo                               │
│       ▼                                                         │
│  ┌─────────────┐                                                │
│  │   PARTNER   │  ← Operador comercial                         │
│  │             │    (vende, implementa, soporta)               │
│  └──────┬──────┘                                                │
│         │                                                       │
│         │ Paga royalty (15-20%)                                │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │ UNIVERSIDAD │  ← Titular de la IP                           │
│  │             │    (licencia, investiga, publica)             │
│  └─────────────┘                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Modalidades de Licencia:**

| Modalidad | Descripción | Destinatario |
|-----------|-------------|--------------|
| **SaaS (consumo)** | Pago por tokens consumidos | Clientes con volumen variable |
| **SaaS (suscripción)** | Cuota fija mensual | Clientes con uso predecible |
| **On-premise** | Instalación en infraestructura cliente | Empresas con requisitos de seguridad |
| **Enterprise** | On-premise + SLA + customización | Grandes organizaciones |

### **Extensibilidad del Cliente (Open Source)**

El cliente open source permite a los partners desarrollar extensiones sin modificar el núcleo:

- **Custom Scripts promocionables:** Scripts personalizados que pueden convertirse en átomos visibles en el menú.
- **Tematización:** Personalización de logo, colores y nombre de la aplicación.
- **Módulos configurables:** Whitelist/blacklist de funcionalidades visibles por vertical.
- **UIContract extensible:** Definición declarativa de interfaces para nuevos procesadores.

---

# **1\. Topología y Protocolo de Comunicación**

El sistema utiliza una arquitectura híbrida donde la inteligencia reside en la nube (**The Brain**) y la ejecución junto con los datos reside localmente (**Client Node**).

---

### **1.1. Protocolo Zero Knowledge (PII)**

**Soberanía de Datos**  
Los datos reales del cliente (nombres, DNI, correos, IBAN...) nunca abandonan el nodo local.

**Anonimización Reversible**  
El cliente utiliza `AnonymizationContext` para detectar entidades sensibles mediante Regex y NER (spaCy). Sustituye los valores por *fakes* generados por **Faker** y mantiene un mapa local de sustitución.

**Rehidratación**  
Tras recibir resultados de la IA, el cliente aplica `deanonymize()` para restaurar los valores reales en el archivo de salida final.

---

### **1.2. Interfaz Cliente–Servidor**

- **Cliente HTTP:** `client_app/app/clients/brain_client.py`.  
- **Autenticación:** cabecera `X-License-Key`.  
- **Separación de Código:** el código del servidor (`server/`) y del cliente (`client_app/`) son independientes. En producción, el cliente se comunica exclusivamente vía API REST con el Brain.  
- **Flujo de Diseño Asistido:** el nodo cliente actúa como orquestador de la sesión de diseño, enviando intenciones anonimizadas y materializando planos técnicos (*Blueprints*) recibidos del Brain.

---

### **1.3. Sistema de Paquetes**

- **Portabilidad:** exportar flujos completos con dependencias recursivas (scripts y playbooks vinculados).  
- **Seguridad:** manifiesto firmado mediante **HMAC** (cliente) o **RSA** (partner) para garantizar integridad y cumplimiento de licencias.  
- **Ingesta Auditada:** scripts externos importados pasan por `ExternalScriptAuditService` antes de su registro como *DRAFT*.

---

### **1.4. Auditabilidad y Cumplimiento (RGPD y RIA Compliance)**

- **Trazabilidad de Ejecución (RunManifest):** cada tarea procesada genera `run_manifest.json` en el nodo local con metadatos de seguridad, versiones de scripts y resultados de validación AST.  
- **Control del Responsable del Tratamiento:** el nodo cliente retiene el 100% de auditorías y datos originales, evitando *shadow processing* en la nube.  
- **Auditoría de Lógica Externa:** `ExternalScriptAuditService` impide flujos de datos no declarados a servidores externos.  
- **Anonimización Proactiva:** `AnonymizationContext` como prueba técnica de medidas (Art. 32 GDPR).  
- **Registro de Auditoría Empresarial Inmutable:** Complementando al `RunManifest`, el `EnterpriseAuditService` registra de forma persistente cada acceso a datos sensibles (rehidratación PII) y cada modificación de políticas de seguridad. Este log local sirve como evidencia inmutable para auditorías externas, asegurando que toda acción de la IA o del usuario sea trazable.  
- **Trazabilidad de Consultas SQL:** el `RunManifest` registra consultas y esquemas impactados.  
- **Eliminación de Cajas Negras:** la IA elabora scripts legibles/auditables; no hay decisiones opacas.

---

### **1.5. IA Frugal y Sostenibilidad Operativa**

- **Generación vs. Inferencia Continua:** se usa IA para generar el script una sola vez; luego es determinista, reduciendo coste y huella.  
- **Efecto Multiplicador y Reutilización:** paquetes `.automatia` para compartir automatismos dentro de una organización o partner.

---

### **1.6. Modelo de Distribución de Capacidades (Blueprints)**

Biblioteca única que integra **Scripts** (un paso) y **Workflows** (multietapa). Permite suscripción a *Blueprints* alojados en el Brain y actualización *push*.

---

**1.8. Políticas en Cascada (Resolución de Conflictos)** 

El sistema implementa una resolución de políticas en orden descendente: **CLIENTE \> PARTNER \> SISTEMA**.

* **Control de Entorno:** Whitelist/Blacklist de librerías Python permitidas en el sandbox.  
* **Límites de Recursos:** Restricciones de tiempo de ejecución (timeout) y memoria RAM por script.  
* **Screenshot Policy:** Control dinámico de capturas de pantalla para agentes RPA (modos: `BLOCK`, `REVIEW` o `TRUSTED`).

---

### **1.9. Firma Digital y Garantía de Ejecución**

Todo código distribuido desde el Brain (maestros o plantillas) se firma criptográficamente. El nodo cliente verifica la firma del Partner antes de la ejecución.

**1.10. Dualidad de Ejecución: Acciones vs. Workflows** 

La arquitectura permite dos modos de operación:

* **Modo Standalone (Acción Directa):** El usuario selecciona una acción y la ejecuta de forma aislada. Los datos se aportan por el usuario a partir del interfaz de usuario que, en el caso de los custom scripts se construye dinámicamente mediante el `UIContract` para solicitar los parámetros necesarios en ese momento.  
* **Modo Orquestado (Flujo):** El átomo se integra como un paso dentro de un `FlowSpec` (Workflow). En este caso, sus entradas no provienen de un formulario manual, sino que son inyectadas automáticamente desde la salida de un paso previo mediante el mapeo del `DataFlowAnalyzer`.

## **2\. The Brain (Server-Side Core)**

Desarrollado con **FastAPI** y **SQLModel**. Gestiona lógica de negocio multitenant, seguridad centralizada y orquestación avanzada de modelos LLM. El servidor es **propietario** y se licencia comercialmente a través de partners, manteniendo la titularidad en la universidad.

---

### **2.1. LLM Gateway Multi-Proveedor (BYOK)**

El Brain implementa un **gateway unificado** que abstrae la comunicación con múltiples proveedores de LLM, permitiendo configuración por tenant:

- **Resolución en Cascada:** `ClientLLMConfig` → `PartnerLLMConfig` → `ServerDefaults`.
- **Proveedores Soportados:** Google Gemini, OpenRouter, OpenAI, Azure OpenAI, Ollama.
- **Almacenamiento Seguro:** API keys cifradas con Fernet en base de datos.
- **Validación Proactiva:** Verificación de keys al configurar, con feedback inmediato.

**Configuración por Cliente (`ClientLLMConfig`):**

| Campo | Descripción |
|-------|-------------|
| `provider` | Proveedor seleccionado (google, openrouter, openai, azure, ollama) |
| `api_key_encrypted` | Key cifrada con Fernet |
| `base_url` | URL base para Ollama o Azure |
| `preferred_model_tier1/2/3` | Modelos preferidos por tier |
| `is_validated` | Estado de validación de la key |

**Auditoría Diferenciada:**

El `TokenLog` registra el origen de cada llamada LLM:

```python
class TokenLog:
    key_source: str  # "CLIENT", "PARTNER", "SERVER"
    client_id: str
    billable: bool   # False si usa key propia
```

Esto permite facturación precisa: solo se cobra cuando se usan keys del partner o servidor.

---

### **2.2. Gestión de Prompts e Inferencia (Control del Admin)**

- La inteligencia reside en un repositorio de *prompts* gestionado exclusivamente por el **Administrador**.
- **Gestión Centralizada:** solo el Admin puede editar/versionar *prompts* del sistema (p.ej. `sys_flow_orchestrator`, `sys_opt_rpa`).
- **Asignación de Modelos por Rol:** el Admin define el LLM por defecto para cada servicio, compatible con BYOK.
- **AIBrainService:** orquestador que resuelve configuración final: `ClientLLMConfig` \> `tier_override` \> `suggested_model` \> `role_key_default`.
- **Tiers de Modelos:**
  **Tier 1 (Flash):** extracción rápida, bajo coste.
  **Tier 2 (Logic):** razonamiento y filtrado semántico.
  **Tier 3 (Pro):** generación de código y orquestación crítica.

---

### **2.3. Servicio de Orquestación Generativa (`sys_flow_orchestrator`)**

Convierte descripciones funcionales en `FlowSpec`. Genera la secuencia lógica sin requerir que los recursos existan previamente, aunque prioriza la reutilización de átomos locales si están disponibles en el contexto enviado por el cliente.

---

### **2.4. El Servidor como Motor de Observabilidad (Telemetría)**

El Brain actúa como el centro neurálgico de observabilidad, permitiendo a Superadmins y Partners monitorizar la salud operativa de toda la base instalada sin comprometer la privacidad (Zero-Knowledge).

- **Centralización de Telemetría:** Implementación del modelo `ClientTelemetryLog` que registra métricas detalladas de cada ejecución local:  
  - **Performance:** Tiempos de ejecución (`execution_time_ms`).  
  - **Consumo:** Seguimiento de tokens utilizados y estimación de costes.  
  - **Resultado:** Estado de la tarea (`success`, `error`) y tipificación de fallos.  
- **Protocolo de Sincronización:** El nodo cliente envía lotes de logs de forma asíncrona hacia el endpoint `/v1/telemetry/sync` del servidor.  
- **Análisis y Refinamiento:** Permite detectar cuellos de botella semánticos o fallos recurrentes en plantillas para refinar de forma proactiva los *system prompts* y la selección de modelos.  
- **Monitorización Multitenant:** Los Partners pueden visualizar estadísticas agregadas por cliente, permitiendo un soporte técnico preventivo.

---

### **2.5. Políticas de Seguridad y Soporte (Partner & Admin)**

- **Políticas Base (Admin):** librerías permitidas, dominios bloqueados, umbrales de anonimización.
- **Adaptación (Partner):** hereda o ajusta políticas por cliente/industria.
- **Soporte Escalado:** `sys_support_diagnostician` genera informes para intervención del Partner con telemetría anonimizada.

---

### **2.6. Billing y Gestión de Licencias (Partner)**

- **Gestión Operativa:** creación, renovación y suspensión de licencias por parte del Partner.  
- **Control de Tokens:** saldo de tokens/créditos por cuenta.  
- **BillingEngine:** valida en tiempo real saldo del Partner y vigencia de licencia del cliente final.

## **3\. Client Node (Local Runtime)**

Desarrollado con **NiceGUI** y **SQLModel (SQLite local)**. El cliente es **open source** (Apache 2.0/MIT) y constituye el punto de entrada para usuarios finales, garantizando la soberanía del dato mediante ejecución 100% local de los automatismos.

---

**3.0 Taxonomía de 4 Capas**

La arquitectura organiza los componentes en cuatro categorías estrictas para garantizar la interoperabilidad:

1. **Triggers:** Disparadores por evento (Email, File Watcher, Scheduler).  
2. **Inputs:** Receptores de datos (SQL, API, Scrapers).  
3. **Processors:** Lógica de negocio y transformación . Incluye tanto scripts deterministas como el **LLM Processor**, que permite realizar llamadas dinámicas a modelos de lenguaje durante la ejecución para tareas de razonamiento en tiempo real. Hay procesadores que requieren del desarrollo de código mediante IA, otros que son deterministas y otros híbridos (pueden ejecutarse de forma determinista o desarrollar código para funcionalidades avanzadas).  Los que son deterministas pueden consumirse directamente desde la función de utilidades.  
4. **Outputs:** Destinos finales (Generación de Docs, envío de avisos, carga en ERP).

**Nota de Diseño:** Todo componente registrado en estas categorías es, por definición, una "unidad funcional independiente". Esto significa que el mismo código (acción) que se usa para una tarea rápida de "limpieza de Excel" desde el menú de *Processors* puede ser utilizado en el diseñador de Blueprints para formar parte de una cadena de suministro de datos compleja.

### **3.1. Persistencia y Organización de Activos (Ácciones)**

El sistema implementa una separación estricta entre la **Definición del Activo** (estática) y el **Contexto de Ejecución** (volátil).

#### **A. Almacén de Acciones (átomos). Estructura Jerárquica**

Cada componente se almacena siguiendo la taxonomía de 4 capas, lo que permite la modularidad y el intercambio de paquetes:

* `atoms/{triggers|inputs|processors|outputs}/{atom_name}/`  
  * `logic.py`: El código fuente determinista generado por la IA.  
  * `contract.json`: Esquema `UIContract` (entradas) y `OutputSchema` (garantías de salida).  
  * `README.md`: Documentación técnica autogenerada tras el "sellado".  
  * `assets/`: Recursos estáticos necesarios para el átomo (plantillas, iconos).

#### **B. Entorno de Ejecución (Runtime Data)**

La gestión de rutas durante la ejecución (`ExecutionService`) garantiza el aislamiento y la limpieza:

* `data/executions/{exec_id}/`:  
  * `/sandbox`: Espacio de trabajo temporal donde se procesan archivos locales.  
  * `/pii_vault`: Almacén temporal de datos sensibles para la rehidratación local (Zero-Knowledge).  
  * `/outputs`: Resultados finales (Excel, PDF, JSON) listos para ser entregados o archivados.  
  * `trace.log`: Registro de telemetría y auditoría del flujo para el Partner.

---

### **3.2. Sandbox de Ejecución Segura**

- **Supervisión Humana (HITL):** el código generado se presenta al usuario para revisión previa a la primera ejecución.  
- **Aislamiento:** ejecución mediante `ProcessPoolExecutor` para no bloquear el hilo principal.  
- **Jailhouse (Jaula):** cambio del CWD al directorio de la ejecución.  
- **Monkey-patching:** `builtins.open` restringe escrituras fuera del *jail*; *imports* filtrados por *whitelist* `ALLOWED_IMPORTS`.  
- **Auditoría AST:** `SecurityAuditor` detecta funciones prohibidas (`eval`, `exec`, `os.system`).

---

### **3.3. Integridad del Flujo de Datos (Data-Link Validation). Análisis de coherencia y bridges**

`DataFlowAnalyzer` valida la secuencialidad de variables. **Regla de tubería:** un paso *n+1* solo consume variables generadas en pasos 1..n. Reordenaciones activan revalidación del grafo de dependencias.

El `WorkflowHealthService` valida tipos de datos entre componentes. Si existe incompatibilidad (ej. un JSON que debe entrar en un campo String), el sistema sugiere o genera automáticamente un "Paso Puente" de transformación.

---

### **3.4. Asistente de Diseño IA** 

El sistema incorpora un panel lateral de asistencia avanzada que implementa un **Triple Sistema de Ayuda Contextual**:

1. **Ayuda Determinista:** Proporciona asistencia inmediata extrayendo información técnica y etiquetas de ayuda directamente de los archivos `README.md` de cada átomo.  
2. **Soporte RAG (Retrieval-Augmented Generation):** El chat del copiloto utiliza un sistema RAG local que envía el `README.md` del componente junto con la pregunta del usuario al LLM, garantizando respuestas precisas basadas en la documentación real del activo.  
3. **Ayuda Activa (Code Injection):** Permite transformar las respuestas del LLM en lógica ejecutable. Esta capacidad es clave en el diseño de Blueprints y en átomos de visualización (Gráficos), transformación y reportes, donde la IA escribe el código técnico por el usuario basándose en su intención.  
4. **Ciclo de Refinamiento:** Soporte para iteración (clarificación de dudas del Brain) y reordenación manual por el usuario.  
   **Inyección de Variables:** El usuario referencia los datos mediante la copia y pegado de identificadores de variables desde el "Inventario de Datos". El sistema valida la integridad de estas conexiones en tiempo real.

---

### **3.5. Capa de Extensibilidad para Partners (Verticalización)**

La aplicación cliente es **open source** (Apache 2.0/MIT), permitiendo a los partners desarrollar extensiones sin modificar el núcleo y contribuir mejoras al proyecto.

#### **3.5.1. Modelo de Extensibilidad Open Source**

El cliente open source permite múltiples mecanismos de extensión:

- **Custom Scripts Promocionables:** Scripts desarrollados por partners pueden "promocionarse" a átomos visibles en el menú principal mediante el campo `is_promoted` en `ScriptLibrary`.
- **Interfaz `IProcessor`:** Contrato base que permite registrar nuevos procesadores sin tocar el código del núcleo.
- **StepRegistry Dinámico:** Registro automático de nuevos tipos de pasos desde código externo.

```python
# Ejemplo: Promoción de Custom Script a átomo visible
await script_library_service.promote_to_atom(
    script_id=123,
    display_name="Validador Fiscal",
    icon="gavel",
    category="processors"
)
```

#### **3.5.2. Tematización y White-Labeling**

Partners pueden personalizar la apariencia del cliente mediante `theme_config.json`:

| Configuración | Descripción |
|---------------|-------------|
| `app_name` | Nombre de la aplicación |
| `logo_path` | Ruta al logo personalizado |
| `primary_color` | Color primario de la UI |
| `modules_whitelist` | Lista de módulos visibles |
| `modules_blacklist` | Lista de módulos ocultos |

Esto permite crear **packs verticales** (Legal, Industrial, Logística) con funcionalidades específicas.

#### **3.5.3. Inyección de Lógica mediante "Master Blueprints"**

- Los Partners registran y distribuyen sus propios *Blueprints* desde el Brain.
- **Aislamiento:** el código del Partner se ejecuta en el nodo local bajo el mismo sandbox.
- **Distribución Selectiva:** segmentación por `access_groups` según licencia/contrato.

#### **3.5.4. Desarrollo de Conectores de Última Milla**

- **Data Fulfillment:** conectores para cierre del ciclo del dato.
- **Adaptadores ERP/CRM:** scripts maestros especializados para SAP, Sage, Navision, etc.
- **Propiedad del Código:** conectores propiedad del Partner, protegidos por Firma Digital.

#### **3.5.5. Interfaz de Plugins NiceGUI**

- Vistas personalizadas (dashboards/formularios) renderizadas dentro del cliente, con métricas sectoriales.
- Componentes reutilizables registrados en el sistema de UI.

---

### **3.4. Estándar de Interfaz Universal (UI Pattern)**

Para garantizar la consistencia, todos los módulos de automatización siguen el patrón **Selector-Contexto-Acción**:

- **Selector de Activos:** Uso del `AutomationSelector` como filtro de entrada para distinguir entre el modo "Creación/Grabación" y el modo "Ejecución Determinista".  
- **Contratos de Interfaz (Dynamic UI):** Los scripts personalizados y activos externos definen sus necesidades mediante un JSON de metadatos (`ui_contract`). La interfaz se construye dinámicamente (renderizado de inputs/outputs) basándose en este contrato, eliminando la necesidad de programar vistas específicas para cada script.  
- **Dynamic UI Standalone:** Para el uso directo de átomos, el sistema genera automáticamente un "Asistente de Ejecución" basado en el `ui_contract`. Esto permite que cualquier script o utilidad se convierta instantáneamente en una herramienta de usuario final sin necesidad de desarrollar vistas personalizadas.

---

### **3.7. Ciclo de Vida y Mantenimiento Proactivo**

Gracias a `SyncManager`, el Partner mantiene control total del mantenimiento: **Hot-Fixing** vía actualización del *Master Blueprint* en el Brain y **propagación automática** a nodos suscritos en el siguiente ciclo de sincronización.

**Gestión de Residuos (Cleanup Service):** El sistema incorpora un servicio de limpieza automática que gestiona el ciclo de vida de los datos temporales en `/sandbox` y `/pii_vault`. Este servicio garantiza que no se sature el almacenamiento local y elimina rastros de datos sensibles tras la ejecución, respetando siempre las sesiones activas de RPA o grabaciones en curso para evitar la corrupción de flujos vivos.

---

### **3.8. Gestor de Informes (Report Designer & Wizard)**

El nodo cliente incluye un subsistema avanzado para la creación y generación de informes corporativos:

- **Diseñador de Bloques:** Interfaz visual para construir plantillas mediante componentes modulares (Markdown, Tablas, Gráficos ECharts).  
- **Vista Previa Zero-Knowledge:** Renderizado en tiempo real usando datos sintéticos (*MockData*) generados a partir del esquema de entrada, permitiendo diseñar el informe sin acceder a datos reales.  
- **Asistente IA de Visualización:** El Brain analiza el esquema de datos (`input_schema`) y propone los mejores bloques y gráficos para representar la información.  
- **Wizard de Generación:** Flujo guiado para el usuario final que combina selección de datos, análisis opcional con IA para generar conclusiones y exportación multiformato.


**3 bis Ciclo de vida de los activos** 

**Servicio de Sellado (Asset Finishing)** Antes de pasar a producción, cada activo debe ser "sellado":

* **Inferencia de Contratos:** Extracción automática de `UIContract` y `OutputSchema` mediante análisis estático.  
* **Auditoría AST:** Escaneo del árbol de sintaxis abstracta para detectar funciones peligrosas (`eval`, `os.system`).  
* **Documentación In-Code:** Generación automática de `README.md` técnico basado en la lógica del script.

## **4\. Automatización e I/O (Client Node)**

### **4.1. Watchers (Fuentes)**

- **FolderWatcher:** basado en `watchdog`; implementa `_wait_for_stability` para asegurar que el archivo ha terminado de escribirse.  
- **EmailWatcher:** conexión IMAP para descarga de adjuntos filtrados por remitente (*whitelist*).  
- **APIWatcher:** cliente REST con paginación automática (offset, cursor, `next_url`).

---

### **4.2. Connectors (Salidas)**

- **HttpConnectorService:** reintentos con *exponential backoff* mediante `tenacity`.  
- **EmailSender:** envío SMTP cifrado, con soporte para adjuntar el `previous_output` de un flujo.

---

### **4.3. SQL Connectors**

- **Conectividad Local Nativa:** el nodo cliente ejecuta consultas directamente contra bases corporativas (SQL Server, PostgreSQL, MySQL…), en red interna o nube.  
- **Seguridad de Credenciales:** cadenas de conexión y credenciales cifradas **solo** en la base local; el Brain no accede a claves.  
- **Interoperabilidad:** conexión SQL como **Fuente** (extracción) o **Salida** (inserción de resultados), eliminando necesidad de archivos intermedios.

## **5\. Procesadores. Las fábricas de Código (Factories)**

### **5.1. PDFFactory (Extracción)**

- **Estrategia Dual:** `fitz` para texto lineal y `pdfplumber` para reconstrucción de tablas complejas.  
- **Anchor-Based:** *prompts* con ejemplos reales para generar selectores basados en **anclas** de texto.  
- **DataConsolidator:** salida unificada `{ "status": "ok", "data": {...}, "meta": {...} }`.

---

### **5.2. RPA y Visión (Navegación)**

- **Motor de Grabación JavaScript:** registra eventos del DOM, selectores y jerarquías en tiempo real.  
- **Cortex:** procesa logs y los traduce en *playbooks* de **Playwright** deterministas.  
- **ScreenshotGuard:** intercepta capturas para modelos multimodales, aplicando reglas de bloqueo o revisión según sensibilidad.  
- **Agentes de Navegación y Visión** Integración de agentes basados en lenguaje natural que operan sobre `Playwright`. Incluye un `ScreenshotGuard` que anonimiza o bloquea capturas visuales antes de que el nodo local las envíe al "Brain" para su análisis.

---

### **5.3. ETL & Data Factory (Transformación)**

- **Transformación Semántica:** scripts **Pandas** para limpieza, normalización y filtrado de volúmenes JSON/DataFrames.  
- **Optimización de Memoria:** técnicas de *downsampling* y gestión eficiente para no superar límites del sandbox.

---

### **5.4. Report & Graphics Factory (Visualización y Documentación)**

Factoría de renderizado de alta fidelidad que transforma datos de flujo en documentos profesionales.

- **Motor de Renderizado Headless (Playwright):** Utiliza Playwright para capturar vistas NiceGUI/HTML y exportarlas a **PDF** o **PNG**. Esto permite una fidelidad total respecto a lo visualizado en el navegador, incluyendo animaciones de gráficos terminadas.  
- **Estructura Basada en Bloques:** Los informes se definen como una secuencia de bloques configurables:  
  - **Texto/Markdown:** Soporte para plantillas Jinja2 y marcadores de posición.  
  - **Tablas Dinámicas:** Generadas automáticamente a partir de listas de objetos.  
  - **Gráficos (ECharts):** Visualizaciones interactivas inyectadas directamente en el DOM para el renderizado.  
- **Mapeo Nativo de Datos:** Integración con `DataFlowAnalyzer` para mapear variables del flujo de trabajo a los campos de la plantilla mediante el `VariableSelector`.  
- **Compatibilidad Legacy:** Soporte mantenido para generación directa de archivos **ODT** (editables) y **PDF** ligeros (ReportLab) para casos que no requieran renderizado HTML complejo.

---

### **5.5. Custom Scripting Factory (Lógica Genérica)**

- **Adaptación de Código Externo:** ingerir scripts Python y adaptarlos al formato de la plataforma (envolver en funciones estándar `transform()` o `extraer_datos()`).  
- **Estandarización `ResourceSpec`:** cumplimiento de contratos de entrada (`input_type`) y extensiones definidas.

---

### **5.6. LLM Processor Factory (Inferencia en Runtime)**

A diferencia de otros componentes donde la IA genera el código previamente, este factoría permite la **inferencia dinámica**:

---

**Integración en Flujo:** Permite que un paso del workflow sea una consulta directa a la IA para procesar datos variables (ej. análisis de sentimiento o resúmenes).

## **6\. Orquestación y Coherencia de Datos**

### **6.1. Workflow Health Service (El copiloto)**

El editor de flujos incorpora un servicio de validación de grafos en tiempo real:

- **Validación de Tipos:** Detecta discordancias entre el output de un átomo y el input del siguiente (ej. JSON vs CSV).  
- **Generación de "Pasos Puente":** Capacidad de la IA para insertar automáticamente átomos de transformación (`CUSTOM_SCRIPT`) que actúan como adaptadores entre pasos incompatibles, garantizando la continuidad del flujo de datos sin intervención manual en el código.

### **6.2. Catálogo dinámico de átomos (acciones)**

El catálogo de tareas se sincroniza automáticamente con el `StepType` de la aplicación, presentándose mediante una galería de tarjetas categorizadas que eliminan la redundancia en el proceso de creación de flujos.

## **7\. Protocolo y Estándares de Desarrollo (Guía para el Agente)**

Para mantener integridad técnica, seguridad y soberanía del dato, todo asistente/desarrollador debe seguir estas reglas.

---

### **7.1. Filosofía de Ingeniería**

- **Determinismo Post-IA:** priorizar creación de activos deterministas; si se usa LLM en *runtime* como *fallback*, advertir al usuario.  
- **Logic-First:** prohibido modificar la interfaz (NiceGUI) sin validar antes la lógica en Servicios/Core.  
- **TDD Obligatorio:** no se escribe código de producción sin tests (unitarios/integración) en `tests/`. Cobertura como métrica principal.  
- **Minimalismo en UI:** nada de librerías de terceros para *wizards/steppers*; usar solo componentes nativos NiceGUI.

---

### **7.2. Estándares Técnicos de Implementación**

- **Patrón de Inyección:** no instanciar servicios manualmente; usar `client_app.app.core.state`.  
- **Asincronía Total:** prohibidos métodos síncronos para I/O; usar `async/await`.  
- **Resiliencia Windows:** reintentos para errores de acceso compartido (WinError 32).  
- **Paridad de Base de Datos:** compatibilidad SQLite (local) y PostgreSQL (servidor); validar JSONB y Enums con scripts de dockerización.

---

### **7.3. Seguridad y Soberanía del Dato**

- **Zero-Knowledge:** anonimizar cualquier flujo antes de enviarlo al servidor.  
- **Validación de Seguridad AST:** integrar `audit_code()` o `SecurityAuditor` en generadores de código/ingestas externas antes del sandbox.

---

### **7.4. Localización y Calidad**

- **i18n Nativa:** prohibido *hardcodear* *strings*; registrar mensajes en `translations.json` y acceder vía `state.i18n.t('key')`.  
- **Métricas de Cobertura:** \-70% en módulos core y \-50% en UI.  
- **Tests Críticos:** validar rehidratación de datos y estructura de paquetes.

## **8\. Roadmap de Evolución (Fases en Desarrollo)**

Esta sección define las capacidades en desarrollo y mejoras planificadas. Los agentes deben consultarla para evitar implementaciones redundantes o fuera de la hoja de ruta.

**Documentos de Planificación Relacionados:**

| Documento | Descripción |
|-----------|-------------|
| `PLAN_OPEN_CORE_SERVER.md` | Estrategia de licenciamiento y modelo de negocio |
| `PLAN_OPEN_CORE.md` | Plan de extensibilidad del cliente |
| `PLAN_LLM_MULTIPROVEEDOR.md` | Diseño técnico de BYOK |
| `ROADMAP.md` | Hoja de ruta de desarrollo actualizada |

---

### **8.1. Fase 1 — Infraestructura Servidor y Seguridad**

Preparación del entorno profesional para Partners tras validar la lógica con SQLite.

- **Prompt 1.1 (Entorno):** Dockerización del Brain y pruebas de persistencia con PostgreSQL en contenedores.  
- **Prompt 1.2 (Base de Datos):** Migración asíncrona a PostgreSQL y orquestación mediante Docker Compose.  
- **Prompt 1.3 (Acceso):** Sistema de autenticación universal y roles (RBAC) para Administrador y Superadministrador.

---

### **8.2. Fase 2 — Flujo de Datos y Validación Visual**

Diseño de flujos de forma gráfica.

- **2.1 (Grafo):** Preparación del Analizador de Dependencias en `DataFlowAnalyzer` para generar el grafo de conexiones de datos.  
- **2.2 (Inventario):** Creación del panel lateral de **Inventario de Datos** con chips de variables arrastrables.  
- **2.3 (Drop Zones):** Zonas de soltado en formularios de pasos para recibir variables arrastradas.  
- **2.4 (Contratos):** Validación de compatibilidad de tipos entre pasos.

---

### **8.3. Fase 3 — Salud, Rendimiento y Mantenimiento Autónomo**

Transformación del sistema en plataforma de mantenimiento predictivo.

- **3.1 (Tiempos):** Evolución de `ResourceListingService` para calcular tiempo medio histórico y ETAs.  
- **3.2 (Dashboard):** Widget de Salud y Rendimiento con *sparklines* de tendencia de velocidad.  
- **3.3 (Self-Healing):** Motor de optimización automática que analiza cuellos de botella y propone parches de código.

---

### **8.4. Fase 4 — Servicios Avanzados y Ecosistema**

Funcionalidades para el mercado industrial y red de partners.

- **4.1 (Visión):** Integración de OCR Local como *fallback* y blur confidencial en capturas RPA.  
- **4.2 (Sistemas):** Daemonización de watchers (Email, Carpetas) como servicios del SO y gestión de licencias multiasiento (`machine_id`).  
- **4.3 (Ecosistema):** Creación del **Partner Hub** para descarga de plantillas y transferencia de automatismos entre partners.

---

### **8.5. Fase 5 — Ecosistema y Verticalización (Desarrollo por Partners)**

Objetivo: delegar especialización sectorial en expertos de dominio manteniendo la integridad del core.

- **6.1 (Conectores ERP):** Librerías de integración con sistemas locales (SQL Server, Oracle, SAP) para cierre del ciclo de datos.  
- **6.2 (Packs de Conocimiento):** Bibliotecas maestras de flujos para sectores específicos (Legal, Industrial, Logística).  
- **6.3 (Nodos Especializados):** Adaptación del cliente para hardware específico (PLCs, sensores industriales) en Industria 4.0.

## **9\. Migración de server\_app a servidor (Split Mode)**

Define la transición del desarrollo **monolito** al modelo **Client-Server** con el Brain en servidor remoto.

---

### **9.1. Resolución Dinámica de Endpoints**

- **Fuente de Verdad Única:** los servicios usan `_get_brain_client` para resolver ubicación del servidor.  
- **Configuración del Usuario:** `brain_url` se recupera de `ServerConnection` (visible en la página de configuración).  
- **Migración:** actualizar `brain_url` con la URL remota (ej. `https://api.automatia.ai`).

---

### **9.2. Gestión de Licencia Real vs. Mocked**

- Se elimina el uso de claves simuladas. `_get_active_license_key()` consulta la licencia activa local.  
- La licencia se inyecta en la cabecera `X-License-Key` en cada petición (`BrainAPIClient`). Si no hay licencia válida, el servicio se detiene.

---

### **9.3. Lógica de Conmutación (Adapter Pattern)**

- **Detección de Modo:** `_get_brain_client` comprueba si existe `state.brain`.  
  - Si existe (Monolito): usa `LocalBrainClient`.  
  - Si no (Split/Remoto): instancia `BrainAPIClient` con URL y licencia de la configuración.  
- **Transparencia:** mismo código en portátil (monolito) y en infraestructura cliente (remoto) sin modificaciones.

**Pasos Operativos para la Migración**

1. **Despliegue del Brain:** instalar la imagen Docker del servidor en el host remoto.  
2. **Configuración del Cliente:** acceder a Configuración y sustituir `http://localhost:8000` por la URL pública del servidor e introducir la License Key oficial.  
3. **Verificación:** al no detectar Brain local, se activará `BrainAPIClient` y se firmarán peticiones con licencia real.