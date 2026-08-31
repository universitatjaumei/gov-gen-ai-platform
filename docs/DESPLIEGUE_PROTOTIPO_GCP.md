# Despliegue del prototipo en GCP — sitio de normativa + asistente público

> **Escrito el 2026-08-16.** Alcance: un **prototipo** para que un grupo de personas lo
> pruebe, **sin dominio propio**. No sustituye al bloque Deploy de `planificacion/Plan_TDD_Fase1.md`
> (D.0–D.6), que es el despliegue en condiciones; esto es lo mínimo para que se pueda usar.
>
> **De qué repositorio se despliega (2026-08-21).** De este, el principal. La gobernanza del
> proyecto prevé que cada organización despliegue desde su propio fork (ver `CONTRIBUTING.md`),
> pero el fork de la universidad no existe todavía y crearlo para una demostración sería poner el
> carro delante: primero se valora si la cosa tiene interés institucional, y entonces se hace el
> fork y se planifica el despliegue desde ahí. Esta nota deja de aplicarse en ese momento.

---

## Son dos cosas, y conviene no mezclarlas

| | Qué es | Dónde va | Qué necesita |
|---|---|---|---|
| **El sitio** | 271 páginas de norma + buscador + portada + PDF. Estático puro | Bucket de GCS con acceso público | Nada: ni servidor, ni base de datos |
| **El asistente** | API, grafo, corpus vectorial | VM con `docker-compose.prod.yml` | Cloud SQL, GCS, credenciales de Vertex |

El sitio funciona **sin** el asistente: es la publicación de la normativa y vale por sí sola.
El asistente sin el sitio también funciona, pero cita PDF en vez de artículos. Se despliegan
por separado y se conectan con tres variables.

---

## 1. El sitio

Se genera en el proyecto del corpus, no aquí:

```
cd Descarregar_pdf/normativa_propia/publicacio_transparencia_2026-07
python passa_el_pipeline.py --aplica
```

Antes de generar, las variables del asistente. Sin `ASSISTENT_CHATBOT` el sitio sale **sin
widget**, que es lo correcto si todavía no hay API desplegada:

```
ASSISTENT_API=https://<host-de-la-api>/api/v1
ASSISTENT_CHATBOT=<uuid del chatbot público>
ASSISTENT_CLAU=<credencial de sitio emitida para ESTE sitio>
```

Y hay que copiar el bundle del widget a la raíz del sitio:

```
cd frontend && npm run build:widget
cp dist/widget/widget.iife.js <sitio>/widget.iife.js
```

Lo que se sube al bucket: `index.html`, `cercador.html`, `html/`, `pdf/`, `img/` y
`widget.iife.js`. **No** se sube nada de `generat/`, que es material de ingesta.

⚠️ **Emite una credencial de sitio nueva para el bucket.** La que uses en local acaba dentro
del HTML generado; si subes esas páginas tal cual, subes la credencial de pruebas. Emítela
en el panel del chatbot, genera el sitio con ella, y revoca la de local.

---

## 2. El asistente

Lo que dice el bloque Deploy (D.4-VM), más lo que ha aparecido en el piloto:

| Variable | Valor | Por qué |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | `uji-teclab` | Vertex. Ya verificado |
| `GOOGLE_CLOUD_LOCATION` | `europe-southwest1` | Madrid: el texto no sale de España |
| `CORPUS_SITE_BASE_URL` | la URL pública del bucket | Sin esto las citas van al PDF |
| `CORS_ALLOWED_ORIGINS` | el origen del bucket | **Sin esto el widget no puede hablar con la API**: en producción la política es cerrada y un origen que falta se traduce en un preflight rechazado, no en un error visible |
| `ENVIRONMENT` | `production` | Cierra el sembrado de desarrollo (SEC.8.0) y la documentación de la API (SEC.7) |

Credenciales de Vertex en la VM: cuenta de servicio con el rol de usuario de Vertex AI, no
una clave de API. En local se resolvió con ADC; en la VM lo aporta la propia máquina.

**El corpus se carga allí con la misma orden que aquí**, contra la BD de Cloud SQL:

```
uv run python -m server.app.modules.agents_hub.ingestion.corpus.load \
    --dir <corpus>/generat/ingesta/normatiu --chatbot-id <uuid> --dry-run
```

Son ~23.300 fragmentos y ~95 peticiones a Vertex para el asistente público. El vocabulario
va antes, o la carga aborta.

---

## 3. Orden

1. Cloud SQL con pgvector, y `alembic upgrade head`.
2. Vocabulario (ámbitos y después submaterias).
3. Chatbot público creado, con su configuración y **su cuota por IP** —ahora se puede fijar
   desde el panel, ya no hace falta SQL—.
4. Corpus cargado y comprobado con una consulta real.
5. Credencial de sitio emitida.
6. Sitio generado con esa credencial y subido al bucket.
7. `CORPUS_SITE_BASE_URL` y `CORS_ALLOWED_ORIGINS` apuntando al bucket, y reinicio.
8. Comprobación de extremo a extremo: una pregunta cuya respuesta cite un artículo, y que el
   enlace de la cita abra la página en ese artículo.

---

---

## 3.bis Aprovisionado el 2026-08-31 (D.0, D.2 y D.3)

