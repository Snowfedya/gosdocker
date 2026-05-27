<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useApi } from '../composables/useApi'
import type { Category } from '../types'
import AppIcon from '../components/AppIcon.vue'

const { fetchCategories } = useApi()
const categories = ref<Category[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const registryCount = computed(() =>
  categories.value.reduce((acc, c) => acc + (c.registry_count || 0), 0)
)
const communityCount = computed(() =>
  categories.value.reduce((acc, c) => acc + (c.community_count || 0), 0)
)

onMounted(async () => {
  try {
    categories.value = await fetchCategories()
  } catch (e) {
    error.value = 'Не удалось загрузить каталог'
  } finally {
    loading.value = false
  }
})

const features = [
  {
    icon: 'shield' as const,
    title: 'Из Реестра Минцифры',
    description: 'Компоненты с доказательной базой безопасности. Все сборки соответствуют требованиям к государственным информационным системам.',
    stats: 'registryCount',
  },
  {
    icon: 'layers' as const,
    title: 'Готовые Docker сборки',
    description: 'Docker Compose сценарии для быстрого развёртывания. Выберите компоненты и получите готовую конфигурацию одной кнопкой.',
    stats: null,
  },
  {
    icon: 'code' as const,
    title: 'Открытый исходный код',
    description: 'Прозрачная система сборки. Каждый компонент сопровождается Dockerfile, SBOM и отчётом Trivy для аудита безопасности.',
    stats: 'communityCount',
  },
]
</script>

<template>
  <div>
    <!-- Hero Section -->
    <section class="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <!-- Subtle grid pattern overlay -->
      <div class="absolute inset-0 opacity-[0.03]" style="background-image: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMCAwaDQwdjQwSDB6IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMC41IiBzdHJva2Utb3BhY2l0eT0iMC4xIi8+PC9zdmc+')" />

      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20 lg:py-24">
        <div class="text-center max-w-3xl mx-auto">
          <!-- Badge -->
          <div class="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-sm rounded-full text-sm text-slate-300 mb-6">
            <AppIcon name="shield" class="w-3.5 h-3.5 text-emerald-400" />
            Реестр Минцифры РФ
          </div>

          <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white mb-6 leading-tight tracking-tight">
            GosDocker
            <span class="block text-primary-300 text-2xl sm:text-3xl lg:text-4xl font-semibold mt-2">
              Docker Compose для государственных задач
            </span>
          </h1>

          <p class="text-lg sm:text-xl text-slate-300 mb-10 max-w-2xl mx-auto leading-relaxed">
            Готовые сборки ИТ-компонентов из Реестра Минцифры РФ и open-source решений.
            Angie PRO, PostgreSQL РЕД ОС, Nextcloud и другие.
          </p>

          <!-- CTA Buttons -->
          <div class="flex flex-col sm:flex-row justify-center gap-4 mb-12">
            <router-link
              to="/catalog"
              class="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-white text-slate-900 rounded-xl font-semibold hover:bg-slate-100 transition shadow-xl hover:shadow-2xl"
            >
              <AppIcon name="catalog" class="w-5 h-5" />
              Перейти в каталог
            </router-link>
            <router-link
              to="/constructor"
              class="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-white/10 backdrop-blur-sm text-white rounded-xl font-semibold border border-white/20 hover:bg-white/20 transition"
            >
              <AppIcon name="constructor" class="w-5 h-5" />
              Собрать свой стек
            </router-link>
          </div>

          <!-- Stats -->
          <div class="flex justify-center gap-8 sm:gap-12">
            <div class="text-center">
              <div class="text-3xl sm:text-4xl font-bold text-white">{{ registryCount }}</div>
              <div class="text-sm text-slate-400 mt-1">из Реестра РФ</div>
            </div>
            <div class="w-px bg-white/20" />
            <div class="text-center">
              <div class="text-3xl sm:text-4xl font-bold text-white">{{ communityCount }}</div>
              <div class="text-sm text-slate-400 mt-1">решений комьюнити</div>
            </div>
            <div class="w-px bg-white/20" />
            <div class="text-center">
              <div class="text-3xl sm:text-4xl font-bold text-white">{{ categories.length }}</div>
              <div class="text-sm text-slate-400 mt-1">категорий</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-10 relative z-10 mb-12">
      <div class="grid md:grid-cols-3 gap-6">
        <div
          v-for="(feature, i) in features"
          :key="i"
          class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
        >
          <div class="w-10 h-10 bg-primary-50 dark:bg-primary-900/30 rounded-lg flex items-center justify-center mb-4">
            <AppIcon :name="feature.icon" class="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <h3 class="text-base font-semibold text-gray-900 dark:text-white mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-gray-500 dark:text-slate-400 leading-relaxed">{{ feature.description }}</p>
        </div>
      </div>
    </section>

    <!-- Quick Access Categories -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
      <div class="text-center mb-8">
        <h2 class="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Категории компонентов</h2>
        <p class="text-gray-500 dark:text-slate-400 mt-2">Выберите категорию для быстрого доступа к компонентам</p>
      </div>

      <div v-if="loading" class="flex flex-wrap justify-center gap-3">
        <div v-for="i in 4" :key="i" class="skeleton h-12 w-36 rounded-lg" />
      </div>
      <div v-else-if="error" class="text-center text-red-500">{{ error }}</div>
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        <router-link
          v-for="cat in categories"
          :key="cat.id"
          :to="`/catalog?category=${cat.slug}`"
          class="group relative bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md transition-all duration-200 overflow-hidden"
        >
          <div class="relative z-10">
            <div class="text-lg font-medium text-gray-900 dark:text-white mb-1">{{ cat.name }}</div>
            <div class="text-sm text-gray-500 dark:text-slate-400">
              <span class="font-medium text-primary-600 dark:text-primary-400">{{ cat.components_count }}</span>
              <span v-if="cat.components_count !== undefined"> компонентов</span>
            </div>
          </div>
          <!-- Subtle accent bar on hover -->
          <div class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
        </router-link>
      </div>
    </section>

    <!-- Bottom CTA -->
    <section class="bg-gradient-to-r from-slate-800 to-slate-900 py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-2xl sm:text-3xl font-bold text-white mb-3">Готовы к развёртыванию?</h2>
        <p class="text-slate-400 mb-8 max-w-lg mx-auto">
          Выберите готовую сборку или соберите собственный стек из компонентов Реестра
        </p>
        <div class="flex justify-center gap-4">
          <router-link
            to="/stacks"
            class="inline-flex items-center gap-2 px-6 py-3 bg-white text-slate-900 rounded-xl font-semibold hover:bg-slate-100 transition shadow-lg"
          >
            <AppIcon name="stacks" class="w-5 h-5" />
            Готовые сборки
          </router-link>
          <router-link
            to="/constructor"
            class="inline-flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur-sm text-white rounded-xl font-semibold border border-white/20 hover:bg-white/20 transition"
          >
            <AppIcon name="constructor" class="w-5 h-5" />
            Конструктор
          </router-link>
        </div>
      </div>
    </section>
  </div>
</template>
