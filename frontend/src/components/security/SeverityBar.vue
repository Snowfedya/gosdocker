<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  bySeverity: { CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number; UNKNOWN: number }
}>()

const segments = [
  { key: 'CRITICAL' as const, color: 'bg-red-500', label: 'Крит.' },
  { key: 'HIGH' as const, color: 'bg-orange-400', label: 'Выс.' },
  { key: 'MEDIUM' as const, color: 'bg-yellow-400', label: 'Сред.' },
  { key: 'LOW' as const, color: 'bg-blue-400', label: 'Низ.' },
  { key: 'UNKNOWN' as const, color: 'bg-gray-300 dark:bg-gray-600', label: 'Неизв.' },
]

const total = computed(() => {
  return Object.values(props.bySeverity).reduce((a, b) => a + b, 0)
})

const barWidths = computed(() => {
  const t = total.value || 1
  return segments.map(seg => ({
    ...seg,
    width: ((props.bySeverity[seg.key] || 0) / t * 100).toFixed(1),
  }))
})
</script>

<template>
  <div>
    <div class="flex h-3 rounded-full overflow-hidden border border-gray-200 dark:border-slate-600">
      <div
        v-for="seg in barWidths"
        :key="seg.key"
        :class="seg.color"
        :style="{ width: seg.width + '%' }"
        :title="`${seg.label}: ${bySeverity[seg.key]}`"
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
