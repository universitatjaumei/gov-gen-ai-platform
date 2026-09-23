## Bloque REPO — Sustituir el repositorio de GitHub por uno sin objetos huérfanos

> ## ⚠️ REPLANIFICADO EL 2026-09-15: la variante B ya no es posible, y lo que queda es la C
>
> **La transferencia se hizo el 2026-09-10, y con ella entró en la organización justo lo que la
> variante B existía para evitar.** La B decía «el repositorio limpio **nace** en
> `universitatjaumei` y no se transfiere nada, porque una transferencia se lleva el almacén de
> objetos completo». Se transfirió. Medido el 2026-09-15 contra la API:
>
> | Comprobación | Resultado |
> |---|---|
> | `repos/universitatjaumei/gov-gen-ai-platform/commits/dc4904e0c763` | **existe** |
> | …`/contents/logs?ref=dc4904e0c763` | **46 ficheros** |
> | …`/contents/logs?ref=152c3d2f3f2e` | **46 ficheros** |
> | Historial **alcanzable** — `git log --all -- logs/` | **0 commits** (limpio) |
> | Visibilidad / *forks* | **privado / 0** |
>
> **Lo que atenúa**: sigue privado y sin *forks*, así que la exposición se limita a quien tenga
> acceso en la organización. **Lo que agrava, y es nuevo**: el objetivo pasa a ser **abrirlo**.
>
> ### Lo que hay dentro, medido y no supuesto (2026-09-15)
>
> Son volcados `llm_anonymized_input_*.txt`, ~1,2 MB. El nombre dice «anonymized» y **el nombre
> miente**. Sobre una muestra de 51 KB, sin leer contenido personal —sólo patrones y dominios—:
>
> * **28 correos: 15 de Faker** (`example.com/net/org`) y **13 de dominios institucionales
>   reales** — `uji.es` (9), `mondragon.edu` (2), `doctor.upv.es`, `edu.uji.es`.
> * 19 cadenas con forma de DNI y 4 de teléfono. **Éstas no discriminan**: el anonimizador
>   sustituye con Faker, o sea que cambia un DNI por **otro DNI válido**, así que su presencia no
>   prueba ni desmiente nada. Los dominios sí discriminan, y dicen que **la anonimización no lo
>   cogió todo**.
>
> Conclusión operativa: **hay datos personales reales en ficheros etiquetados como anonimizados**,
> y eso decide el resto del bloque. No se investiga más: caracterizar basta para decidir, y leer
> los volcados para «confirmar» sería hacer con ellos justo lo que se quiere evitar.
>
> ### Por qué `filter-repo` NO basta, que es el punto entero
>
> El historial alcanzable **ya está limpio** (0 commits con `logs/`). Los volcados viven en
> **commits huérfanos**, fuera de la historia, y `git filter-repo` reescribe lo alcanzable: no los
> toca. Sobreviven en el almacén de objetos hasta que GitHub recoja basura, **sin plazo
> garantizado** — llevan así desde el 2026-08-21.
>
> Y al abrir el repositorio eso deja de ser un detalle: **cualquiera con el SHA los descarga**, y
> en cuanto exista un *fork* los objetos se propagan a la red de *forks* de forma permanente.
>
> ### ~~La variante C~~ → **LA VARIANTE D** (corregido el mismo 2026-09-15)
>
> **La C —repositorio nuevo con almacén nuevo— está BLOQUEADA POR PERMISOS**, medido:
>
> | | |
> |---|---|
> | Rol en la organización | **`member`** (no *owner*) |
> | `members_can_create_repositories` | **`false`** |
> | Permiso sobre el repositorio | **`admin=true`** |
>
> O sea: **se puede borrar el repositorio pero no crear uno**, y pedir el permiso otra vez es
> justo lo que se quiere evitar. La C exigiría una gestión con UADTI por cada intento.
>
> **Y la alternativa que descarté al escribir la C estaba MAL DESCARTADA.** El argumento fue que
> pedir la purga a GitHub Support «deja el resultado en manos de un tercero y **sin forma de
> comprobarlo desde fuera**». La segunda mitad es falsa: **se comprueba con la misma llamada que
> encontró el problema**, `gh api …/commits/<sha>` → 404. Que dependa de un tercero es un problema
> de plazo, no de verificabilidad, y no es lo mismo.
>
> **La variante D: pedir a GitHub Support la recogida de basura, y verificar.** Y hay tres
> mediciones que dicen que aquí funciona limpiamente, porque **nada ancla los huérfanos**:
>
> | Lo que podría anclarlos | Medido |
> |---|---|
> | *Forks* (heredan el almacén de objetos) | **0** |
> | *Pull requests* (sus `refs/pull/*` los harían alcanzables) | **0** |
> | Refs de *pull* en el remoto | **0** |
> | `logs/` en el historial alcanzable | **0 commits** |
>
> Con cero *forks* y cero *pull requests*, los dos commits son **genuinamente inalcanzables**: una
> recogida de basura se los lleva. Ésa es exactamente la condición en la que la purga de Support
> hace lo que promete; si hubiera un *fork* o un PR que los citara, no bastaría y habría que
> volver a la C.
>
> **La exposición mientras tanto, medida**: repositorio privado, **7 colaboradores directos** y 30
> miembros en la organización. Es acotada y conocida, no pública.

> **Estado (2026-09-15): 5 prompts, DOS hechos.** REPO.3 ✅ (triaje de `docs/`) y **REPO.5 ✅**
> (los valores de esta casa fuera de los documentos publicables).
>
> Pendientes: **REPO.1** (ahora variante C: repositorio nuevo en la organización), **REPO.4**
> (retirar los anclajes al dueño anterior) y **REPO.2** (los otros dos repositorios).
>
> El orden es **REPO.1 → REPO.4 → REPO.2**, y REPO.1 y REPO.2 los ejecuta el usuario.
> **El rol `admin` sobre la organización, que era el prerrequisito que faltaba, está desde el
> 2026-09-14.**
>
> **El paso 0.bis está HECHO (2026-09-15)**: los tres ficheros que sólo protegía
> `.git/info/exclude` —que no viaja— se movieron a `_local/docs_operacion/`, cubierto por
> `.gitignore:139`, que sí viaja. Comprobado además que **ninguno de los tres entró nunca al
> historial**, así que no van en la lista de filtrado.

> **Planificado el 2026-08-21.** No es un bloque de código: es una operación sobre GitHub que ejecuta
> el usuario. Está aquí, versionado, porque el guion detallado vivía en `_local/`, que es una carpeta
> ignorada y de usar y tirar — y esto no puede perderse con ella.
>
> **Va después del Bloque NIC, a propósito.** No tiene sentido montar el repositorio definitivo y acto
> seguido meterle la retirada de 500 ficheros de legacy.

### Prompt REPO.1 (manual del usuario) — El cambio de repositorio

**Modelo sugerido**: — (no es un prompt de agente)

