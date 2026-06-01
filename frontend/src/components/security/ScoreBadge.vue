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
