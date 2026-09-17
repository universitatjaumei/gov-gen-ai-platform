# Bloque IMG — Que CI construya la imagen y la arranque

> Nacido el 2026-09-15, **el mismo día en que el hueco tumbó producción 35 minutos**. No es una
> sospecha ni una mejora: es la medida de un incidente que ya se pagó.

**Un prompt.** Va **antes de FUN**, que es el bloque más grande y el que más superficie nueva mete,
y por tanto el peor momento para descubrir que la imagen no arranca.

---

## Lo medido, que es de donde sale todo

**El 2026-09-15 el contenedor `app` no arrancó en producción**:

```
exec: "uvicorn": executable file not found in $PATH
```

`uvicorn` es lo que **ejecuta** la aplicación —el `CMD` del `Dockerfile` es
`uvicorn server.app.main:app`— y **no estaba declarado** en `pyproject.toml`. Llegaba de rebote
por `browser-use → mcp → uvicorn`, y DEP.1 mandó `browser-use` al extra `agente-navegador`.

**Y lo que importa no es el paquete, es la clase de agujero**, que sigue abierto:

| Comprobación | Qué instala | ¿Vio el fallo? |
|---|---|---|
| `Lint & Test` de CI | `uv sync --locked --all-extras` | **No** — con extras, `uvicorn` está |
| `test_dep1_no_hay_dependencias_de_rebote.py` | — | **No** — busca *imports*, y `uvicorn` se invoca |
| Comprobar que la app **importa** con el conjunto base | base | **No** — importar funciona; falta el proceso |
| `test_dep8_…_ejecutables_del_dockerfile…` (DEP, 15-09) | — | **Sí, pero sólo el `CMD`** |
| La imagen real, construida y arrancada | base, como el despliegue | **Sí** — y nadie la construye en CI |

O sea: **el único conjunto de dependencias que se despliega es el único que nadie prueba.**
`ci.yml` no construye ni una imagen; los cuatro `Dockerfile` se revisan a mano antes de `main`, y
una revisión a mano no ve un ejecutable que desapareció de un árbol transitivo.

**Medido también el 2026-09-15, después del arreglo**: reconstruido el conjunto base
(`uv sync --frozen --no-dev`, sin extras) la aplicación **arranca y sirve** —`/health` 200,
`/openapi.json` 200, y ni una degradación en el log—. O sea que **hoy no hay una segunda
instancia esperando**, y por eso este bloque es importante pero no urgente. Esa medición es de
Windows y de un día; no sustituye a construir la imagen en Linux en cada push.

---

### Prompt IMG.1 (RED/GREEN) — La imagen se construye y se levanta en CI

**Modelo sugerido**: Sonnet — el alcance está cerrado y lo que decide es si el contenedor
responde. Sube a Opus sólo si al medir el tiempo hay que rediseñar cuándo corre.

