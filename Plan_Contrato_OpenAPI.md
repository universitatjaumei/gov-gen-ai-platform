# Plan Contract-First — Alineación Backend/Frontend mediante OpenAPI + Orval

> Creado: 2026-05-05. Bloque previo al retorno a la Fase 1 del plan principal.
> Sustituye cualquier desarrollo "a mano" de DTOs y llamadas API en el frontend.
> Referencia estratégica: `Estrategia alineacion_backend_frontend.txt`.

---

## Propósito

Detener la acumulación de deuda de integración backend/frontend implantando una
**infraestructura contractual mínima** antes de continuar con los prompts 9B.4+ de la Fase 1.

El síntoma que motiva este bloque: cambios en DTOs Pydantic del backend han quedado
desalineados con los tipos TypeScript manuales del frontend (`frontend/src/shared/api/*.ts`),
provocando bugs de integración que solo se descubren en prueba manual.

La solución es que cualquier cambio de contrato que no adapte el frontend **rompa la
compilación TypeScript**, y que eso sea verificable en CI antes de mergear.

---

## Estado inicial verificado (2026-05-05)

| Elemento | Estado |
|---|---|
| `export_openapi.py` | ❌ No existe |
| `openapi.json` | ❌ No existe |
| Orval en `frontend/package.json` | ❌ No instalado |
| `frontend/orval.config.ts` | ❌ No existe |
| `frontend/src/shared/api/generated/` | ❌ No existe |
| DTOs manuales en `frontend/src/shared/api/` | ✅ Existen (chatbots, clients, llmConfigs, feedback, ingestion, promptTemplates) |
| `@tanstack/react-query` | ✅ v5.100.1 |
| `zod` | ✅ v4.3.6 |
| `@hookform/resolvers` | ✅ v5.2.2 |
| CI pipeline | ✅ `.github/workflows/ci.yml` — sin pasos frontend |

---

## Reglas obligatorias de este bloque

1. **No editar manualmente** los archivos de `src/shared/api/generated/`.
2. **No crear nuevas interfaces TypeScript** para DTOs ya presentes en OpenAPI.
3. **No introducir llamadas manuales a `fetch`** si existe hook generado por Orval.
4. **No hardcodear enums** si pueden venir del contrato.
5. **No considerar terminado** un refactor backend si no se valida el formulario afectado.
6. **Cada prompt debe dejar los tests pasando** antes de cerrar (salvo los RED que definen el fallo esperado).

---

## Nomenclatura de prompts

`CF.N.P` donde:
- `CF` = Contract-First
- `N` = número de bloque (1 = backend export, 2 = Orval, 3 = compilación, 4 = formulario piloto, 5 = CI)
- `P` = fase TDD (1 = RED, 2 = GREEN, 3 = REFACTOR)

---

## Mapa de ejecución

```
CF.1.1 (RED)   → Escribir test que verifica exportación OpenAPI
CF.1.2 (GREEN) → Implementar export_openapi.py + generar openapi.json
CF.1.3 (RED)   → Test de estructura mínima del contrato (schemas críticos)
CF.1.4 (GREEN) → Ajustar schemas Pydantic si faltan campos críticos

CF.2.1 (RED)   → Verificar que npm run generate:api falla (Orval no instalado)
CF.2.2 (GREEN) → Instalar Orval, crear orval.config.ts, ejecutar generación inicial
CF.2.3 (REFACTOR) → Ordenar y verificar la carpeta generated/

CF.3.1 (RED)   → Ejecutar tsc --noEmit y capturar errores actuales como baseline
CF.3.2 (GREEN) → Reemplazar imports manuales por tipos generados en los módulos que tengan errores
CF.3.3 (REFACTOR) → Eliminar interfaces manuales duplicadas; tsc --noEmit debe pasar limpio

CF.4.1 (RED)   → Tests de formulario Chatbot Create/Edit antes de refactorizar
CF.4.2 (GREEN) → Refactorizar formulario con hooks generados + react-hook-form + zodResolver
CF.4.3 (GREEN) → Implementar mapper de errores API → formulario
CF.4.4 (REFACTOR) → Extraer utilidades comunes reutilizables

CF.5.1 (GREEN) → Añadir pasos de contrato al CI existente
CF.5.2 (RED/GREEN) → Verificar que CI falla cuando el contrato cambia sin actualizar frontend
```

---

## BLOQUE CF.1 — Exportación offline del contrato OpenAPI

### Prompt CF.1.1 (RED) — Test de exportación del contrato

