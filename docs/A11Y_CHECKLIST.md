# Checklist de accesibilidad manual — WCAG 2.2 AA

> Complementa la auditoría automatizada con axe-core (`npm run test:a11y`).
> Ejecutar con Lighthouse + lector de pantalla antes de cada release.

---

## Herramientas recomendadas

| Herramienta | Uso |
|-------------|-----|
| **axe DevTools** (extensión Chrome/Firefox) | Auditoría en tiempo real en el navegador |
| **Lighthouse** (Chrome DevTools > Audits) | Score de accesibilidad + recomendaciones |
| **NVDA** (Windows) | Lector de pantalla de referencia en Windows |
| **VoiceOver** (macOS/iOS) | Lector de pantalla en Apple |
| **Colour Contrast Analyser** (TPGi) | Verificación de ratios de contraste |
| **axe-core DevTools** | Tests manuales sobre el DOM real en navegador |

---

## Categoría 1 — Labels y nombres accesibles

### Qué automatiza axe
- `label`, `select-name`, `button-name`, `link-name`, `input-button-name`

### Verificación manual

- [ ] Todo `<input>`, `<select>`, `<textarea>` tiene `<label>` o `aria-label` visible en el lector de pantalla
- [ ] Botones con solo icono anuncian su propósito (no "unlabelled button")
- [ ] Links descriptivos: "Ver detalles del chatbot Demo" en vez de "Ver más"
- [ ] Placeholders NO son el único nombre accesible de un campo

### Pantallas a verificar
- PromptsPage — filtros de la barra lateral
- ChatbotsPage — formulario de creación/edición (modal)
- ClientsPage — formulario de creación/edición (modal)
- LLMDraftPreviewPage — textarea de prompt
- ScriptProposalWizardPage — textarea paso 1

---

## Categoría 2 — Color contrast

### Qué automatiza axe
- `color-contrast` (solo funciona en navegador real, no en jsdom)

### Ratios requeridos
- Texto normal (< 18pt / < 14pt bold): ≥ **4.5:1**
- Texto grande (≥ 18pt / ≥ 14pt bold): ≥ **3:1**
- Componentes UI e iconos informativos: ≥ **3:1**

### Tokens a verificar manualmente (`src/themes/base.css`)

| Token | Sobre fondo | Ratio mínimo |
|-------|-------------|-------------|
| `--foreground` sobre `--background` | — | 4.5:1 |
| `--muted-foreground` sobre `--background` | Labels secundarios | 4.5:1 |
| `--destructive` sobre `--background` | Mensajes error | 4.5:1 |
| `--primary-foreground` sobre `--primary` | Botón primario | 4.5:1 |
| Tier chip verde (`#166534` sobre `#dcfce7`) | TierChip Tier 1 | 4.5:1 |
| Tier chip amarillo (`#854d0e` sobre `#fef9c3`) | TierChip Tier 2 | 4.5:1 |
| Tier chip rojo (`#991b1b` sobre `#fee2e2`) | TierChip Tier 3 | 4.5:1 |

### Cómo verificar
1. Abre Colour Contrast Analyser
2. Usa el eyedropper para capturar texto y fondo
3. Anota el ratio obtenido

---

## Categoría 3 — Heading order y landmarks

### Qué automatiza axe
- `landmark-one-main`, `region`, `heading-order` (parcialmente)

### Verificación manual

- [ ] Cada página tiene exactamente un `<h1>` con el título de la sección
- [ ] La jerarquía h1 → h2 → h3 no salta niveles (no h1 → h3)
- [ ] Con NVDA: lista de encabezados (Insert+F6) muestra el árbol correcto
- [ ] Con NVDA: lista de landmarks (Insert+F7) muestra main, nav, aside relevantes

### Árbol de headings esperado por pantalla

| Pantalla | h1 | h2 | h3 |
|----------|----|----|-----|
| ChatbotsPage | "Chatbots" | nombre chatbot en modal | — |
| ClientsPage | "Organizaciones" | nombre cliente en modal | — |
| PromptsPage | — (ajustar: añadir h1) | selected chatbot/template | — |
| LLMDraftPreviewPage | "Generar informe" | — | — |
| LoginPage | título login | — | — |

