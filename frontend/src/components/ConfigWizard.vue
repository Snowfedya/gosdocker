<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Component, ComponentConfig } from '../types'
import { useApi } from '../composables/useApi'

const props = defineProps<{
  component: Component
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { generateStack } = useApi()

interface PortEntry {
  external: string
  internal: number
}

const portEntries = ref<PortEntry[]>(
  Object.entries(props.component.default_ports).map(([ext, int]) => ({
    external: ext,
    internal: int as number
  }))
)

const config = computed<ComponentConfig>(() => ({
  ports: Object.fromEntries(portEntries.value.map(p => [p.external, p.internal])),
  volumes: { ...props.component.default_volumes },
  env: { ...props.component.default_env }
}))

const downloading = ref(false)
const error = ref<string | null>(null)

async function download() {
  downloading.value = true
  error.value = null
  try {
    const blob = await generateStack([props.component.slug], {
      [props.component.slug]: config.value
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${props.component.slug}.zip`
    a.click()
    URL.revokeObjectURL(url)
    emit('close')
  } catch (e) {
    error.value = 'Ошибка генерации'
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
      <h2 class="text-xl font-bold mb-4">⚙️ Настройка: {{ component.name }}</h2>

      <!-- Ports -->
      <div class="mb-4">
        <label class="block text-sm font-medium mb-2 text-gray-700">Порты</label>
        <div class="space-y-2">
          <div v-for="(port, idx) in portEntries" :key="idx" class="flex items-center gap-2">
            <input
              v-model="port.external"
              class="w-24 px-2 py-1 border rounded text-sm"
              placeholder="Внешний"
            />
            <span class="text-gray-400">→</span>
            <input
              v-model.number="port.internal"
              class="w-24 px-2 py-1 border rounded text-sm"
              type="number"
              placeholder="Внутр"
            />
          </div>
        </div>
      </div>

      <!-- Env -->
      <div class="mb-4">
        <label class="block text-sm font-medium mb-2 text-gray-700">Переменные окружения</label>
        <div class="space-y-2">
          <div v-for="(value, key) in config.env" :key="key" class="flex items-center gap-2">
            <input
              :value="key"
              class="w-32 px-2 py-1 border rounded text-sm bg-gray-50"
              disabled
            />
            <input
              :value="value"
              @input="(e) => { const t = e.target as HTMLInputElement; config.env[key as string] = t.value }"
              class="flex-1 px-2 py-1 border rounded text-sm"
            />
          </div>
        </div>
      </div>

      <div v-if="error" class="mb-4 text-sm text-red-500">{{ error }}</div>

      <div class="flex gap-2">
        <button
          @click="emit('close')"
          class="flex-1 px-4 py-2 border rounded hover:bg-gray-50 transition"
        >
          Отмена
        </button>
        <button
          @click="download"
          :disabled="downloading"
          class="flex-1 px-4 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50"
        >
          {{ downloading ? '⏳...' : '📥 Скачать' }}
        </button>
      </div>
    </div>
  </div>
</template>