```markdown
# PROMPT CF.1.1 (RED) — Test: el backend puede exportar openapi.json offline

Objetivo: escribir un test pytest que verifique que el backend puede generar un openapi.json
válido sin levantar Uvicorn ni conectarse a la base de datos.

Contexto:
- El proyecto FastAPI está en server/app/main.py.
- No existe aún export_openapi.py ni openapi.json.
- Este test DEBE FALLAR inicialmente porque no existe el mecanismo de exportación.

Instrucciones:

1. Crear el archivo server/tests/test_openapi_export.py.

2. El test debe:
   a. Importar la instancia de FastAPI (app) desde server/app/main.py sin
      levantar Uvicorn ni conectarse a la BD (mockear o parchear lo necesario).
   b. Llamar a app.openapi() y verificar que devuelve un dict.
   c. Verificar que el dict contiene las claves "openapi", "info", "paths" y "components".
   d. Verificar que "paths" contiene al menos uno de estos prefijos:
      "/api/v1/hub/chatbots", "/api/v1/hub/clients", "/api/v1/hub/llm-configs".
   e. Verificar que "components" > "schemas" contiene al menos uno de estos nombres:
      "ChatbotCreate", "ChatbotRead", "ClientCreate", "ClientRead".

3. Ejecutar pytest server/tests/test_openapi_export.py y confirmar que FALLA.
   Si pasa sin implementar nada, el test está mal — revisar y corregir.

4. Documentar en comentario qué dependencias de startup bloquean la importación
   de la app (BD, variables de entorno, lifespan hooks) para el siguiente prompt.

Criterio de RED correcto:
- El test existe y define el comportamiento esperado.
- Falla por ImportError, AttributeError, AssertionError o similar — no por error de sintaxis.
- Quedan documentados los obstáculos de inicialización encontrados.
```

---

### Prompt CF.1.2 (GREEN) — Implementar export_openapi.py

```markdown
# PROMPT CF.1.2 (GREEN) — Implementar export_openapi.py y generar openapi.json

Objetivo: crear el script server/export_openapi.py que exporte el contrato OpenAPI
a un archivo openapi.json sin levantar Uvicorn ni requerir conexión a BD.

Contexto:
- El test CF.1.1 definió qué debe contener el openapi.json.
- Los obstáculos de inicialización (si los hay) quedaron documentados en CF.1.1.
- El script debe poder ejecutarse en CI sin Docker ni BD activa.

Instrucciones:

1. Crear server/export_openapi.py con estas propiedades:
   a. Importa la instancia FastAPI (app) desde server/app/main.py.
   b. Si la inicialización de la app requiere variables de entorno, establece
      valores mínimos ficticios ANTES de importar la app:
      os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
      os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg2://x:x@localhost/x")
      (y cualquier otra variable que bloquee el import según CF.1.1)
   c. NO ejecuta ningún lifespan, no conecta a BD, no levanta Uvicorn.
   d. Llama a app.openapi() para obtener el schema.
   e. Guarda el resultado en server/openapi.json (JSON indentado, codificación UTF-8).
   f. Imprime "openapi.json generado: N paths, M schemas" al terminar.

2. Ejecutar el script:
   cd server && python export_openapi.py

3. Verificar que server/openapi.json existe y es JSON válido:
   python -c "import json; d=json.load(open('server/openapi.json')); print(len(d['paths']), 'paths')"

4. Copiar server/openapi.json a frontend/openapi.json:
   (en Windows: copy server\openapi.json frontend\openapi.json)

5. Ejecutar el test de CF.1.1:
   cd server && uv run pytest tests/test_openapi_export.py -v
   → Debe pasar.

6. Añadir server/openapi.json y frontend/openapi.json al .gitignore si no están ya,
   con comentario "# Generado por export_openapi.py — no editar manualmente".

Criterio de done:
- server/export_openapi.py existe y se ejecuta sin errores.
- server/openapi.json y frontend/openapi.json existen y son JSON válidos.
- El test CF.1.1 pasa.
- Los archivos .json están en .gitignore.
```

---

### Prompt CF.1.3 (RED) — Test de estructura mínima del contrato