Lo que ya está hecho en `uji-teclab`, para no repetirlo ni adivinarlo:

| Qué | Cómo quedó |
|---|---|
| Servicios de GCP | **14 habilitados y comprobados** con `scripts/gcp_enable_services.sh` (D.0). Idempotente: se relanza sin miedo |
| Cloud SQL | Instancia **`govgenai-prod`**: POSTGRES_16, `db-g1-small`, edición **ENTERPRISE**, `europe-southwest1`, disco con crecimiento automático, copias a las 03:00 y **PITR activado**. Nombre de conexión `uji-teclab:europe-southwest1:govgenai-prod` |
| Base y usuario | BD **`govgenai`** y usuario **`govgenai`**, con la contraseña en Secret Manager (nunca en un fichero) |
| `pgvector` | **No hace falta paso manual**: la primera migración ejecuta `CREATE EXTENSION IF NOT EXISTS vector` (`a1b2c3d4e5f6_hub_schema.py:22`) y el usuario creado por la API de Cloud SQL tiene permiso |
| Secretos | Seis, inventariados en `scripts/lib/secretos.tsv` y creados con `scripts/gcp_create_secrets.sh`. Cinco con valor; **falta `govgenai-google-api-key`**, que lo aporta una persona |

**La edición importa**: el proyecto crea por defecto en `ENTERPRISE_PLUS`, que **rechaza** los
tiers de núcleo compartido (`db-g1-small`). Hay que pasar `--edition=ENTERPRISE` o el comando
falla con «Invalid Tier ... for (ENTERPRISE_PLUS) Edition».

**Cómo llegan los secretos al contenedor.** En el despliegue gestionado los inyectaba la
plataforma; en una VM lo hace `scripts/vm_fetch_secrets.sh`, que escribe
`/opt/govgenai/.env.runtime` con permisos 600 leyendo Secret Manager, y se niega a escribir un
fichero a medias si algún secreto falta. Rotar una credencial es cambiar el secreto y
reiniciar: no se entra en la máquina a editar nada.

> **Cuidado con el retorno de carro, que costó dos diagnósticos.** Ejecutando estos guiones
> **desde Windows**, `openssl` y algunas salidas de `gcloud` terminan en CRLF y `$(...)` sólo se
> come el `\n`: el `\r` se queda dentro del valor. Un `\r` en una contraseña hace que
> `gcloud sql users create` falle con «batch file arguments are invalid», y en un fichero de
> entorno se lleva la línea entera. Los dos guiones lo limpian ahora en un solo sitio. Y para
> comprobar un secreto, **`od -c` sobre un fichero**, no una comparación en el intérprete: la
> propia captura puede añadir el CR que estás buscando.

---

## 3.ter El nombre de la API, que sin dominio sigue haciendo falta

El sitio no necesita dominio —el bucket sirve por HTTPS con el de Google—, pero **la API sí
necesita un nombre**, y esto no es una preferencia:

- Las páginas del bucket se sirven por **HTTPS**, y ahí `ASSISTENT_API` tiene que ser `https://`.
  Una llamada a `http://IP` la bloquea el navegador por contenido mixto, sin error visible.
- Y `https://IP` **no puede tener certificado válido**: Let's Encrypt no emite para direcciones
  IP desnudas.

**Decisión del usuario (2026-08-31): `sslip.io` para el prototipo**, pidiendo en paralelo el
subdominio institucional. `<ip-con-guiones>.sslip.io` resuelve solo a esa IP y Let's Encrypt
emite con normalidad, sin trámite. El nombre sólo aparece en `ASSISTENT_API` y en el
certificado; nadie lo lee.

Cambiar después al subdominio cuesta: registro A, certificado nuevo, y **regenerar y volver a
subir el sitio** con el `ASSISTENT_API` nuevo (una orden, porque la URL se inyecta al generar y
no está escrita a mano en las 313 páginas). Los dos nombres pueden convivir mientras se cambia,
así que no hay ventana de caída. Lo que **no** cambia es la URL de cada norma, que es la que
cita el asistente y la que la gente guarda.

---

## 4. Lo que este prototipo deja fuera a propósito

- **Dominio propio.** Decisión del usuario: es un prototipo. El bucket sirve por HTTPS con el
  dominio de Google, y la API va por `sslip.io` con certificado de Let's Encrypt (ver 3.ter).
- **El asistente de Gerencia.** Es interno (`restricted` + grupo SAML) y no tiene sentido en
  un prototipo público. Se prueba desde el panel.
- **Copias de seguridad y vigilancia**, que son D.6.

## 5. Riesgos que conviene mirar antes de abrirlo a gente

| Riesgo | Estado |
|---|---|
| Chatbot público sin límite por IP | **Resuelto**: las cuotas de SEC.4 ya tienen superficie en el panel. Ponle un valor |
| Presupuesto total de tokens agotable | `total_token_budget` a 0 es «sin techo». Para un prototipo abierto, conviene poner uno |
| Respuestas que citan mal | El aviso de vigencia desplazada ya viaja (PIL.3), pero **219 defectos del corpus siguen pendientes de Secretaría General** y 43 documentos no tienen la vigencia validada |
| La página de documentos del panel se bloquea con 297 documentos | Sin arreglar. Es del panel de administración, no del sitio público |
