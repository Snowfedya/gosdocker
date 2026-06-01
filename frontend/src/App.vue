<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterView, RouterLink, useRoute } from 'vue-router'
import Footer from './components/Footer.vue'
import AppIcon from './components/AppIcon.vue'

const route = useRoute()
const mobileMenuOpen = ref(false)
const darkMode = ref(false)

watch(() => route.path, () => { mobileMenuOpen.value = false })

function toggleDarkMode() {
  darkMode.value = !darkMode.value
  document.documentElement.classList.toggle('dark')
}

const navLinks = [
  { path: '/catalog', label: 'Каталог', icon: 'catalog' },
  { path: '/constructor', label: 'Конструктор', icon: 'constructor' },
  { path: '/stacks', label: 'Сборки', icon: 'stacks' },
]

function isActive(path: string): boolean {
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gray-50 dark:bg-slate-900 transition-colors duration-200">
    <!-- Navigation -->
    <nav class="bg-white/95 dark:bg-slate-800/95 backdrop-blur-sm border-b border-gray-200 dark:border-slate-700 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <RouterLink to="/" class="flex items-center gap-2.5 group">
            <div class="w-9 h-9 bg-gradient-to-br from-primary-600 to-primary-800 rounded-lg flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
              <span class="text-white text-lg font-bold">G</span>
            </div>
            <div class="hidden sm:block">
              <span class="text-lg font-bold text-gray-900 dark:text-white">GosDocker</span>
              <span class="block text-[10px] leading-tight text-gray-400 dark:text-slate-500 -mt-0.5">Каталог ИТ-компонентов</span>
            </div>
          </RouterLink>

          <!-- Desktop Nav -->
          <div class="hidden md:flex items-center gap-1">
            <RouterLink
              v-for="link in navLinks"
              :key="link.path"
              :to="link.path"
              :class="[
                'inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                isActive(link.path)
                  ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700'
              ]"
            >
              <AppIcon :name="link.icon" class="w-4 h-4" />
              {{ link.label }}
            </RouterLink>
          </div>

          <!-- Right section -->
          <div class="flex items-center gap-2">
            <!-- Dark mode toggle -->
            <button
              @click="toggleDarkMode"
              class="p-2 rounded-lg text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition"
              :title="darkMode ? 'Светлая тема' : 'Тёмная тема'"
            >
              <AppIcon :name="darkMode ? 'sun' : 'moon'" class="w-5 h-5" />
            </button>

            <!-- Mobile hamburger -->
            <button
              @click="mobileMenuOpen = !mobileMenuOpen"
              class="md:hidden p-2 rounded-lg text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition"
            >
              <AppIcon :name="mobileMenuOpen ? 'close' : 'menu'" class="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      <!-- Mobile Menu -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-2"
      >
        <div v-if="mobileMenuOpen" class="md:hidden border-t border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          <div class="px-4 py-3 space-y-1">
            <RouterLink
              v-for="link in navLinks"
              :key="link.path"
              :to="link.path"
              :class="[
                'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition',
                isActive(link.path)
                  ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700'
              ]"
            >
              <AppIcon :name="link.icon" class="w-5 h-5" />
              {{ link.label }}
            </RouterLink>
          </div>
        </div>
      </Transition>
    </nav>

    <!-- Page Content -->
    <main class="flex-1">
      <RouterView v-slot="{ Component: PageComponent }">
        <Transition name="page" mode="out-in">
          <component :is="PageComponent" />
        </Transition>
      </RouterView>
    </main>

    <Footer />
  </div>
</template>

<style scoped>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
