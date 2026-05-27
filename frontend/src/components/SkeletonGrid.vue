<script setup lang="ts">
defineProps<{
  count?: number
  height?: string
}>()
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div v-for="i in (count || 6)" :key="i" class="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
      <!-- Title skeleton -->
      <div class="flex items-start justify-between mb-3">
        <div class="space-y-2 flex-1">
          <div class="skeleton h-5 w-3/4 rounded" />
          <div class="skeleton h-3 w-1/3 rounded" />
        </div>
        <div class="skeleton h-5 w-14 rounded ml-2" />
      </div>
      <!-- Description skeleton -->
      <div class="space-y-2 mb-4">
        <div class="skeleton h-3 w-full rounded" />
        <div class="skeleton h-3 w-2/3 rounded" />
      </div>
      <!-- URL skeleton -->
      <div class="skeleton h-8 w-full rounded-lg mb-4" />
      <!-- Buttons skeleton -->
      <div class="flex gap-2">
        <div class="skeleton h-9 flex-1 rounded-lg" />
        <div class="skeleton h-9 flex-1 rounded-lg" />
      </div>
    </div>
  </div>
</template>
