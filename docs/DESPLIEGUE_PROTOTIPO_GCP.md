# Despliegue del prototipo en GCP — sitio de normativa + asistente público

> **Escrito el 2026-08-16.** Alcance: un **prototipo** para que un grupo de personas lo
> pruebe, **sin dominio propio**. No sustituye al bloque Deploy de `Plan_TDD_Fase1.md`
> (D.0–D.6), que es el despliegue en condiciones; esto es lo mínimo para que se pueda usar.

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

## 4. Lo que este prototipo deja fuera a propósito

- **Dominio propio y HTTPS con certificado propio.** Decisión del usuario: es un prototipo.
  El bucket sirve por HTTPS con el dominio de Google, que basta para probar.
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
