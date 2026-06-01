# Security Report Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the overloaded inline security report in ComponentView with a compact SecuritySummary + dedicated SecurityReportView full-audit page, and add security visibility to ConstructorView.

**Architecture:** Keep existing backend API (`GET /api/registry/{slug}/reports`). New composable `useSecurityReport` wraps fetch + score calculation. Five leaf components (ScoreBadge, SeverityBar, SecuritySummary, CveTable, DependencyGraph) compose into SecurityReportView. ComponentView security tab slimmed to SecuritySummary with CTA to full page.

**Tech Stack:** Vue 3 + Composition API, TypeScript, Tailwind 3, Vue Router 4. Backend: FastAPI + pytest for unit tests.

---

### Task 1: Create `useSecurityReport` composable

**Files:**
- Create: `frontend/src/composables/useSecurityReport.ts`

- [ ] **Step 1.1: Write the composable**

```typescript
import { ref, computed } from 'vue'
import type { SecurityReport, Vulnerability } from '../types'
import { useApi } from './useApi'

export function useSecurityReport(slug: string) {
  const report = ref<SecurityReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const { fetchReports, buildComponent } = useApi()

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      report.value = await fetchReports(slug)
    } catch (e) {
      report.value = null
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function scan(profile: string = 'standard'): Promise<void> {
    loading.value = true
    error.value = null
    try {
      report.value = await buildComponent(slug, profile)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  /** Score 0–100 based on Trivy severity counts */
  const score = computed<number>(() => {
    if (!report.value?.trivy) return 100
    const s = report.value.trivy.by_severity
    const raw = 100 - (s.CRITICAL * 15 + s.HIGH * 5 + s.MEDIUM * 2 + s.LOW * 0.5)
    return Math.max(0, Math.min(100, Math.round(raw)))
  })

  const scoreGrade = computed<string>(() => {
    const v = score.value
    if (v >= 90) return 'A'
    if (v >= 70) return 'B'
    if (v >= 50) return 'C'
    if (v >= 30) return 'D'
    return 'E'
  })

  const totalVulnerabilities = computed<number>(() => {
    return report.value?.trivy?.total_vulnerabilities ?? 0
  })

  const vulnerabilities = computed<Vulnerability[]>(() => {
    return report.value?.trivy?.vulnerabilities ?? []
  })

  const severitySummary = computed(() => {
    if (!report.value?.trivy) return { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
    return report.value.trivy.by_severity
  })

  return {
    report,
    loading,
    error,
    score,
    scoreGrade,
    totalVulnerabilities,
    vulnerabilities,
    severitySummary,
    load,
    scan,
  }
}
```

- [ ] **Step 1.2: Verify TypeScript compiles**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: no errors about useSecurityReport

---

### Task 2: Create `ScoreBadge.vue` and `SeverityBar.vue`

**Files:**
- Create: `frontend/src/components/security/ScoreBadge.vue`
- Create: `frontend/src/components/security/SeverityBar.vue`

- [ ] **Step 2.1: Create ScoreBadge.vue**

```vue
<script setup lang="ts">
defineProps<{
  score: number
  grade: string
}>()

const gradeColors: Record<string, string> = {
  A: 'bg-emerald-500 text-white',
  B: 'bg-blue-500 text-white',
  C: 'bg-amber-400 text-white',
  D: 'bg-orange-500 text-white',
  E: 'bg-red-500 text-white',
}
</script>

<template>
  <div class="flex items-center gap-3">
    <div
      class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shadow-sm shrink-0"
      :class="gradeColors[grade] || gradeColors.E"
    >
      {{ grade }}
    </div>
    <div>
      <div class="text-xs text-gray-500 dark:text-slate-400">Скоринг</div>
      <div class="text-lg font-bold text-gray-900 dark:text-white tabular-nums">{{ score }}</div>
    </div>
  </div>
</template>
```

- [ ] **Step 2.2: Create SeverityBar.vue**

