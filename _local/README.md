# `_local/` — trabajo de esta máquina, fuera del repositorio

Todo lo que hay en esta carpeta está en `.gitignore` **menos este fichero**. Es el sitio para lo
que hace falta para trabajar y no es código fuente:

- **Ficheros de entrada de pruebas**: el `.md` de un informe real, el CSV de saldos, el PDF que
  se le da al asistente para preguntarle cosas. Son datos de la institución y no tienen por qué
  estar en un repositorio que se va a abrir.
- **Salidas y volcados**: informes generados, DOCX descargados, resultados de una pasada de
  tests que se quiere conservar un rato.
- **Notas de trabajo** de una sesión concreta, que no son documentación del proyecto.

## Por qué existe

Antes esto caía en la raíz, y la raíz es lo primero que ve quien abre el repositorio. Con el
tiempo se acumularon volcados de errores, resultados de tests de hace meses y páginas web
capturadas, mezclados con los ficheros que de verdad describen el proyecto.

## Lo que **no** va aquí

- **Documentación del proyecto** → `docs/`.
- **Scripts que se usan más de una vez** → `scripts/`, versionados.
- **Secretos**: siguen yendo en `server/.env`, que ya está ignorado. Esta carpeta no está
  cifrada ni protegida; simplemente no se sube.

Como está ignorada, lo que pongas aquí **no tiene copia en el repositorio**. Si algo importa,
que viva en otro sitio.
