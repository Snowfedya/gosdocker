<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '../composables/useApi'
import type { Component, SecurityReport } from '../types'
import AppIcon from '../components/AppIcon.vue'
import SourceBadge from '../components/SourceBadge.vue'
import ConfigWizard from '../components/ConfigWizard.vue'

const route = useRoute()
const { fetchComponents, fetchRegistryManifest, buildComponent, fetchReports, fetchProfiles } = useApi()

const component = ref<Component | null>(null)
const registryManifest = ref<Record<string, unknown> | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showWizard = ref(false)
const activeTab = ref<'info' | 'ports' | 'env' | 'registry' | 'security'>('info')

// Security report state
const report = ref<SecurityReport | null>(null)
const reportLoading = ref(false)
const reportError = ref<string | null>(null)
const selectedProfile = ref<string>('standard')
const profiles = ref<{ slug: string; label: string; description: string }[]>([])
const profilesLoading = ref(false)

onMounted(async () => {
  try {
    const slug = route.params.slug as string

    const fetched = await fetchComponents()
    const found = fetched.find(c => c.slug === slug)
    if (found) {
      component.value = found
    }

    try {
      registryManifest.value = await fetchRegistryManifest(slug)
    } catch {
      // Not found in registry — that's OK
    }

    if (!found) {
      error.value = 'Компонент не найден'
    }

    // Load profiles and existing reports if this is a registry component
    if (registryManifest.value) {
      loadProfiles()
      loadExistingReport()
    }
  } catch (e) {
    error.value = 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
})

async function loadProfiles() {
  profilesLoading.value = true
  try {
    profiles.value = await fetchProfiles()
  } catch {
    // Profiles optional
  } finally {
    profilesLoading.value = false
  }
}

async function loadExistingReport() {
  const slug = route.params.slug as string
  try {
    report.value = await fetchReports(slug)
  } catch {
    // No report yet — that's OK
  }
}

async function runSecurityScan() {
  const slug = route.params.slug as string
  reportLoading.value = true
  reportError.value = null
  report.value = null
  try {
    report.value = await buildComponent(slug, selectedProfile.value)
  } catch (e) {
    reportError.value = 'Ошибка запуска проверки безопасности'
  } finally {
    reportLoading.value = false
  }
}

const manifestPorts = computed(() => {
  if (!registryManifest.value) return {}
  return (registryManifest.value as any)?.component?.ports || {}
})

const manifestEnv = computed(() => {
  if (!registryManifest.value) return {}
  return (registryManifest.value as any)?.component?.default_env || {}
})

const tabs = computed(() => {
  const t = [
    { id: 'info' as const, label: 'Информация', icon: 'info' as const },
    { id: 'ports' as const, label: 'Порты', icon: 'port' as const },
    { id: 'env' as const, label: 'Переменные', icon: 'key' as const },
  ]
  if (registryManifest.value) {
    t.push({ id: 'registry' as const, label: 'Сборка', icon: 'cube' as const })
    t.push({ id: 'security' as const, label: 'Безопасность', icon: 'shield' as const })
  }
  return t
})

const buildMethodLabels: Record<string, string> = {
  configure_make: './configure && make',
  go_build: 'Go build',
  php_extract: 'PHP extraction',
  node_go: 'Node.js + Go',
  cmake_make: 'cmake + make',
  make: 'make',
}

const severityColor = (sev: string): string => {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    HIGH: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
    MEDIUM: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    LOW: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    UNKNOWN: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  }
  return colors[sev] || colors.UNKNOWN
}

