# MEGIDO Design System

## Architecture

The design system is a **token-first, CSS-variable-bridged** architecture that serves two consumers:

1. **CSS / Tailwind** — via custom properties in `globals.css` (`@theme inline` block), producing utility classes like `bg-megido-primary`, `text-megido-text-heading`, `shadow-megido-card`.
2. **TypeScript / JS** — via typed token objects in `src/design-system/tokens/`, used by Recharts, cva variants, and any runtime logic that needs color or spacing values.

Both consumers reference the **same hex values**. The TypeScript tokens are the source of truth; the CSS custom properties are kept in sync manually (a deliberate choice for Tailwind v4 compatibility, which uses CSS-first theme configuration).

```
src/design-system/
  tokens/
    colors.ts          Core palette + scales (50-950) + semantic aliases
    typography.ts       Font families, type scale, weights, line heights
    spacing.ts          4px base unit, numeric scale, named sizes
    shadows.ts          Elevation levels + component shadows
    borders.ts          Radii, widths, colors
    chart-colors.ts     Chart palettes (primary, categorical, heatmaps)
    index.ts            Barrel re-export + merged theme object + CSS generator
  variants.ts          cva variant definitions (Button, Card, Badge, Text, Input)
  system.md            This file
```

---

## Token Naming Conventions

### CSS Custom Properties

All MEGIDO tokens use the `--megido-` prefix (or `--color-megido-` / `--shadow-megido-` inside the `@theme` block for Tailwind utility generation).

| Pattern | Example | Tailwind class |
|---------|---------|----------------|
| `--color-megido-{name}` | `--color-megido-primary` | `bg-megido-primary` |
| `--color-megido-{scale}-{step}` | `--color-megido-primary-600` | `bg-megido-primary-600` |
| `--shadow-megido-{name}` | `--shadow-megido-card` | `shadow-megido-card` |

### TypeScript Tokens

Tokens follow a nested object structure:

```ts
import { theme } from "@/design-system/tokens";

theme.colors.core.primary          // "#2563EB"
theme.colors.primary[600]          // "#2563EB"
theme.colors.semantic["card-bg"]   // "#FFFFFF"
theme.typography.fontSize.lg       // "1.25rem"
theme.spacing.named.md             // "16px"
theme.shadows.elevation.md         // "0 4px 6px ..."
theme.borders.radius.lg            // "12px"
theme.chartColors.primary          // ["#2563EB", "#1E3A5F", ...]
```

---

## How to Swap Brand Book

To rebrand from MEGIDO Deep Blue to another palette:

1. **Update TypeScript tokens** — Edit the hex values in `src/design-system/tokens/colors.ts`. The `corePalette` object contains the 16 core colors; the `*Scale` objects contain the 50-950 gradients.

2. **Update CSS custom properties** — Mirror the new values in `src/app/globals.css`:
   - `:root` block (shadcn tokens + `--megido-*` properties)
   - `@theme inline` block (`--color-megido-*` for Tailwind utility generation)
   - `.dark` block (dark mode overrides)

3. **Update chart colors** — Edit `src/design-system/tokens/chart-colors.ts` to match the new palette. Ensure categorical colors have sufficient perceptual distance.

4. **Verify** — Run `npm run build` to catch any TypeScript errors, then visually verify the dashboard, charts, and sidebar.

The `generateCssCustomProperties()` function in `tokens/index.ts` can help automate step 2 by producing a flat `Record<string, string>` of all `--megido-*` properties from the TypeScript tokens.

---

## Component Styling Guidelines

### Layered Approach

Components use a three-layer styling strategy:

1. **shadcn/ui base** — The existing shadcn components (`Button`, `Card`, `Badge`, etc.) use shadcn's semantic tokens (`--primary`, `--border`, etc.) which are mapped to MEGIDO colors in `globals.css`.

2. **MEGIDO variants** (`src/design-system/variants.ts`) — Supplementary `cva` definitions that reference `--megido-*` custom properties directly. Use these for custom components or when you need MEGIDO-specific variant combinations not covered by shadcn.

3. **One-off overrides** — Use the `cn()` utility to merge Tailwind classes for component-specific tweaks.

### When to Use Which

