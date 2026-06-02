<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'
import type { Stack } from '../types'
import AppIcon from '../components/AppIcon.vue'
import SourceBadge from '../components/SourceBadge.vue'

const route = useRoute()
const router = useRouter()
const { fetchStacks, generateStack } = useApi()

const stack = ref<Stack | null>(null)
const loading = ref(true)
const downloading = ref(false)
const error = ref<string | null>(null)
const selectedProfile = ref<string>('standard')

onMounted(async () => {
  const slug = route.params.slug as string
  try {
    const allStacks = await fetchStacks()
    const found = allStacks.find(s => s.slug === slug)
    if (!found) {
      error.value = 'Сборка не найдена'
      return
    }
    stack.value = found
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
})

async function downloadStack() {
  if (!stack.value) return
  downloading.value = true
  try {
    const slugs = stack.value.components.map(c => c.slug)
    const blob = await generateStack(slugs, {}, selectedProfile.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${stack.value.slug}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed', e)
  } finally {
    downloading.value = false
  }
}

function openConstructor() {
  if (!stack.value) return
  const slugs = stack.value.components.map(c => c.slug).join(',')
  router.push(`/constructor?components=${slugs}`)
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Breadcrumbs -->
    <nav class="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-6">
      <router-link to="/stacks" class="hover:text-primary-600 dark:hover:text-primary-400 transition">&larr; Все сборки</router-link>
      <span v-if="stack" class="text-gray-300 dark:text-slate-600">/</span>
      <span v-if="stack" class="text-gray-900 dark:text-white font-medium">{{ stack.name }}</span>
    </nav>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-16">
      <AppIcon name="spinner" class="w-8 h-8 mx-auto animate-spin text-primary-500" />
      <p class="text-sm text-gray-400 mt-3">Загрузка...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-16">
      <div class="w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
        <AppIcon name="warning" class="w-8 h-8 text-red-500" />
      </div>
      <p class="text-lg font-medium text-gray-900 dark:text-white mb-2">Ошибка</p>
      <p class="text-sm text-gray-500 dark:text-slate-400">{{ error }}</p>
      <router-link to="/stacks" class="inline-flex items-center gap-2 mt-6 px-5 py-2.5 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition">
        <AppIcon name="arrow-left" class="w-4 h-4" />
        Вернуться к сборкам
      </router-link>
    </div>

    <!-- Stack detail -->
    <div v-else-if="stack" class="max-w-3xl">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center gap-3 mb-3">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ stack.name }}</h1>
          <span v-if="stack.is_featured" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
            <AppIcon name="star" class="w-3.5 h-3.5" />
            Рекомендуемая
          </span>
        </div>
        <p class="text-gray-500 dark:text-slate-400">{{ stack.description }}</p>
      </div>

      <!-- Components list -->
      <div class="mb-8">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Компоненты сборки ({{ stack.components.length }})
        </h2>
        <div class="space-y-3">
          <div
            v-for="comp in stack.components"
            :key="comp.slug"
            class="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm"
          >
            <div class="w-10 h-10 bg-gray-100 dark:bg-slate-700 rounded-lg flex items-center justify-center shrink-0">
              <AppIcon name="cube" class="w-5 h-5 text-gray-500 dark:text-slate-400" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <router-link
                  :to="`/components/${comp.slug}`"
                  class="font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 transition truncate"
                >
                  {{ comp.name }}
                </router-link>
                <SourceBadge :is-registry="comp.is_registry" />
              </div>
              <p v-if="comp.image" class="text-xs text-gray-400 dark:text-slate-500 mt-0.5 font-mono truncate">
                {{ comp.image }}
              </p>
            </div>
            <router-link
              :to="`/components/${comp.slug}`"
              class="shrink-0 text-sm text-primary-600 dark:text-primary-400 hover:underline"
            >
              Подробнее
            </router-link>
          </div>
        </div>
      </div>

      <!-- Download section -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Скачать сборку</h2>

        <div class="flex flex-col sm:flex-row gap-3 sm:items-end mb-4">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-500 dark:text-slate-400 mb-1.5">Профиль безопасности</label>
            <select
              v-model="selectedProfile"
              class="w-full sm:w-64 px-3 py-2 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="basic">Базовый</option>
              <option value="standard">Стандартный</option>
              <option value="hardened">Усиленный</option>
            </select>
          </div>
          <button
            @click="downloadStack"
            :disabled="downloading"
            class="inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition shadow-sm"
          >
            <AppIcon :name="downloading ? 'refresh' : 'download'" class="w-4 h-4" :class="downloading ? 'animate-spin' : ''" />
            {{ downloading ? 'Подготовка...' : 'Скачать .zip' }}
          </button>
        </div>

        <div class="pt-4 border-t border-gray-100 dark:border-slate-700">
          <router-link
            :to="`/constructor?components=${stack.components.map(c => c.slug).join(',')}`"
            class="inline-flex items-center gap-2 text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            <AppIcon name="constructor" class="w-4 h-4" />
            Редактировать сборку в конструкторе
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