async function dlDockerfile(slug: string) {
  const { downloadDockerfile } = useApi()
  try {
    const blob = await downloadDockerfile(slug)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${slug}.Dockerfile`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed', e)
  }
}

async function dlManifest(slug: string) {
  const { downloadManifest } = useApi()
  try {
    const blob = await downloadManifest(slug)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${slug}-manifest.yml`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed', e)
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div v-if="loading" class="text-center py-16">
      <div class="inline-block w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      <p class="mt-4 text-gray-500">Загрузка...</p>
    </div>

    <div v-else-if="error" class="text-center py-16">
      <div class="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-slate-700 rounded-full flex items-center justify-center">
        <AppIcon name="search" class="w-8 h-8 text-gray-400" />
      </div>
      <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">{{ error }}</h2>
      <p class="text-gray-500 dark:text-slate-400">Компонент не найден или был удалён</p>
    </div>

    <div v-else-if="component" class="max-w-4xl mx-auto">
      <!-- Breadcrumb -->
      <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-6">
        <router-link to="/catalog" class="hover:text-primary-600 transition flex items-center gap-1">
          <AppIcon name="catalog" class="w-3.5 h-3.5" />
          Каталог
        </router-link>
        <span class="text-gray-300 dark:text-slate-600">/</span>
        <span class="text-gray-900 dark:text-white font-medium">{{ component.name }}</span>
      </div>

      <!-- Header Card -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6 mb-6">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{{ component.name }}</h1>
            <SourceBadge :is-registry="component.is_registry" />
          </div>
          <span v-if="component.version" class="px-3 py-1 bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 rounded-lg text-sm font-mono">
            v{{ component.version }}
          </span>
        </div>

        <p class="text-gray-600 dark:text-slate-400 leading-relaxed mb-4">
          {{ component.description || 'Нет описания' }}
        </p>

        <div class="flex flex-wrap gap-4 text-sm">
          <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
            <AppIcon name="cube" class="w-4 h-4 text-gray-400" />
            <div>
              <span class="text-gray-500 dark:text-slate-400 block text-xs">Образ</span>
              <code class="text-gray-900 dark:text-white font-mono text-xs">{{ component.registry_url }}</code>
            </div>
          </div>
          <div v-if="component.registry_number" class="flex items-center gap-2 px-3 py-2 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg">
            <AppIcon name="shield" class="w-4 h-4 text-emerald-500" />
            <div>
              <span class="text-emerald-600 dark:text-emerald-400 block text-xs">Реестр</span>
              <span class="text-emerald-700 dark:text-emerald-300 font-medium text-sm">{{ component.registry_number }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div class="flex border-b border-gray-200 dark:border-slate-700 overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'inline-flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition -mb-px shrink-0',
              activeTab === tab.id
                ? 'border-primary-600 text-primary-700 dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
            ]"
          >
            <AppIcon :name="tab.icon" class="w-4 h-4" />
            {{ tab.label }}
          </button>
        </div>

        <div class="p-6">
          <!-- Info Tab -->
          <div v-if="activeTab === 'info'" class="space-y-6">
            <div>
              <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Категория</h3>
              <span class="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 rounded-lg text-sm text-gray-700 dark:text-slate-300">
                {{ component.category || 'Не указана' }}
              </span>
            </div>
            <div>
              <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Источник образа</h3>
              <code class="text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-slate-700 px-3 py-1.5 rounded-lg block truncate">
                {{ component.image_source || component.registry_url }}
              </code>
            </div>
          </div>

          <!-- Ports Tab -->
          <div v-if="activeTab === 'ports'">
            <div v-if="Object.keys(component.default_ports).length === 0 && Object.keys(manifestPorts).length === 0" class="text-center py-6 text-gray-400">
              Нет настраиваемых портов
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div v-for="(intv, ext) in { ...component.default_ports, ...manifestPorts }" :key="ext"
                class="flex items-center justify-between p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                <span class="text-sm text-gray-700 dark:text-slate-300 flex items-center gap-2">
                  <AppIcon name="port" class="w-3.5 h-3.5 text-gray-400" />
                  Порт {{ ext }}
                </span>
                <code class="text-sm text-primary-600 dark:text-primary-400 font-mono">{{ intv }}</code>
              </div>
            </div>
          </div>

          <!-- Env Tab -->
          <div v-if="activeTab === 'env'">
            <div v-if="Object.keys(component.default_env).length === 0 && Object.keys(manifestEnv).length === 0" class="text-center py-6 text-gray-400">
              Нет переменных окружения
            </div>
            <div class="space-y-2">
              <div v-for="(value, key) in { ...component.default_env, ...manifestEnv }" :key="key"
                class="flex items-center p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                <AppIcon name="key" class="w-3.5 h-3.5 text-gray-400 mr-3" />
                <code class="text-sm font-mono text-gray-800 dark:text-slate-200 min-w-[200px]">{{ key }}</code>
                <span class="text-sm text-gray-500 dark:text-slate-400 ml-4">= {{ value }}</span>
              </div>
            </div>
          </div>

          <!-- Registry Tab (structured) -->
          <div v-if="activeTab === 'registry' && registryManifest">
            <div class="space-y-6">
              <!-- Build method -->
              <div>
                <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Метод сборки</h3>
                <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium"
                  :class="
                    registryManifest.component?.build_method === 'go_build' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300' :
                    registryManifest.component?.build_method === 'php_extract' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
                    registryManifest.component?.build_method === 'node_go' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' :
                    'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'"
                >
                  <AppIcon name="cube" class="w-4 h-4" />
                  {{ buildMethodLabels[registryManifest.component?.build_method] || registryManifest.component?.build_method }}
                </span>
              </div>

              <!-- Source URL -->
              <div v-if="registryManifest.component?.source_url">
                <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Исходный код</h3>
                <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                  <AppIcon :name="(registryManifest.component?.source_url as string || '').includes('github.com') ? 'github' : 'shield'"
                    class="w-4 h-4 shrink-0"
                    :class="(registryManifest.component?.source_url as string || '').includes('github.com') ? 'text-gray-400' : 'text-emerald-500'" />
                  <a
                    :href="registryManifest.component?.source_url as string"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-sm text-primary-600 dark:text-primary-400 truncate flex-1 hover:underline"
                  >
                    {{ (registryManifest.component?.source_url as string || '').replace(/^https?:\/\//, '') }}
                  </a>
                  <span
                    class="shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded"
                    :class="(registryManifest.component?.source_url as string || '').includes('github.com')
                      ? 'text-gray-500 dark:text-slate-400 bg-gray-200 dark:bg-slate-600'
                      : 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30'"
                  >
                    {{ (registryManifest.component?.source_url as string || '').includes('github.com') ? 'GitHub' : 'Офиц.' }}
                  </span>
                </div>
              </div>

              <!-- Community URL -->
              <div v-if="registryManifest.component?.community_url">
                <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Community</h3>
                <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                  <AppIcon name="github" class="w-4 h-4 text-gray-400 shrink-0" />
                  <a
                    :href="registryManifest.component?.community_url as string"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-sm text-gray-600 dark:text-slate-300 truncate flex-1 hover:underline"
                  >
                    {{ (registryManifest.component?.community_url as string || '').replace(/^https?:\/\//, '') }}
                  </a>
                  <span class="shrink-0 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:text-slate-400 bg-gray-200 dark:bg-slate-600 rounded">Community</span>
                </div>
              </div>

              <!-- Provides -->
              <div v-if="registryManifest.component?.dependencies?.provides?.length">
                <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Предоставляет</h3>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="p in registryManifest.component?.dependencies?.provides"
                    :key="p"
                    class="text-xs px-2.5 py-1 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded-lg font-medium"
                  >
                    {{ p }}
                  </span>
                </div>
              </div>

              <!-- Requires -->
              <div v-if="registryManifest.component?.dependencies?.requires?.length">
                <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Зависимости</h3>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="r in registryManifest.component?.dependencies?.requires"
                    :key="r"
                    class="text-xs px-2.5 py-1 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded-lg font-medium"
                  >
                    {{ r }}
                  </span>
                </div>
              </div>

              <!-- Documentation -->
              <div v-if="registryManifest.component?.documentation_url">
                <h3 class="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">Документация</h3>
                <a
                  :href="registryManifest.component?.documentation_url as string"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1.5 text-sm text-primary-600 dark:text-primary-400 hover:underline"
                >
                  <AppIcon name="external-link" class="w-4 h-4" />
                  {{ (registryManifest.component?.documentation_url as string || '').replace(/^https?:\/\//, '') }}
                </a>
              </div>

              <!-- Download buttons -->
              <div class="flex gap-3 pt-2">
                <button
                  @click="dlDockerfile(registryManifest.component?.slug as string || component.slug)"
                  v-if="registryManifest"
                  class="inline-flex items-center justify-center gap-1.5 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition"
                >
                  <AppIcon name="document-text" class="w-4 h-4" />
                  Dockerfile
                </button>
                <button
                  @click="dlManifest(registryManifest.component?.slug as string || component.slug)"
                  class="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-slate-600 transition"
                >
                  <AppIcon name="document" class="w-4 h-4" />
                  Манифест
                </button>
              </div>
            </div>
          </div>

          <!-- 🛡 Security Tab -->
          <div v-if="activeTab === 'security' && registryManifest">
            <div class="space-y-6">
              <!-- Profile selector + build button -->
              <div class="flex flex-col sm:flex-row gap-3 sm:items-end">
                <div class="flex-1">
                  <label class="block text-sm font-medium text-gray-500 dark:text-slate-400 mb-1.5">Профиль безопасности</label>
                  <select
                    v-model="selectedProfile"
                    class="w-full sm:w-64 px-3 py-2 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    :disabled="reportLoading"
                  >
                    <option v-for="p in profiles" :key="p.slug" :value="p.slug">{{ p.label }}</option>
                    <option v-if="!profiles.length" value="basic">Basic</option>
                    <option value="standard">Standard</option>
                    <option value="hardened">Hardened</option>
                  </select>
                </div>
                <button
                  @click="runSecurityScan"
                  :disabled="reportLoading"
                  class="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
                >
                  <AppIcon v-if="reportLoading" name="spinner" class="w-4 h-4 animate-spin" />
                  <AppIcon v-else name="shield" class="w-4 h-4" />
                  {{ reportLoading ? 'Сканирование...' : 'Запустить проверку безопасности' }}
                </button>
              </div>

              <!-- Error -->
              <div v-if="reportError"
                class="px-4 py-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
                <AppIcon name="warning" class="w-4 h-4 shrink-0" />
                {{ reportError }}
              </div>

              <!-- No report yet -->
              <div v-if="!report && !reportLoading && !reportError"
                class="text-center py-8 text-gray-400 dark:text-slate-500">
                <AppIcon name="shield" class="w-10 h-10 mx-auto mb-2 opacity-40" />
                <p class="text-sm">Проверка безопасности не запущена</p>
              </div>

              <!-- Report results -->
              <div v-if="report" class="space-y-6">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-mono text-gray-400 dark:text-slate-500">
                    Профиль: <strong class="text-gray-600 dark:text-slate-300">{{ report.profile }}</strong>
                  </span>
                  <span v-if="report.status === 'ok'" class="px-2 py-0.5 text-xs font-medium bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded">
                    ✅ Успешно
                  </span>
                  <span v-else class="px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded">
                    ❌ Ошибки
                  </span>
                </div>

                <!-- SBOM summary -->
                <div v-if="report.sbom" class="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                    <AppIcon name="document-text" class="w-4 h-4 text-gray-400" />
                    SBOM (CycloneDX)
                  </h4>
                  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                    <div class="text-center">
                      <div class="text-xl font-bold text-gray-900 dark:text-white">{{ report.sbom.total_components }}</div>
                      <div class="text-xs text-gray-500 dark:text-slate-400">компонентов</div>
                    </div>
                    <div v-for="(count, type) in report.sbom.by_type" :key="type" class="text-center">
                      <div class="text-xl font-bold text-gray-900 dark:text-white">{{ count }}</div>
                      <div class="text-xs text-gray-500 dark:text-slate-400 capitalize">{{ type }}</div>
                    </div>
                  </div>
                  <div v-if="report.sbom.top_dependencies?.length" class="mt-2">
                    <p class="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Топ зависимостей:</p>
                    <div class="flex flex-wrap gap-1.5">
                      <span v-for="dep in report.sbom.top_dependencies.slice(0, 8)" :key="dep.name"
                        class="text-xs px-2 py-0.5 bg-white dark:bg-slate-600 rounded text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-500">
                        {{ dep.name }}@{{ dep.version }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Trivy vulnerabilities -->
                <div v-if="report.trivy" class="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                    <AppIcon name="warning" class="w-4 h-4 text-gray-400" />
                    Trivy — уязвимости
                  </h4>
                  <div class="grid grid-cols-5 gap-2 mb-3">
                    <div v-for="(count, sev) in report.trivy.by_severity" :key="sev" class="text-center">
                      <div class="text-lg font-bold"
                        :class="{
                          'text-red-600': sev === 'CRITICAL',
                          'text-orange-500': sev === 'HIGH',
                          'text-yellow-500': sev === 'MEDIUM',
                          'text-blue-500': sev === 'LOW',
                          'text-gray-400': sev === 'UNKNOWN',
                        }">
                        {{ count }}
                      </div>
                      <div class="text-[10px] text-gray-500 dark:text-slate-400">{{ sev }}</div>
                    </div>
                  </div>
                  <div v-if="report.trivy.vulnerabilities?.length">
                    <div class="overflow-x-auto">
                      <table class="w-full text-xs">
                        <thead>
                          <tr class="text-gray-500 dark:text-slate-400 border-b border-gray-200 dark:border-slate-600">
                            <th class="text-left py-1 pr-2">ID</th>
                            <th class="text-left py-1 pr-2">Пакет</th>
                            <th class="text-left py-1 pr-2">Severity</th>
                            <th class="text-left py-1 pr-2">Фикс</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="v in report.trivy.vulnerabilities.slice(0, 10)" :key="v.id"
                            class="border-b border-gray-100 dark:border-slate-700">
                            <td class="py-1.5 pr-2 font-mono text-gray-800 dark:text-slate-200">{{ v.id }}</td>
                            <td class="py-1.5 pr-2 text-gray-600 dark:text-slate-400">{{ v.pkg }}</td>
                            <td class="py-1.5 pr-2">
                              <span class="px-1.5 py-0.5 rounded text-[10px] font-medium" :class="severityColor(v.severity)">
                                {{ v.severity }}
                              </span>
                            </td>
                            <td class="py-1.5 text-gray-500 dark:text-slate-500">{{ v.fixed || '—' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <p v-if="report.trivy.vulnerabilities.length > 10" class="text-xs text-gray-400 mt-2">
                      + {{ report.trivy.vulnerabilities.length - 10 }} уязвимостей
                    </p>
                  </div>
                  <div v-else class="text-center py-2 text-emerald-600 dark:text-emerald-400 text-sm">
                    ✅ Уязвимостей не найдено
                  </div>
                </div>

                <!-- OWASP DC -->
                <div v-if="report.owasp" class="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                    <AppIcon name="search" class="w-4 h-4 text-gray-400" />
                    OWASP Dependency-Check
                  </h4>
                  <div class="grid grid-cols-2 gap-3">
                    <div class="text-center">
                      <div class="text-xl font-bold text-gray-900 dark:text-white">{{ report.owasp.total_dependencies }}</div>
                      <div class="text-xs text-gray-500 dark:text-slate-400">зависимостей</div>
                    </div>
                    <div class="text-center">
                      <div class="text-xl font-bold text-gray-900 dark:text-white">{{ report.owasp.total_vulnerabilities }}</div>
                      <div class="text-xs text-gray-500 dark:text-slate-400">уязвимостей</div>
                    </div>
                  </div>
                </div>

                <!-- Cosign status -->
                <div class="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                    <AppIcon name="key" class="w-4 h-4 text-gray-400" />
                    Cosign — подпись
                  </h4>
                  <div class="flex items-center gap-2">
                    <span v-if="report.cosign.signed" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
                      <span>✅</span> Подписан
                    </span>
                    <span v-else class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-200 dark:bg-slate-600 text-gray-500 dark:text-slate-400">
                      <span>⏳</span> Не подписан
                    </span>
                  </div>
                </div>

                <!-- Pipeline errors -->
                <div v-if="report.errors?.length" class="px-4 py-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                  <p class="text-sm font-medium text-orange-600 dark:text-orange-400 mb-1">Предупреждения pipeline:</p>
                  <ul class="text-xs text-orange-600 dark:text-orange-400 list-disc list-inside space-y-0.5">
                    <li v-for="err in report.errors" :key="err">{{ err }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Download -->
      <div class="mt-6 flex gap-3">
        <router-link
          to="/constructor"
          class="flex-1 inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded-xl font-medium hover:bg-gray-200 dark:hover:bg-slate-600 transition"
        >
          <AppIcon name="constructor" class="w-5 h-5" />
          В конструктор
        </router-link>
        <button
          @click="showWizard = true"
          class="flex-1 inline-flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition shadow-sm"
        >
          <AppIcon name="settings" class="w-5 h-5" />
          Настроить и скачать
        </button>
      </div>
    </div>

    <ConfigWizard v-if="showWizard && component" :component="component" @close="showWizard = false" />
  </div>
</template>
