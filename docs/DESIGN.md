# Design System

**Purpose:** Single source of truth for dashboard visual and interaction patterns. The UI is an engineering monitoring console, not a marketing site.

## 1. Visual direction

- Calm, information-dense, operational and legible.
- Prioritize current status, phase comparison, faults and timestamps.
- Use consistent alignment and units; avoid decorative gradients, oversized hero sections, glass effects and gratuitous animation.
- Color communicates state but never carries meaning alone.
- Prefer compact tables and charts for engineering data; reserve cards for summary values.

## 2. Design principles

1. **Status first:** show whether data is normal, abnormal, stale, offline or unavailable.
2. **Compare phases easily:** R/Y/B values share the same layout and units.
3. **Trustworthy data:** every reading includes a timestamp and quality/staleness cue.
4. **Progressive detail:** overview first, then device/fault details.
5. **Safe controls:** destructive or physical commands require explicit intent, permission and confirmation.
6. **Honest uncertainty:** missing values are shown as unavailable, never silently converted to zero.
7. **Consistent language:** use the backend's canonical status/fault vocabulary.

## 3. Color tokens

Use CSS variables or the project's existing theme token mechanism. These are proposed defaults and can be adjusted after a visual review.

| Token | Value | Use |
|---|---|---|
| App background | `#F4F6F8` | Main canvas |
| Surface | `#FFFFFF` | Cards, panels, tables |
| Surface muted | `#EEF2F5` | Secondary panel/background |
| Text primary | `#17212B` | Main text |
| Text secondary | `#526170` | Supporting labels |
| Border | `#D7DEE5` | Dividers and outlines |
| Primary | `#145DA0` | Primary actions, links, selected navigation |
| Normal | `#237A57` | Normal state with text/icon |
| Warning | `#946200` | Warning state |
| Fault | `#B42318` | Fault/critical state |
| Info | `#2457A7` | Informational state |
| Offline/unknown | `#596579` | Offline, unknown or communication issue |

Do not hard-code colors in individual components when a shared token exists. Validate contrast for actual text sizes.

## 4. Typography

- Use the existing system font stack unless the repository already establishes a consistent font.
- Page title: 24–28 px, semibold.
- Section title: 16–20 px, semibold.
- Body: 14–16 px.
- Labels and metadata: 12–14 px; never make critical status unreadably small.
- Numerical readings: use tabular numerals where available; keep units adjacent to values.
- Use sentence case; avoid all-caps labels except phase identifiers and short status tags.

## 5. Spacing and layout

- Base spacing scale: 4, 8, 12, 16, 24, 32 px.
- Main content max width: flexible; use full available width for tables/charts, with 16–24 px page gutters.
- Desktop: persistent navigation rail/sidebar plus content area if that matches the existing app shell.
- Tablet: collapsible navigation and two-column summary layout.
- Mobile: one-column summary cards, horizontally scrollable charts/tables only when unavoidable; keep fault severity, phase and timestamp visible.
- Use consistent panel padding (16–20 px) and 8–12 px gaps within related controls.

## 6. Reusable components

- **App shell:** navigation, page title, user/role menu, API/connectivity status where available.
- **Status badge:** text + icon; variants normal, warning, fault, sensor/communication error, offline, pending.
- **Phase card:** phase label, voltage, current, power, energy, frequency, PF when available, timestamp/quality and phase status.
- **Metric value:** value, unit, label, optional trend; supports unavailable/stale states.
- **Data table:** sortable only where needed, clear column headings, empty state, pagination if dataset size requires it.
- **Time-range selector:** fixed sensible ranges first; custom range only where implemented.
- **Chart panel:** title, units, selected range, legend, accessible summary and empty/error state.
- **Fault row/detail:** type, severity, phase, detected time, measured/expected value, status and actions permitted for current user.
- **Timeline item:** timestamp, actor/source, action and concise detail.
- **Form field:** visible label, helper text when useful, inline validation and focus indicator.
- **Confirmation dialog:** required for high-impact actions such as closing an incident or issuing a physical relay command.
- **Notification/toast:** concise success/failure feedback; persistent failures must also be visible in the page.

