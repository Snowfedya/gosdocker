<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import type { Stack } from '../types'
import StackCard from '../components/StackCard.vue'

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
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-2">Готовые сборки</h1>
    <p class="text-gray-600 mb-8">Протестированные комбинации компонентов</p>

    <div v-if="loading" class="text-center py-12 text-gray-500">Загрузка...</div>
    <div v-else-if="error" class="text-center py-12 text-red-500">{{ error }}</div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <StackCard v-for="stack in stacks" :key="stack.slug" :stack="stack" />
    </div>
  </div>
</template>
