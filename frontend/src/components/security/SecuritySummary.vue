<script setup lang="ts">
import { calculateSecurityScore, scoreToGrade } from '../../utils/security'
import type { SecurityReport } from '../../types'
import ScoreBadge from './ScoreBadge.vue'
import SeverityBar from './SeverityBar.vue'
import AppIcon from '../AppIcon.vue'
import { computed } from 'vue'

const props = defineProps<{
  report: SecurityReport | null
  loading: boolean
  error: string | null
  slug: string
}>()

const score = computed(() => {
  if (!props.report?.trivy) return 100
  return calculateSecurityScore(props.report.trivy.by_severity)
})

const grade = computed(() => scoreToGrade(score.value))

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

    <!-- Scan prompt (cached report may be missing) -->
    <div v-else-if="error && !loading"
      class="px-4 py-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-sm text-orange-600 dark:text-orange-400 flex items-center gap-2">
      <AppIcon name="warning" class="w-4 h-4 shrink-0" />
      <span class="flex-1">{{ error }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-4">
      <AppIcon name="spinner" class="w-6 h-6 mx-auto animate-spin text-primary-500" />
      <p class="text-sm text-gray-400 mt-2">Сканирование...</p>
    </div>

    <!-- Report summary -->
    <div v-if="report && !loading" class="space-y-4">
      <div class="flex items-start gap-4">
        <ScoreBadge :score="score" :grade="grade" />

        <div class="text-xs text-gray-500 dark:text-slate-400">
          <span class="block">Профиль: <strong class="text-gray-700 dark:text-slate-300">{{ report.profile }}</strong></span>
          <span class="block mt-0.5">Зависимостей в SBOM: <strong class="text-gray-700 dark:text-slate-300">{{ depCount }}</strong></span>
        </div>

        <div class="ml-auto">
          <span
            class="px-2 py-0.5 text-xs font-medium rounded"
            :class="report.status === 'ok'
              ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
              : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'"
          >
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

    <!-- Pipeline errors -->
    <div v-if="report?.errors?.length" class="px-4 py-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
      <p class="text-sm font-medium text-orange-600 dark:text-orange-400 mb-1">Предупреждения pipeline:</p>
      <ul class="text-xs text-orange-600 dark:text-orange-400 list-disc list-inside space-y-0.5">
        <li v-for="err in report.errors" :key="err">{{ err }}</li>
      </ul>
    </div>
  </div>
</template>
