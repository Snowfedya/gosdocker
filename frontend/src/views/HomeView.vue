<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useApi } from '../composables/useApi'
import type { Category } from '../types'

const { fetchCategories } = useApi()
const categories = ref<Category[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const registryCount = computed(() => categories.value.reduce((acc, c) => acc + (c.registry_count || 0), 0))
const communityCount = computed(() => categories.value.reduce((acc, c) => acc + (c.community_count || 0), 0))

onMounted(async () => {
  try {
    categories.value = await fetchCategories()
  } catch (e) {
    error.value = 'Не удалось загрузить каталог'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <!-- Hero Section -->
    <section class="bg-gradient-to-br from-blue-50 to-indigo-100 border-b">
      <div class="container mx-auto px-4 py-16 text-center">
        <h1 class="text-5xl font-bold text-gray-900 mb-4">GosDocker</h1>
        <p class="text-xl text-gray-600 mb-8">Каталог Docker Compose-сборок для госструктур</p>
        <div class="flex justify-center gap-4 text-sm">
          <span class="px-4 py-2 bg-green-100 text-green-700 rounded-full font-medium">
            🏛 {{ registryCount }}
            из Реестра РФ
          </span>
          <span class="px-4 py-2 bg-blue-100 text-blue-700 rounded-full font-medium">
            📦 {{ communityCount }}
            решений комьюнити
          </span>
        </div>
      </div>
    </section>

    <!-- Navigation Cards -->
    <section class="container mx-auto px-4 py-12">
      <h2 class="text-2xl font-bold text-gray-900 mb-8 text-center">Быстрый старт</h2>
      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">

        <!-- Полный стек (РФ) -->
        <router-link to="/stacks"
          class="group block p-6 bg-white rounded-xl shadow-sm border border-green-200 hover:shadow-md hover:border-green-400 transition-all">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-3xl">🏛</span>
            <h3 class="text-lg font-semibold text-gray-900">Полный стек (РФ)</h3>
          </div>
          <p class="text-gray-600 text-sm mb-4">
            Angie PRO + PostgreSQL РЕД ОС + Nextcloud — все из Реестра Минцифры
          </p>
          <span class="inline-flex items-center text-green-600 text-sm font-medium group-hover:gap-2 transition-all">
            Скачать одной кнопкой →
          </span>
        </router-link>

        <!-- Полный стек Community -->
        <router-link to="/stacks"
          class="group block p-6 bg-white rounded-xl shadow-sm border border-blue-200 hover:shadow-md hover:border-blue-400 transition-all">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-3xl">📦</span>
            <h3 class="text-lg font-semibold text-gray-900">Полный стек Community</h3>
          </div>
          <p class="text-gray-600 text-sm mb-4">
            nginx + PostgreSQL + Prometheus + Grafana — популярные open-source решения
          </p>
          <span class="inline-flex items-center text-blue-600 text-sm font-medium group-hover:gap-2 transition-all">
            Скачать одной кнопкой →
          </span>
        </router-link>

        <!-- Каталог компонентов -->
        <router-link to="/catalog"
          class="group block p-6 bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-gray-400 transition-all">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-3xl">📋</span>
            <h3 class="text-lg font-semibold text-gray-900">Каталог компонентов</h3>
          </div>
          <p class="text-gray-600 text-sm mb-4">
            Выберите нужные компоненты и скачайте с настройками
          </p>
          <span class="inline-flex items-center text-gray-600 text-sm font-medium group-hover:gap-2 transition-all">
            Перейти в каталог →
          </span>
        </router-link>

      </div>
    </section>

    <!-- Categories Overview -->
    <section class="container mx-auto px-4 pb-12">
      <h2 class="text-2xl font-bold text-gray-900 mb-6 text-center">Категории</h2>
      <div class="flex flex-wrap justify-center gap-3">
        <router-link
          v-for="cat in categories"
          :key="cat.id"
          :to="`/catalog?category=${cat.slug}`"
          class="px-4 py-2 bg-white rounded-lg border border-gray-200 hover:border-gray-400 hover:shadow-sm transition-all text-sm">
          <span>{{ cat.icon }}</span>
          {{ cat.name }}
          <span class="text-gray-400">({{ cat.components_count }})</span>
        </router-link>
      </div>
    </section>

    <!-- Footer -->
    <div v-if="loading" class="text-center py-8 text-gray-500">Загрузка...</div>
    <div v-if="error" class="text-center py-8 text-red-500">{{ error }}</div>
  </div>
</template>