```vue
<script setup lang="ts">
defineProps<{
  bySeverity: { CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number; UNKNOWN: number }
}>()

const segments = [
  { key: 'CRITICAL' as const, color: 'bg-red-500', label: 'Крит.' },
  { key: 'HIGH' as const, color: 'bg-orange-400', label: 'Выс.' },
  { key: 'MEDIUM' as const, color: 'bg-yellow-400', label: 'Сред.' },
  { key: 'LOW' as const, color: 'bg-blue-400', label: 'Низ.' },
  { key: 'UNKNOWN' as const, color: 'bg-gray-300 dark:bg-gray-600', label: 'Неизв.' },
]
</script>

<template>
  <div>
    <div class="flex h-3 rounded-full overflow-hidden border border-gray-200 dark:border-slate-600">
      <div
        v-for="seg in segments"
        :key="seg.key"
        :class="seg.color"
        :style="{ width: `0%` }"
      />
    </div>
    <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2">
      <div v-for="seg in segments" :key="seg.key" class="flex items-center gap-1.5 text-xs">
        <span class="w-2.5 h-2.5 rounded-full shrink-0" :class="seg.color" />
        <span class="text-gray-500 dark:text-slate-400">{{ seg.label }}:</span>
        <span class="font-semibold text-gray-800 dark:text-slate-200 tabular-nums">{{ bySeverity[seg.key] }}</span>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2.3: TypeScript check**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 3: Create `SecuritySummary.vue`

**Files:**
- Create: `frontend/src/components/security/SecuritySummary.vue`

This is the compact summary shown on the ComponentView security tab.

- [ ] **Step 3.1: Write SecuritySummary.vue**

```vue
<script setup lang="ts">
import type { SecurityReport } from '../../types'
import ScoreBadge from './ScoreBadge.vue'
import SeverityBar from './SeverityBar.vue'
import { computed } from 'vue'

const props = defineProps<{
  report: SecurityReport | null
  loading: boolean
  error: string | null
  slug: string
}>()

const emit = defineEmits<{ scan: [] }>()

const gradeColors: Record<string, string> = {
  A: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  B: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  C: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  D: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  E: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

// Score calculation isolated here too for when we only have computed props
const score = computed(() => {
  if (!props.report?.trivy) return 100
  const s = props.report.trivy.by_severity
  const raw = 100 - (s.CRITICAL * 15 + s.HIGH * 5 + s.MEDIUM * 2 + s.LOW * 0.5)
  return Math.max(0, Math.min(100, Math.round(raw)))
})
const grade = computed(() => {
  const v = score.value
  if (v >= 90) return 'A'
  if (v >= 70) return 'B'
  if (v >= 50) return 'C'
  if (v >= 30) return 'D'
  return 'E'
})

const depCount = computed(() => props.report?.sbom?.total_components ?? 0)
</script>

<template>
  <div class="space-y-4">
    <!-- Empty state -->
    <div v-if="!report && !loading && !error"
      class="text-center py-6 text-gray-400 dark:text-slate-500">
      <AppIcon name="shield" class="w-10 h-10 mx-auto mb-2 opacity-40" />
      <p class="text-sm">Проверка безопасности не запущена</p>
    </div>

    <!-- Error -->
    <div v-if="error"
      class="px-4 py-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
      <AppIcon name="warning" class="w-4 h-4 shrink-0" />
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-4">
      <AppIcon name="spinner" class="w-6 h-6 mx-auto animate-spin text-primary-500" />
      <p class="text-sm text-gray-400 mt-2">Сканирование...</p>
    </div>

    <!-- Report summary -->
    <div v-if="report && !loading" class="space-y-4">
      <div class="flex items-center gap-4">
        <ScoreBadge :score="score" :grade="grade" />

        <div class="text-xs text-gray-500 dark:text-slate-400">
          <span class="block">Профиль: <strong class="text-gray-700 dark:text-slate-300">{{ report.profile }}</strong></span>
          <span class="block mt-0.5">Зависимостей в SBOM: <strong class="text-gray-700 dark:text-slate-300">{{ depCount }}</strong></span>
        </div>

        <div class="ml-auto">
          <span class="px-2 py-0.5 text-xs font-medium rounded"
            :class="report.status === 'ok' ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'">
            {{ report.status === 'ok' ? '✅ Успешно' : '❌ Ошибки' }}
          </span>
        </div>
      </div>

      <!-- Severity bar -->
      <SeverityBar v-if="report.trivy" :by-severity="report.trivy.by_severity" />

      <!-- CTA to full report -->
      <div class="pt-2">
        <router-link
          :to="`/components/${slug}/security`"
          class="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-slate-600 transition"
        >
          <AppIcon name="external-link" class="w-4 h-4" />
          📄 Полный отчёт
        </router-link>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 3.2: Verify TypeScript**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 4: Create `CveTable.vue`

**Files:**
- Create: `frontend/src/components/security/CveTable.vue`

- [ ] **Step 4.1: Write CveTable.vue**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Vulnerability } from '../../types'

