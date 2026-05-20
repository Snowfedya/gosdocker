<script setup lang="ts">
defineProps<{
  isRegistry: boolean
}>()
</script>

<template>
  <span
    :class="[
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
      isRegistry
        ? 'bg-green-100 text-green-700'
        : 'bg-blue-100 text-blue-700'
    ]"
  >
    {{ isRegistry ? '🏛 Из Реестра РФ' : '📦 Community' }}
  </span>
</template>