```
# PROMPT IMG.1 (RED/GREEN) — De «se revisa a mano» a «CI la arranca»
# Deploy: no aplica (integracion continua)

## Por que
El conjunto de dependencias que se despliega —base, sin extras— es el unico que no prueba
nadie, y el 2026-09-15 eso costo 35 minutos de produccion caida por un ejecutable que
desaparecio de un arbol transitivo. El guardarrail de DEP cubre los ejecutables del CMD, que
es una rendija; lo que falta es levantar la imagen.

## Que hacer
1. Un job nuevo en `ci.yml` que CONSTRUYA la imagen del servidor con el mismo Dockerfile del
   despliegue. Sin `--all-extras` ni atajos: si el despliegue usa `uv sync --frozen --no-dev`,
   aqui igual, o no se esta midiendo lo que se despliega.
2. ARRANCARLA y esperar a que responda. Un `docker run` con Postgres de servicio —el job
   `test` ya levanta uno, copiar ese patron— y un `curl` a `/health` con reintentos. El
   criterio es el mismo que usa el despliegue, para que no haya dos definiciones de «sirve».
3. Medir cuanto tarda ANTES de decidir donde va. Si son minutos, entra en cada push como un
   job mas; si es caro, en `pull_request` a `main` y en `push` a `main`, y se dice por que.
   La medicion va escrita en el fichero, como en el resto de este plan.
4. Las otras tres imagenes (`frontend`, `mcp_server`, `services/script_sandbox`): construirlas
   SIEMPRE —construir es barato y caza un Dockerfile roto—; arrancar solo las que tengan una
   comprobacion de salud que signifique algo. Decir cual y por que.
5. Retirar de `docs/` la promesa de que los Dockerfile «se revisan a mano antes de main», si
   esta escrita: cuando lo comprueba CI, esa frase deja de ser verdad y pasa a ser ruido.

## Tests (RED primero)
- Un guardarrail que fije el diseno, en `tests/infra/`:
  - el job existe y NO lleva `continue-on-error`;
  - construye con el MISMO Dockerfile que el despliegue (nada de uno «de test»);
  - la instalacion NO lleva `--all-extras` ni `--dev`, que es el punto entero del bloque;
  - arranca el contenedor y comprueba `/health`.
- Y su mutacion comprobada: con `--all-extras` en el job, el guardarrail se pone ROJO.

## Criterio de done
- [ ] La imagen del servidor se construye y ARRANCA en CI, con /health en 200
- [ ] Guardarrail del job, con sus mutaciones comprobadas una a una
- [ ] El tiempo medido y escrito, y la decision de cuando corre justificada con esa medida
- [ ] Comprobado que el job SE PONE ROJO si se quita `uvicorn` del manifiesto — el caso real
      del 2026-09-15, que es la unica forma de saber que este bloque sirve para lo que nacio
```

---

## Lo que este bloque NO hace

- **No toca la reversión automática del despliegue.** Ya se arregló el 2026-09-15: el paso
  «Comprobar que sirve, y volver atrás si no» lleva `if: always()` y lo fija
  `test_d5vm_despliegue.py::test_la_reversion_corre_aunque_el_despliegue_falle`. Era la mitad
  cara del incidente y está cerrada.
- **No publica las imágenes que construye.** Construir para comprobar y publicar para desplegar
  son cosas distintas; mezclarlas mete en CI permisos de escritura sobre el registro que hoy no
  necesita.
- **No sustituye al escaneo de la cadena de suministro.** DEP.7 vigila vulnerabilidades; esto
  vigila que lo que se despliega arranque. Son preguntas distintas y por eso son jobs distintos.

---

## Ejecutado el 2026-09-17 — el job `imagen`

**Lo que quedó montado**, en `ci.yml`, con `needs: contract`:

1. **Las cuatro imágenes se construyen** con los `Dockerfile` y los contextos del despliegue.
2. **Sólo se arranca la de la aplicación**, que es la única con una comprobación de salud que
   signifique algo sin montar red ni configuración: el frontend sirve estáticos y el *sandbox* y
   el MCP necesitan una red que este job no levanta. Construir las tres, sí: es barato y caza un
   `Dockerfile` roto, que es justo lo que pasó el 2026-09-16.
3. **Migra con la imagen recién construida** (`alembic upgrade head`), como el servicio `migrate`
   de `docker-compose.prod.yml`. Sin eso el arranque muere en la primera consulta y el job se
   pondría rojo por una razón distinta de la que existe para vigilar.
4. **Arranca con `ENVIRONMENT=production`**, que es lo que se despliega y lo que activa los tres
   gates de `core/config.py`, y espera a `/health` con reintentos: el mismo criterio del paso
   «Comprobar que sirve, y volver atrás si no» de `deploy.yml`.
5. **El cliente de la API se descarga del job `contract`** en vez de volver a instalar uv y node
   aquí. `frontend/src/shared/api/generated/` no viaja en el repositorio, y `docker build
   ./frontend` a secas falla con veinte «Cannot find module»: es donde murió el primer
   despliegue.

