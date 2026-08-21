# Gov Gen AI Platform

Plataforma de IA generativa para administración pública. Nace de la actividad investigadora del
grupo **INNOVAP** (Derecho Público e Innovación) de la Universitat Jaume I, y su finalidad no es
cubrir las necesidades de una universidad concreta: es ofrecer una solución de **software libre
multiorganización**, utilizable por otras administraciones públicas y en particular por **entidades
locales**, que rara vez tienen capacidad para construir algo así por su cuenta.

Ese propósito no es una declaración de intenciones del README: es lo que explica media
arquitectura. La jerarquía Plataforma → Organización → Chatbot, la separación entre configuración y
dato operacional, y la frontera edge/cloud existen porque el sistema tiene que servir a
instituciones distintas sin que ninguna vea los datos de otra. Un sistema hecho para una sola
institución no necesitaría nada de eso.

Cuatro módulos sobre una misma base:

| Módulo | Qué hace |
|---|---|
| **Chatbots** | Asistentes con recuperación sobre corpus normativo propio (RAG en tres niveles), publicables como widget embebible o como agente identificado. |
| **Informes** | Redacción asistida de informes: tablas deterministas calculadas desde los datos, valoración escrita por el modelo y **aprobada o editada por una persona** antes de exportar. |
| **Automatización** | Flujos, ETL, extracción de PDF y scripts generados a medida, ejecutados en un sandbox aislado. |
| **Curación** | Rastreo del portal institucional, detección de contenido caducado o contradictorio, y selección de lo que entra al corpus. |

El principio que ordena el diseño: **el servidor decide, el cliente pinta**. El frontend no
calcula qué acciones están permitidas, ni conoce a priori los campos de un formulario; los recibe.
Ver `docs/Arquitectura.md`.

## Dos modos de despliegue

El mismo código sirve a los dos, y esa es una restricción de arquitectura, no una opción:

- **Cloud-only** — todo corre en el servidor del proveedor; los datos se anonimizan antes de
  llegar al modelo.
- **Edge + Cloud** — la lógica que toca datos del cliente (RAG, grafos, ingesta, expedientes)
  corre **dentro de la nube de la institución**; el cloud sólo guarda configuración y métricas
  anonimizadas.

La frontera se sostiene con dos bases ORM separadas y una clasificación explícita de routers y
módulos, con tests que fallan si se cruza. Detalle en `CLAUDE.md` §Frontera Edge-Cloud.

## Stack

Python 3.13 con **uv** · FastAPI · LangGraph · PostgreSQL 16 + pgvector · React + TypeScript +
Vite · i18next (`ca` / `es` / `en`) · Alembic · pytest + vitest.

## Arrancar en local

