/** Abrevia recuentos de tokens para la tabla y los banners: 1200 → «1.2 k». */
export function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)} k`
  return String(n)
}
