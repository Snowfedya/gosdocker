<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Component, ComponentConfig } from '../types'
import AppIcon from './AppIcon.vue'
import { useApi } from '../composables/useApi'

const props = defineProps<{ component: Component }>()
const emit = defineEmits<{ (e: 'close'): void }>()

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
const activeTab = ref<'ports' | 'env'>('ports')

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
  <div class="fixed inset-0 bg-black/50 dark:bg-black/60 flex items-center justify-center z-50 p-4" @click.self="emit('close')">
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-lg w-full max-h-[85vh] overflow-hidden flex flex-col animate-slide-up">
      
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <AppIcon name="settings" class="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h2 class="text-lg font-bold text-gray-900 dark:text-white">{{ component.name }}</h2>
          </div>
          <button @click="emit('close')" class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition">
            <AppIcon name="close" class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-gray-200 dark:border-slate-700 px-6">
        <button
          v-for="tab in [{ id: 'ports' as const, label: 'Порты', icon: 'port' }, { id: 'env' as const, label: 'Переменные', icon: 'key' }]"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition -mb-px',
            activeTab === tab.id
              ? 'border-primary-600 text-primary-700 dark:text-primary-400'
              : 'border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
          ]"
        >
          <AppIcon :name="tab.icon" class="w-4 h-4" />
          {{ tab.label }}
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Ports Tab -->
        <div v-if="activeTab === 'ports'" class="space-y-3">
          <div v-if="portEntries.length === 0" class="text-sm text-gray-400 dark:text-slate-500 text-center py-6">
            Нет настраиваемых портов
          </div>
          <div v-for="(port, idx) in portEntries" :key="idx" class="flex items-center gap-3">
            <div class="flex-1">
              <label class="block text-xs text-gray-500 dark:text-slate-400 mb-1">Внешний порт</label>
              <input
                v-model="port.external"
                class="w-full px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
                placeholder="8080"
              />
            </div>
            <span class="text-gray-400 mt-5">→</span>
            <div class="flex-1">
              <label class="block text-xs text-gray-500 dark:text-slate-400 mb-1">Внутренний порт</label>
              <input
                v-model.number="port.internal"
                class="w-full px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
                type="number"
                placeholder="80"
              />
            </div>
          </div>
        </div>

        <!-- Env Tab -->
        <div v-if="activeTab === 'env'" class="space-y-3">
          <div v-if="Object.keys(config.env).length === 0" class="text-sm text-gray-400 dark:text-slate-500 text-center py-6">
            Нет переменных окружения
          </div>
          <div v-for="(value, key) in config.env" :key="key" class="flex items-center gap-3">
            <div class="flex-1">
              <label class="block text-xs text-gray-500 dark:text-slate-400 mb-1">Ключ</label>
              <input
                :value="key"
                class="w-full px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-gray-50 dark:bg-slate-700 text-gray-500 dark:text-slate-400 font-mono"
                disabled
              />
            </div>
            <div class="flex-1">
              <label class="block text-xs text-gray-500 dark:text-slate-400 mb-1">Значение</label>
              <input
                :value="value"
                @input="(e: Event) => { const t = e.target as HTMLInputElement; config.env[key as string] = t.value }"
                class="w-full px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200 dark:border-slate-700">
        <div v-if="error" class="mb-3 text-sm text-red-500 dark:text-red-400">{{ error }}</div>
        <div class="flex gap-3">
          <button
            @click="emit('close')"
            class="flex-1 px-4 py-2.5 border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-slate-700 transition"
          >
            Отмена
          </button>
          <button
            @click="download"
            :disabled="downloading"
            class="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition shadow-sm disabled:opacity-50"
          >
            <AppIcon :name="downloading ? 'refresh' : 'download'" class="w-4 h-4" :class="downloading ? 'animate-spin' : ''" />
            {{ downloading ? 'Генерация...' : 'Скачать' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
