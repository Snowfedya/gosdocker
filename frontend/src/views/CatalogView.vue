<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'
import type { Category, Component } from '../types'
import AppIcon from '../components/AppIcon.vue'
import ComponentCard from '../components/ComponentCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'

const route = useRoute()
const { fetchCategories, fetchComponents } = useApi()

const categories = ref<Category[]>([])
const components = ref<Component[]>([])
const selectedCategory = ref<string | null>(null)
const searchQuery = ref('')
const loading = ref(true)
const error = ref<string | null>(null)
const registryOnly = ref(false)

const buildMethodLabels: Record<string, string> = {
  configure_make: './configure && make',
  go_build: 'Go build',
  php_extract: 'PHP extraction',
  node_go: 'Node.js + Go',
  cmake_make: 'cmake + make',
}

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const [cats, comps] = await Promise.all([
      fetchCategories(),
      fetchComponents(selectedCategory.value || undefined),
    ])
    categories.value = cats
    components.value = comps
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const catParam = route.query.category as string | undefined
  if (catParam) {
    selectedCategory.value = catParam
  }
  if (route.query.registry === 'true') {
    registryOnly.value = true
  }
  loadData()
})

watch(() => route.query.category, (newCat) => {
  if (newCat && newCat !== selectedCategory.value) {
    selectedCategory.value = newCat as string
    loadData()
  }
})

async function selectCategory(slug: string | null) {
  selectedCategory.value = slug
  await loadData()
}

function toggleRegistry() {
  registryOnly.value = !registryOnly.value
}

const filteredComponents = computed(() => {
  let result = components.value
  if (registryOnly.value) {
    result = result.filter(c => c.has_registry)
  }
  if (!searchQuery.value) return result
  const q = searchQuery.value.toLowerCase().trim()
  return result.filter(c =>
    c.name.toLowerCase().includes(q) ||
    c.description?.toLowerCase().includes(q) ||
    c.slug.toLowerCase().includes(q)
  )
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Каталог компонентов</h1>
        <p class="text-gray-500 dark:text-slate-400 mt-1">
          Docker-образы для государственных информационных систем
        </p>
      </div>

      <!-- Search -->
      <div class="relative w-full sm:w-72">
        <AppIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Поиск компонентов..."
          class="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
        />
      </div>
    </div>

    <!-- Category filters -->
    <div class="flex gap-2 mb-4 flex-wrap">
      <button
        @click="selectCategory(null)"
        :class="[
          'px-4 py-2 rounded-full text-sm font-medium transition',
          selectedCategory === null
            ? 'bg-primary-600 text-white shadow-sm'
            : 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-600'
        ]"
      >
        Все
      </button>
      <button
        v-for="cat in categories"
        :key="cat.slug"
        @click="selectCategory(cat.slug)"
        :class="[
          'inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition',
          selectedCategory === cat.slug
            ? 'bg-primary-600 text-white shadow-sm'
            : 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-600'
        ]"
      >
        {{ cat.name }}
        <span v-if="cat.components_count !== undefined" class="text-xs opacity-70">({{ cat.components_count }})</span>
      </button>
    </div>

    <!-- Registry filter toggle -->
    <div class="flex items-center gap-3 mb-6">
      <label class="inline-flex items-center gap-2 cursor-pointer select-none">
        <input type="checkbox" :checked="registryOnly" @change="toggleRegistry" class="sr-only peer" />
        <div class="w-9 h-5 bg-gray-200 dark:bg-slate-600 rounded-full peer-checked:bg-primary-600 relative transition after:content-[''] after:absolute after:top-0.5 after:start-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full"></div>
        <span class="text-sm text-gray-600 dark:text-slate-400 font-medium">Только из реестра</span>
      </label>
      <AppIcon name="shield" class="w-4 h-4 text-emerald-500" v-if="registryOnly" />
    </div>

    <!-- Results -->
    <div v-if="loading">
      <SkeletonGrid :count="6" />
    </div>
    <div v-else-if="error" class="text-center py-12">
      <div class="w-12 h-12 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
        <AppIcon name="warning" class="w-6 h-6 text-red-500" />
      </div>
      <p class="text-red-500 font-medium">{{ error }}</p>
    </div>
    <div v-else-if="filteredComponents.length === 0" class="text-center py-12">
      <div class="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-slate-700 rounded-full flex items-center justify-center">
        <AppIcon name="search" class="w-8 h-8 text-gray-400" />
      </div>
      <p class="text-lg font-medium text-gray-900 dark:text-white">Ничего не найдено</p>
      <p class="text-sm text-gray-500 dark:text-slate-400 mt-1">Попробуйте изменить фильтры или поисковый запрос</p>
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <ComponentCard
        v-for="comp in filteredComponents"
        :key="comp.slug"
        :component="comp"
      />
    </div>
  </div>
</template>