| Scenario | Use |
|----------|-----|
| Standard button/card/input | shadcn component (already themed via `globals.css`) |
| Custom status badge | `megidoBadge({ status: "success" })` from variants.ts |
| Chart tooltip card | `megidoCard({ variant: "elevated" })` from variants.ts |
| Heading text | `megidoText({ variant: "heading", size: "2xl" })` |
| Direct Tailwind | `bg-megido-primary-100 text-megido-text-heading` |

### Example Usage

```tsx
import { cn } from "@/lib/cn";
import { megidoCard, megidoBadge, megidoText } from "@/design-system/variants";

function TenderCard({ tender }) {
  return (
    <div className={cn(megidoCard({ variant: "elevated" }))}>
      <h3 className={megidoText({ variant: "heading", size: "lg" })}>
        {tender.name}
      </h3>
      <span className={megidoBadge({ status: "success" })}>
        פעיל
      </span>
    </div>
  );
}
```

---

## RTL Considerations

The app defaults to RTL (`<html lang="he" dir="rtl">` in `layout.tsx`, `direction: rtl` in `globals.css`).

### Key Rules

1. **Use logical properties** — Prefer `ps-4` / `pe-4` (padding-inline-start/end) over `pl-4` / `pr-4`. Tailwind's logical property utilities (`ms-`, `me-`, `ps-`, `pe-`, `rounded-s-`, `rounded-e-`) auto-flip in RTL.

2. **Sidebar shadow** — The sidebar is on the right in RTL. Use `shadows.component.sidebarRtl` (negative X offset) or the CSS variable `--shadow-megido-sidebar-rtl` (not yet in `@theme`; add if needed).

3. **Numeric content** — Wrap numbers, dates, and LTR strings in `.ltr-nums` to prevent RTL reordering:
   ```html
   <span class="ltr-nums">₪1,234,567</span>
   ```

4. **Flex/Grid direction** — `flex-row` automatically reverses in RTL. If you need explicit LTR ordering (e.g., pagination `< 1 2 3 >`), add `dir="ltr"` on the container.

5. **Icons** — Directional icons (arrows, chevrons) should be mirrored. Use `rtl:rotate-180` on icons that point in a direction.

6. **Tables** — Column order should read right-to-left. The most important column goes rightmost (first in visual order for Hebrew readers).

---

## Chart Color Usage Guide

### Palette Selection

| Chart Type | Palette | Import |
|------------|---------|--------|
| Bar / Line / Area (ordered data) | `MEGIDO_CHART_COLORS` | `import { MEGIDO_CHART_COLORS } from "@/design-system/tokens"` |
| Pie / Donut (categorical) | `categoricalColors` | `import { categoricalColors } from "@/design-system/tokens"` |
| Heatmap (warm intensity) | `goldHeatmapScale` | `import { goldHeatmapScale } from "@/design-system/tokens"` |
| Heatmap (cool intensity) | `blueHeatmapScale` | `import { blueHeatmapScale } from "@/design-system/tokens"` |
| Positive vs Negative | `divergingColors` | `import { divergingColors } from "@/design-system/tokens"` |
| KPI indicators | `statusColors` | `import { statusColors } from "@/design-system/tokens"` |
| > 6 categories | `MEGIDO_CHART_COLORS_EXTENDED` | 12 colors, maximized distinction |

### Recharts Example

```tsx
import { MEGIDO_CHART_COLORS } from "@/design-system/tokens";

<BarChart data={data}>
  {categories.map((cat, i) => (
    <Bar
      key={cat}
      dataKey={cat}
      fill={MEGIDO_CHART_COLORS[i % MEGIDO_CHART_COLORS.length]}
    />
  ))}
</BarChart>
```

### Accessibility

- The primary 6-color palette passes WCAG AA contrast against white backgrounds.
- For adjacent bars/slices, maintain at least 2 steps of perceptual distance.
- Always include tooltips and labels; never rely solely on color to convey meaning.

---

## Spacing Quick Reference

| Token | Value | Use Case |
|-------|-------|----------|
| `xs` | 4px | Icon padding, tight gaps |
| `sm` | 8px | Between related items |
| `md` | 16px | Card padding, form gaps |
| `lg` | 24px | Section spacing |
| `xl` | 32px | Major section breaks |
| `2xl` | 48px | Page-level vertical spacing |
| `3xl` | 64px | Hero/splash areas |

Layout constants (sidebar width, topbar height, etc.) are in `spacing.layout`.
