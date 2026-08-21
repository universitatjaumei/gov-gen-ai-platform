# Gov Gen AI Platform

Plataforma de IA generativa para administración pública. Nace de la actividad investigadora del
grupo **INNOVAP** de la Universitat Jaume I, y su finalidad no es cubrir las necesidades de una
universidad concreta: es ofrecer una solución de **software libre multiorganización**, utilizable
por otras administraciones públicas y en particular por **entidades locales**, que rara vez tienen
capacidad para construir algo así por su cuenta.

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

## Gobernanza: proyecto de investigación con contribuciones institucionales

Este repositorio es el **principal** (*upstream*): aquí se decide la dirección del proyecto y aquí
se mantiene su carácter multiorganización.

| Repositorio | Papel |
|---|---|
| GitHub — `ModestoFabra/gov-gen-ai-platform` | **Principal.** Referencia del proyecto de software libre. |
| Bitbucket de la UJI *(pendiente de crear)* | **Fork institucional.** Despliegue en la universidad y desarrollos para necesidades propias de la UJI. |

El desarrollo institucional —el que se aborde desde el **Teclab**, el laboratorio de tecnología de
la Delegación del rector para la estrategia digital y la inteligencia artificial— se hace en el
fork y llega al principal **como contribución, por *pull request***. No en sentido contrario.

La razón es la que da sentido al proyecto: está destinado a varias administraciones, no a una. Si
las necesidades de una institución entraran directamente en el principal, en poco tiempo el
principal *sería* el sistema de esa institución, y el resto heredaría decisiones tomadas para un
contexto que no es el suyo. Con fork y *pull request*, lo específico se queda donde es específico y
sólo sube al principal lo que sirve a todos.

El detalle operativo —qué se acepta como contribución, cómo se prepara— está en `CONTRIBUTING.md`.

## Licencia, titularidad y procedencia

Copyright © 2026 **Universitat Jaume I de Castelló**  
Desarrollado en el grupo de investigación **INNOVAP** (Universitat Jaume I)  
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

Ese mismo §13 impone una obligación **a este despliegue también**: una aplicación web bajo AGPL
debe dar a sus usuarios una vía para obtener el fuente — en la práctica, un enlace visible al
repositorio desde la propia interfaz. Está pendiente de añadir.
