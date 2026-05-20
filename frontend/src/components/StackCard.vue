<script setup lang="ts">
import { ref } from 'vue'
import type { Stack } from '../types'
import SourceBadge from './SourceBadge.vue'
import { useApi } from '../composables/useApi'

const props = defineProps<{
  stack: Stack
}>()

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
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border p-6">
    <div class="flex items-start justify-between mb-3">
      <div class="flex items-center gap-2">
        <h3 class="text-lg font-semibold text-gray-900">{{ stack.name }}</h3>
        <span v-if="stack.is_featured" class="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded-full">
          ★ Избранное
        </span>
      </div>
    </div>

    <p class="text-gray-600 text-sm mb-4">{{ stack.description }}</p>

    <div class="flex flex-wrap gap-2 mb-4">
      <span
        v-for="comp in stack.components"
        :key="comp.slug"
        class="px-2 py-1 bg-gray-50 text-gray-600 text-xs rounded border"
      >
        {{ comp.name }}
        <SourceBadge :is-registry="comp.is_registry" class="ml-1" />
      </span>
    </div>

    <button class="w-full px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition" @click="downloadStack" :disabled="downloading">
      {{ downloading ? '⏳...' : '📥 Скачать сборку' }}
    </button>
  </div>
</template>
