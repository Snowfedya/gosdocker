<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'
import type { Component } from '../types'
import SourceBadge from '../components/SourceBadge.vue'
import ConfigWizard from '../components/ConfigWizard.vue'

const route = useRoute()
const { fetchComponents } = useApi()
const components = ref<Component[]>([])
const component = ref<Component | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showWizard = ref(false)

onMounted(async () => {
  try {
    const slug = route.params.slug as string
    const fetched = await fetchComponents()
    components.value = fetched
    component.value = fetched.find(c => c.slug === slug) || null
    if (!component.value) {
      error.value = 'Компонент не найден'
    }
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div v-if="loading" class="text-center py-12 text-gray-500">Загрузка...</div>
    <div v-else-if="error" class="text-center py-12 text-red-500">{{ error }}</div>
    <div v-else-if="component" class="max-w-2xl mx-auto">
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-3xl font-bold mb-2">{{ component.name }}</h1>
          <SourceBadge :is-registry="component.is_registry" />
        </div>
        <span v-if="component.version" class="text-sm text-gray-500">v{{ component.version }}</span>
      </div>

      <div class="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <p class="text-gray-700 mb-4">{{ component.description }}</p>

        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-gray-500">Образ:</span>
            <code class="ml-2 text-xs bg-gray-100 px-2 py-1 rounded">{{ component.registry_url }}</code>
          </div>
          <div v-if="component.registry_number">
            <span class="text-gray-500">Реестр:</span>
            <span class="ml-2">{{ component.registry_number }}</span>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h2 class="font-semibold mb-4">Порты по умолчанию</h2>
        <div class="flex gap-2 flex-wrap">
          <span
            v-for="(intv, ext) in component.default_ports"
            :key="ext"
            class="px-3 py-1 bg-gray-100 rounded text-sm"
          >
            {{ ext }} → {{ intv }}
          </span>
        </div>
      </div>

      <button
        @click="showWizard = true"
        class="w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
      >
        ⚙️ Настроить и скачать
      </button>
    </div>

    <ConfigWizard
      v-if="showWizard && component"
      :component="component"
      @close="showWizard = false"
    />
  </div>
</template>