```
# PROMPT REPO.1 — Lo hace el usuario
# Deploy: n/a

## Por que
El 2026-08-21 se reescribio el historial para sacar `logs/` —45 volcados `llm_anonymized_input_*.txt`
con datos de usuarios reales— y se forzo el push. Los commits viejos quedaron **inalcanzables pero no
borrados**: GitHub los sirve por URL de SHA hasta que recoge basura, sin plazo garantizado.

Hacerlo **antes de que exista el primer fork**: un fork conserva los objetos del original. Y
tambien antes de TRANSFERIR: una transferencia se lleva el almacen de objetos completo.

**Comprobado el 2026-09-07: la exposicion sigue viva, 17 dias despues de la reescritura.** El
commit huerfano `dc4904e0c763` todavia sirve `logs/` con 46 ficheros por la API. GitHub no ha
recogido basura y no promete cuando.

## A donde va el nuevo — ELEGIDA LA VARIANTE B (decision del usuario, 2026-09-07)
El orden acordado es **limpiar, mover y abrir despues**. Habia dos formas:

  A) Crear el limpio en `ModestoFabra` y TRANSFERIRLO despues.
  B) Crear el limpio DIRECTAMENTE en `universitatjaumei`. **ELEGIDA.**

**Y conviene decirlo con precision porque el nombre confunde: con B NO HAY TRANSFERENCIA.** No se
usa la operacion «Transfer» de GitHub en ningun momento. Se crea un repositorio nuevo en la
organizacion y se le empuja el historial limpio; el viejo se borra al final. Eso es exactamente lo
que hace que nazca limpio: **una transferencia se lleva el almacen de objetos completo**, asi que
con A los 46 volcados entrarian en la organizacion de la universidad y solo desaparecerian al
borrar el original. Con B no entran nunca, ni un minuto.

Se ahorra ademas un paso entero con su ventana de riesgo.

**Requisito de B**: permiso para crear repositorios en `universitatjaumei`. Si no lo hay, se cae a
A, que sigue documentada en el historial de git de este fichero.

Su unico coste es que el nombre pasa a `universitatjaumei/gov-gen-ai-platform`, y **la
autenticacion del despliegue esta anclada al nombre en DOS sitios**, los dos en GCP:
  - condicion del proveedor:  assertion.repository=='ModestoFabra/gov-gen-ai-platform'
  - enlace de la cuenta:      principalSet://.../attribute.repository/ModestoFabra/gov-gen-ai-platform
Con A el nombre acaba siendo el mismo y WIF sobrevive solo; con B hay que tocarlos, y se hace
**aditivo primero, sin ventana de rotura**: ampliar la condicion a los dos nombres con `||`,
anadir el segundo principalSet, subir, verificar un despliegue real, y solo entonces retirar el
viejo. No hay que tocar codigo: `deploy.yml` lee el proveedor de una variable y el nombre del
recurso no cambia.

## El reparto de `docs/` (decidido el 2026-09-07, REVISADO el mismo dia, se ejecuta en 5.bis)

GitHub **no permite mezclar visibilidad dentro de un repositorio**: no hay carpetas privadas, las
ramas heredan la visibilidad, un *Project* es un tablero y no almacena ficheros, y un submodulo
privado sigue siendo otro repositorio y rompe el clon de quien no tiene acceso. Asi que la
eleccion es en QUE repositorio vive cada documento — o si vive fuera de los repositorios.

### La primera version de este reparto estaba mal, y conviene saber por que

**Se propuso un repositorio privado de operacion para 15 ficheros, y el usuario lo cuestiono con
razon.** Dos motivos, los dos validos:

1. **Un repositorio privado de operacion es un patron habitual, pero para otra cosa**: codigo y
   configuracion que el equipo trabaja —Terraform, Ansible, estado de entornos, registro de
   incidencias—. Quince documentos estaticos, once de ellos instantaneas congeladas, no son un
   repositorio de operacion: son **un archivo disfrazado de repositorio de operacion**.
2. **Y el argumento con el que se defendio no aguanta.** Se dijo que un Drive «pierde el
   historial» y que los tableros valen por poder compararse con la medicion de hace un mes. Pero
   son **instantaneas fechadas e inmutables**: cada fichero ES el registro, y una medicion nueva
   produce un fichero nuevo. Git no aporta casi nada ahi.

**Y habia una incoherencia de fondo**: a la pregunta del *fork* institucional se respondio «no lo
crees hasta que tenga peso, hoy estaria vacio». El mismo criterio se aplica aqui y no se aplico.

**Ademas, tres ficheros estaban clasificados por su NOMBRE y no por su contenido**, y los tres
resultaron ser documentacion publicable:

| Fichero | Lo que parecia | Lo que es |
|---|---|---|
| `DATOS_DEL_PILOTO.md` | datos del piloto | documento de **diseno**: la distincion entre catalogo de producto y datos operativos, y como viaja cada uno |
| `RUNBOOK_REINGESTA.md` | operacion de esta casa | **procedimiento**: los comandos exactos, en orden, con la puerta de comprobacion delante |
| `CASO_CURACION_ESCOLA_DOCTORAT.md` | un centro concreto | **caso guia**, con los umbrales que hubo que corregir, «para repetirlo en otro apartado sin volver a descubrirlo todo» |

Los tres llevan valores o nombres reales, y eso lo arregla **REPO.5** generalizandolos, no
sacarlos del repositorio. Clasificar por el nombre del fichero es como se llego a un reparto
tres veces mas grande de lo necesario.

### El reparto que queda

**FUERA DEL REPOSITORIO — 7 rutas, a `_local/docs_operacion/` y copia en Drive.** No hay
repositorio privado: se crea cuando tenga peso de verdad (Terraform, registro de incidencias,
rondas de medicion futuras), con el mismo test que el *fork*.

* **Los tres `VALIDACION_GERENCIA*.html`, y NO por sensibilidad: es que no son documentos.**
  Renderizan `p.pregunta` de un array de datos: son las **hojas de anotacion** que se envian a los
  informadores, con salida del modelo **sin validar**, pendiente de veredicto humano. Publicar
  salida sin validar como si fuera un documento induce a error, y un instrumento no tiene lector
  fuera de su proceso. Si alguna vez se publica el **resultado** de esas validaciones, sera otro
  documento.
* **El trio de marca**, ya sacado del arbol el 2026-09-07 a `_local/docs_operacion/`. Aqui el
  motivo **si** es distinto: identidad institucional, no secreto.

**SE PUBLICAN los otros ocho tableros** (decision del usuario el 2026-09-07: «no hay problema en
publicar los tableros, si tienen interes»). Lo tienen, y bastante: `CALIDAD_RESPUESTA_TOP_K`
—«redacta mejor con menos documentos»—, `DIAGNOSTICO_POR_QUE_NO_CONTESTA` —«y por que no es la
anchura»—, `GERENCIA_TOP_K_Y_UMBRAL` —«lo calla el umbral»—, `EXPERIMENTO_GRANULARIDAD_CONTEXTO`
—«que puede decidir un lote de 25»—, mas `MEDICION_RETRIEVAL_TOP_K`, `BLOQUE_HIB_CIERRE`,
`GERENCIA_CIERRE_BLOQUE_HIB` y `CONFIGURACION_APERTURA_PILOTO`. Son hallazgos utiles a cualquiera
que monte un RAG en administracion publica, y **la evidencia de la tesis del proyecto**: garantia
→ mecanismo → precio. Comprobado ademas: cero datos personales, cero credenciales.

**Y dos de ellos casi se clasifican mal por el nombre, otra vez**: `GERENCIA_TOP_K_Y_UMBRAL` y
`GERENCIA_CIERRE_BLOQUE_HIB` se llaman «Gerencia» y son **metodologicos**; el primero incluso
lleva la seccion «Por que el agentico contesta a todo», que es la advertencia de que la
comparacion RAG/agentico es asimetrica por construccion. Abrir el fichero antes de decidir.

**Los ocho viven desde el 2026-09-07 en `docs/mediciones/`**, con la fecha delante
(`AAAA-MM-DD_NOMBRE.html`) y su propio indice. La carpeta existe porque `docs/` mezclaba dos cosas
que **envejecen distinto** —referencia que se mantiene e instantaneas que no se tocan nunca mas—,
y porque **ninguno de los doce `.html` estaba en el indice**: no eran «documentacion menos
estable», eran ficheros que solo encontraba quien supiera el nombre. Un guardarrail comprueba que
no queden `.html` sueltos en la raiz de `docs/`, con estos cuatro como excepcion fechada que **este
paso 5.bis vacia**.
* **`LITERATURA_ASISTENTES_NORMATIVA.html`**, las 43 referencias del articulo para AI&Law. Ni
  publico ni operacion: material de investigacion sin publicar, y su sede es donde vivan los
  papers.

**AL PUBLICO — el resto (~48)**: arquitectura, especificaciones, contratos, las seis decisiones,
metodologia, multitenencia, accesibilidad, licencia, MCP, registro de actividad, sandbox, los tres
reclasificados de arriba, y `DESPLIEGUE_PROTOTIPO_GCP.md` **generalizado y NO retirado**: el
procedimiento —VM, proxy de Cloud SQL, WIF sin claves, migraciones antes de la imagen— es de lo
mas valioso que se puede publicar, porque es justo lo que una entidad local no sabe hacer. Lo que
se va son los valores. Eso es **REPO.5**.

**Esa decision ya esta tomada** (2026-09-07): se publican ocho de los once, y el filtro quedo en
**7 rutas**. Lo que la decidio no fue conveniencia sino abrir los ficheros: ocho son mediciones
con hallazgo propio y tres son instrumentos de anotacion, que es otra cosa.

**Sobre el historial, que es la parte que no se puede deshacer.** La visibilidad alcanza a los
commits: borrar un fichero antes de abrir **no lo saca del pasado**. Medido el 2026-09-07, el
filtro seria quirurgico —de **707** commits, las 7 rutas tocan pocos: `chatbots-publicos/` 5,
`DATOS_DEL_PILOTO.md` 2 y `RUNBOOK_REINGESTA.md` 1—, y la ventana es esta: REPO.1 ya reescribe y
empuja desde cero. Hacerlo despues de abrir cuesta otra reescritura, otro push forzado y otro
periodo de objetos huerfanos servidos por SHA, que es de lo que se esta saliendo.

**Lo que el filtro NO arregla**: los valores reales que quedan en versiones antiguas de los cinco
documentos de despliegue. `filter-repo` retira **ficheros**, no cadenas; para eso haria falta
`--replace-text` sobre los 707 commits. **Recomendado no hacerlo**: un id de proyecto de GCP y un
numero de proyecto no son credenciales —lo que protege el acceso es IAM, no que el nombre sea
secreto—. Se generaliza la version publicada por utilidad y para no invitar a sondear, no por
secreto.

## Lo que se pierde (inventariado el 2026-08-21, REVISADO el 2026-09-07)
Issues, PRs, releases, tags, webhooks: 0 de todo. Secretos de Actions: ninguno, el CI no usa.
Proteccion de rama: no hay. Forks, estrellas, watchers: 0.

**Y las 12 VARIABLES de Actions, que el inventario original no podia ver.** Se escribio el
2026-08-21 y el despliegue no empezo a funcionar hasta el 2026-08-31: hoy `deploy.yml` lee
`vars.GCP_WIF_PROVIDER`, `vars.GCP_DEPLOY_SA`, `vars.GOVGENAI_HOST` y nueve mas. Un repositorio
nuevo nace VACIO de variables, y con eso vacio la autenticacion falla de un modo que **no se
parece a su causa** (el proveedor llega como cadena vacia). Recrearlas es un paso, no un detalle:
  gh variable list                      # en el viejo, ANTES de borrarlo: apuntar los 12 pares
  gh variable set NOMBRE --body VALOR   # en el nuevo, uno por uno
Ninguna es secreta —son identificadores y rutas, lo dice el propio `deploy.yml`— asi que se
pueden leer y copiar sin ceremonia.

**Solo se pierden de verdad la fecha de creacion (2026-04-22) y el historial de ejecuciones de
Actions.**

## LOS PASOS VIGENTES — VARIANTE D (2026-09-15)

**No hace falta crear ningún repositorio ni pedir permisos nuevos.** Son tres cosas: filtrar lo
que sí está en la historia, pedir a Support la recogida de basura, y **no abrir hasta que los dos
SHA den 404**.

```
# PROMPT REPO.1 (variante D) — Lo hace el usuario
# Deploy: n/a

