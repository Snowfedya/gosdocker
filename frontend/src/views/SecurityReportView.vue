<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSecurityReport } from '../composables/useSecurityReport'
import ScoreBadge from '../components/security/ScoreBadge.vue'
import SeverityBar from '../components/security/SeverityBar.vue'
import CveTable from '../components/security/CveTable.vue'
import DependencyGraph from '../components/security/DependencyGraph.vue'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const slug = route.params.slug as string

const { report, loading, error, score, scoreGrade, severitySummary, vulnerabilities, load } = useSecurityReport(slug)

const activeTab = ref<'vulns' | 'deps'>('vulns')
const scanning = ref(false)

onMounted(async () => {
  await load()
  // Auto-run scan if no report exists yet
  if (!report.value) {
    await runScan()
  }
})

async function runScan(profile: string = 'standard') {
  scanning.value = true
  try {
    await scan(profile)
  } finally {
    scanning.value = false
  }
}

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

    <!-- Loading / Scanning -->
    <div v-if="loading || scanning" class="text-center py-16">
      <div class="inline-block w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      <p class="mt-4 text-gray-500">{{ scanning ? 'Запуск сканирования безопасности...' : 'Загрузка отчёта...' }}</p>
      <p v-if="scanning" class="mt-2 text-xs text-gray-400">Это может занять до 2 минут</p>
    </div>

    <!-- Error / empty -->
    <div v-else-if="error || !report"
      class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-12 text-center">
      <AppIcon name="shield" class="w-14 h-14 mx-auto mb-3 text-gray-300 dark:text-slate-600" />
      <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">Отчёт не найден</h2>
      <p class="text-gray-500 dark:text-slate-400 mb-6">{{ error || 'Сканирование не выполнено.' }}</p>
      <button
        @click="runScan()"
        :disabled="scanning"
        class="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition shadow-sm disabled:opacity-40"
      >
        <AppIcon :name="scanning ? 'refresh' : 'shield'" class="w-4 h-4" :class="scanning ? 'animate-spin' : ''" />
        {{ scanning ? 'Сканирование...' : 'Запустить проверку' }}
      </button>
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
