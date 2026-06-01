<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Vulnerability } from '../../types'
import AppIcon from '../AppIcon.vue'

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

  if (severityFilter.value !== 'all') {
    list = list.filter(v => v.severity === severityFilter.value)
  }

  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(v =>
      v.id.toLowerCase().includes(q) ||
      v.pkg.toLowerCase().includes(q) ||
      (v.title || '').toLowerCase().includes(q)
    )
  }

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