## Por que
Los 92 volcados viven en dos commits huerfanos y contienen correos institucionales reales.
`filter-repo` no los alcanza porque no estan en la historia. Y no se puede crear un repositorio
limpio: la organizacion tiene `members_can_create_repositories=false`.

Lo que si se puede: pedir a GitHub que recoja basura. Y funciona porque NADA los ancla — cero
forks, cero pull requests, cero refs de pull. Medido el 2026-09-15.

## Los pasos
1. RESPALDO fuera del portatil, con fecha de hoy:
   git bundle create ../respaldo-$(date +%F).bundle --all
   git bundle verify ../respaldo-$(date +%F).bundle

2. FILTRAR LO QUE SI ESTA EN LA HISTORIA (las 7 rutas del reparto de docs/), en un CLON DE
   TRABAJO y nunca aqui: filter-repo reescribe todos los SHA.
   git clone --no-local . ../filtrado && cd ../filtrado
   git filter-repo --invert-paths \
     --path docs/VALIDACION_GERENCIA.html \
     --path docs/VALIDACION_GERENCIA_AUTONOMA.html \
     --path docs/VALIDACION_GERENCIA_RAG_VS_AGENTICO.html \
     --path docs/LITERATURA_ASISTENTES_NORMATIVA.html \
     --path docs/chatbots-publicos/demo-uji.html \
     --path docs/chatbots-publicos/uji-theme.css \
     --path docs/chatbots-publicos/marcauji.png

   OJO: tres de las siete NO estan en `git ls-files` y es CORRECTO — el trio de marca salio del
   arbol el 2026-09-07 pero sigue en el historial, que es sobre lo que actua filter-repo. Quien
   coteje contra el arbol y «arregle» lo que no resuelve, publica el logotipo.
   Los tres de 0.bis NO van: se comprobo que nunca entraron al historial.

3. COMPROBAR EN EL FILTRADO antes de empujar:
   - las siete rutas desaparecidas:  git log --all --oneline -- <ruta>   (vacio)
   - el recuento de commits no se desploma (eran ~740 el 15-09)
   - la suite verde: test_repo3_el_indice_de_docs_no_miente.py y
     test_ninguna_marca_institucional_esta_versionada.py lo demuestran

4. EMPUJAR FORZADO las dos ramas. ESTO CREA MAS HUERFANOS —los actuales— y no importa: van en
   la misma peticion a Support del paso 5.
   git push --force-with-lease origin main
   git push --force-with-lease origin desarrollo

5. ABRIR TICKET A GITHUB SUPPORT (support.github.com), pidiendo la recogida de basura del
   repositorio `universitatjaumei/gov-gen-ai-platform` para eliminar objetos inalcanzables.
   Citar los dos SHA: dc4904e0c763 y 152c3d2f3f2e. Decir que el repositorio es privado, sin
   forks y sin pull requests, que es lo que hace la operacion limpia.

6. VERIFICAR, y este paso es la PUERTA:
   gh api repos/universitatjaumei/gov-gen-ai-platform/commits/dc4904e0c763   -> 404
   gh api repos/universitatjaumei/gov-gen-ai-platform/commits/152c3d2f3f2e   -> 404
   Y los huerfanos que cree el paso 4, si se apuntaron sus SHA.

7. RECLONAR EN LOCAL: este clon tiene los SHA viejos tras el filtrado.

## Criterio de done
- [ ] Las 7 rutas fuera del historial alcanzable, y la suite verde
- [ ] Ticket abierto a Support, con los dos SHA citados
- [ ] LOS DOS SHA DAN 404 — sin esto el bloque NO esta cerrado y NO SE ABRE el repositorio
- [ ] Reclonado en local

