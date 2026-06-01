<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SbomDependency } from '../../types'
import AppIcon from '../AppIcon.vue'

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
