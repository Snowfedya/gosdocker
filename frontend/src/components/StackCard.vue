<script setup lang="ts">
import { ref } from 'vue'
import type { Stack } from '../types'
import SourceBadge from './SourceBadge.vue'
import AppIcon from './AppIcon.vue'
import { useApi } from '../composables/useApi'

const props = defineProps<{ stack: Stack }>()

const { generateStack } = useApi()
const downloading = ref(false)

async function downloadStack() {
  downloading.value = true
  try {
    const slugs = props.stack.components.map(c => c.slug)
    const blob = await generateStack(slugs, {})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${props.stack.slug}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed', e)
  } finally {
    downloading.value = false
  }
}

function isRegistryStack(): boolean {
  return props.stack.components.some(c => c.is_registry)
}
</script>

<template>
  <div class="bg-white dark:bg-slate-800 rounded-xl border shadow-sm hover:shadow-lg transition-all duration-200 overflow-hidden"
    :class="isRegistryStack() ? 'border-emerald-200 dark:border-emerald-800' : 'border-blue-200 dark:border-blue-800'">
    
    <!-- Color accent bar -->
    <div :class="isRegistryStack() ? 'bg-emerald-500' : 'bg-blue-500'" class="h-1" />

    <div class="p-6">
      <div class="flex items-start justify-between mb-3">
        <div class="flex items-center gap-2">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ stack.name }}</h3>
          <span v-if="stack.is_featured" class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
            <AppIcon name="star" class="w-3 h-3" />
            Избранное
          </span>
        </div>
      </div>

      <p class="text-gray-600 dark:text-slate-400 text-sm mb-4 leading-relaxed">{{ stack.description }}</p>

      <!-- Component chips -->
      <div class="flex flex-wrap gap-2 mb-4">
        <span
          v-for="comp in stack.components"
          :key="comp.slug"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 dark:bg-slate-700/50 text-gray-700 dark:text-slate-300 text-xs rounded-lg border border-gray-100 dark:border-slate-600"
        >
          <AppIcon name="cube" class="w-3 h-3 text-gray-400" />
          {{ comp.name }}
          <SourceBadge :is-registry="comp.is_registry" />
        </span>
      </div>

      <button
        class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition shadow-sm disabled:opacity-50"
        @click="downloadStack"
        :disabled="downloading"
      >
        <AppIcon :name="downloading ? 'refresh' : 'download'" class="w-4 h-4" :class="downloading ? 'animate-spin' : ''" />
        {{ downloading ? 'Подготовка...' : 'Скачать сборку' }}
      </button>
    </div>
  </div>
</template>