## La puerta, dicha aparte porque es lo unico irreversible
**NO SE CAMBIA LA VISIBILIDAD A PUBLICA HASTA QUE EL PASO 6 DE 404.** Abrir con los huerfanos
dentro los hace descargables por cualquiera con el SHA, y en cuanto exista un fork se propagan de
forma permanente. Es el unico paso de todo el bloque que no tiene vuelta atras.

## Si Support tarda o se niega
Entonces —y solo entonces— se vuelve a la variante C, que exige UNA gestion con UADTI: que un
owner cree el repositorio vacio, o que ponga `members_can_create_repositories=true` una vez.
Borrar el sucio SI se puede sin pedir nada (`admin=true` sobre el repo y
`members_can_delete_repositories=true`), asi que lo unico que hay que pedir es la creacion.
```

---

## Los pasos de la variante C (BLOQUEADA por permisos el 2026-09-15 — se conservan como plan B)

**El objetivo es dejarlo listo para ABRIRLO**, y por eso el criterio de cada paso es «que el
repositorio publico NUNCA haya contenido esto», no «que ya no se vea».

**Lo que YA ESTA HECHO y no hay que repetir** (medido el 2026-09-15):

- El remoto es `universitatjaumei/gov-gen-ai-platform`; las dos ramas estan subidas y al dia.
- Las **12 variables** estan puestas y verificadas.
- **Los dos anclajes de GCP** aceptan el nombre nuevo, y no es teoria: el 2026-09-15 se
  desplegaron DOS veces desde ahi (`8e518e0`), con `deploy.yml` verde hasta el paso de salud.
  Eso era el paso 6 de la variante B, y ya esta cumplido.
- **0.bis**: los tres ficheros de `.git/info/exclude` movidos a `_local/docs_operacion/`.
- El historial **alcanzable** no tiene `logs/` (0 commits).

```
# PROMPT REPO.1 (variante C) — Lo hace el usuario
# Deploy: n/a

## Por que
El repositorio de la organizacion arrastra DOS commits huerfanos con 92 volcados que contienen
correos institucionales reales. `filter-repo` no los alcanza: no estan en la historia. Abrir el
repositorio con ellos dentro los hace descargables por SHA para cualquiera, y permanentes en
cuanto exista un fork.

## Los pasos, y el orden importa
1. RESPALDO fuera del portatil, otra vez y con fecha de hoy:
   git bundle create ../respaldo-$(date +%F).bundle --all
   git bundle verify ../respaldo-$(date +%F).bundle
   El del 2026-09-07 existe (11,1 MB) pero es anterior a 29 commits.

2. FILTRAR EN UN CLON DE TRABAJO, nunca aqui: `filter-repo` reescribe todos los SHA y dejaria
   este clon divergente de lo que ya esta empujado.
   git clone --no-local . ../filtrado && cd ../filtrado
   git filter-repo --invert-paths \
     --path docs/VALIDACION_GERENCIA.html \
     --path docs/VALIDACION_GERENCIA_AUTONOMA.html \
     --path docs/VALIDACION_GERENCIA_RAG_VS_AGENTICO.html \
     --path docs/LITERATURA_ASISTENTES_NORMATIVA.html \
     --path docs/chatbots-publicos/demo-uji.html \
     --path docs/chatbots-publicos/uji-theme.css \
     --path docs/chatbots-publicos/marcauji.png

   OJO: tres de las siete rutas NO estan en `git ls-files` y es CORRECTO — el trio de marca salio
   del arbol el 2026-09-07 pero sigue en el historial, que es sobre lo que actua filter-repo.
   Quien coteje la lista contra el arbol y «arregle» lo que no resuelve, publica el logotipo.
   Se comprueba contra el historial:
     git log --all --oneline -- docs/chatbots-publicos/marcauji.png

   Y NO hay que anadir los tres de 0.bis: se comprobo que nunca entraron al historial.

3. COMPROBAR EN EL FILTRADO, antes de empujar y las cuatro cosas:
   - las siete rutas han desaparecido:  git log --all --oneline -- <ruta>   (vacio)
   - `logs/` tampoco esta:              git log --all --oneline -- logs/    (vacio)
   - el recuento de commits no se desploma (eran ~736 el 15-09): filter-repo borra commits que
     se quedan vacios, y decenas de menos significaria que un --path cazo de mas;
   - la suite sigue verde, que lo demuestran `test_repo3_el_indice_de_docs_no_miente.py` y
     `test_ninguna_marca_institucional_esta_versionada.py` en vez de suponerlo.

4. RENOMBRAR EL SUCIO, que pasa a ser la red:
   gh repo rename gov-gen-ai-platform-sucio --repo universitatjaumei/gov-gen-ai-platform
   NO se borra todavia. Hasta el paso 8 es lo unico que garantiza que no se ha perdido nada.

5. CREAR EL LIMPIO, VACIO, con el nombre canonico que acaba de quedar libre:
   gh repo create universitatjaumei/gov-gen-ai-platform --private
   Sin README, sin .gitignore y sin licencia: si GitHub crea un commit inicial, el push choca.
   ALMACEN DE OBJETOS NUEVO — es el punto entero de la variante C.

6. EMPUJAR LAS DOS RAMAS desde el clon filtrado:
   git remote set-url origin git@github.com:universitatjaumei/gov-gen-ai-platform.git
   git push -u origin main
   git push -u origin desarrollo
   Las dos: `desarrollo` es donde vive el trabajo y subir solo `main` dejaria fuera lo no
   desplegado.

7. REHACER LO QUE NO VIAJA con el repositorio, y verificarlo:
   - las 12 variables (gh variable list en el sucio -> gh variable set en el limpio);
   - los anclajes de GCP NO hay que tocarlos: la condicion es por RUTA
     (`assertion.repository=='universitatjaumei/gov-gen-ai-platform'`) y el nombre no cambia;
   - un commit firmado y CI+DCO en verde;
   - **UN DESPLIEGUE REAL** desde el limpio, hasta el paso de salud. Es lo unico que demuestra
     que WIF sigue aceptando, y que el almacen nuevo no rompio nada.
   - **Y LA COMPROBACION QUE DA NOMBRE AL BLOQUE**:
       gh api repos/universitatjaumei/gov-gen-ai-platform/commits/dc4904e0c763   -> 404
       gh api repos/universitatjaumei/gov-gen-ai-platform/commits/152c3d2f3f2e   -> 404
     Si alguno responde, el almacen nuevo NO esta limpio y no se sigue.

8. BORRAR EL SUCIO. Aqui mueren los 92 volcados, y no antes:
   gh auth refresh -h github.com -s delete_repo   (el token no trae ese permiso por defecto)
   gh repo delete universitatjaumei/gov-gen-ai-platform-sucio --yes

9. RECLONAR EN LOCAL. Este clon tiene los SHA viejos y quedaria divergente para siempre; seguir
   trabajando en el es garantia de volver a empujar lo filtrado.

## Criterio de done
- [ ] Los dos SHA huerfanos dan 404 en el repositorio nuevo
- [ ] Las dos ramas coinciden con las locales del clon filtrado
- [ ] Las 12 variables puestas, CI y DCO verdes, y UN DESPLIEGUE REAL en verde
- [ ] El sucio borrado
- [ ] Reclonado en local

## Lo que NO hace este prompt
- **No abre el repositorio.** Abrir es el ULTIMO paso y va despues de REPO.4, que retira los
  anclajes al dueno anterior. Un repositorio abierto que todavia se nombra a si mismo con el
  dueno viejo es un repositorio que hay que tocar despues de abrirlo.
- **No renuncia a pedir la purga a GitHub Support.** Se puede hacer ademas, y no en lugar de:
  borrar el repositorio es verificable desde fuera y un ticket no.
