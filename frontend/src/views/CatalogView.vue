<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import type { Category } from '../types'
import ComponentCard from '../components/ComponentCard.vue'

const { fetchCategories, fetchComponents } = useApi()
const categories = ref<Category[]>([])
const selectedCategory = ref<string | null>(null)
const components = ref<Component[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    categories.value = await fetchCategories()
    components.value = await fetchComponents()
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
})

async function selectCategory(slug: string | null) {
  selectedCategory.value = slug
  loading.value = true
  try {
    components.value = await fetchComponents(slug || undefined)
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-8">Каталог компонентов</h1>

    <!-- Category filters -->
    <div class="flex gap-2 mb-8 flex-wrap">
      <button
        @click="selectCategory(null)"
        :class="[
          'px-4 py-2 rounded-full text-sm font-medium transition',
          selectedCategory === null
            ? 'bg-gray-900 text-white'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        ]"
      >
        Все
      </button>
      <button
        v-for="cat in categories"
        :key="cat.slug"
        @click="selectCategory(cat.slug)"
        :class="[
          'px-4 py-2 rounded-full text-sm font-medium transition',
          selectedCategory === cat.slug
            ? 'bg-gray-900 text-white'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        ]"
      >
        {{ cat.icon }} {{ cat.name }}
        <span class="text-xs opacity-70">({{ cat.components_count }})</span>
      </button>
    </div>

    <!-- Components grid -->
    <div v-if="loading" class="text-center py-12 text-gray-500">Загрузка...</div>
    <div v-else-if="error" class="text-center py-12 text-red-500">{{ error }}</div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <ComponentCard
        v-for="comp in components"
        :key="comp.slug"
        :component="comp"
      />
    </div>
  </div>
</template>