**El guardarraíl es `server/tests/infra/test_img1_ci_construye_y_arranca_la_imagen.py`**, y lee de
`deploy.yml` qué imágenes y qué `Dockerfile` usa el despliegue **en vez de copiarlos**: si el
despliegue añade una imagen o mueve un fichero, este test se entera. Copiar la lista es cómo
empiezan las dos verdades.

### Las cinco mutaciones, comprobadas una a una

| Mutación | Resultado |
|---|---|
| `--all-extras` dentro del job | rojo |
| `continue-on-error` en el paso que arranca | rojo |
| construir `Dockerfile.test` en vez del del despliegue | rojo (2 tests) |
| construir y **no** arrancar | rojo |
| acotar el job con un `if` | rojo |

**Y la cuarta se quedó VERDE en la primera versión**, que es el hallazgo de método de este
prompt: la comprobación preguntaba si el script contenía `docker run`, y el paso de migraciones
también ejecuta uno. Quitar el arranque de la aplicación no se notaba. Ahora la pregunta es
`docker run -d` **de una etiqueta que este mismo job acaba de construir**, y el caso está escrito
como test. Es otra vez la misma lección: un guardarraíl sólo ve la pregunta que le hicieron.

### La medida, y la decisión que sale de ella (2026-09-17)

**La secuencia entera, ejecutada en local** con Docker Desktop (motor Linux), en frío y contra un
Postgres desechable en su propia red —la base de desarrollo no se tocó—:

| Paso | Tiempo |
|---|---|
| Construir `app` | 166 s |
| Construir `frontend` | 66 s |
| Construir `sandbox` | 59 s |
| Construir `mcp` | 18 s |
| Migrar con la imagen recién construida | 6 s |
| Arrancar hasta `/health` 200 | ~20 s |
| **Total** | **≈ 5,6 min** |

Y sirvió para lo que una medición sirve además de dar un número: **la secuencia funciona de punta
a punta**. El contenedor arrancó con `ENVIRONMENT=production` y el registro salió con **0 errores
y 0 avisos**, `Application startup complete`, el sembrado **omitiendo los datos de desarrollo**
como debe fuera de desarrollo, y los dos refrescos de arranque resolviendo sin credenciales por su
lista de reserva.

**Contra los tiempos reales de CI** (run `35117521768`, rama `desarrollo`): `Lint & Test` **6,28
min** —que es quien marca el total—, `contract` 3,38 min, `supply-chain` 1,27 min, `a11y` 0,68
min.

**Decisión: el job corre en cada ejecución del flujo, sin `if`.** Con `needs: contract` (3,38 min)
más lo suyo, quedaría alrededor de 9 min y **pasaría a ser el camino crítico**, añadiendo unos 2-3
min al total. Se acepta, y la razón es que la alternativa no protege: acotarlo a `main` llegaría
tarde, porque `deploy.yml` dispara **con ese mismo push y en paralelo**, así que un rojo ahí no
frena nada. El valor entero está en cazarlo en `desarrollo`, antes del merge.

**La palanca, escrita por si algún día molesta**: sólo la imagen del frontend necesita el cliente
generado. Partir el job —las tres que no lo necesitan sin `needs`— las sacaría del camino crítico.
No se hace ahora: un job es más fácil de leer que dos, y el coste medido no lo justifica todavía.

**Dos avisos sobre la medida, para que nadie la lea como lo que no es**: es de Windows y de una
pasada, y su contexto de construcción es **mayor** que el de CI (`_local/` y `htmlcov/` no están
en el checkout). Sirve para dimensionar, no para presumir de cifra.

### Lo que sigue sin comprobarse fuera de CI

**El caso real del 2026-09-15 en vivo**: quitar `uvicorn` del manifiesto y ver el job rojo. Exige
una ejecución de CI. Lo comprobado sin ella: `test_dep8` se pone rojo con ese mismo cambio, y la
imagen construida aquí arranca — que es la otra mitad de la afirmación.