```

---

## Los pasos de la variante B (SUPERADOS el 2026-09-15 por la transferencia — se conservan porque explican de dónde salen las decisiones)
0. PRERREQUISITOS que no se averiguan desde fuera, y que van ANTES de tocar nada. Son las tres
   preguntas a UADTI: rol con el que se incorpora el mantenedor y **quien aprueba la creacion**,
   **permisos base para miembros** de la organizacion (decide quien ve el repositorio mientras
   siga privado), y **plan** de la organizacion (si no es Enterprise, los rulesets sobre repos
   privados pueden no estar disponibles).
0.bis. **`.git/info/exclude` NO VIAJA, y hoy protege tres ficheros que no deben publicarse.**
   Descubierto el 2026-09-07, al ponerse roja en CI una comprobacion que en local pasaba. Esa
   lista es **por clon**: no esta versionada, no va en el bundle y **el clon nuevo no la tendra**.
   Hoy contiene:
     docs/convocatoria_tecnologo_A2_TecLab.md
     docs/EU_GOVERNANCE_CONCEPT_NOTE.md
     docs/EU_GOVERNANCE_TOPICS.md
   Como el repositorio **se va a abrir**, el riesgo es concreto: en el clon nuevo un `git add -A`
   los mete, y acaban en un repositorio publico una convocatoria de plaza y dos notas de
   proyecto europeo. Antes de empujar hay que decidir por cada uno: **`.gitignore`** si nunca
   deben entrar (lo expresa para todos los clones y sí viaja), o sacarlos de `docs/` a `_local/`,
   que ya esta ignorada. **Dejarlo en `.git/info/exclude` no es una opcion en el clon nuevo**,
   porque nadie se acordara de recrearlo.
   Nota aparte: `git ls-files` es lo unico que dice la verdad sobre que hay en el arbol; el disco
   del mantenedor tiene mas cosas. El guardarrail de REPO.3 se arreglo para preguntar a git.
1. Copia de seguridad fuera del portatil: `git bundle create ../respaldo.bundle --all`, y
   `git bundle verify` ejecutado desde dentro del repositorio.
   HECHO el 2026-09-07: `Documents/respaldo-gov-gen-ai-platform-2026-09-07.bundle`, 11,1 MB,
   «complete history», con `main`, `desarrollo` y HEAD. **Falta sacarlo del portatil.**
2. Apuntar las 12 variables del viejo, que en el nuevo no estan:
   gh variable list --repo ModestoFabra/gov-gen-ai-platform
   NO se renombra el viejo. En B se queda como esta y sirviendo hasta el paso 7: es la red.
3. Crear el nuevo en la ORGANIZACION, VACIO (sin README, sin .gitignore, sin licencia: si GitHub
   crea un commit inicial, el push choca):
   gh repo create universitatjaumei/gov-gen-ai-platform --private
3.bis. COPIAR A `_local/docs_operacion/` LO QUE SALE DEL ARBOL, y de ahi al Drive, ANTES de
   filtrar. Si se filtra primero y algo sale mal, esos ficheros solo estarian en el bundle.
   El trio de marca ya esta ahi desde el 2026-09-07. Faltan los TRES `VALIDACION_GERENCIA*.html`
   y la revision de literatura — los otros ocho tableros se publican y no salen del arbol. **La copia en Drive va antes del paso 5.bis**, no despues: `_local/` esta ignorada
   y no la respalda nadie.

4. AMPLIAR LA AUTENTICACION A LOS DOS NOMBRES, antes de empujar. Aditivo, sin ventana de rotura:
   gh variable list -> copiar los 12 pares al nuevo (gh variable set ... --repo universitatjaumei/...)
   gcloud iam workload-identity-pools providers update-oidc modestofabra-gov-gen-ai-platform \
     --project=<PROYECTO_GCP> --location=global --workload-identity-pool=github \
     --attribute-condition="assertion.repository=='ModestoFabra/gov-gen-ai-platform' || assertion.repository=='universitatjaumei/gov-gen-ai-platform'"
   gcloud iam service-accounts add-iam-policy-binding govgenai-deploy@<PROYECTO_GCP>.iam.gserviceaccount.com \
     --project=<PROYECTO_GCP> --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/<NUMERO_DE_PROYECTO>/locations/global/workloadIdentityPools/github/attribute.repository/universitatjaumei/gov-gen-ai-platform"
   Los dos anclajes estan medidos el 2026-09-07 y son los dos sitios que llevan el nombre. El
   codigo NO se toca: `deploy.yml` lee el proveedor de una variable y el nombre del recurso no
   cambia.
5. Subir **LAS DOS RAMAS** al nuevo:
   git remote set-url origin git@github.com:universitatjaumei/gov-gen-ai-platform.git
   git push -u origin main
   git push -u origin desarrollo

5.bis. FILTRAR DEL HISTORIAL lo que sale del repositorio (7 rutas). **Se hace en un CLON DE
   TRABAJO, no aqui**:
   `filter-repo` reescribe todos los SHA, asi que el clon de desarrollo quedaria divergente de lo
   que ya se ha empujado. Se clona, se filtra, se empuja el resultado, y luego se reclona.
   Es lo que hace que el repositorio publico NUNCA haya contenido estos ficheros:

   git clone --no-local . ../filtrado && cd ../filtrado
   git filter-repo --invert-paths \
     --path docs/VALIDACION_GERENCIA.html \
     --path docs/VALIDACION_GERENCIA_AUTONOMA.html \
     --path docs/VALIDACION_GERENCIA_RAG_VS_AGENTICO.html \
     --path docs/LITERATURA_ASISTENTES_NORMATIVA.html \
     --path docs/chatbots-publicos/demo-uji.html \
     --path docs/chatbots-publicos/uji-theme.css \
     --path docs/chatbots-publicos/marcauji.png

   **OJO al verificar esta lista: tres de las siete rutas NO existen en `git ls-files`**, y es
   correcto. El trio de marca salio del arbol el 2026-09-07 a `_local/`, pero **sigue en el
   historial**, que es sobre lo que actua `filter-repo`. Quien coteje la lista contra el arbol y
   «arregle» lo que no resuelve, borra tres entradas buenas y publica el logotipo. Se comprueba
   contra el historial: `git log --all --oneline -- docs/chatbots-publicos/marcauji.png`.

   Comprobar en el filtrado ANTES de empujar, y las tres cosas:
   - los 18 caminos han desaparecido de todo el historial:
     git log --all --oneline -- docs/DATOS_DEL_PILOTO.md   (vacio)
   - **la suite sigue verde**: retirar ficheros del historial no deberia tocar el arbol de la
     punta, pero `test_repo3_el_indice_de_docs_no_miente.py` y
     `test_ninguna_marca_institucional_esta_versionada.py` lo demuestran en vez de suponerlo;
   - el recuento de commits no se ha desplomado: eran 707. `filter-repo` borra commits que se
     quedan vacios, y si desaparecieran decenas seria que un `--path` cazo mas de lo previsto.

   OJO con el orden: los ficheros hay que **retirarlos tambien del arbol de la punta** en un
   commit normal (`git rm`), porque `--invert-paths` los saca del pasado pero el commit de la
   punta se reescribe sin ellos y el indice de `docs/` quedaria enlazando al vacio. Los dos
   guardarrailes de arriba se pondran rojos si se olvida, que es para lo que estan.
   La rama `desarrollo` nacio el 2026-09-02, despues de escribirse este plan, y es DONDE VIVE EL
   TRABAJO: subir solo `main` dejaria fuera todo lo no desplegado. Comprobar que estan las dos:
   gh api repos/.../branches --jq '.[].name'
6. Verificar CON EL ANTERIOR TODAVIA EN PIE. Si algo falla, se para y no se ha perdido nada:
   - las dos puntas coinciden: git rev-parse main / desarrollo contra
     gh api repos/.../commits/{main,desarrollo} --jq .sha
     (si coinciden esta todo: git no puede subir un commit sin sus ancestros);
   - gh api repos/.../commits/dc4904e0c763  da 404  <- EL QUE IMPORTA, ver abajo;
   - gh api repos/.../contents/logs  da 404;
   - las 12 variables estan: gh variable list --repo universitatjaumei/... | wc -l
   - CI en verde: un commit firmado (git commit -s) y los dos workflows pasan.
   - **UN DESPLIEGUE REAL desde el nuevo**, que es lo unico que demuestra que WIF acepta el
     nombre nuevo. Sin esto no se puede seguir: llevar `desarrollo` a `main` en el nuevo y ver
     `deploy.yml` en verde hasta el paso de salud.

   Sobre que SHA comprobar: la version anterior de este paso miraba
   `82f475b6c6d382e1586e7cc0319a9a0917fb3475`, y **ese no demuestra nada**. Medido el 2026-09-07
   caminando la cadena de huerfanos en GitHub: el arbol de `82f475b` NO tiene `logs/` —es la punta
   posterior al borrado y anterior a la reescritura—, asi que su `contents/logs` da 404 aunque la
   exposicion siga viva. El primer ancestro que SI sirve los volcados es **`dc4904e0c763`**
   (2026-08-21 06:20:35), con **46 ficheros**, y por debajo `152c3d2f3f2e` con otros 46. Comprobar
   `82f475b` era medir lo que no era, que es el fallo de instrumento habitual de esta casa.
7. Borrar el viejo. **Aqui es donde mueren los 46 volcados**, y no antes: hasta este punto la
   exposicion sigue viva y el viejo es la red por si algo del paso 6 falla.
   gh auth refresh -h github.com -s delete_repo   (el token no trae ese permiso por defecto)
   gh repo delete ModestoFabra/gov-gen-ai-platform --yes
8. ESTRECHAR la autenticacion, ya sin vuelta atras que proteger:
   gcloud ... providers update-oidc ... --attribute-condition="assertion.repository=='universitatjaumei/gov-gen-ai-platform'"
   gcloud iam service-accounts remove-iam-policy-binding ... --member="principalSet://.../attribute.repository/ModestoFabra/gov-gen-ai-platform"
   Y un despliegue mas para comprobar que sigue en verde con la condicion estrecha.

## Despues
- **Abrir es el ULTIMO paso**, y va despues de transferir: limpiar -> transferir -> abrir.
  Settings -> Danger Zone -> Change visibility -> Public. Y ojo: una vez en la organizacion, esa
  decision **deja de ser solo del mantenedor**.
- Cualquier otro clon en otra maquina conserva los volcados. No hacer pull: borrarlo y clonar.
- El nombre corto NO cambia: sigue siendo `gov-gen-ai-platform`. Lo que cambia con la variante B
  es el dueno, y con el los dos anclajes de WIF.
- **Poner proteccion de rama en `main`**, que hoy no tiene ninguna siendo el disparador del
  despliegue. Es el momento: el repositorio se recrea de cero.
```

