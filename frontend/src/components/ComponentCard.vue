<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Component } from '../types'
import AppIcon from './AppIcon.vue'
import SourceBadge from './SourceBadge.vue'
import ConfigWizard from './ConfigWizard.vue'
import { useApi } from '../composables/useApi'

const props = defineProps<{ component: Component }>()

const router = useRouter()
const showWizard = ref(false)
const { generateStack, constructorGenerate, fetchProfiles } = useApi()
const downloading = ref(false)
const selectedProfile = ref('standard')
const profiles = ref<{ slug: string; label: string; description: string }[]>([])
const profilesLoaded = ref(false)

// Lazy-load profiles on first interaction
async function ensureProfiles() {
  if (profilesLoaded.value) return
  try {
    profiles.value = await fetchProfiles()
  } catch {
    profiles.value = []
  }
  profilesLoaded.value = true
}

const buildMethodLabels: Record<string, string> = {
  configure_make: './configure && make',
  go_build: 'Go build',
  php_extract: 'PHP extraction',
  node_go: 'Node.js + Go',
  cmake_make: 'cmake + make',
  make: 'make',
}

function openDetail() {
  router.push({ name: 'component', params: { slug: props.component.slug } })
}

async function quickDownload() {
  downloading.value = true
  try {
    // Registry components use constructor with profile; others use legacy generate
    if (props.component.has_registry) {
      const blob = await constructorGenerate({
        components: [props.component.slug],
        profile: selectedProfile.value,
        configs: {
          [props.component.slug]: {
            ports: { ...props.component.default_ports },
            volumes: { ...props.component.default_volumes },
            env: { ...props.component.default_env },
          },
        },
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${props.component.slug}-${selectedProfile.value}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } else {
      const blob = await generateStack([props.component.slug], {
        [props.component.slug]: {
          ports: { ...props.component.default_ports },
          volumes: { ...props.component.default_volumes },
          env: { ...props.component.default_env },
        },
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${props.component.slug}.zip`
      a.click()
      URL.revokeObjectURL(url)
    }
  } catch (e) {
    console.error('Download failed', e)
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div
    class="group bg-white dark:bg-slate-800 rounded-xl border shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer overflow-hidden"
    :class="component.is_registry ? 'border-emerald-200 dark:border-emerald-800 hover:border-emerald-400' : 'border-gray-200 dark:border-slate-700 hover:border-primary-300'"
    @click="openDetail"
  >
    <div class="p-5">
      <!-- Header -->
      <div class="flex items-start justify-between mb-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white truncate">{{ component.name }}</h3>
            <SourceBadge v-if="component.is_registry !== undefined" :is-registry="component.is_registry" />
          </div>
        </div>
        <span v-if="component.version" class="shrink-0 ml-2 px-2 py-0.5 bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 rounded text-xs font-mono">
          v{{ component.version }}
        </span>
      </div>

      <!-- Description -->
      <p class="text-sm text-gray-600 dark:text-slate-400 mb-3 line-clamp-2 leading-relaxed">
        {{ component.description || 'Нет описания' }}
      </p>

      <!-- Build method badge for registry components -->
      <div v-if="component.has_registry && component.build_method" class="flex flex-wrap gap-1 mb-3">
        <span class="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
          :class="
            component.build_method === 'go_build' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300' :
            component.build_method === 'php_extract' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
            component.build_method === 'node_go' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' :
            component.build_method === 'cmake_make' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300' :
            component.build_method === 'make' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300' :
            'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'"
        >
          <AppIcon name="cube" class="w-3 h-3" />
          {{ buildMethodLabels[component.build_method] || component.build_method }}
        </span>
      </div>

      <!-- Sources -->
      <div class="mb-4 space-y-1.5">
        <div class="flex items-center gap-1.5 px-2 py-1.5 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <AppIcon name="external-link" class="w-3.5 h-3.5 text-gray-400 shrink-0" />
          <span class="text-[10px] font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wider mr-0.5">Образ:</span>
          <code class="text-xs text-gray-600 dark:text-slate-300 truncate flex-1">{{ component.registry_url }}</code>
        </div>
        <div v-if="component.is_registry && component.image_source" class="flex items-center gap-1.5 px-2 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
          <AppIcon name="server" class="w-3.5 h-3.5 text-emerald-500 shrink-0" />
          <span class="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mr-0.5">Реестр РФ:</span>
          <code class="text-xs text-emerald-700 dark:text-emerald-300 truncate flex-1">{{ component.image_source }}</code>
        </div>
      </div>

      <!-- Profile selector (registry only) -->
      <div v-if="component.has_registry" class="mb-3" @click.stop>
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wider">Профиль:</span>
          <div class="flex gap-1">
            <button
              v-for="p in ['basic', 'standard', 'hardened']"
              :key="p"
              @click="selectedProfile = p"
              class="text-[11px] px-2 py-1 rounded-md font-medium transition"
              :class="selectedProfile === p
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300 ring-1 ring-primary-300 dark:ring-primary-600'
                : 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600'"
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2">
        <button
          @click.stop="quickDownload"
          :disabled="downloading"
          class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-slate-700 transition disabled:opacity-50"
        >
          <AppIcon :name="downloading ? 'refresh' : 'download'" class="w-4 h-4" :class="downloading ? 'animate-spin' : ''" />
          {{ downloading ? 'Подготовка...' : 'Скачать' }}
        </button>
        <button
          @click.stop="showWizard = true"
          class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition shadow-sm"
        >
          <AppIcon name="settings" class="w-4 h-4" />
          Настроить
        </button>
      </div>
    </div>
  </div>

  <ConfigWizard v-if="showWizard" :component="component" @close="showWizard = false" />
</template>
