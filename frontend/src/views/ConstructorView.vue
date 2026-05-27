<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useApi } from '../composables/useApi'
import type { RegistryComponent, SecurityProfile, ConstructorDiagnostic } from '../types'
import AppIcon from '../components/AppIcon.vue'

const { fetchRegistry, constructorDiagnostic, constructorGenerate, fetchProfiles } = useApi()

const registry = ref<RegistryComponent[]>([])
const profiles = ref<SecurityProfile[]>([])
const selected = ref<Record<string, boolean>>({})
const selectedProfile = ref('standard')
const loading = ref(true)
const generating = ref(false)
const error = ref<string | null>(null)
const result = ref<ConstructorDiagnostic | null>(null)
const showResult = ref(false)

const selectedCount = computed(() => Object.values(selected.value).filter(Boolean).length)

onMounted(async () => {
  try {
    const [reg, profs] = await Promise.all([fetchRegistry(), fetchProfiles()])
    registry.value = reg
    profiles.value = profs
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
})

function toggleSelection(slug: string) {
  selected.value[slug] = !selected.value[slug]
}

async function runDiagnostic() {
  const selectedSlugs = Object.entries(selected.value)
    .filter(([_, v]) => v)
    .map(([k]) => k)

  if (selectedSlugs.length === 0) {
    error.value = 'Выберите хотя бы один компонент'
    return
  }

  error.value = null
  try {
    result.value = await constructorDiagnostic({
      components: selectedSlugs,
      profile: selectedProfile.value,
      configs: {},
    })
    showResult.value = true
  } catch (e) {
    error.value = 'Ошибка диагностики'
  }
}

async function generate() {
  const selectedSlugs = Object.entries(selected.value)
    .filter(([_, v]) => v)
    .map(([k]) => k)

  if (selectedSlugs.length === 0) return

  generating.value = true
  error.value = null

  try {
    const blob = await constructorGenerate({
      components: selectedSlugs,
      profile: selectedProfile.value,
      configs: {},
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gosdocker-stack-${selectedSlugs[0]}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = 'Ошибка генерации'
  } finally {
    generating.value = false
  }
}

const categoryGroups = computed(() => {
  const groups: Record<string, RegistryComponent[]> = {}
  for (const comp of registry.value) {
    const cat = comp.category || 'other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(comp)
  }
  return groups
})

const categoryLabels: Record<string, string> = {
  'web-servers': 'Веб-серверы',
  'databases': 'Базы данных',
  'file-storage': 'Файловые хранилища',
  'monitoring': 'Мониторинг',
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex items-center gap-3 mb-8">
      <div class="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
        <AppIcon name="constructor" class="w-5 h-5 text-primary-600 dark:text-primary-400" />
      </div>
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Конструктор стека</h1>
        <p class="text-gray-500 dark:text-slate-400 text-sm">Соберите Docker-стек из компонентов Реестра</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left: Selection panel -->
      <div class="lg:col-span-2">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Выберите компоненты:</h2>

        <div v-if="loading" class="text-center py-8 text-gray-500">Загрузка...</div>
        <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg text-sm mb-4">{{ error }}</div>

        <div v-for="(comps, cat) in categoryGroups" :key="cat" class="mb-6">
          <h3 class="text-sm font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3">
            {{ categoryLabels[cat] || cat }}
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label
              v-for="comp in comps"
              :key="comp.slug"
              class="flex items-center gap-3 p-3.5 rounded-lg border-2 cursor-pointer transition-all duration-150"
              :class="selected[comp.slug]
                ? 'border-primary-400 dark:border-primary-500 bg-primary-50 dark:bg-primary-900/20 shadow-sm'
                : 'border-gray-200 dark:border-slate-700 hover:border-gray-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800'"
            >
              <input
                type="checkbox"
                :checked="selected[comp.slug] || false"
                @change="toggleSelection(comp.slug)"
                class="w-4 h-4 text-primary-600 rounded border-gray-300 dark:border-slate-600 focus:ring-primary-500"
              />
              <div class="flex-1 min-w-0">
                <div class="font-medium text-sm text-gray-900 dark:text-white truncate">{{ comp.name }}</div>
                <div class="text-xs text-gray-400 dark:text-slate-500">v{{ comp.version }}</div>
              </div>
              <span class="shrink-0 text-[11px] text-gray-400 dark:text-slate-500 bg-gray-50 dark:bg-slate-700/50 px-2 py-0.5 rounded">
                {{ comp.provides.join(', ') }}
              </span>
            </label>
          </div>
        </div>
      </div>

      <!-- Right: Config panel -->
      <div class="lg:col-span-1">
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6 sticky top-20">
          <div class="flex items-center gap-2 mb-5">
            <AppIcon name="settings" class="w-5 h-5 text-gray-500 dark:text-slate-400" />
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Настройки</h2>
          </div>

          <div class="mb-5">
            <label class="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
              Профиль безопасности
            </label>
            <select
              v-model="selectedProfile"
              class="w-full px-3 py-2.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition"
            >
              <option
                v-for="p in profiles"
                :key="p.slug"
                :value="p.slug"
              >
                {{ p.label }}
              </option>
            </select>
            <p v-if="profiles.find(p => p.slug === selectedProfile)" class="text-xs text-gray-400 dark:text-slate-500 mt-1.5">
              {{ profiles.find(p => p.slug === selectedProfile)?.description }}
            </p>
          </div>

          <div class="mb-6 pt-4 border-t border-gray-100 dark:border-slate-700">
            <div class="flex items-baseline justify-between">
              <span class="text-sm text-gray-600 dark:text-slate-400">Выбрано:</span>
              <span class="text-2xl font-bold text-primary-600 dark:text-primary-400">{{ selectedCount }}</span>
            </div>
            <div class="text-xs text-gray-400 dark:text-slate-500 mt-1">
              Зависимости будут добавлены автоматически
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <button
              @click="runDiagnostic"
              :disabled="selectedCount === 0"
              class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-700 border-2 border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-40 transition"
            >
              <AppIcon name="check" class="w-4 h-4" />
              Проверить
            </button>
            <button
              @click="generate"
              :disabled="selectedCount === 0 || generating"
              class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-40 transition shadow-sm"
            >
              <AppIcon :name="generating ? 'refresh' : 'download'" class="w-4 h-4" :class="generating ? 'animate-spin' : ''" />
              {{ generating ? 'Генерация...' : 'Сгенерировать и скачать' }}
            </button>
          </div>

          <!-- Diagnostic result -->
          <div v-if="showResult && result" class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700">
            <div class="flex items-center gap-2 mb-4">
              <AppIcon name="check" class="w-4 h-4 text-green-500" />
              <h3 class="font-medium text-gray-900 dark:text-white text-sm">Результат проверки</h3>
            </div>

            <div class="mb-3">
              <div class="text-xs text-gray-500 dark:text-slate-400 mb-2">Разрешённые компоненты:</div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="slug in result.resolved"
                  :key="slug"
                  class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md"
                  :class="result.auto_added.some(a => a.slug === slug)
                    ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800'
                    : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'"
                >
                  {{ slug }}
                  <span v-if="result.auto_added.some(a => a.slug === slug)" class="text-[10px] opacity-60">(auto)</span>
                </span>
              </div>
            </div>

            <div v-if="result.auto_added.length" class="text-xs bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-100 dark:border-yellow-800/30 p-3 rounded-lg mb-3">
              <p class="font-medium text-yellow-700 dark:text-yellow-300 mb-1">Автоматически добавлены:</p>
              <ul class="text-yellow-600 dark:text-yellow-400 space-y-0.5">
                <li v-for="a in result.auto_added" :key="a.slug" class="flex items-center gap-1">
                  <AppIcon name="arrow-right" class="w-3 h-3 shrink-0" />
                  {{ a.slug }} — {{ a.reason }}
                </li>
              </ul>
            </div>

            <div v-if="result.errors.length" class="text-xs bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800/30 p-3 rounded-lg">
              <p class="font-medium text-red-600 dark:text-red-400">{{ result.errors.join(', ') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