### Prompt REPO.2 (manual del usuario) — Los otros dos repositorios

**Modelo sugerido**: — (no es un prompt de agente)

```
# PROMPT REPO.2 — Lo hace el usuario
# Deploy: n/a

Son dos repositorios previos, y NO SE NOMBRAN AQUI a proposito: uno es personal y ajeno por
completo a este proyecto, y publicar su nombre permitiria inferir informacion privada de un
tercero. Los nombres y los pasos exactos viven en `_local/LIMPIEZA_REPOSITORIOS_GITHUB.md`, que
no esta versionado.

Lo que si conviene dejar escrito aqui, porque es la parte reutilizable:

- Uno es un fork publico SIN TRABAJO PROPIO y sin actividad desde hace anos. Borrar sin mas; no
  afecta al proyecto del que salio.
- El otro es el predecesor privado de este repositorio y contiene los mismos volcados que
  motivaron la limpieza de REPO.1. Su clon local ya es el archivo real, asi que borrarlo de
  GitHub no pierde historia — pero ANTES hay que limpiar los volcados en ese clon
  (`git filter-repo --path logs --invert-paths --force`) y guardar un bundle fuera, porque pasa
  a ser la unica copia.
```


### Prompt REPO.4 (RED/GREEN) — Retirar los anclajes al dueño anterior

**Modelo sugerido**: **Sonnet** — es una retirada mecánica con un guardarraíl; el criterio ya está
decidido.

> **Nuevo el 2026-09-07**, al elegir la variante B. Con la variante A no hacía falta: el nombre
> acababa siendo el mismo. Con B cambia el dueño, y el repositorio se nombra a sí mismo en seis
> sitios. Va **después de REPO.1**, porque hasta que el repositorio no está en la organización el
> guardarraíl no puede estar verde.

```
# PROMPT REPO.4 (RED/GREEN) — El repositorio deja de nombrar a su dueño anterior
# Deploy: n/a

## Por que
Medido el 2026-09-07: seis sitios del arbol escriben `ModestoFabra`, y ninguno es codigo de
negocio. Cuatro son ficheros vivos que un lector nuevo consulta, y dos son documentacion:

  .github/CODEOWNERS                      14 entradas a @ModestoFabra
  server/pyproject.toml                   Repository = "https://github.com/ModestoFabra/..."
  mcp_server/pyproject.toml               idem
  CONTRIBUTING.md                         la tabla de §«Donde trabajas» nombra el principal
  docs/DESPLIEGUE_PROTOTIPO_GCP.md §177   la condicion de WIF, con el nombre viejo
  planificacion/PLAN_DESARROLLO.md        dos menciones de contexto

`deploy.yml` NO lleva el nombre: lee el proveedor de una variable. Comprobado.

## Que hacer
1. CODEOWNERS: a un equipo de la organizacion, no a una persona. Es el cambio con mas fondo del
   prompt —una persona no es un mantenedor sostenible para un repositorio institucional— asi que
   el equipo tiene que existir antes (paso 0 de REPO.1).
2. Los dos `Repository =` de los `pyproject.toml`, al nombre nuevo.
3. `CONTRIBUTING.md`: la tabla de §«Donde trabajas» pasa a nombrar el principal en la
   organizacion. **OJO con no romper lo que esa seccion dice**: la regla es que NO hay fork
   privilegiado, «incluida la universidad donde nacio». Que el principal viva en la organizacion
   de la UJI **no le da privilegio**, y el texto tiene que seguir diciendolo — si no, la
   gobernanza se lee como que la UJI dirige.
4. `docs/DESPLIEGUE_PROTOTIPO_GCP.md` §177: la condicion de WIF, con el nombre nuevo. Y el
   `principalSet`, que ese documento no menciona y deberia: son DOS anclajes, no uno.
5. `planificacion/PLAN_DESARROLLO.md`: las dos menciones de contexto.
6. NO se toca `planificacion/HISTORIAL.md` ni los planes de fase cerrados: son registro.

## Tests (RED primero)
- RED: ningun fichero vivo escribe `ModestoFabra`. El barrido excluye `HISTORIAL.md`,
  `planificacion/fase1/` y `docs/` marcados como instantanea fechada — la misma distincion
  registro/activo que ya usa `test_repo3_el_indice_de_docs_no_miente.py`.
- RED: `CODEOWNERS` no asigna a un usuario individual (`@usuario`), sino a un equipo
  (`@org/equipo`). Es lo que impide que la retirada se haga cambiando un nombre de persona por
  otro.

## Criterio de done
- [ ] Los seis sitios, al nombre nuevo, y el guardarrail verde
- [ ] CODEOWNERS a un equipo
- [ ] `CONTRIBUTING.md` sigue diciendo que no hay fork privilegiado
- [ ] `docs/DESPLIEGUE_PROTOTIPO_GCP.md` documenta LOS DOS anclajes de WIF
```

