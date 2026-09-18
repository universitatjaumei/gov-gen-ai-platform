# `paquete-funcion-demo` — cómo empaqueta una función un equipo externo

Este directorio **no se instala en la suite**, y eso es una decisión, no un olvido.

## Por qué está aquí sin instalarse

Los tests de FUN.5 (`server/tests/modules/redaccion/test_fun5_paquete.py`) simulan
`importlib.metadata` en vez de instalar una distribución de verdad. El precedente es de PLG, que
ya lo midió para los perfiles de grafo y lo dejó escrito en
`agents_hub/agent/public_graphs/plugins.py`:

> Simular un paquete roto o dos que chocan instalando distribuciones de verdad sería lento y
> frágil; lo que importa comprobar es el comportamiento del cargador ante lo que
> `importlib.metadata` devuelva.

A eso se suman dos cosas propias de este caso. Un `pip install -e` dentro de la suite añadiría
una distribución al entorno del desarrollador que ninguna ejecución retira, y los escenarios que
de verdad importan —contrato incoherente, versión no semver, mayor distinto del anclado,
desinstalación— exigirían **cinco** distribuciones distintas o reinstalaciones a mitad de la
suite. Lo que sí es real en los tests es el `FuncionEmpaquetada` y su `ContratoFuncion`, que es
donde estaba el riesgo: los valida el mismo validador de FUN.2 que valida una función de
autoservicio.

Lo que este directorio aporta es **el ejemplo completo y correcto** para el primer equipo que
empaquete una función: el `pyproject.toml` con su *entry point* y el módulo con su descriptor.
Se copia, se cambia el nombre y se instala en el despliegue.

## Los tres ficheros

- `pyproject.toml` — la declaración del *entry point* en el grupo `govgenai.funciones`.
- `paquete_funcion_demo/__init__.py` — el descriptor y su `run`.
- Este README.

## Instalarlo de verdad, cuando haga falta

Para probar el descubrimiento contra un paquete instalado (una comprobación de despliegue, no de
suite):

```bash
uv pip install -e server/tests/fixtures/paquete_funcion_demo
```

Al arrancar el servidor, el log dirá `Funciones empaquetadas: 1 instaladas (1 nuevas, 1 versiones
nuevas, 0 fuera de servicio)` y la función aparecerá en el catálogo con nivel 3, su distribución y
su versión. Para quitarlo: `uv pip uninstall paquete-funcion-demo`, y al arrancar de nuevo su
versión pasa a `no_instalada` **sin borrarse** — hay manifiestos que la citan.

## Una advertencia honesta para el primer equipo externo

Este ejemplo importa `ContratoFuncion`, `FuncionEmpaquetada` y `ExtractionResult` **de
`server.app`**, que es el paquete de la plataforma. Un equipo de fuera no tiene eso instalado.

Es una consecuencia conocida de la decisión de FUN.5: el contrato público vive en
`server/app/modules/redaccion/funciones_paquete.py` porque hoy tiene **un** consumidor, y
publicar un SDK para un solo consumidor es prometer una superficie estable antes de saber cuál
es. Cuando aparezca el segundo —REG ya tiene su propio patrón de extensión— esos tres nombres se
mueven a un paquete `govgenai-sdk` ligero y este ejemplo pasa a importarlos de ahí, sin que
cambie nada más: ni el grupo del *entry point*, ni la forma del descriptor, ni el anclaje.

Hasta entonces, un equipo que quiera empaquetar una función necesita la plataforma como
dependencia de desarrollo. Está escrito aquí para que no se descubra a mitad del primer intento.
