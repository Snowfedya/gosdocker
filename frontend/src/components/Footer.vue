<template>
  <footer class="bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 mt-auto">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- Brand -->
        <div>
          <div class="flex items-center gap-2 mb-3">
            <div class="w-8 h-8 bg-gradient-to-br from-primary-600 to-primary-800 rounded-lg flex items-center justify-center">
              <span class="text-white text-sm font-bold">G</span>
            </div>
            <span class="text-lg font-bold text-gray-900 dark:text-white">GosDocker</span>
          </div>
          <p class="text-sm text-gray-500 dark:text-slate-400 leading-relaxed">
            Реестр Docker Compose-сборок государственных ИТ-компонентов с доказательной базой безопасности.
          </p>
        </div>

        <!-- Links -->
        <div>
          <h4 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Разделы</h4>
          <ul class="space-y-2 text-sm">
            <li>
              <router-link to="/catalog" class="text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition">
                Каталог компонентов
              </router-link>
            </li>
            <li>
              <router-link to="/catalog?registry=true" class="text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition">
                Из реестра Минцифры
              </router-link>
            </li>
            <li>
              <router-link to="/constructor" class="text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition">
                Конструктор стека
              </router-link>
            </li>
            <li>
              <router-link to="/stacks" class="text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition">
                Готовые сборки
              </router-link>
            </li>
          </ul>
        </div>

        <!-- Info -->
        <div>
          <h4 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Технологии</h4>
          <ul class="space-y-2 text-sm">
            <li class="text-gray-500 dark:text-slate-400">Vue 3 + TypeScript</li>
            <li class="text-gray-500 dark:text-slate-400">FastAPI + SQLAlchemy</li>
            <li class="text-gray-500 dark:text-slate-400">Docker + Docker Compose</li>
            <li class="text-gray-500 dark:text-slate-400">Tailwind CSS</li>
          </ul>
        </div>
      </div>

      <div class="border-t border-gray-200 dark:border-slate-700 mt-8 pt-6 text-center">
        <p class="text-xs text-gray-400 dark:text-slate-500">
          &copy; {{ new Date().getFullYear() }} GosDocker — Реестр государственных ИТ-компонентов с доказательной базой
        </p>
      </div>
    </div>
  </footer>
</template>