---

### Prompt REPO.6 (RED/GREEN) — La revisión del contenido antes de abrirlo

**Modelo sugerido**: **Opus** — hay una decisión de criterio dentro (qué se hace con una deuda de
seguridad viva que no se puede publicar pero tampoco perder) y un guardarraíl que hay que diseñar
para que no se dispare con su propia documentación, cosa que en este bloque ya ha pasado tres veces.

> **Nuevo el 2026-09-16**, a petición del usuario: «no sé si hay algún otro aspecto del contenido
> del repo actual que convendría revisar antes de hacerlo público». La purga del historial cerró
> **de dónde viene** el repositorio; esto mira **qué contiene hoy**, que es lo otro que se publica
> al cambiar la visibilidad y que ningún bloque anterior había barrido entero.
>
> **El hallazgo que justifica el prompt por sí solo no es un fichero, es un guardarraíl.** REPO.5
> puso un test para que `docs/` no publicara los valores de esta instalación, y su patrón escribe
> la IP como `34-175-38-129`, **con guiones** —la forma del host provisional de entonces—. El
> documento la escribe `34.175.38.129`, con puntos. El test lleva desde el 07-09 **pasando en
> verde sin mirar la IP**, que es la avería que este proyecto persigue en todas partes. No se
> encontró ejecutando el test —está verde— sino barriendo el contenido a mano.
>
> **Y una decisión de criterio que el prompt no puede tomar solo.** `PROJECT_STATE.md` nombra a
> seis personas con su correo institucional y dice que sus seis cuentas son superadministradoras
> de producción **compartiendo una contraseña que no pueden cambiar**. Medido el 2026-09-16: la
> deuda **sigue viva** —«sólo entonces retirar los seis `SuperAdminAccount`», pendiente de una
> persona—, así que no vale reescribirla como resuelta. Publicarla es a la vez dato personal y el
> mapa de qué atacar. Pero borrarla del cursor sería perder una deuda de seguridad abierta, que
> es peor.

```
# PROMPT REPO.6 (RED/GREEN) — Lo que contiene el repositorio el dia que se abre
# Deploy: n/a

## Por que
La purga verifico que el historial no arrastra los 92 volcados. Eso cierra de donde VIENE el
repositorio. Falta lo que CONTIENE: al poner `Public` se publica el arbol de trabajo entero, y eso
no lo habia barrido ningun bloque. Medido el 2026-09-16 sobre los 1525 ficheros versionados.

## Los cinco hallazgos, medidos

1. **`planificacion/PROJECT_STATE.md` publica seis correos institucionales reales** —los seis
   probadores del piloto— **y ademas dice que esas seis cuentas son superadministradoras de
   produccion con una contrasena compartida que no pueden cambiar**. Es dato personal y es el mapa
   de que atacar. Y la deuda SIGUE VIVA: la retirada de los seis `SuperAdminAccount` esta
   pendiente de una persona.

   `PROJECT_STATE.md` **no es registro**. La distincion de REPO.3/REPO.4/REPO.5 es entre lo que
   cuenta lo que paso —`HISTORIAL.md` y `planificacion/fase1/`, que se conservan— y lo que un
   lector consulta como verdad presente. El cursor es lo segundo.

2. **El guardarrail de REPO.5 no mira la IP.** `_VALORES_DE_ESTA_CASA` busca `34-175-38-129` (con
   guiones) y `docs/DESPLIEGUE_PROTOTIPO_GCP.md:307` la escribe `34.175.38.129` (con puntos). El
   test pasa en verde con la IP de produccion dentro desde el 2026-09-07.

3. **`server/my_errores.txt`**: 90 KB, UTF-16, un volcado de pytest del 2026-05-02 con rutas
   `C:\Users\fabra\...`. Es literalmente lo que `_local/README.md` dice que no va al repositorio.

4. **Siete scripts que no puede ejecutar nadie**: `scripts/audit_translations.py`,
   `check_duplicates.py`, `debug_audit.py`, `find_fragmentation.py`, `find_root_keys.py`,
   `find_second_level_keys.py` y `find_specific_keys.py`. Los siete abren
   `c:\Users\fabra\Documents\AutomatIA\translations.json`, que no esta en este repositorio y
   pertenece a la app NiceGUI retirada el 2026-09-04.

5. **Falta `CODE_OF_CONDUCT.md`**. Es lo unico del juego estandar que no esta: LICENSE, README,
   CONTRIBUTING, SECURITY, DCO, CODEOWNERS y las plantillas de issue y PR si estan.

## Que hacer

1. **La deuda de las seis cuentas se queda; las seis identidades, no.** Reescribir el aviso de
   `PROJECT_STATE.md` para que siga diciendo **que la deuda existe, que sigue abierta, cuantas
   cuentas son, que poderes tienen y que comparten contrasena** —eso es lo que hace que no se
   olvide— y que **no diga quienes son**. La lista nominal va a `_local/`, que es exactamente para
   lo que existe. Mismo tratamiento a cualquier otra aparicion en la superficie viva.

   NO se toca `HISTORIAL.md` ni `planificacion/fase1/`: son registro.

2. **Arreglar el patron de REPO.5** para que cace la IP en las dos formas, y dejar
   `docs/DESPLIEGUE_PROTOTIPO_GCP.md` con marcador. Ojo al §3.sexies: ahi la IP aparece en una
   frase de procedencia («el registro A de normativa.uji.es a … aparecio el 2026-09-02»), asi que
   la sustitucion tiene que dejar la frase con sentido, no cortarla.

3. **Borrar `server/my_errores.txt` y los siete scripts.** Se retira borrando; el historial de git
   es la fuente de verdad del pasado. Comprobar antes que nada los importe.

4. **Anadir `CODE_OF_CONDUCT.md`**: Contributor Covenant 2.1, con un correo de contacto real y
   enlazado desde `CONTRIBUTING.md` y `README.md`.

## Lo que NO hace este prompt, y por que se dice
- **No toca el numero de proyecto ni la IP en `HISTORIAL.md` ni en `planificacion/fase1/`.**
  REPO.5 decidio que son registro y que generalizar una procedencia de medicion la destruye. Se
  escribe aqui para que no se replantee cada vez que alguien los encuentre.
- **No toca los ~190 correos `@uji.es` de los tests** (`root@`, `x@`, `persona-manual@`): son
  sinteticos y no nombran a nadie.
- **No cambia la visibilidad del repositorio.** Eso es decision del usuario y va despues.

## Tests (RED primero)
- RED: **ningun fichero de la superficie viva lleva un correo `@uji.es`** que no sea el contacto
  publicado del mantenedor o uno de la lista corta de sinteticos, **cada uno con su razon**.
  Superficie viva = lo versionado menos `HISTORIAL.md`, `planificacion/fase1/` y los directorios de
  tests. Medido: hoy solo fallan las seis de `PROJECT_STATE.md`.
- RED: el patron de REPO.5 caza la IP escrita con puntos, y `docs/` queda limpio con el arreglado.
- RED: `server/my_errores.txt` no esta versionado, y **ningun fichero de `scripts/` lleva una ruta
  absoluta de una maquina concreta**.
- RED: existe `CODE_OF_CONDUCT.md`, lleva un contacto y `CONTRIBUTING.md` lo enlaza.
- **El guardarrail tiene que leer solo lineas de datos, no su propia documentacion.** En este
  bloque ya se ha disparado tres veces contra si mismo: por una frase partida en dos lineas, por
  la palabra `@usuario` dentro de un comentario suyo, y por llevar escrito el nombre que buscaba.
  Si el test se mira a si mismo via `git ls-files`, **se prueba despues de `git add`**: antes da
  falso verde.

## Criterio de done
- [ ] La superficie viva sin correos institucionales de personas, y la deuda de las seis cuentas
      SIGUE dicha en el cursor
- [ ] El guardarrail de REPO.5 caza la IP con puntos, y `docs/` verde
- [ ] `my_errores.txt` y los siete scripts fuera
- [ ] `CODE_OF_CONDUCT.md` existe y esta enlazado
- [ ] Los cinco guardarrailes en verde DESPUES de `git add`
```