const props = defineProps<{
  vulnerabilities: Vulnerability[]
}>()

const search = ref('')
const severityFilter = ref<string>('all')
const sortField = ref<'id' | 'severity' | 'pkg'>('severity')
const sortDir = ref<'asc' | 'desc'>('desc')

const severityOrder: Record<string, number> = {
  CRITICAL: 5, HIGH: 4, MEDIUM: 3, LOW: 2, UNKNOWN: 1,
}

const filtered = computed(() => {
  let list = [...props.vulnerabilities]

  // Filter by severity
  if (severityFilter.value !== 'all') {
    list = list.filter(v => v.severity === severityFilter.value)
  }

  // Search
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(v =>
      v.id.toLowerCase().includes(q) ||
      v.pkg.toLowerCase().includes(q) ||
      v.title?.toLowerCase().includes(q)
    )
  }

  // Sort
  list.sort((a, b) => {
    let cmp = 0
    if (sortField.value === 'severity') {
      cmp = (severityOrder[a.severity] || 0) - (severityOrder[b.severity] || 0)
    } else if (sortField.value === 'id') {
      cmp = a.id.localeCompare(b.id)
    } else {
      cmp = a.pkg.localeCompare(b.pkg)
    }
    return sortDir.value === 'asc' ? cmp : -cmp
  })

  return list
})

const severityColor = (sev: string): string => {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    HIGH: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    MEDIUM: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    LOW: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    UNKNOWN: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  }
  return colors[sev] || colors.UNKNOWN
}

function toggleSort(field: 'id' | 'severity' | 'pkg') {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'desc'
  }
}

const sortIndicator = (field: string) => {
  if (sortField.value !== field) return ''
  return sortDir.value === 'asc' ? ' ▲' : ' ▼'
}
</script>