```markdown
# PROMPT CF.1.3 (RED) — Test: el openapi.json contiene los schemas públicos críticos

Objetivo: verificar que el contrato refleja correctamente los DTOs que el frontend
ya consume manualmente, detectando gaps antes de configurar Orval.

Contexto:
- server/openapi.json y frontend/openapi.json ya existen (CF.1.2).
- Los DTOs manuales actuales del frontend están en:
  frontend/src/shared/api/chatbots.ts (Chatbot, ChatbotCreate, ChatbotUpdate)
  frontend/src/shared/api/clients.ts (Client, ClientCreate, ClientUpdate)
  frontend/src/shared/api/llmConfigs.ts (LLMConfig, LLMConfigCreate, LLMConfigUpdate)
  frontend/src/shared/api/feedback.ts (Interaction)
  frontend/src/shared/api/ingestion.ts (IngestionJob)

Instrucciones:

1. Ampliar server/tests/test_openapi_export.py con una nueva clase de test
   TestOpenAPISchemaContract que verifique:

   a. Para Chatbot:
      - Existe "ChatbotRead" en components.schemas con propiedades:
        id, name, slug, retrieval_mode, is_active, client_id
      - Existe "ChatbotCreate" con las propiedades requeridas correspondientes.
      - Existe "ChatbotUpdate" (o similar) para edición parcial.

   b. Para Client:
      - Existe "ClientRead" (o "HubClientRead") con: id, name, slug
      - Existe "ClientCreate" con los campos requeridos.

   c. Para LLMConfig:
      - Existe algún schema con: id, provider, model_name, api_key (o similar).

   d. Para los endpoints principales:
      - GET /api/v1/hub/chatbots existe en paths.
      - POST /api/v1/hub/chatbots existe en paths.
      - GET /api/v1/hub/clients existe en paths.

2. Ejecutar el test y capturar todos los fallos: qué schemas faltan o tienen campos
   que no coinciden con los tipos manuales del frontend.

3. Crear un archivo server/tests/contract_gaps.md que liste:
   - Schemas ausentes en OpenAPI.
   - Campos presentes en el frontend manual pero ausentes en OpenAPI.
   - Campos presentes en OpenAPI pero ausentes en el frontend manual.

Criterio de RED correcto:
- El test falla en al menos un assertion (si pasa todo sin tocar nada, el contrato
  ya está completo y se puede saltar a CF.2.1 directamente).
- El archivo contract_gaps.md documenta las diferencias encontradas.
```

---

### Prompt CF.1.4 (GREEN) — Ajustar schemas Pydantic según gaps detectados

```markdown
# PROMPT CF.1.4 (GREEN) — Cerrar gaps de contrato en modelos Pydantic

Objetivo: hacer que el test CF.1.3 pase ajustando los modelos Pydantic de respuesta
de los routers que presenten gaps documentados en contract_gaps.md.

Contexto:
- Los gaps están documentados en server/tests/contract_gaps.md (CF.1.3).
- La regla de arquitectura es: los routers deben devolver modelos Pydantic específicos
  para la API pública (ChatbotRead, ChatbotCreate, ClientRead, etc.), no modelos ORM.
- Los modelos de respuesta pública deben estar en server/app/schemas/ o en el módulo
  correspondiente de server/app/modules/.

Instrucciones:

1. Para cada gap en contract_gaps.md:
   a. Localizar el router y el modelo de respuesta actual.
   b. Crear o ajustar el modelo Pydantic response_model del endpoint para que incluya
      los campos esperados.
   c. Nunca devolver el modelo ORM directamente (SQLAlchemy model) — usar
      model_validate() o from_orm() sobre un schema Pydantic.

2. Regenerar el contrato:
   cd server && python export_openapi.py
   copy server\openapi.json frontend\openapi.json   (Windows)

3. Ejecutar el test CF.1.3:
   cd server && uv run pytest tests/test_openapi_export.py::TestOpenAPISchemaContract -v
   → Debe pasar.

4. Ejecutar la suite completa para confirmar que no hay regresiones:
   cd server && uv run pytest -x -q

Criterio de done:
- El test CF.1.3 pasa.
- openapi.json refleja los schemas ChatbotRead, ChatbotCreate, ClientRead,
  ClientCreate, LLMConfigRead y equivalentes.
- No hay regresiones en la suite de tests.
- openapi.json regenerado en server/ y copiado a frontend/.
```

---

## BLOQUE CF.2 — Generación de cliente frontend con Orval

### Prompt CF.2.1 (RED) — Verificar que generate:api falla antes de configurar Orval

```markdown
# PROMPT CF.2.1 (RED) — Verificar estado inicial: npm run generate:api no existe

Objetivo: documentar el estado inicial de generación y confirmar que el script
npm run generate:api aún no existe o falla por falta de Orval.

Instrucciones:

1. Desde frontend/, ejecutar:
   npm run generate:api
   → Debe fallar con "Missing script: generate:api" o similar.

2. Verificar que no existe frontend/orval.config.ts ni frontend/orval.config.js.

3. Verificar que `orval` no está en frontend/package.json (devDependencies).

4. Documentar el output del fallo como baseline para CF.2.2.

Criterio de RED correcto:
- El comando falla como se esperaba.
- Confirmado que Orval no está instalado ni configurado.
```

