# Security Report Redesign — Design Doc

## Context

GosDocker currently displays full security reports (SBOM, Trivy CVEs, OWASP DC, Cosign)
inside the ComponentView security tab. This creates a cognitive overload problem:
users see hundreds of CVEs, a dependency tree, and scanner details all at once
on a page meant for component overview.

## Goals

- Replace overloaded inline report with a **compact summary** on the ComponentView tab
- Provide a **dedicated SecurityReportView** page for deep audit (full CVE table,
  dependency graph, filtering, export)
- Add **constructor integration**: show security summary after stack generation
- Fix dep resolver bug: grafana now requires `[monitoring, database]`
- Fix catch-all error messages in ConstructorView

## Non-Goals

- No changes to the backend security pipeline itself
- No changes to the scan/build API
- No real-time scanning — data comes from cached report

## Approach

**Hybrid model:**

1. **ComponentView security tab** → `SecuritySummary.vue`
   - Score badge (A–E, colour-coded)
   - Severity counts (CRITICAL/HIGH/MEDIUM/LOW)
   - Dependency count
   - CTA button: «📄 Полный отчёт» → links to `/components/:slug/security`
   - Profile selector + «Запустить проверку» button preserved

2. **SecurityReportView** — full `/components/:slug/security` page
   - Breadcrumb: Каталог / Component / Безопасность
   - Score badge + severity bar
   - Tab panel: «Уязвимости» | «Граф зависимостей»
   - CveTable: sortable, searchable, filterable by severity
   - DependencyGraph: type-grouped collapsible sections
   - Export: JSON download + browser print

3. **ConstructorView** — security block after diagnostic/generate
   - Summary: component count, min/avg score
   - Per-component security links to SecurityReportView
   - «Запустить проверку» if unscanned

## Alternatives Considered

- **Full detail on tab (current)**: rejected — cognitive overload, cluttered
- **Modal overlay**: rejected — breaks navigation, poor for audit workflows
- **Side panel (slide-over)**: rejected — limited space for CVE table

## Architecture

### Data Flow

```
ComponentView mounts
  → useSecurityReport(slug) fetches /api/registry/{slug}/reports
    → returns SecurityReport { sbom, trivy, owasp, cosign }
  → SecuritySummary.vue renders compact view from report data
  → CTA → router.push(`/components/${slug}/security`)
    → SecurityReportView.vue uses same useSecurityReport()

ConstructorView diagnostic
  → resolved slugs → useSecurityReport() for each component
  → renders security summary block
```

### New Files

```
frontend/src/
├── views/
│   └── SecurityReportView.vue       # Full audit page
├── components/security/
│   ├── SecuritySummary.vue          # Compact tab summary
│   ├── CveTable.vue                 # Sortable/filterable CVE table
│   ├── SeverityBar.vue              # Visual severity distribution
│   ├── DependencyGraph.vue          # Type-grouped dependency tree
│   └── ScoreBadge.vue               # Color score indicator
└── composables/
    └── useSecurityReport.ts         # Fetch + reactive state
```

### Modified Files

| File | Change |
|------|--------|
| `ComponentView.vue:420-603` | Replace full report HTML with `<SecuritySummary>` |
| `ConstructorView.vue` | Add security block after diagnostic result |
| `router/index.ts` | Add `/components/:slug/security` route |

## Component Specifications

### ScoreBadge.vue
- **Props**: `score: number` (0–100)
- **CSS colour scale**: 90-100→A green, 70-89→B blue, 50-69→C yellow, 30-49→D orange, 0-29→E red
- **Display**: 36×36px circle with letter + number
- **Score formula**: computed from trivy.by_severity: 100 - (critical*15 + high*5 + medium*2 + low*0.5) with max(0, min(100, result))

### SeverityBar.vue
- **Props**: `bySeverity: { CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN }`
- 5 proportional coloured segments
- Labels + count on each segment

### CveTable.vue
- **Props**: `vulnerabilities: Vulnerability[]`
- Columns: CVE ID, Severity (colored badge), Package, Title, Fixed version
- Sort by any column (click header)
- Filter dropdown by severity
- Search input (free-text on ID/package/title)
- Emits: `@row-click` (optional, for drill-down)

### DependencyGraph.vue
- **Props**: `dependencies: SbomDependency[]`
- Grouped by type (library, application, framework, etc.)
- Collapsible type sections
- Shows name@version per dependency
- Visual tree with indentation

### SecuritySummary.vue
- **Props**: `report: SecurityReport | null`, `loading: boolean`, `error: string | null`
- **Emits**: `scan()` — triggers build
- Displays: ScoreBadge, SeverityBar, dependency count, CTA button
- No profile selector here (lives in ComponentView parent)

### SecurityReportView.vue
- **Route**: `/components/:slug/security`
- Loads SecurityReport via useSecurityReport(slug)
- Full-page layout with header, breadcrumb, CTA back
- Tab panel: CveTable tab + DependencyGraph tab
- Export actions: JSON download (stringify report), Print (window.print)
- Empty state: «Сканирование не выполнено» with CTA to scan

## Open Questions

None.

## Implementation Plan

See writing-plans output next.
