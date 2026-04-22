# Instrucciones para agentes de programación

## Contexto del proyecto

Gov Gen AI Platform es el resultado de integrar **AI Agents Hub** (chatbots RAG, LangGraph) y **AutomatIA**
(automatización, scripts, RPA) en un monorepo. El plan de desarrollo completo está en `PLAN_DESARROLLO.md`.

El cliente NiceGUI (`client_app/`) está siendo migrado progresivamente al servidor FastAPI y al frontend React.
**El código NiceGUI es legacy y debe eliminarse** a medida que cada módulo quede cubierto en el nuevo sistema.

---

## Regla crítica: migración = código nuevo + borrado del legacy

Una tarea de migración **no está completa** hasta que se elimine el código original.
No dejes código muerto, imports sin usar, archivos vacíos ni comentarios `# TODO: migrate`.

### Definición de "migración completa" (checklist obligatorio)

Antes de cerrar cualquier tarea de migración, verifica y ejecuta cada punto:

- [ ] La nueva implementación tiene tests que pasan (`pytest` o equivalente)
- [ ] El endpoint o servicio nuevo está integrado y verificado end-to-end
- [ ] El archivo o módulo legacy correspondiente está **eliminado** (no comentado, no archivado)
- [ ] Los imports del legacy han sido eliminados de todos los ficheros que los referenciaban
- [ ] No quedan referencias al código eliminado en ningún fichero del proyecto (`grep -r` antes de cerrar)
- [ ] El `docker compose up` + suite de tests completa sigue pasando tras el borrado

---

## Normas generales de limpieza

**Borra, no comentes.**
Si el código ya no se usa, elimínalo. Los comentarios `# deprecated`, `# old version` o `# legacy`
son deuda técnica disfrazada. El historial de git es la fuente de verdad del pasado.

**Borra, no archives.**
El directorio `_legacy_archive/` existe por razones históricas. No añadas nada nuevo ahí.
Si hay algo en `_legacy_archive/` que ya esté migrado, bórralo también.

**Sin backwards-compatibility shims.**
No renombres variables a `_old_foo`, no re-exportes símbolos eliminados, no añadas
comentarios `# removed` donde había código. Si algo se elimina, se elimina limpiamente.

**Sin código muerto especulativo.**
No dejes funciones, clases o módulos "por si acaso se necesitan en el futuro".
Si no se usa ahora, no existe.

---

## Estructura de módulos y dónde vive cada cosa

```
server/app/modules/automation/   ← lógica de flows, ETL, PDF, scripts (migrado desde client_app)
server/app/modules/agents_hub/   ← RAG, LangGraph, chatbots, Docling
server/app/core/                 ← servicios compartidos: LLM gateway, auth, tenancy, MCP
frontend/src/automation/         ← UI de flujos y scripts (reemplaza vistas NiceGUI)
frontend/src/widget/             ← chatbot público embebible
frontend/src/agent/              ← modo agente expandido
frontend/src/admin/              ← panel admin hub + plataforma
client_app/                      ← SOLO agente de ejecución local (RPA, folder watcher)
                                    Todo lo demás aquí es legacy pendiente de migrar
```

Si estás escribiendo código nuevo en `client_app/` fuera del agente de ejecución local,
para y consulta si pertenece al servidor o al frontend.

---

## Estándares de desarrollo

- **TDD obligatorio**: escribe el test antes del código de producción. No hay PR sin tests.
- **Asincronía total**: prohibidos métodos síncronos para I/O en el servidor. Usa `async/await`.
- **Sin instanciar servicios manualmente**: usa inyección de dependencias (FastAPI `Depends`).
- **i18n obligatorio en el frontend**: ningún string hardcodeado en la UI. Usa `i18next`.
- **Sin features no pedidas**: no añadas manejo de errores, validaciones, flags ni abstracciones
  para escenarios que no están en la tarea actual.