---

### Prompt CF.2.2 (GREEN) — Instalar Orval y configurar generación

```markdown
# PROMPT CF.2.2 (GREEN) — Instalar Orval, crear orval.config.ts, ejecutar generación

Objetivo: configurar Orval para que genere tipos TypeScript, cliente API y hooks
de React Query a partir de frontend/openapi.json.

Prerrequisito: frontend/openapi.json existe y es válido (CF.1.2 completado).

Instrucciones:

1. Instalar Orval como devDependency:
   cd frontend && npm install -D orval

2. Crear frontend/orval.config.ts con esta configuración:

   import { defineConfig } from 'orval';

   export default defineConfig({
     govgenai: {
       input: {
         target: './openapi.json',
       },
       output: {
         mode: 'tags-split',
         target: './src/shared/api/generated',
         schemas: './src/shared/api/generated/model',
         client: 'react-query',
         override: {
           mutator: {
             path: './src/shared/api/client.ts',
             name: 'customInstance',
           },
           header: (info) =>
             `// ARCHIVO AUTOGENERADO — NO EDITAR MANUALMENTE\n// Fuente: openapi.json\n// Regenerar: npm run generate:api\n`,
         },
       },
     },
   });

3. Crear frontend/src/shared/api/client.ts si no existe, con un axios/fetch customInstance
   que lea la baseURL desde la variable de entorno VITE_API_URL. Ejemplo mínimo:

   import axios from 'axios';

   export const customInstance = <T>(config: any): Promise<T> => {
     const instance = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '/api' });
     return instance(config).then((r) => r.data);
   };

   Si axios no está instalado, añadirlo: npm install axios

4. Añadir el script a frontend/package.json:
   "generate:api": "orval --config orval.config.ts"

5. Ejecutar la generación:
   cd frontend && npm run generate:api

6. Verificar que se ha creado frontend/src/shared/api/generated/ con archivos .ts.

7. Añadir src/shared/api/generated/ al .gitignore del frontend con comentario
   "# Generado por Orval — no editar manualmente. Regenerar: npm run generate:api".

Criterio de done:
- frontend/orval.config.ts existe.
- npm run generate:api ejecuta sin errores.
- frontend/src/shared/api/generated/ contiene archivos TypeScript generados.
- Los archivos generados tienen la cabecera "ARCHIVO AUTOGENERADO".
- src/shared/api/generated/ está en .gitignore.
```

---

### Prompt CF.2.3 (REFACTOR) — Verificar y ordenar la carpeta generated

```markdown
# PROMPT CF.2.3 (REFACTOR) — Verificar la calidad del código generado

Objetivo: comprobar que los archivos generados son correctos y útiles antes
de usarlos en formularios.

Instrucciones:

1. Listar los archivos generados en src/shared/api/generated/ y sus exports principales.

2. Verificar que existen hooks de React Query para los endpoints principales:
   - useGetHubChatbots (o nombre equivalente generado por Orval)
   - useCreateHubChatbot / usePostHubChatbots
   - useGetHubClients
   - useCreateHubClient

3. Verificar que existen tipos TypeScript para los schemas principales:
   - ChatbotRead (o nombre generado equivalente)
   - ChatbotCreate
   - ClientRead
   - ClientCreate

4. Ejecutar tsc --noEmit sobre el frontend para detectar errores en el código generado:
   cd frontend && npx tsc --noEmit
   Documentar los errores (si los hay) como lista en un comentario de respuesta
   — no corregir todavía (eso es CF.3).

5. Si hay problemas en la generación (tipos any excesivos, nombres inconsistentes),
   ajustar orval.config.ts — por ejemplo activar zod validation o cambiar el modo
   de naming — y regenerar.

Criterio de done:
- Los hooks y tipos críticos existen en generated/.
- Documentados los errores actuales de tsc --noEmit.
- La generación es reproducible ejecutando npm run generate:api.
```

---

## BLOQUE CF.3 — TypeScript como test de contrato

### Prompt CF.3.1 (RED) — Baseline de errores TypeScript actuales

```markdown
# PROMPT CF.3.1 (RED) — Ejecutar tsc --noEmit y documentar errores como baseline

Objetivo: establecer un baseline de los errores de compilación TypeScript actuales
para poder medir el progreso de la migración.

Instrucciones:

1. Ejecutar en el frontend:
   cd frontend && npx tsc --noEmit 2>&1

2. Guardar el output completo en frontend/tsc_baseline.txt.

