---
name: taste-skill
description: >-
  tasteskill v2, the anti-slop frontend skill. Art direction and UI craft for web interfaces and app screens.
  Enforces a strict no-slop house style (anti-AI defaults, no gratuitous gradients, no icon-topped cards,
  no fake vanity numbers) and disciplined typography/spacing craft. Use when designing, restyling, polishing,
  or auditing engineering dashboards, admin screens, consoles, and web components.
---

# Taste Skill (Frontend Craft & Anti-Slop Guidelines)

Art direction, visual discipline, and UI craft distilled into actionable engineering principles.

> **CRITICAL PRECEDENCE INVARIANT:**
> `docs/DESIGN.md` is the single source of truth and authoritative design contract for this repository.
> The IoT Power Monitoring System is a mission-critical, high-density operational electrical monitoring console, NOT a marketing website.
> All telemetry rules, status tokens, 3-phase phase card layouts, relay safety controls, and engineering console constraints in `docs/DESIGN.md` take absolute precedence over generic design directions or consumer landing page conventions.

---

## App Screens vs. Marketing Pages

This repository contains an **App Screen (Engineering Console)**:
- Users work in it: live telemetry monitoring, 3-phase electrical analysis, fault triage, maintenance scheduling, and device auditing.
- Follow the **App Screen Principles**: quiet borders, compact panels, high data density, clear tabular alignments, and subdued tone steps.
- Gradients, decorative glows, floating glass pills, consumer testimonials, and oversized marketing hero blocks are strictly prohibited.

---

## The Anti-Slop House Style

Generic AI-generated interfaces often look like the unconsidered average of thousands of templates: centered headings with small decorative labels, rows of identical icon cards, soft colored gradients, backdrop blur, and floating shadows.

This skill bans those decorative crutches in favor of genuine visual craft:

| Generic AI Slop | Taste Skill / Engineering Discipline |
|---|---|
| Gratuitous background / button gradients | Solid, flat, accessible color fills |
| Shadows and glows on resting elements | Tone steps between surfaces (`#FFFFFF` on `#F4F6F8`) |
| Floating glassmorphism / backdrop-blur | Clean, grounded panels with crisp borders (`#D7DEE5`) |
| Rows of generic icon-topped cards | Compact tables, structured metrics, or phase cards |
| Tiny tracked all-caps labels ("eyebrows") | Clear sentence-case labels at readable sizes (12–14px) |
| Monospace on standard labels or body | High-quality system sans-serif; `tabular-nums` for numbers |
| Invented vanity numbers / dummy data | Real live telemetry and explicit `unavailable`/`offline` states |
| Decorative blobs, emojis, and icons in tinted squares | Functional electrical symbols, standard status badges, and real data |
| Rainbow chart colors | Standardized 3-phase convention (Phase A/B/C) and semantic tokens |

---

## Laws of the Craft for Operational Consoles

### 1. Typography
- **Single font family:** Rely on the system sans-serif stack or approved clean UI font.
- **Tabular figures:** Always apply `font-variant-numeric: tabular-nums` to numerical measurements, voltages, currents, power, power factor, timestamps, and table columns.
- **Controlled hierarchy:** Limit text sizes to 4–5 intentional steps (Page title 24–28px, Section title 16–20px, Body 14–16px, Secondary/Labels 12–14px). Never render critical status unreadably small.
- **Left alignment:** Keep content and numbers left-aligned or right-aligned for numeric comparison; avoid centered body text in engineering tables.

### 2. Space & Layout
- **Unified grid & alignment:** Use a disciplined 4/8/12/16/24/32px spacing scale. Align left edges across adjacent panels.
- **Dense information hierarchy:** Optimize screen real estate for operational awareness. Avoid vast empty voids or unnecessary spacing sprawl.
- **Equal outer margins:** Ensure balanced gutters (16–24px) without crowding viewport edges.

### 3. Color & Contrast
- **Tone steps over outlines:** Separate background canvas (`#F4F6F8`) and card surfaces (`#FFFFFF`) through subtle tone contrast.
- **Semantic color token discipline:**
  - Normal / Operational: `#237A57`
  - Warning: `#946200`
  - Fault / Critical: `#B42318`
  - Primary / Interactive: `#145DA0`
  - Offline / Unknown: `#596579`
- **Never rely on color alone:** Pair every status color with explicit text status badges and descriptive icons (WCAG 2.2 AA).

### 4. Honest Data & Uncertainty
- **No placeholder illusions:** When a sensor reading is missing, invalid, or communication has failed, explicitly render `"Unavailable"`, `"--"`, or `"Offline"`.
- Never substitute missing physical readings with zeros, simulated values, or decorative approximations without explicit user indication.

### 5. Interactive & Focus States
- **Clear clickability:** Buttons must have unambiguous hover and active states.
- **Unambiguous focus:** Visible `:focus-visible` focus rings for keyboard navigation.
- **Protected actions:** Destructive commands (clearing faults, tripping breakers, physical relay triggers) require explicit multi-step confirmation dialogs.

---

## Review and Audit Workflow

When auditing or refining UI components:
1. **Audit current layout:** Read the component and its callers. Check against `docs/DESIGN.md`.
2. **Strip decorative slop:** Remove unneeded gradients, glows, backdrop-filters, and superfluous icon boxes.
3. **Refine typography:** Enforce `tabular-nums` on numbers, balance measures, and eliminate all-caps labels.
4. **Clarify hierarchy:** Elevate primary operational metrics (Phase Voltage, Active Power, Fault Alerts); subdue static meta-labels.
5. **Verify contrast & accessibility:** Validate minimum 4.5:1 text contrast and accessible focus states.
6. **Preserve application code & contracts:** Never alter backend schemas, API contracts, or hardware definitions during design reviews.