> **Deuda detectada**: PromptsPage no tiene `<h1>`. Añadir en 20.3 o en próximo PR.

---

## Categoría 4 — Focus management

### Qué automatiza axe
- `tabindex`, `focus-order-semantics`

### Verificación manual con teclado

- [ ] Navegar por Tab/Shift+Tab completa todos los elementos interactivos sin trampas
- [ ] El foco es visible en todos los estados (no `outline: none` sin reemplazo)
- [ ] Al abrir un modal/drawer, el foco entra dentro del modal
- [ ] Al cerrar un modal/drawer, el foco vuelve al botón que lo abrió
- [ ] DrawerHub (1C.0) trapa el foco correctamente con react-focus-lock
- [ ] El modal de ChatbotsPage trapa el foco (tiene `aria-modal="true"` ✅)
- [ ] El modal de PromptsPage trapa el foco (tiene `aria-modal="true"` ✅ tras 20.2)

### Cómo verificar
1. Pon foco en el botón "Nuevo chatbot"
2. Pulsa Enter — el modal se abre
3. Verifica que Tab mueve el foco dentro del modal (no fuera)
4. Pulsa Escape — el modal se cierra
5. Verifica que el foco vuelve al botón "Nuevo chatbot"

---

## Categoría 5 — ARIA

### Qué automatiza axe
- `aria-required-attr`, `aria-valid-attr`, `aria-valid-attr-value`, `aria-required-children`

### Verificación manual

- [ ] Con NVDA: las regiones de navegación se anuncian con sus etiquetas ("Navegación principal", "Navegación del Hub")
- [ ] `aria-expanded` en acordeones/dropdowns refleja el estado real
- [ ] `aria-current="page"` en el NavLink activo (react-router-dom v6 lo añade automáticamente ✅)
- [ ] Widgets vivos (`aria-live`) anuncian los cambios de estado de bloque (WorkspaceEditor ✅)
- [ ] Modales tienen `aria-labelledby` apuntando al título correcto

---

## Categoría 6 — Imágenes y media

### Qué automatiza axe
- `image-alt`, `svg-img-alt`

### Verificación manual

- [ ] Iconos Lucide son decorativos → `aria-hidden="true"` (Lucide React lo añade por defecto en v1+)
- [ ] Si un icono Lucide transmite información (p. ej. icono de error rojo), añadir `<title>` o `aria-label` explícitos
- [ ] Gráficos Recharts: añadir `aria-label` o tabla de datos alternativa para usuarios de lectores de pantalla

---

## Categoría 7 — Forms y errores

### Qué automatiza axe
- `label`, `form-field-multiple-labels`

### Verificación manual

- [ ] Mensajes de error están asociados al input por `aria-describedby` (no solo por proximidad visual)
- [ ] Campos requeridos tienen `aria-required="true"` o texto "(obligatorio)" — no solo asterisco rojo
- [ ] react-hook-form: asegurarse de que `{errors.field.message}` tiene `id` referenciado por `aria-describedby` en el input

### Patrón correcto con react-hook-form

```tsx
<label htmlFor="name">Nombre *</label>
<input
  id="name"
  aria-required="true"
  aria-describedby={errors.name ? 'name-error' : undefined}
  {...register('name')}
/>
{errors.name && (
  <p id="name-error" role="alert" className="text-destructive text-xs">
    {errors.name.message}
  </p>
)}
```

### Pantallas con formularios a revisar
- ChatbotsPage — modal crear/editar chatbot (react-hook-form)
- ClientsPage — modal crear/editar organización (react-hook-form)
- LLMConfigsPage — formulario configuración LLM (react-hook-form)

---

## Proceso de auditoría recomendado antes de release

1. `npm run test:a11y` — suite automatizada (debe pasar 100%)
2. Lighthouse en Chrome DevTools sobre las 9 pantallas principales (target: score ≥ 90)
3. Tabular con teclado las 3 páginas más interactivas (ChatbotsPage, PromptsPage, ScriptWizardPage)
4. NVDA + Chrome sobre LoginPage y ChatbotsPage (formulario crítico)
5. Verificar contraste de los tier chips (Tier 1/2/3) y botones primary con Colour Contrast Analyser
