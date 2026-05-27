<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import type { Stack } from '../types'
import AppIcon from '../components/AppIcon.vue'
import StackCard from '../components/StackCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'

const { fetchStacks } = useApi()
const stacks = ref<Stack[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    stacks.value = await fetchStacks()
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Готовые сборки</h1>
      <p class="text-gray-500 dark:text-slate-400 mt-1">
        Протестированные комбинации компонентов для быстрого развёртывания
      </p>
    </div>

    <div v-if="loading">
      <SkeletonGrid :count="4" />
    </div>
    <div v-else-if="error" class="text-center py-12">
      <div class="w-12 h-12 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
        <AppIcon name="warning" class="w-6 h-6 text-red-500" />
      </div>
      <p class="text-red-500 font-medium">{{ error }}</p>
    </div>
    <div v-else-if="stacks.length === 0" class="text-center py-12">
      <div class="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-slate-700 rounded-full flex items-center justify-center">
        <AppIcon name="stacks" class="w-8 h-8 text-gray-400" />
      </div>
      <p class="text-lg font-medium text-gray-900 dark:text-white">Пока нет готовых сборок</p>
      <p class="text-sm text-gray-500 dark:text-slate-400 mt-1">Воспользуйтесь конструктором, чтобы собрать свой стек</p>
      <router-link to="/constructor" class="inline-flex items-center gap-2 mt-4 px-5 py-2.5 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition">
        <AppIcon name="constructor" class="w-4 h-4" />
        Перейти в конструктор
      </router-link>
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <StackCard v-for="stack in stacks" :key="stack.slug" :stack="stack" />
    </div>
  </div>
</template>
