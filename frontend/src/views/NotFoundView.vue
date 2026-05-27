<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center px-4">
    <div class="text-center max-w-md">
      <div class="w-20 h-20 mx-auto mb-6 bg-gray-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center">
        <AppIcon name="search" class="w-10 h-10 text-gray-400" />
      </div>
      <h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-2">404</h1>
      <p class="text-lg text-gray-500 dark:text-slate-400 mb-8">Страница не найдена</p>
      <RouterLink
        to="/"
        class="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition shadow-sm"
      >
        <AppIcon name="home" class="w-5 h-5" />
        На главную
      </RouterLink>
    </div>
  </div>
</template>
