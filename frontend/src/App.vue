<script setup lang="ts">
import { RouterView } from 'vue-router'
import Footer from './components/Footer.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gray-50">
    <RouterView />
    <Footer />
  </div>
</template>