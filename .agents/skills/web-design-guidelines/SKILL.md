---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review UI files for compliance with Web Interface Guidelines.

> **CRITICAL PRECEDENCE INVARIANT:**
> `docs/DESIGN.md` is the single source of truth and authoritative design contract for this repository.
> The IoT Power Monitoring System is a high-density, mission-critical engineering console, not a marketing website.
> If any generic web design rule conflicts with `docs/DESIGN.md` (such as high-density 3-phase telemetry grids, industrial status badge vocabulary, or electrical safety gates), `docs/DESIGN.md` takes precedence.

---

## How It Works

1. Read the specified UI files (or prompt for files/pattern).
2. Check against the core interface rules below.
3. Validate against `docs/DESIGN.md` to ensure domain requirements are respected.
4. Output findings in the concise `file:line` format.

---

## Rules

### Accessibility

- Icon-only buttons must have an accessible label (`aria-label` or visually hidden text).
- Form controls must have associated `<label>` (using `htmlFor`) or `aria-label`.
- Interactive elements must have keyboard handlers (`onKeyDown`/`onKeyUp`) if non-native.
- Use `<button>` for actions, `<a>`/`<Link>` for navigation (never `<div onClick>`).
- Images must have `alt` attributes (use `alt=""` for purely decorative images).
- Decorative icons must have `aria-hidden="true"`.
- Async status updates (toasts, alerts, banner updates) must use appropriate live regions (`aria-live="polite"`).
- Prefer semantic HTML (`<button>`, `<a>`, `<label>`, `<table>`) over ARIA role overrides.
- Maintain hierarchical headings (`<h1>`–`<h6>`) without skipping levels; include skip links for main dashboard views.
- Ensure all media controls have complete keyboard support.

### Focus States

- Interactive elements must show a visible focus indicator: use `:focus-visible` (avoid generic focus rings on click).
- Never use `outline: none` or Tailwind `outline-none` without providing an accessible `:focus-visible` replacement.
- Use `:focus-within` to group focus for composite or segmented controls.
- Sticky headers, floating toolbars, and modal overlays must never obscure the currently focused element.

### Forms & Controls

- Inputs must have appropriate `autocomplete` attributes and meaningful `name` attributes.
- Use appropriate semantic input types (`email`, `number`, `tel`, `url`) and `inputmode`.
- Never block paste operations (`onPaste` + `preventDefault`).
- Form labels must be clickable (`htmlFor` referencing the input ID or wrapping the input control).
- Disable spellcheck for technical identifiers, codes, and emails (`spellCheck={false}`).
- Checkbox and radio controls must share a single hit target with their labels (eliminate dead zones).
- Submit buttons must remain enabled until submission initiates, followed by an inline progress/loading spinner.
- Display validation errors inline adjacent to their fields; move focus to the first error upon invalid submission.
- Form inputs without values must never trigger unexpected state exceptions.
- Provide confirmation warnings before navigating away from forms with unsaved changes.

### Animation & Motion

- Always respect user motion preferences via `@media (prefers-reduced-motion: reduce)`.
- Restrict animations to compositor-friendly properties: `transform` and `opacity`.
- Never use `transition: all`; explicitly enumerate animated properties.
- Ensure animations are interruptible and do not block subsequent user interaction.
- Critical electrical fault alerts and telemetry status updates must update immediately without distracting or delayed animations.

### Typography

- Use typographical ellipsis `…` rather than three periods `...`.
- Use curly quotation marks `“` `”` for display text rather than straight quotes `"`.
- Use non-breaking spaces where appropriate (e.g., `230&nbsp;V`, `50&nbsp;Hz`, `10&nbsp;kW`).
- Display loading states with standard ellipsis conventions (`"Loading…"`, `"Saving…"`).
- Always enable tabular figures (`font-variant-numeric: tabular-nums`) for electrical readings, timestamps, counters, and comparison tables.
- Use `text-wrap: balance` or `text-wrap: pretty` on headings to avoid awkward orphans/widows.

### Content Handling & Layout

- Text containers must gracefully handle overflow: `truncate`, `line-clamp-*`, or `break-words`.
- Flex children intended to truncate require `min-w-0` to avoid layout blowout.
- Implement explicit empty states (e.g., "No active faults", "No devices found") rather than broken or collapsed layouts.
- Guard against null, undefined, or empty arrays without crashing or showing blank gaps.

### Performance

- Virtualize large datasets (>50 items) or apply `content-visibility: auto`.
- Avoid layout thrashing: do not interleave DOM reads (`getBoundingClientRect`, `offsetHeight`) with DOM writes.
- Keep controlled input keystroke handlers lightweight.
- Provide explicit `width` and `height` dimensions on images and SVG icons to prevent Cumulative Layout Shift (CLS).

### Navigation & State

- Reflect significant state (active device, selected tab, filter criteria) in URL query parameters.
- Links must use standard anchor navigation (`<a>`/`<Link>`) supporting Ctrl/Cmd+click and middle-click.
- Destructive actions (incident resolution, relay triggers, user deletion) require explicit confirmation dialogs.

### Dark Mode & Theming

- Apply `color-scheme: dark` (or light) on `<html>` to ensure native browser controls match the active theme.
- Ensure `<meta name="theme-color">` aligns with the dashboard surface background.
- Guarantee sufficient WCAG AA contrast ratios (minimum 4.5:1 for normal text, 3:1 for large text and UI components).
- Never communicate status solely through color; pair color with text labels and distinct icons.

### Anti-Patterns to Flag

- `user-scalable=no` or `maximum-scale=1` disabling viewport zoom.
- `onPaste` with `preventDefault`.
- `transition: all`.
- `outline: none` without a `:focus-visible` replacement.
- `<div>` or `<span>` used as buttons without keyboard or ARIA support.
- Hardcoded timestamps or currencies without `Intl` formatting.
- Unlabeled form fields or icon buttons without `aria-label`.
- Invented or simulated data presented as real live readings.

---

## Output Format

Group findings by file using the concise `file:line` format:

```text
## frontend/src/components/FaultsList.tsx

frontend/src/components/FaultsList.tsx:42 - icon button missing aria-label
frontend/src/components/FaultsList.tsx:68 - transition: all → list properties explicitly
frontend/src/components/FaultsList.tsx:112 - missing tabular-nums on timestamp column

## frontend/src/components/RelayControls.tsx

frontend/src/components/RelayControls.tsx:25 - button lacks visible :focus-visible outline
frontend/src/components/RelayControls.tsx:84 - destructive action requires confirmation dialog

## frontend/src/components/Header.tsx

✓ pass
```

State the issue and exact location concisely. Skip unnecessary exposition.