## 7. Navigation

Primary navigation should be limited to:
- Overview
- Locations / Devices
- Faults
- Maintenance
- Notifications
- Administration (role-gated)
- Audit (role-gated)

Hide links the current user cannot use, but always enforce permissions on the backend too. Current route inventory should be checked before renaming or replacing existing routes.

## 8. Forms and interaction

- Use explicit labels, units and allowed ranges.
- Preserve form values after recoverable server errors.
- Disable submit while a request is in progress; prevent accidental double submission.
- Display field-level validation where possible and a form-level summary for server errors.
- Use confirmations for irreversible or physical actions.
- Never show “Relay ON” as confirmed from a database command alone; show requested/commanded state and device-confirmed state separately.
- Use keyboard-accessible controls and visible focus outlines.
- Do not use hover as the only way to reveal information or actions.

## 9. Loading, empty, error and stale states

- Loading: restrained skeletons or progress indicator matching final layout.
- Empty: explain why content is absent and what can be done next; do not fill with invented demo readings.
- Error: human-readable message, retry action where safe, and no raw stack traces.
- Stale: show last updated timestamp and a clear stale/offline label.
- Partial telemetry: render valid phases while explicitly marking missing/invalid phases.
- No faults: “No active faults” plus last update/evaluation time.
- Permission denied: explain access limitation without exposing data.
- Relay pending/timeout: show command status distinctly from actual state.

## 10. Charts and tables

- Every axis has a label and unit.
- Use consistent time zone display and disclose the selected range.
- Avoid smoothing or interpolation that could imply measurements were taken when they were not.
- Make phase series distinguishable by label and line style as well as color.
- Tooltips show timestamp, value and unit.
- Tables should show a clear empty state and avoid excessive columns on mobile.
- Energy is cumulative; do not plot it as an instantaneous rate without explicit conversion.

## 11. Interactions and motion

- Keep transitions subtle (roughly 120–180 ms) for menus and dialogs.
- Do not animate live values continuously; update them without distracting motion.
- Respect reduced-motion preferences.
- No animation may delay or obscure fault warnings or command results.

## 12. Responsive behavior

- Desktop/laptop: show all three phase cards in one row when space permits; trends and faults below.
- Tablet: use a two-column grid, with the third phase wrapping naturally.
- Mobile: stack phase cards and summary metrics; keep active fault count and system status near the top.
- Navigation collapses into an accessible menu.
- Forms use full-width fields on narrow screens.
- Charts preserve readable axes; allow horizontal scrolling only when no responsive alternative is practical.

## 13. Accessibility

- Target WCAG 2.2 AA where practical.
- Maintain text/background contrast; do not rely on red/green alone.
- Use semantic headings, buttons, form labels and table headers.
- Provide keyboard navigation and visible focus.
- Announce meaningful asynchronous status changes to assistive technology without announcing every telemetry refresh.
- Include text alternatives/summaries for charts.
- Use sufficiently large touch targets on mobile.
- Errors identify the field and how to correct it.
- Never communicate fault severity through color alone.

## 14. Page-level guidance

### Overview
System status and last update first; three phase cards; total power/energy and temperature; trends; recent active faults.

### Location/device explorer
Clear breadcrumb: College → Block → Floor → Device. Show inactive/unassigned states. Device list shows name, unique ID, location and last seen.

### Device detail
Device health and timestamp; phase-wise values; trend controls; telemetry quality/communication issues; no false “live” state for stale readings.

### Faults
Default to active/open faults; filters by status, severity, phase and date only where supported. Fault detail exposes evidence and lifecycle.

### Maintenance
Show assignment and current state; chronological attempts; diagnosis/restoration; prevent invalid transitions.

### Administration
Separate user, device, threshold and relay configuration. Destructive actions require confirmation and audit. Keep relay control visibly uncommissioned until approved.

### Login
Minimal, focused form; accessible validation; generic invalid-credential message; no public registration unless explicitly approved.