Requisitos: Docker Desktop, [uv](https://docs.astral.sh/uv/), Node 20+. `.env.example` documenta
cada variable para quien prefiera rellenarlas a mano.

```bash
scripts/generate_env.sh              # genera .env, server/.env y frontend/.env con secretos
docker compose up -d postgres        # el servicio se llama postgres, no db
cd server; uv sync --extra local-models --extra shared
uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000
```

Y el frontend, en otra terminal:

```bash
cd frontend; npm install; npm run dev     # http://localhost:5173
```

En Windows, `arranque.bat` hace las dos cosas.

El primer arranque del backend tarda varios minutos: carga los modelos locales de embedding y
reranking. Hasta que no escriba `Application startup complete` no responde.

## Tests

```bash
cd server;   uv run pytest tests          # desde Git Bash, no PowerShell
cd frontend; npm test
```

El detalle de por qué Git Bash, y qué subconjunto corresponde a cada momento, está en
`CLAUDE.md`. **TDD es obligatorio**: el test va antes del código.

## El contrato es la fuente de verdad

`openapi.json` lo genera el servidor y el cliente TypeScript se deriva de él con Orval. No se
escribe a mano:

```bash
cd server;   uv run python export_openapi.py
cd frontend; npm run generate:api
```

## Dónde está cada cosa

```
server/app/modules/     agents_hub · automation · curation · redaccion
server/app/core/        servicios compartidos: LLM gateway, auth, tenancy, storage
frontend/src/           admin · curation · redaccion · widget
client_app/             agente de ejecución local (RPA); el resto es legacy
docs/                   arquitectura, decisiones, manuales, casos guía
planificacion/          plan de desarrollo, cursor del trabajo e historial
pruebas_manuales/       guiones .bat de lo que sólo puede juzgar una persona
_legacy_nicegui/        cuarentena de la migración; sólo lectura
```

## Documentación

- `docs/Arquitectura.md` — qué es la plataforma y qué principios la rigen.
- `docs/MARCO_GOBERNANZA_IA.md` — gobernanza, trazabilidad y protección de datos.
- `CONTRIBUTING.md` — cómo se trabaja aquí.
- `CLAUDE.md` — reglas duras para agentes de programación, y de paso el contrato de estilo
  del proyecto.
- `planificacion/PROJECT_STATE.md` — dónde está el desarrollo ahora mismo.

## Estado

En desarrollo activo. La migración desde la aplicación NiceGUI original sigue en curso: lo que
vive en `_legacy_nicegui/` es referencia en cuarentena, no código en uso.

## Gobernanza: un principal y tantos forks como organizaciones

Este repositorio es el **principal** (*upstream*): aquí se decide la dirección del proyecto y aquí
se mantiene su carácter multiorganización.

Cada organización que despliegue la plataforma —una universidad, una diputación, un ayuntamiento—
trabaja sobre **su propio fork**: ahí van su despliegue, su configuración y los desarrollos que
responden a necesidades suyas. Lo que se pueda generalizar **se pide** que suba al principal por
*pull request*.

La regla vale igual para todas, **incluida la Universitat Jaume I**, donde nació el proyecto: su
desarrollo institucional entra como aportación, no como dirección. Por eso este documento no nombra
ningún fork en particular; no hay uno privilegiado.

La razón es la que da sentido al proyecto: está destinado a varias administraciones, no a una. Si
las necesidades de una institución entraran directamente en el principal, en poco tiempo el
principal *sería* el sistema de esa institución, y el resto heredaría decisiones tomadas para un
contexto que no es el suyo. Con fork y *pull request*, lo específico se queda donde es específico y
sólo sube al principal lo que sirve a todos.

### Lo que obliga la licencia y lo que pide el proyecto

Conviene no confundirlos, porque son cosas de naturaleza distinta y sólo una es exigible.

| | |
|---|---|
| **La licencia obliga a** | Dar el código fuente de **tu versión** a **los usuarios de tu despliegue**, si la has modificado y la ofreces por red (§13). Y a distribuirla bajo AGPL, con su fuente, si la distribuyes (§5 y §6). |
| **La licencia NO obliga a** | Enviar nada al principal. **Ningún copyleft obliga a contribuir aguas arriba**, ni la AGPL ni la GPL. Tampoco a publicar al mundo: la obligación es frente a los usuarios de esa instancia. |
| **El proyecto pide** | Que lo generalizable llegue por *pull request*. Es una **convención de gobernanza**, no una cláusula. |

El modelo funciona igual, pero por otra vía: la licencia garantiza que ninguna mejora quede cerrada
y que el principal **pueda** incorporarla legalmente; el *pull request* es lo que evita tener que ir
a buscarla. La licencia asegura la posibilidad, la convención asegura la comodidad — y conviene no
confiar en la segunda como si fuera la primera.

Las contribuciones al principal exigen **DCO** (*Developer Certificate of Origin* 1.1): una línea
`Signed-off-by` en cada commit, que `git commit -s` añade sola. Certifica que tienes derecho a
aportar el código; **no cede derechos**, conservas tu copyright. Texto íntegro en `DCO`.

El detalle operativo —qué se acepta como contribución y qué no, cómo se prepara— está en
`CONTRIBUTING.md`.

## Licencia, titularidad y procedencia

Copyright © 2026 **Universitat Jaume I de Castelló**  
Desarrollado en el grupo de investigación **INNOVAP** — Derecho Público e Innovación (Universitat Jaume I)  
Autor: **Modesto Fabra** — `fabra@uji.es`

La titularidad corresponde a la UJI, que es la persona jurídica. **INNOVAP** consta como
procedencia porque no es un dato accesorio: la aplicación nace de actividad investigadora, y de ahí
viene su vocación multiorganización. El desarrollo que la universidad realice sobre ella no cambia
ese origen; entra como aportación al proyecto de software libre.

Este programa se distribuye bajo la **GNU Affero General Public License v3.0 o posterior**
(`AGPL-3.0-or-later`). El texto completo está en `LICENSE`, íntegro y sin modificar: la propia
licencia permite copiarla literalmente pero no alterarla, así que la procedencia y el propósito se
declaran aquí y no dentro de ella.

> This program is free software: you can redistribute it and/or modify it under the terms of the
> GNU Affero General Public License as published by the Free Software Foundation, either version 3
> of the License, or (at your option) any later version.
>
> This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
> without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
> GNU Affero General Public License for more details.
>
> You should have received a copy of the GNU Affero General Public License along with this program.
> If not, see <https://www.gnu.org/licenses/>.

### Por qué AGPL y no GPL

Por el §13. Quien despliegue una versión modificada de esta plataforma **como servicio en red**
tiene que ofrecer el código fuente de esa versión a quien la use. Para software de administración
pública servido por web, esa es la diferencia que importa: sin ella, una modificación puede
servirse a la ciudadanía sin devolver nada. Y siendo el destinatario otras administraciones, es
también lo que impide que una mejora pagada con fondos públicos quede cerrada.

### La obligación del §13 sobre cada despliegue

Pendiente de implementar, y con tres condiciones que no son opcionales:

- **Va en la interfaz del despliegue**, no en este README. La obligación es de quien ejecuta la
  versión modificada, frente a los usuarios de **esa instancia**.
- **Apunta al fuente de esa versión** —el fork, en el commit desplegado—, no al principal. El §13
  pide el *Corresponding Source*, no «el proyecto». Por eso tiene que ser **configuración**
  (`SOURCE_URL` o equivalente) y no una URL fija en el código: fijarla al principal haría que
  cualquier despliegue modificado incumpliera.
- **Tiene que verse donde están los usuarios**, y eso incluye el **widget público embebido**: la
  ciudadanía que usa el chatbot también son usuarios interactuando remotamente. Es el caso que se
  olvida.

El §13 se activa **si se modifica** el programa: quien despliegue el código tal cual no queda
sujeto a esta obligación concreta, aunque enlazar el fuente sigue siendo lo razonable.
