/**
 * Qué color de la paleta alimenta qué variable del panel (REV.9).
 *
 * Hasta REV.9 la cascada del servidor **no pintaba el panel**: su único consumidor era el
 * logotipo (`useMarca`), y los colores salían de las variables escritas a mano en `index.css`.
 * Dos fuentes de verdad que no se hablaban, y la consecuencia visible era que se podía cambiar
 * cualquier color en «Identidad visual» y no cambiaba nada.
 *
 * Los nombres de la izquierda son campos de `ThemeColors`; los de la derecha, las variables que
 * consume Tailwind. `index.css` **sigue ahí y sigue siendo necesario**: es lo que se ve mientras
 * la cascada está en vuelo y cuando no hay ningún tema. Un test del servidor
 * (`test_rev9_la_paleta_es_una.py`) exige que los valores por omisión del contrato sean
 * exactamente los de ese fichero, así que aplicar la cascada sobre una instalación sin tema no
 * cambia nada de lo que se ve.
 */
export const VARIABLE_POR_COLOR: Readonly<Record<string, string>> = {
  primary: '--primary',
  primaryForeground: '--primary-foreground',
  accent: '--accent',
  accentForeground: '--accent-foreground',
  ring: '--ring',
  sidebar: '--sidebar',
  sidebarForeground: '--sidebar-foreground',
  sidebarPrimary: '--sidebar-primary',
  sidebarAccent: '--sidebar-accent',
  sidebarAccentForeground: '--sidebar-accent-foreground',
  sidebarBorder: '--sidebar-border',
}

/**
 * Escribe en `:root` los colores que trae la cascada, y **sólo esos**.
 *
 * Lo que el tema no define no se toca: así el valor de `index.css` sigue mandando en vez de
 * quedarse en blanco, que es la diferencia entre «este nivel no lo configura» y «este nivel lo
 * pone vacío». Devuelve las variables que ha escrito, que es lo que se puede comprobar.
 */
export function aplicarColoresDelPanel(
  colores: Record<string, unknown> | undefined,
  raiz: HTMLElement = document.documentElement,
): string[] {
  if (!colores) return []
  const escritas: string[] = []
  for (const [campo, variable] of Object.entries(VARIABLE_POR_COLOR)) {
    const valor = colores[campo]
    if (typeof valor !== 'string' || !valor.trim()) continue
    raiz.style.setProperty(variable, valor)
    escritas.push(variable)
  }
  return escritas
}
