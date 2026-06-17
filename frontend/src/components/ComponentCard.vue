<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Component } from '../types'
import SourceBadge from './SourceBadge.vue'
import ConfigWizard from './ConfigWizard.vue'
import { useApi } from '../composables/useApi'

const props = defineProps<{ component: Component }>()

const router = useRouter()
const showWizard = ref(false)
const { generateStack, constructorGenerate } = useApi()
const downloading = ref(false)
const selectedProfile = ref('standard')

async function quickDownload() {
  downloading.value = true
  try {
    if (props.component.has_registry) {
      const blob = await constructorGenerate({
        components: [props.component.slug],
        profile: selectedProfile.value,
        // AC-CONST-4 / Bug #18: card-level "Скачать" on /catalog must
        // use the fast path. The user is downloading a stack template,
        // not requesting a security audit. They can always go to the
        // Constructor view to choose the full security path explicitly.
        with_owasp: false,
        fast_mode: true,
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

function openDetail() {
  router.push({ name: 'component', params: { slug: props.component.slug } })
}
</script>

<template>
  <div
    class="group bg-white dark:bg-slate-800 rounded-xl border shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer overflow-hidden"
    :class="component.is_registry ? 'border-emerald-200 dark:border-emerald-800 hover:border-emerald-400' : 'border-gray-200 dark:border-slate-700 hover:border-primary-300'"
    @click="openDetail"
  >
    <div class="p-5">
      <!-- Header: Name + Badges -->
      <div class="flex items-start justify-between gap-2 mb-2">
        <div class="flex items-center gap-2 min-w-0">
          <h3 class="text-base font-semibold text-gray-900 dark:text-white truncate">{{ component.name }}</h3>
          <SourceBadge v-if="component.is_registry !== undefined" :is-registry="component.is_registry" />
        </div>
        <span v-if="component.version" class="shrink-0 px-2 py-0.5 bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 rounded text-xs font-mono">
          v{{ component.version }}
        </span>
      </div>

      <!-- Description -->
      <p class="text-sm text-gray-600 dark:text-slate-400 mb-4 line-clamp-2 leading-relaxed">
        {{ component.description || 'Нет описания' }}
      </p>

      <!-- Actions: Single primary CTA -->
      <div class="flex gap-2">
        <button
          @click.stop="quickDownload"
          :disabled="downloading"
          class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-sm font-medium transition shadow-sm text-white"
          :class="component.is_registry
            ? 'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800'
            : 'bg-primary-600 hover:bg-primary-700 active:bg-primary-800'"
        >
          <svg v-if="downloading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-6.219-8.56" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {{ downloading ? 'Подготовка...' : 'Скачать Docker образ' }}
        </button>
        <button
          @click.stop="showWizard = true"
          class="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-slate-700 transition"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  <ConfigWizard v-if="showWizard" :component="component" @close="showWizard = false" />
</template>