<template>
  <div>
    <!-- Controls -->
    <div class="flex flex-col sm:flex-row gap-3 mb-4">
      <div class="flex-1 relative">
        <AppIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          v-model="search"
          type="text"
          placeholder="Поиск по CVE, пакету или описанию..."
          class="w-full pl-9 pr-3 py-2 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
      <select
        v-model="severityFilter"
        class="w-full sm:w-40 px-3 py-2 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="all">Все severity</option>
        <option value="CRITICAL">CRITICAL</option>
        <option value="HIGH">HIGH</option>
        <option value="MEDIUM">MEDIUM</option>
        <option value="LOW">LOW</option>
        <option value="UNKNOWN">UNKNOWN</option>
      </select>
    </div>

    <!-- Count -->
    <p class="text-xs text-gray-500 dark:text-slate-400 mb-2">
      Показано: <strong class="text-gray-700 dark:text-slate-300">{{ filtered.length }}</strong>
      из {{ vulnerabilities.length }} уязвимостей
    </p>

    <!-- Table -->
    <div v-if="filtered.length" class="overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-700">
      <table class="w-full text-xs">
        <thead class="bg-gray-50 dark:bg-slate-800">
          <tr class="text-gray-500 dark:text-slate-400 border-b border-gray-200 dark:border-slate-700">
            <th class="text-left py-2.5 px-3 font-medium cursor-pointer hover:text-gray-700 dark:hover:text-slate-200 select-none"
              @click="toggleSort('id')">CVE{{ sortIndicator('id') }}</th>
            <th class="text-left py-2.5 px-3 font-medium cursor-pointer hover:text-gray-700 dark:hover:text-slate-200 select-none"
              @click="toggleSort('severity')">Severity{{ sortIndicator('severity') }}</th>
            <th class="text-left py-2.5 px-3 font-medium cursor-pointer hover:text-gray-700 dark:hover:text-slate-200 select-none"
              @click="toggleSort('pkg')">Пакет{{ sortIndicator('pkg') }}</th>
            <th class="text-left py-2.5 px-3 font-medium hidden sm:table-cell">Описание</th>
            <th class="text-left py-2.5 px-3 font-medium">Фикс</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-slate-700">
          <tr v-for="v in filtered" :key="v.id + v.pkg"
            class="hover:bg-gray-50 dark:hover:bg-slate-800/50 transition">
            <td class="py-2 px-3 font-mono text-gray-800 dark:text-slate-200 whitespace-nowrap">
              <a v-if="v.id.startsWith('CVE-')"
                :href="`https://nvd.nist.gov/vuln/detail/${v.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="hover:text-primary-600 dark:hover:text-primary-400 hover:underline"
              >{{ v.id }}</a>
              <span v-else>{{ v.id }}</span>
            </td>
            <td class="py-2 px-3 whitespace-nowrap">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-medium" :class="severityColor(v.severity)">
                {{ v.severity }}
              </span>
            </td>
            <td class="py-2 px-3 text-gray-600 dark:text-slate-400 font-mono whitespace-nowrap max-w-[160px] truncate">{{ v.pkg }}</td>
            <td class="py-2 px-3 text-gray-500 dark:text-slate-400 max-w-xs truncate hidden sm:table-cell">{{ v.title }}</td>
            <td class="py-2 px-3 text-gray-500 dark:text-slate-500 font-mono whitespace-nowrap">{{ v.fixed || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty -->
    <div v-else class="text-center py-8 text-gray-400 dark:text-slate-500">
      <AppIcon name="search" class="w-8 h-8 mx-auto mb-2 opacity-40" />
      <p class="text-sm">Уязвимостей не найдено</p>
    </div>
  </div>
</template>
```

- [ ] **Step 4.2: TypeScript check**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 5: Create `DependencyGraph.vue`

**Files:**
- Create: `frontend/src/components/security/DependencyGraph.vue`

- [ ] **Step 5.1: Write DependencyGraph.vue**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SbomDependency } from '../../types'

const props = defineProps<{
  dependencies: SbomDependency[]
}>()

const expanded = ref<Record<string, boolean>>({})

const groups = computed(() => {
  const map: Record<string, SbomDependency[]> = {}
  for (const dep of props.dependencies) {
    const type = dep.type || 'unknown'
    if (!map[type]) map[type] = []
    map[type].push(dep)
  }
  // Sort groups by size (largest first)
  const sorted = Object.entries(map).sort((a, b) => b[1].length - a[1].length)
  return sorted.map(([type, deps]) => ({
    type,
    count: deps.length,
    dependencies: deps,
    expanded: expanded.value[type] ?? true,
  }))
})

function toggleGroup(type: string) {
  expanded.value[type] = !(expanded.value[type] ?? true)
}
</script>

<template>
  <div class="space-y-3">
    <div v-for="group in groups" :key="group.type"
      class="bg-gray-50 dark:bg-slate-700/50 rounded-lg overflow-hidden border border-gray-100 dark:border-slate-600/50">
      <!-- Group header -->
      <button
        @click="toggleGroup(group.type)"
        class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-slate-700 transition"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-gray-700 dark:text-slate-300 capitalize">{{ group.type }}</span>
          <span class="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-slate-600 text-gray-500 dark:text-slate-400 rounded-full">{{ group.count }}</span>
        </div>
        <AppIcon :name="group.expanded ? 'chevron-up' : 'chevron-down'" class="w-4 h-4 text-gray-400" />
      </button>
      <!-- Dependency list -->
      <div v-if="group.expanded" class="px-4 pb-3 space-y-1">
        <div v-for="dep in group.dependencies" :key="dep.name + dep.version"
          class="flex items-center gap-2 text-xs pl-4 border-l-2 border-gray-200 dark:border-slate-600 py-0.5">
          <span class="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-slate-500 shrink-0" />
          <code class="text-gray-700 dark:text-slate-300">{{ dep.name }}</code>
          <span v-if="dep.version" class="text-gray-400 dark:text-slate-500">@{{ dep.version }}</span>
        </div>
      </div>
    </div>

    <div v-if="groups.length === 0" class="text-center py-6 text-gray-400 dark:text-slate-500">
      <p class="text-sm">Нет данных о зависимостях</p>
    </div>
  </div>
</template>
```

- [ ] **Step 5.2: TypeScript check**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 6: Create `SecurityReportView.vue`

**Files:**
- Create: `frontend/src/views/SecurityReportView.vue`

- [ ] **Step 6.1: Write SecurityReportView.vue**

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSecurityReport } from '../composables/useSecurityReport'
import ScoreBadge from '../components/security/ScoreBadge.vue'
import SeverityBar from '../components/security/SeverityBar.vue'
import CveTable from '../components/security/CveTable.vue'
import DependencyGraph from '../components/security/DependencyGraph.vue'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string

const { report, loading, error, score, scoreGrade, severitySummary, vulnerabilities, load } = useSecurityReport(slug)

const activeTab = ref<'vulns' | 'deps'>('vulns')

onMounted(() => {
  load()
})

function exportJson() {
  if (!report.value) return
  const blob = new Blob([JSON.stringify(report.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${slug}-security-report.json`
  a.click()
  URL.revokeObjectURL(url)
}

function handlePrint() {
  window.print()
}

const depsArray = computed(() => report.value?.sbom?.top_dependencies ?? [])
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Breadcrumb -->
    <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-6">
      <router-link to="/catalog" class="hover:text-primary-600 transition flex items-center gap-1">
        <AppIcon name="catalog" class="w-3.5 h-3.5" />
        Каталог
      </router-link>
      <span class="text-gray-300 dark:text-slate-600">/</span>
      <router-link :to="`/components/${slug}`" class="hover:text-primary-600 transition">
        {{ slug }}
      </router-link>
      <span class="text-gray-300 dark:text-slate-600">/</span>
      <span class="text-gray-900 dark:text-white font-medium">Безопасность</span>
    </div>

    <!-- Header -->
    <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6 mb-6">
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Отчёт безопасности</h1>
        <div class="sm:ml-auto flex gap-2">
          <button @click="exportJson"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-xs text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 transition">
            <AppIcon name="document" class="w-3.5 h-3.5" />
            JSON
          </button>
          <button @click="handlePrint"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-xs text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 transition">
            <AppIcon name="external-link" class="w-3.5 h-3.5" />
            Печать
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-16">
      <div class="inline-block w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      <p class="mt-4 text-gray-500">Загрузка отчёта...</p>
    </div>

    <!-- Error / empty -->
    <div v-else-if="error || !report" class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-12 text-center">
      <AppIcon name="shield" class="w-14 h-14 mx-auto mb-3 text-gray-300 dark:text-slate-600" />
      <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">Отчёт не найден</h2>
      <p class="text-gray-500 dark:text-slate-400 mb-6">{{ error || 'Сканирование не выполнено' }}</p>
      <router-link
        :to="`/components/${slug}`"
        class="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition shadow-sm"
      >
        <AppIcon name="arrow-left" class="w-4 h-4" />
        Запустить проверку
      </router-link>
    </div>

    <!-- Report content -->
    <div v-else class="space-y-6">
      <!-- Score card -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6">
        <div class="flex flex-col sm:flex-row items-start gap-6">
          <ScoreBadge :score="score" :grade="scoreGrade" />
          <div class="flex-1 w-full">
            <SeverityBar :by-severity="severitySummary" />
          </div>
          <div class="text-xs text-gray-500 dark:text-slate-400 whitespace-nowrap">
            <span class="block">Профиль: <strong class="text-gray-700 dark:text-slate-300">{{ report.profile }}</strong></span>
            <span class="block mt-0.5">Статус: <strong :class="report.status === 'ok' ? 'text-emerald-600' : 'text-red-500'">{{ report.status }}</strong></span>
            <span class="block mt-0.5">SBOM: <strong class="text-gray-700 dark:text-slate-300">{{ report.sbom?.total_components ?? 0 }} комп.</strong></span>
          </div>
        </div>
      </div>

      <!-- Tab panel -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div class="flex border-b border-gray-200 dark:border-slate-700">
          <button
            @click="activeTab = 'vulns'"
            :class="[
              'inline-flex items-center gap-1.5 px-5 py-3 text-sm font-medium border-b-2 transition -mb-px',
              activeTab === 'vulns'
                ? 'border-primary-600 text-primary-700 dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
            ]"
          >
            <AppIcon name="warning" class="w-4 h-4" />
            Уязвимости ({{ vulnerabilities.length }})
          </button>
          <button
            @click="activeTab = 'deps'"
            :class="[
              'inline-flex items-center gap-1.5 px-5 py-3 text-sm font-medium border-b-2 transition -mb-px',
              activeTab === 'deps'
                ? 'border-primary-600 text-primary-700 dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
            ]"
          >
            <AppIcon name="document-text" class="w-4 h-4" />
            Граф зависимостей ({{ depsArray.length }})
          </button>
        </div>

        <div class="p-6">
          <CveTable v-if="activeTab === 'vulns'" :vulnerabilities="vulnerabilities" />
          <DependencyGraph v-if="activeTab === 'deps'" :dependencies="depsArray" />
        </div>
      </div>

      <!-- Cosign status -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <AppIcon name="key" class="w-4 h-4 text-gray-400" />
          Cosign — подпись образа
        </h3>
        <div class="flex items-center gap-2">
          <span v-if="report.cosign.signed"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
            <span>✅</span> Подписан
          </span>
          <span v-else
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-200 dark:bg-slate-600 text-gray-500 dark:text-slate-400">
            <span>⏳</span> Не подписан
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 6.2: TypeScript check**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 7: Update `ComponentView.vue` — security tab

**Files:**
- Modify: `frontend/src/views/ComponentView.vue` — lines 420-603

- [ ] **Step 7.1: Add import of SecuritySummary in `<script setup>`**

Add after the last import line:
```typescript
import SecuritySummary from '../components/security/SecuritySummary.vue'
```

- [ ] **Step 7.2: Replace lines 420-603 (the entire security tab) with SecuritySummary**

**Replace** the entire security tab block (from `<!-- 🛡 Security Tab -->` to the `</div>` before `<!-- Download -->`):

```vue
          <!-- 🛡 Security Tab -->
          <div v-if="activeTab === 'security' && registryManifest" class="space-y-6">
            <!-- Profile selector + build button -->
            <div class="flex flex-col sm:flex-row gap-3 sm:items-end">
              <div class="flex-1">
                <label class="block text-sm font-medium text-gray-500 dark:text-slate-400 mb-1.5">Профиль безопасности</label>
                <select
                  v-model="selectedProfile"
                  class="w-full sm:w-64 px-3 py-2 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  :disabled="reportLoading"
                >
                  <option v-for="p in profiles" :key="p.slug" :value="p.slug">{{ p.label }}</option>
                  <option v-if="!profiles.length" value="basic">Basic</option>
                  <option value="standard">Standard</option>
                  <option value="hardened">Hardened</option>
                </select>
              </div>
              <button
                @click="runSecurityScan"
                :disabled="reportLoading"
                class="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
              >
                <AppIcon v-if="reportLoading" name="spinner" class="w-4 h-4 animate-spin" />
                <AppIcon v-else name="shield" class="w-4 h-4" />
                {{ reportLoading ? 'Сканирование...' : 'Запустить проверку безопасности' }}
              </button>
            </div>

            <SecuritySummary
              :report="report"
              :loading="reportLoading"
              :error="reportError"
              :slug="component.slug"
              @scan="runSecurityScan"
            />
          </div>
```

- [ ] **Step 7.3: TypeScript check**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 8: Update Router + ConstructorView

**Files:**
- Modify: `frontend/src/router/index.ts` — add route
- Modify: `frontend/src/views/ConstructorView.vue` — add security block

- [ ] **Step 8.1: Add security route to router/index.ts**

Add before the `{ path: '/:pathMatch(.*)*', redirect: '/' }` catch-all:

```typescript
{
  path: '/components/:slug/security',
  name: 'security-report',
  component: () => import('../views/SecurityReportView.vue'),
  meta: { title: 'Отчёт безопасности' },
},
```

- [ ] **Step 8.2: Add import of useSecurityReport to ConstructorView.vue**

```typescript
import { useSecurityReport } from '../composables/useSecurityReport'
```

- [ ] **Step 8.3: Add security summary block after diagnostic result in ConstructorView**

After the existing diagnostic result (`<!-- Diagnostic result -->`) block, add:

```vue
          <!-- Security summary per component -->
          <div v-if="showResult && result?.resolved.length" class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700">
            <div class="flex items-center gap-2 mb-3">
              <AppIcon name="shield" class="w-4 h-4 text-gray-500 dark:text-slate-400" />
              <h3 class="font-medium text-gray-900 dark:text-white text-sm">Безопасность компонентов</h3>
            </div>
            <div class="space-y-1.5">
              <div v-for="slug in result.resolved" :key="slug"
                class="flex items-center justify-between px-2.5 py-1.5 bg-gray-50 dark:bg-slate-700/30 rounded-lg">
                <span class="text-xs font-mono text-gray-700 dark:text-slate-300">{{ slug }}</span>
                <router-link
                  :to="`/components/${slug}/security`"
                  class="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                >
                  → отчёт
                </router-link>
              </div>
            </div>
          </div>
```

- [ ] **Step 8.4: TypeScript check**

```bash
cd /opt/gosdocker/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

---

### Task 9: Write backend unit tests for dependency resolver

**Files:**
- Create: `backend/tests/test_dependency_resolver.py`

- [ ] **Step 9.1: Write unit tests**

```python
"""Unit tests for the DependencyResolver.

These tests are fast — no API calls, no Docker — just pure logic.
Run with: python3 -m pytest backend/tests/test_dependency_resolver.py -v
"""
import pytest
from app.services.dependency_resolver import DependencyResolver


# ── fixtures ──────────────────────────────────────────────────

@pytest.fixture
def resolver():
    """Standard resolver with known graph."""
    return DependencyResolver()


@pytest.fixture
def empty_resolver():
    """Resolver with no dependencies defined."""
    return DependencyResolver(
        graph={},
        providers={},
        preferred={},
    )


# ── basic resolution ──────────────────────────────────────────

class TestBasicResolution:
    def test_empty_selection(self, resolver):
        assert resolver.resolve([]) == []

    def test_single_no_deps(self, resolver):
        result = resolver.resolve(["nginx"])
        assert "nginx" in result
        assert len(result) == 1

    def test_single_with_dep(self, resolver):
        """nextcloud requires database → adds postgresql."""
        result = resolver.resolve(["nextcloud"])
        assert "nextcloud" in result
        assert "postgresql" in result


# ── dependency auto‑add ───────────────────────────────────────

class TestDependencyAutoAdd:
    def test_grafana_requires_both(self, resolver):
        """grafana needs monitoring + database → adds prometheus + postgresql."""
        result = resolver.resolve(["grafana"])
        assert "grafana" in result
        assert "prometheus" in result
        assert "postgresql" in result
        assert len(result) == 3

    def test_dependency_already_satisfied(self, resolver):
        """postgresql already selected → no redundant add."""
        result = resolver.resolve(["nextcloud", "postgresql"])
        assert "nextcloud" in result
        assert "postgresql" in result
        assert len(result) == 2

    def test_multiple_components_same_dep(self, resolver):
        """both nextcloud and grafana need database → only one postgresql added."""
        result = resolver.resolve(["nextcloud", "grafana"])
        assert "nextcloud" in result
        assert "grafana" in result
        assert "postgresql" in result
        assert "prometheus" in result
        # Count occurrences each slug appears at most once
        for slug in result:
            assert result.count(slug) == 1


# ── alternative providers ─────────────────────────────────────

class TestAlternativeProviders:
    def test_preferred_provider(self, resolver):
        """database uses preferred provider 'postgresql', not 'postgresql-redos'."""
        result = resolver.resolve(["nextcloud"])
        assert "postgresql" in result
        assert "postgresql-redos" not in result

    def test_fallback_when_preferred_unavailable(self):
        """If preferred provider is removed from providers, fallback to first available."""
        r = DependencyResolver(
            graph={"app": {"database"}},
            providers={"database": {"postgresql-redos"}},
            preferred={"database": "postgresql"},  # postgresql not in available
        )
        result = r.resolve(["app"])
        assert "postgresql-redos" in result
        assert "postgresql" not in result

    def test_no_provider_available(self):
        """Component needs a dependency type with zero providers → no crash, empty."""
        r = DependencyResolver(
            graph={"app": {"missing-type"}},
            providers={},
            preferred={},
        )
        result = r.resolve(["app"])
        assert "app" in result


# ── resolve_with_metadata ─────────────────────────────────────

class TestResolveWithMetadata:
    def test_auto_added_tracking(self, resolver):
        resolved, auto_added = resolver.resolve_with_metadata(["nextcloud"])
        assert "nextcloud" in resolved
        assert len(auto_added) == 1
        assert auto_added[0]["slug"] == "postgresql"
        assert "required by nextcloud" in auto_added[0]["reason"]
        assert auto_added[0]["provides"] == "database"

    def test_no_auto_added(self, resolver):
        resolved, auto_added = resolver.resolve_with_metadata(["nginx"])
        assert len(auto_added) == 0
        assert resolved == ["nginx"]


# ── edge cases ────────────────────────────────────────────────

class TestEdgeCases:
    def test_unknown_slug(self, resolver):
        """Unknown slug (not in graph) → added as-is with no deps."""
        result = resolver.resolve(["unknown-component"])
        assert "unknown-component" in result

    def test_duplicate_slugs(self, resolver):
        """Duplicate input slugs → deduplicated."""
        result = resolver.resolve(["nginx", "nginx", "nginx"])
        assert result.count("nginx") == 1

    def test_all_components_together(self, resolver):
        """All known components at once → no conflicts."""
        all_slugs = ["nextcloud", "grafana", "postgresql", "postgresql-redos",
                      "nginx", "angie-pro", "prometheus"]
        result = resolver.resolve(all_slugs)
        for slug in all_slugs:
            assert slug in result
```

- [ ] **Step 9.2: Run the tests**

```bash
cd /opt/gosdocker && python3 -m pytest backend/tests/test_dependency_resolver.py -v
```
Expected: all tests PASS

- [ ] **Step 9.3: Run existing integration tests if backend available**

```bash
cd /opt/gosdocker && API_BASE=http://localhost:8000 python3 -m pytest backend/tests/test_registry.py -v
```
Expected: all tests PASS (or skip gracefully if backend not running)

---

### Task 10: Integration smoke test

- [ ] **Step 10.1: Restart frontend and verify**

```bash
cd /opt/gosdocker/frontend && npm run build 2>&1 | tail -5
```
Expected: build succeeds with no errors

- [ ] **Step 10.2: Verify router works**

```bash
grep -r "security-report" /opt/gosdocker/frontend/src/router/index.ts
```
Expected: route for security-report found

- [ ] **Step 10.3: Verify ComponentView still renders security tab**

Check that SecuritySummary is imported and used in ComponentView.

---

## Verification

- [ ] All frontend TypeScript checks pass
- [ ] Frontend build succeeds (`npm run build`)
- [ ] Backend unit tests for dependency resolver pass
- [ ] Router has new route for SecurityReportView
- [ ] ComponentView security tab shows SecuritySummary
- [ ] ConstructorView shows security block after diagnostic
