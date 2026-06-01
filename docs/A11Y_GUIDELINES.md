# Guía de Accesibilidad — WCAG 2.2 AA

Este documento describe cómo auditar, mantener y corregir la accesibilidad en el frontend de Gov Gen AI Platform. La suite de tests automatiza la detección de violaciones críticas y serias; las revisiones manuales con lector de pantalla completan la cobertura.

---

## Añadir un test a11y a una nueva pantalla

1. Crea el archivo en `frontend/src/__tests__/a11y/<nombre>.a11y.test.tsx`.
2. Usa el helper `expectNoA11yViolations` del módulo `@/test/a11y`:

```tsx
import { describe, it, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { MiPantalla } from '@/admin/pages/MiPantalla'
import { expectNoA11yViolations } from '@/test/a11y'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

describe('MiPantalla — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <MiPantalla />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await expectNoA11yViolations(container)
  })
})
```

3. Mockea los hooks de React Query o fetch según el patrón de la página.
4. Ejecuta `npm run test:a11y` para verificar localmente antes de hacer commit.

---

## Reglas WCAG 2.2 AA cubiertas automáticamente

El helper `expectNoA11yViolations` ejecuta axe-core con las siguientes reglas activas y falla ante violaciones de impacto **critical** o **serious**:

| Regla axe | Qué verifica |
|-----------|-------------|
| `color-contrast` | Ratio de contraste ≥ 4.5:1 (texto normal) y ≥ 3:1 (texto grande, UI) |
| `label` | Cada `<input>`, `<select>`, `<textarea>` tiene `<label>` asociado |
| `button-name` | Botones con solo icono tienen `aria-label` |
| `link-name` | Links descriptivos (no "haz clic aquí") |
| `aria-required-attr` | Atributos ARIA obligatorios presentes |
| `aria-valid-attr-value` | Valores ARIA válidos según la especificación |
| `duplicate-id` | No hay IDs duplicados en el DOM |
| `html-has-lang` | `<html>` tiene atributo `lang` |
| `image-alt` | Imágenes con `alt` o `role="presentation"` |
| `landmark-one-main` | Exactamente un `<main>` por página |
| `region` | El contenido está dentro de landmarks |
| `tabindex` | No hay `tabindex > 0` |
| `focus-order-semantics` | Orden de foco lógico |

### Reglas que requieren revisión manual

Las siguientes situaciones **no se detectan automáticamente** y deben revisarse con un lector de pantalla (NVDA/VoiceOver) o Lighthouse:

- **Focus visible en estados custom**: CSS con `outline: none` reemplazado por estilos personalizados.
- **Heading order en contenido dinámico**: axe no puede detectar `<h2>` sin `<h1>` si el `<h1>` está en otro componente renderizado fuera del contenedor de test.
- **Tiempo suficiente**: mensajes que desaparecen solos deben durar ≥ 5 segundos (WCAG 2.2.1).
- **Operación con teclado en drag-and-drop**: subir archivos vía teclado (1C.0 dropzones).
- **Nombre accesible de componentes Recharts**: los SVG de gráficos necesitan `<title>` o `aria-label`.

---

## Cómo interpretar y corregir violaciones comunes

### `label` — Input sin etiqueta

```tsx
// ❌ Incorrecto
<input type="email" placeholder="Email" />

// ✅ Correcto
<label htmlFor="email">Email</label>
<input id="email" type="email" />

// ✅ También correcto (cuando no hay espacio para label visible)
<input type="search" aria-label="Buscar" />
```

### `color-contrast` — Contraste insuficiente

Usa el inspector de contraste de DevTools o [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/).

- Texto normal (< 18pt no bold): ratio ≥ **4.5:1**
- Texto grande (≥ 18pt, o ≥ 14pt bold): ratio ≥ **3:1**
- Componentes UI e iconos: ratio ≥ **3:1**

Los tokens de color están en `src/themes/base.css`. Ajusta los valores CSS custom properties para cumplir el ratio.

### `button-name` — Botón sin nombre accesible

```tsx
// ❌ Solo icono sin descripción
<button><TrashIcon /></button>

// ✅ Con aria-label
<button aria-label="Eliminar chatbot">
  <TrashIcon aria-hidden="true" />
</button>

// ✅ Con texto visualmente oculto
<button>
  <TrashIcon aria-hidden="true" />
  <span className="sr-only">Eliminar chatbot</span>
</button>
```

### `landmark-one-main` — Sin `<main>` o con múltiples

Cada página debe renderizar exactamente un `<main>`. Comprueba que el layout de la app lo incluye y que los tests no renderizan múltiples instancias del layout.

### `region` — Contenido fuera de landmark

Envuelve el contenido de la página en `<main>` y secciones significativas en `<section aria-labelledby="...">` o `<nav>`, `<aside>`, etc.

---

## Ejecutar la suite

```bash
# Todos los tests a11y baseline
npm run test:a11y

# Un solo archivo
npx vitest run src/__tests__/a11y/auth-login.a11y.test.tsx

# Con detalle de violaciones
npx vitest run src/__tests__/a11y --reporter=verbose
```

---

## Integración CI

El job `a11y` en `.github/workflows/ci.yml` ejecuta `npm run test:a11y` después de `contract`. Está configurado con `continue-on-error: true` hasta que el prompt 20.2 corrija todas las violaciones baseline. Una vez 20.2 esté verde, se eliminará el `continue-on-error` para que el gate sea obligatorio.