3. Analizar y agrupar los errores por categoría:
   a. Errores en src/shared/api/*.ts (DTOs manuales).
   b. Errores en componentes que usan tipos manuales.
   c. Errores en el código generado por Orval.
   d. Otros errores no relacionados con el contrato.

4. Crear frontend/migration_status.md con:
   - Número total de errores TypeScript.
   - Lista de archivos con errores en la categoría (a) y (b).
   - Lista de archivos con errores en la categoría (c) — a corregir en Orval config.
   - Archivos en src/shared/api/*.ts que pueden eliminarse una vez migrados
     (los que solo contienen tipos e interfaces que ya están en generated/).

Criterio de RED correcto:
- El output de tsc está documentado en tsc_baseline.txt.
- migration_status.md identifica los archivos a migrar prioritariamente.
```

---

### Prompt CF.3.2 (GREEN) — Migrar imports de tipos manuales a tipos generados

```markdown
# PROMPT CF.3.2 (GREEN) — Sustituir tipos manuales por tipos generados (sin romper nada)

Objetivo: hacer que los componentes y hooks del frontend usen los tipos generados
por Orval en lugar de las interfaces manuales, empezando por los archivos
identificados en CF.3.1 como prioritarios.

Contexto:
- Los tipos generados están en src/shared/api/generated/.
- Los tipos manuales están en src/shared/api/chatbots.ts, clients.ts, llmConfigs.ts, etc.
- Se migra archivo por archivo para no romper todo a la vez.

Instrucciones:

1. Para cada archivo identificado en migration_status.md categoría (a) y (b),
   en orden de menor a mayor número de errores:

   a. Localizar los componentes que importan ese archivo manual.
   b. Cambiar los imports para apuntar a src/shared/api/generated/.
   c. Ajustar nombres si el schema generado tiene naming diferente
      (ej. "HubChatbot" en vez de "Chatbot" — dependerá del openapi.json).
   d. Ejecutar tsc --noEmit tras cada archivo migrado para confirmar progreso.

2. NO eliminar todavía los archivos manuales de src/shared/api/ — eso va en CF.3.3.
   En este prompt solo se cambian los imports.

3. Si un componente mezcla tipo manual y llamada fetch manual, solo cambiar el tipo.
   Las llamadas fetch se migran en CF.4 (formulario piloto).

4. Al terminar, ejecutar:
   cd frontend && npx tsc --noEmit
   El número de errores debe ser menor que el baseline de CF.3.1.

Criterio de done:
- Al menos los componentes principales de chatbots y clients usan tipos generados.
- tsc --noEmit tiene menos errores que el baseline.
- Los archivos manuales siguen existiendo (aún no se eliminan).
```

---

### Prompt CF.3.3 (REFACTOR) — Eliminar interfaces manuales redundantes

```markdown
# PROMPT CF.3.3 (REFACTOR) — Eliminar DTOs manuales ya cubiertos por generated/

Objetivo: eliminar las interfaces TypeScript manuales que duplican tipos ya presentes
en el código generado por Orval, dejando solo las llamadas fetch manuales
(que se migrarán en CF.4).

Prerrequisito: CF.3.2 completado, tsc --noEmit pasa o tiene solo errores residuales.

Instrucciones:

1. Para cada archivo en src/shared/api/ (chatbots.ts, clients.ts, etc.):
   a. Identificar qué exporta: interfaces/types vs. funciones fetch.
   b. Si el archivo solo tiene interfaces/types ya cubiertos por generated/:
      → Eliminar el archivo completo.
      → Eliminar todos los imports que apuntaban a él (ya migrados en CF.3.2).
   c. Si el archivo tiene mezcla de interfaces y funciones fetch:
      → Eliminar solo las interfaces (dejando las funciones fetch para CF.4).
      → Añadir un comentario al inicio del archivo:
        "// TODO CF.4: migrar funciones fetch a hooks de Orval"

2. Ejecutar tsc --noEmit y confirmar que compila limpio (0 errores de tipo).

3. Ejecutar los tests del frontend:
   cd frontend && npm test -- --watchAll=false
   → No deben haber regresiones.

4. Actualizar frontend/migration_status.md con el estado actual.

Criterio de done:
- No existen interfaces TypeScript manuales que dupliquen tipos en generated/.
- tsc --noEmit: 0 errores de tipo.
- Tests del frontend pasan.
- Los archivos src/shared/api/*.ts que quedan solo contienen funciones fetch
  (pendientes de CF.4).
```

---

## BLOQUE CF.4 — Primer formulario crítico como vertical slice

> **Formulario piloto elegido**: Chatbot Create/Edit — es el formulario más usado,
> tiene el mayor número de campos y representa el patrón a replicar.

### Prompt CF.4.1 (RED) — Tests del formulario Chatbot Create/Edit

```markdown
# PROMPT CF.4.1 (RED) — Tests: formulario de creación/edición de Chatbot

Objetivo: escribir tests que describan el comportamiento esperado del formulario
ANTES de refactorizarlo. Los tests deben fallar inicialmente porque el formulario
aún usa fetch manual y tipos manuales.

Instrucciones:

1. Crear frontend/src/admin/chatbots/__tests__/ChatbotForm.test.tsx
   (o la ruta equivalente donde esté el componente del formulario de chatbot).

2. Los tests deben verificar:

   a. El formulario carga datos iniciales desde el hook generado useGetHubChatbotsId
      (o equivalente) en modo edición.
   b. El submit en modo creación llama a la mutation generada usePostHubChatbots
      (o equivalente), NO a fetch('/api/...').
   c. El submit en modo edición llama a la mutation generada usePatchHubChatbotsId
      o usePutHubChatbotsId.
   d. Un campo required (ej. "name") muestra mensaje de error si se envía vacío.
   e. Si el backend devuelve un error 422 con detail[].loc["body","name"],
      el campo "name" del formulario muestra el mensaje de error.
   f. TypeScript falla si el DTO cambia: el test importa el tipo generado
      ChatbotCreate y lo usa para tipar el payload del submit.

3. Usar @testing-library/react y vitest (o jest, el que use el proyecto).
   Mockear los hooks de Orval con vi.mock() o jest.mock().

4. Ejecutar los tests:
   cd frontend && npm test -- ChatbotForm
   → Deben FALLAR porque el formulario actual no usa los hooks generados.

Criterio de RED correcto:
- Los tests existen y describen el comportamiento esperado.
- Fallan porque el formulario actual usa fetch manual, no hooks de Orval.
- El tipo ChatbotCreate importado del código generado compila correctamente.
```

---

### Prompt CF.4.2 (GREEN) — Refactorizar formulario Chatbot con hooks generados

```markdown
# PROMPT CF.4.2 (GREEN) — Refactorizar ChatbotForm con Orval + react-hook-form + zodResolver

Objetivo: hacer pasar los tests CF.4.1 refactorizando el formulario de Chatbot
para que use hooks generados por Orval, react-hook-form y zodResolver.

Contexto:
- El formulario actual usa fetch manual y tipos manuales.
- Los hooks generados están en src/shared/api/generated/.
- react-hook-form y zod ya están instalados.

Instrucciones:

1. Localizar el componente del formulario de Chatbot (ChatbotForm o equivalente).

2. Sustituir:
   - import { Chatbot, ChatbotCreate } from '../api/chatbots'
     → import { ChatbotRead, ChatbotCreate } from '../api/generated/model'
   - const response = await fetch('/api/v1/hub/chatbots', { method: 'POST', ... })
     → const mutation = usePostHubChatbots()  (o el nombre generado por Orval)
       mutation.mutate(data)

3. Integrar react-hook-form:
   const { register, handleSubmit, formState: { errors }, setError } =
     useForm<ChatbotCreate>({ resolver: zodResolver(chatbotCreateSchema) })

4. Crear frontend/src/admin/chatbots/schemas/chatbotSchemas.ts con el schema Zod
   estrictamente tipado contra el tipo generado ChatbotCreate:
   - Debe derivarse del openapi.json cuando sea posible.
   - Los campos required, minLength, maxLength deben coincidir con el backend.
   - Usar z.infer<typeof chatbotCreateSchema> para asegurar compatibilidad con ChatbotCreate.

5. En el submit handler:
   a. Llamar a mutation.mutate(data).
   b. En onError: si el error es un ValidationError (422) del backend, extraer
      detail[].loc y detail[].msg y llamar a setError() por cada campo afectado.
      (Implementar la función mapApiErrorsToFormErrors — se extraerá en CF.4.4.)

6. Ejecutar los tests:
   cd frontend && npm test -- ChatbotForm
   → Deben PASAR.

7. Ejecutar tsc --noEmit para confirmar que no hay errores de tipo.

Criterio de done:
- Los tests CF.4.1 pasan.
- El formulario usa hooks generados por Orval.
- El formulario usa react-hook-form + zodResolver.
- Los errores por campo del backend se mapean al formulario.
- tsc --noEmit: sin errores nuevos.
```

---

### Prompt CF.4.3 (GREEN) — Implementar mapper de errores API → formulario

```markdown
# PROMPT CF.4.3 (GREEN) — Utility: mapApiErrorsToFormErrors

Objetivo: extraer el mapper de errores de validación FastAPI (422) a errores de
formulario react-hook-form como utilidad reutilizable.

Contexto:
- FastAPI devuelve errores de validación con este formato:
  { "detail": [{ "loc": ["body", "name"], "msg": "Field required", "type": "missing" }] }
- Necesitamos una función que transforme ese formato en llamadas setError() de react-hook-form.

Instrucciones:

1. Crear frontend/src/shared/utils/formErrors.ts con:

   import type { FieldValues, UseFormSetError, FieldPath } from 'react-hook-form';

   interface FastAPIValidationError {
     detail: Array<{
       loc: (string | number)[];
       msg: string;
       type: string;
     }>;
   }

   export function mapApiErrorsToFormErrors<T extends FieldValues>(
     error: unknown,
     setError: UseFormSetError<T>
   ): void {
     if (!isFastAPIValidationError(error)) return;
     for (const item of error.detail) {
       const field = item.loc.slice(1).join('.') as FieldPath<T>;
       setError(field, { type: 'server', message: item.msg });
     }
   }

   function isFastAPIValidationError(e: unknown): e is FastAPIValidationError {
     return (
       typeof e === 'object' && e !== null &&
       'detail' in e && Array.isArray((e as any).detail)
     );
   }

2. Crear frontend/src/shared/utils/__tests__/formErrors.test.ts con:
   - Test: un error 422 con loc ["body", "name"] llama setError("name", ...).
   - Test: un error no 422 no llama setError.
   - Test: un error con loc ["body", "config", "model"] llama setError("config.model", ...).

3. Actualizar ChatbotForm para importar y usar mapApiErrorsToFormErrors.

4. Ejecutar todos los tests del frontend:
   cd frontend && npm test -- --watchAll=false
   → Deben pasar.

Criterio de done:
- frontend/src/shared/utils/formErrors.ts existe y está tipado correctamente.
- Tests de la utilidad pasan.
- ChatbotForm usa la utilidad en lugar de lógica inline.
```

---

### Prompt CF.4.4 (REFACTOR) — Extraer utilidades y documentar el patrón

```markdown
# PROMPT CF.4.4 (REFACTOR) — Extraer utilidades comunes y documentar el patrón Contract-First

Objetivo: consolidar las utilidades creadas en CF.4 y dejar un patrón documentado
para replicar en los siguientes formularios.

Instrucciones:

1. Verificar que existen y funcionan estas utilidades en src/shared/utils/:
   - formErrors.ts (mapApiErrorsToFormErrors)
   - Cualquier helper de createDefaultValues que se haya creado.

2. Eliminar las llamadas fetch manuales de src/shared/api/chatbots.ts
   (las que están marcadas con "TODO CF.4" desde CF.3.3).
   Si el archivo queda vacío tras eliminar las llamadas fetch, eliminarlo.

3. Eliminar las llamadas fetch manuales del componente ChatbotForm si aún quedan.

4. Ejecutar la suite completa:
   cd frontend && npm test -- --watchAll=false
   cd frontend && npx tsc --noEmit
   → Sin errores ni regresiones.

5. Crear frontend/src/shared/api/PATTERN.md (solo si el usuario lo pide — no
   crear documentación si no se solicita explícitamente).

Criterio de done:
- No quedan llamadas fetch manuales en el formulario de Chatbot ni en chatbots.ts.
- Si chatbots.ts quedó vacío, está eliminado.
- Suite de tests pasa limpia.
- tsc --noEmit: 0 errores.
```

---

## BLOQUE CF.5 — Blindaje del contrato en CI/CD

### Prompt CF.5.1 (GREEN) — Añadir pipeline de contrato al CI existente

```markdown
# PROMPT CF.5.1 (GREEN) — Añadir pasos de contrato a .github/workflows/ci.yml

Objetivo: extender el pipeline CI existente para que exporte openapi.json,
regenere el cliente frontend y compile TypeScript, fallando si hay desalineación.

Contexto:
- El CI existente está en .github/workflows/ci.yml.
- Actualmente ejecuta: ruff, tests pytest. No tiene pasos frontend.
- El objetivo es que si alguien cambia un DTO en backend sin actualizar el frontend,
  el CI falle antes del merge.

Instrucciones:

1. Leer el .github/workflows/ci.yml existente para entender su estructura.

2. Añadir un nuevo job llamado "contract" (o "api-contract") con estos pasos:

   contract:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4

       - name: Set up Python
         uses: actions/setup-python@v5
         with:
           python-version: '3.11'

       - name: Install uv
         run: pip install uv

       - name: Install backend dependencies
         run: cd server && uv sync --frozen

       - name: Export OpenAPI schema
         run: cd server && uv run python export_openapi.py
         env:
           DATABASE_URL: "postgresql+asyncpg://x:x@localhost/x"
           DATABASE_URL_SYNC: "postgresql+psycopg2://x:x@localhost/x"
           SECRET_KEY: "ci-dummy-secret"
           # Añadir cualquier otra variable de entorno requerida por la app

       - name: Copy schema to frontend
         run: cp server/openapi.json frontend/openapi.json

       - name: Set up Node.js
         uses: actions/setup-node@v4
         with:
           node-version: '20'
           cache: 'npm'
           cache-dependency-path: frontend/package-lock.json

       - name: Install frontend dependencies
         run: cd frontend && npm ci

       - name: Generate API client
         run: cd frontend && npm run generate:api

       - name: TypeScript contract check
         run: cd frontend && npx tsc --noEmit

       - name: Frontend tests
         run: cd frontend && npm test -- --watchAll=false --passWithNoTests

3. Verificar que el job no interfiere con los jobs existentes (puede ejecutarse
   en paralelo con los tests de backend si no hay dependencias entre ellos).

4. Hacer commit y push del workflow modificado para verificar que pasa en CI.

Criterio de done:
- El job "contract" aparece en el CI y pasa.
- El pipeline falla si openapi.json no es coherente con el frontend.
- El job existente de tests backend no se ve afectado.
```

---

### Prompt CF.5.2 (RED/GREEN) — Verificar que el CI detecta desalineaciones

```markdown
# PROMPT CF.5.2 (RED/GREEN) — Prueba de fuego: el CI detecta un cambio incompatible

Objetivo: demostrar que la infraestructura contractual funciona introduciendo
un cambio incompatible controlado y verificando que el CI falla.

Instrucciones (ejecutar localmente, NO mergear el cambio):

1. Introducir un cambio incompatible controlado en un schema Pydantic del backend:
   - Renombrar un campo en ChatbotRead (ej: "name" → "display_name").
   - O añadir un campo required en ChatbotCreate que no tenga default.

2. Regenerar openapi.json:
   cd server && python export_openapi.py
   cp server/openapi.json frontend/openapi.json

3. Regenerar el cliente frontend:
   cd frontend && npm run generate:api

4. Ejecutar tsc --noEmit:
   cd frontend && npx tsc --noEmit
   → Debe fallar con error de tipo en los componentes que usan el campo renombrado.

5. Verificar que el formulario de Chatbot da error de compilación específicamente
   en el campo afectado.

6. Revertir el cambio (git checkout -- server/... frontend/...).

7. Confirmar que tras revertir, tsc --noEmit pasa de nuevo.

Criterio de done:
- El cambio incompatible provocó un error de compilación TypeScript específico.
- El error apunta al componente y campo concreto que falló.
- Tras revertir, el pipeline vuelve a pasar.
- Documentar en un comentario de respuesta el error exacto que TypeScript dio.

Este prompt valida que la infraestructura contractual cumple su objetivo:
convertir la desalineación backend/frontend en algo imposible de ignorar.
```

---

## Criterio de done del bloque CF completo

El bloque se considera completado cuando:

- [ ] `server/export_openapi.py` existe y genera `openapi.json` offline.
- [ ] `frontend/openapi.json` se genera copiando desde `server/openapi.json`.
- [ ] Orval está configurado y `npm run generate:api` genera tipos y hooks en `src/shared/api/generated/`.
- [ ] `npx tsc --noEmit` pasa sin errores de tipo.
- [ ] No existen interfaces TypeScript manuales que dupliquen tipos del contrato.
- [ ] El formulario de Chatbot usa hooks generados, react-hook-form y zodResolver.
- [ ] Los errores 422 del backend se mapean a errores de campo en el formulario.
- [ ] El CI incluye el job "contract" que exporta OpenAPI, regenera cliente y compila TS.
- [ ] Un cambio incompatible en el backend provoca fallo en tsc o en CI antes de producción.

---

## Continuación tras este bloque

Una vez completado CF.5.2, reanudar la Fase 1 a partir del **Prompt 9B.4** de `Plan_TDD_Fase1.md`,
pero con la regla activa:

> **Todo nuevo endpoint o formulario debe seguir el patrón CF:**
> DTO Pydantic → openapi.json → Orval generate → tipo generado → react-hook-form + zodResolver.

La migración del resto de formularios (clients, llmConfigs, promptTemplates, ingestion)
puede hacerse como vertical slices dentro de los prompts de funcionalidad correspondientes,
no como un bloque de migración masivo previo.
