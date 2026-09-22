# Versionado

Este documento dice qué significa el número de versión de la plataforma, dónde vive y cuándo
cambia. Es corto a propósito: un esquema de versionado que necesita muchas páginas no lo sigue
nadie.

## Qué se versiona

**El despliegue**, no un paquete. Una versión identifica un conjunto concreto: las **cuatro
imágenes** —`app`, `frontend`, `sandbox`, `mcp`— más la **cabeza de Alembic** que les corresponde.

Por eso la fuente única es el fichero [`VERSION`](../VERSION) de la raíz, y no el `pyproject.toml`
de ninguno de los cuatro proyectos: ninguno es más «el proyecto» que los otros, y elegir uno
dejaría a los demás divergiendo en silencio. Fue lo que pasó antes de existir este documento —tres
manifiestos decían `0.1.0` y el del frontend `0.0.0`— sin que nada lo cruzara.

## El formato: `0.MENOR.PARCHE`

| Parte | Cuándo cambia |
|---|---|
| **`0.`** | **No cambia.** Es la declaración de que el proyecto es experimental |
| **MENOR** | Algo que quien lo tenga instalado necesitaría saber: una capacidad nueva, o **una acción manual requerida** —una variable nueva obligatoria, un cambio de configuración, una migración no reversible, una ruptura del contrato de la API o del widget— |
| **PARCHE** | Correcciones y actualizaciones de dependencias. Nada nuevo, nada que hacer |

### Por qué el `0.` se queda

En *semantic versioning*, `0.x` significa literalmente que cualquier cosa puede romperse entre
versiones. **Eso es exactamente lo que este proyecto tiene que comunicar.** Subir a `1.0.0` diría
lo contrario —que hay un compromiso de compatibilidad y un camino de actualización— y la
Universitat Jaume I **publica este código pero no presta servicio sobre él**: no hay soporte, ni
mantenimiento comprometido, ni atención de incidencias de instalaciones ajenas. Está dicho con
todas las letras en el [README](../README.md), «Qué no acompaña a la publicación».

Numerar sin comprometer soporte no es una contradicción: **el número es descripción, no promesa**.
Sirve para que quien lo instale sepa qué ejecuta y para que un informe de fallo sea comprobable.
Nada más, y ya es bastante.

## Cuándo se etiqueta

**Por acontecimiento, no por calendario.** No hay cadencia comprometida, por la misma razón que no
hay soporte: una fecha anunciada y no cumplida erosiona más la confianza que no haberla anunciado.

Se etiqueta cuando entra algo que alguien de fuera necesitaría saber. En la práctica: una capacidad
nueva, una acción manual requerida, o un arreglo de seguridad.

Hay un efecto secundario útil de no tener calendario: una `0.4.0` parada seis meses no parece
abandono, mientras que una `1.3.0` parada un año sí lo parece.

## Dónde se lee

**En un sistema en marcha**, sin credencial:

```
GET /api/v1/instancia
{"source_url": "...", "version": "0.1.0"}
```

Va ahí y no en `/health` porque `/health` es una sonda de vida —la consume un supervisor que sólo
mira el código de estado— mientras que `instancia` ya declara ser los metadatos públicos del
despliegue. Y es público a propósito: quien reporta un fallo desde el widget embebido tiene que
poder decir en qué versión le pasó.

**En la imagen**, la versión se estampa al construir: `deploy.yml` lee `VERSION` y la pasa como
`--build-arg GOVGENAI_VERSION`. En desarrollo, sin esa variable, se lee del fichero. Nunca queda
vacía: el valor de reserva es `0.0.0+desconocida`, que no es una versión plausible a propósito —si
aparece en un informe de fallo, lo que hay que arreglar es el empaquetado y no el número—.

## Qué impide que esto se pudra

`server/tests/infra/test_ver_la_version_es_una_sola_y_se_puede_preguntar.py` cruza los seis sitios
que tienen que decir lo mismo: el fichero `VERSION`, los cuatro manifiestos, el `ARG`/`ENV` del
`Dockerfile` y el `--build-arg` de `deploy.yml`. Sin ese cruce, «la versión» vuelve a ser seis
valores que se parecen — que es el estado del que salió.

## Las notas de cada versión

Empiezan por **qué hay que hacer**, no por qué cambió. Es lo único que lee quien administra una
instalación:

1. **Acciones requeridas** — variables nuevas, cambios de configuración, pasos manuales. Si no hay
   ninguna, se dice explícitamente: «ninguna».
2. **Migraciones** — si las hay y si se aplican solas.
3. **Novedades y correcciones.**
4. **Dependencias actualizadas.**
