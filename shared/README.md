# `automatia-shared` — lo poco que de verdad se comparte

Contratos de datos compartidos entre el servidor y quien lo consuma: **DTOs de Pydantic**,
**enumerados canónicos** y las **utilidades de cifrado**. Nada más.

## Qué contiene

| Módulo | Qué hay |
|---|---|
| `automatia_shared.dtos` | Modelos Pydantic de transferencia (`accounts`, `trigger_payloads`) |
| `automatia_shared.enums` | Los enumerados canónicos de la plataforma |
| `automatia_shared.crypto_utils` | Cifrado simétrico de secretos, sobre `cryptography` |

```python
from automatia_shared.dtos import ...
from automatia_shared.enums import ...
```

## Qué contenía, y por qué ya no

Hasta **APER.12** este paquete declaraba también `contracts/`, `core/`, `security/`, `utils/` y
`validators/`. Se retiraron enteros: eran **el 81% de un paquete muerto** heredado de AutomatIA,
sin un solo importador fuera de sí mismos y de sus propios tests. Con ellos se fue `pdfplumber`,
que arrastraba `pillow` y diecinueve avisos de seguridad que desaparecieron **sin actualizar
nada**, simplemente dejando de depender.

Este fichero siguió describiéndolos durante esa PR, con un ejemplo de uso que importaba el
módulo `validators` y habría dado `ModuleNotFoundError` a quien lo copiara. Lo encontró
la revisión automática de la PR #50 y lo corrige **APER.24**. Importa más de lo que parece: es el
`readme` declarado en el manifiesto, o sea que es la documentación que se publica con el paquete.

Si hace falta ver cómo eran aquellos módulos, están en el historial de git, que es la fuente de
verdad del pasado en este repositorio.

## Lo que este paquete NO puede contener

Y la lista sigue vigente, porque es la razón de que exista separado:

- acceso a base de datos;
- llamadas de red o HTTP;
- operaciones de sistema de ficheros;
- secretos o credenciales;
- automatización de navegador;
- cualquier código volátil que cambie con frecuencia en un solo lado.

Lo que se comparte entre dos lados que se despliegan por separado tiene que poder actualizarse
sin coordinarlos, y eso sólo es cierto si es un contrato de datos y no lógica.
