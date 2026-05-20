<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Component } from '../types'
import SourceBadge from './SourceBadge.vue'
import ConfigWizard from './ConfigWizard.vue'
import { useApi } from '../composables/useApi'

const props = defineProps<{
  component: Component
}>()

const router = useRouter()
const showWizard = ref(false)
const { generateStack } = useApi()
const downloading = ref(false)

function openDetail() {
  router.push({ name: 'component', params: { slug: props.component.slug } })
}

async function quickDownload() {
  downloading.value = true
  try {
    const blob = await generateStack([props.component.slug], {
      [props.component.slug]: {
        ports: { ...props.component.default_ports },
        volumes: { ...props.component.default_volumes },
        env: { ...props.component.default_env }
      }
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${props.component.slug}.zip`
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
  <div class="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition cursor-pointer" @click="openDetail">
    <div class="flex items-start justify-between mb-3">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">{{ component.name }}</h3>
        <SourceBadge :is-registry="component.is_registry" />
      </div>
      <span v-if="component.version" class="text-sm text-gray-500">v{{ component.version }}</span>
    </div>

    <p class="text-gray-600 text-sm mb-3 line-clamp-2">
      {{ component.description }}
    </p>

    <code class="text-xs text-gray-400 block mb-4 truncate">
      {{ component.registry_url }}
    </code>

    <div class="flex gap-2">
      <button
        @click.stop="quickDownload"
        :disabled="downloading"
        class="flex-1 px-3 py-2 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
      >
        {{ downloading ? '⏳' : '📥 Скачать' }}
      </button>
      <button class="flex-1 px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700" @click.stop="showWizard = true">
        ⚙️ Настроить
      </button>
    </div>
  </div>
  <ConfigWizard v-if="showWizard" :component="component" @close="showWizard = false" />
</template>