---

### Prompt REPO.5 ✅ (RED/GREEN, HECHO el 2026-09-07) — Los documentos de despliegue dejan de llevar los valores reales

**Modelo sugerido**: **Sonnet** — sustitución acotada con un guardarraíl; el criterio está decidido.

> **Nuevo el 2026-09-07**, y **ejecutado el mismo día**. Se planificó «después de REPO.1, para no
> reescribir dos veces los mismos documentos», y **esa dependencia desapareció con la revisión del
> reparto**: `RUNBOOK_REINGESTA.md` dejó de ir al filtro, así que ninguno de los cinco documentos
> de este prompt está en la lista de rutas filtradas. Se adelantó a propósito — su guardarraíl
> impide que la documentación que se escriba durante la espera vuelva a meter valores reales.
>
> No es por secreto: un id de proyecto de GCP no es una credencial. Es por **utilidad** —el
> procedimiento tiene que servir a otra administración, y con los valores de esta casa dentro no
> sirve— y por no publicar el inventario de qué sondear.
>
> **Fueron cinco documentos y no cuatro**: `RUNBOOK_REINGESTA.md` entró al reclasificarse como
> público. Y aparecieron **tres datos que habían dejado de ser ciertos** en
> `DESPLIEGUE_PROTOTIPO_GCP.md`: decía «tres imágenes» (son cuatro desde REG.4), «diez variables»
> (son doce) y **un solo anclaje de WIF** (son dos). Un documento de despliegue que miente en las
> cifras es peor que no tenerlo: quien lo siga creerá que ha terminado cuando le falta algo.

```
# PROMPT REPO.5 (RED/GREEN) — El procedimiento se publica; los valores, no
# Deploy: n/a

## Por que
Medido el 2026-09-07: cinco documentos llevan los valores reales de la instalacion —`uji-teclab`,
`govgenai-prod`, `govgenai-vm`, el numero de proyecto `618806480921`, la IP `34-175-38-129` y
`europe-southwest1`—. `DESPLIEGUE_PROTOTIPO_GCP.md` acumula 22 apariciones; las otras cuatro, unas
pocas cada una: `DECISION_MODELOS_EMBEDDING_RERANKER.md`, `EVOLUCIO_I_ASPECTES_PENDENTS.md`,
`WIDGET_INCRUSTACION.md` y `RUNBOOK_REINGESTA.md` —este ultimo se va al privado en REPO.1, asi
que queda fuera de este prompt—.

Es exactamente lo que el codigo ya resolvio y la documentacion no: identificadores en variables,
no escritos dentro. `deploy.yml` no lleva ninguno.

## Que hacer
1. Sustituir por marcadores que se lean como marcadores: `<PROYECTO_GCP>`, `<INSTANCIA_SQL>`,
   `<REGION>`, `<NUMERO_DE_PROYECTO>`, `<HOST>`. NO por otro valor plausible: un ejemplo que
   parece real se copia y pega.
2. Anadir a `DESPLIEGUE_PROTOTIPO_GCP.md` una tabla de «que valor va en cada marcador y de donde
   sale», que es lo que convierte el documento en reutilizable de verdad.
3. Documentar **los DOS anclajes de WIF** (condicion del proveedor y `principalSet` de la cuenta
   de servicio). Hoy §177 menciona uno, y quien siga el documento se quedaria a medias.
4. NO se toca el historial: `filter-repo --replace-text` sobre 707 commits no se justifica para
   identificadores que no son credenciales. Se dice aqui para que nadie lo replantee.

## Tests (RED primero)
- RED: ningun documento de `docs/` contiene los valores de esta instalacion. La lista de patrones
  vive en el test, y **excluye `HISTORIAL.md` y los planes de fase**, que son registro.
- RED: `DESPLIEGUE_PROTOTIPO_GCP.md` menciona los dos anclajes de WIF, no uno.

## Criterio de done
- [ ] Los cuatro documentos con marcadores, y el guardarrail verde
- [ ] La tabla de marcadores existe y dice de donde sale cada valor
- [ ] Los dos anclajes de WIF documentados
```

---

### Prompt REPO.3 ✅ (RED/GREEN, HECHO el 2026-09-07) — El triaje editorial de `docs/`

**Modelo sugerido**: **Opus** — decide qué se publica y qué no, y algunas instantáneas llevan
asuntos abiertos dentro.

```
# PROMPT REPO.3 (RED/GREEN) — Que instantaneas viajan al repositorio publico
# Deploy: n/a (documentacion)

## Por que
El 2026-08-22, al revisar `docs/` para abrir el repositorio, salieron tres clases de documento y
sólo una se resolvio entonces:

- **La isla AutomatIA** (17 ficheros que describian otro producto) → a cuarentena ese mismo dia.
- **Premisa caducada** (los que razonaban sobre Cloud Run) → prompt D.0.doc, antes de desplegar.
- **Ciertos pero historicos** → esto. Se dejo para aqui a proposito: no estan mal, son
  instantaneas y razonamiento, y decidir si un repositorio publico los quiere es una eleccion
  **editorial** que se toma mejor mirando al publico que va a leerlos.

Y hay un motivo mas para no haberlo hecho antes: algunos llevan **asuntos abiertos** dentro
—`VALORACION_PROYECTO.md` tenia hallazgos con decisiones marcadas como pendientes—, asi que
esto es triar, no borrar a bulto. Borrarlos sin leerlos pierde trabajo por hacer.

## Que hacer
1. Leer y clasificar, uno a uno: `VALORACION_PROYECTO.md`, `AUDITORIA_PRE_DEPLOY.md`,
   `PRUEBAS_PENDIENTES.md`, `CAMBIOS_ARQUITECTURA.md`, `CAMBIOS_PLANIFICACION.md`, los cuatro
   `COMPARATIVA_*.md`, `PLAN_CHATBOTS_E_INGESTA_LOCAL.md` y
   `DECISION_OPENWEBUI_CARCASA_CHAT.md` (una decision **descartada**, que puede seguir siendo
   util precisamente por eso).
2. **Antes de tirar nada, extraer lo que siga abierto** y llevarlo a donde vive el trabajo
   pendiente: `planificacion/PROJECT_STATE.md` o un bloque. Un hallazgo sin resolver no se
   archiva, se traslada.
3. Decidir para cada uno: se queda como instantanea fechada, se resume en el historial y se
   retira, o se va. **Razonar cada retirada en el commit**, no borrar en lote.
4. Unificar `MCP_SERVER.md` y `mcp.md`, que se solapan; el indice ya lo señala.
5. Dejar `docs/README.md` coherente con lo que quede.

## Tests (RED primero)
- RED: `docs/README.md` no enlaza ningun fichero que no exista (indice sin enlaces rotos).
- RED: ningun documento activo referencia uno retirado.

## Criterio de done
- [ ] Los doce clasificados, con la razon de cada retirada en el commit
- [ ] Cero asuntos abiertos perdidos: los que habia, trasladados y citados
- [ ] `MCP_SERVER.md` y `mcp.md` unificados
- [ ] `docs/README.md` sin enlaces rotos
```

---
