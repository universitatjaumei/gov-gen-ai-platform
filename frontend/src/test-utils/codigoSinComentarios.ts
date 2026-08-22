/**
 * Quita los comentarios de un fichero de código antes de buscar patrones en su texto.
 *
 * Hace falta porque los guardarraíles de este proyecto **explican en un comentario qué
 * están impidiendo**, y un test que busca la cadena prohibida en el fichero entero se
 * dispara con su propia explicación. Es el mismo problema que ya documentó
 * `test_theme_persistence.py` en el backend: «se comprueba el módulo cargado y no el texto
 * del fichero, porque buscar la cadena obligaría a no poder contarla».
 *
 * Ocurrió de verdad: al retirar `@/assets/logo-uji.png` de `AppLayout`, el comentario que
 * contaba por qué se retiraba volvió a poner en rojo a `assetsVersionados.test.ts`.
 *
 * `//` solo se corta cuando no va detrás de `:`, para no partir un `https://…` que esté
 * dentro de una cadena.
 */
export function codigoSinComentarios(contenido: string): string {
  return contenido
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1')
}
