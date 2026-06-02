# GosDocker Frontend — Comprehensive Testing Plan

**Дата:** 2 июня 2026  
**Проект:** GosDocker (gosdocker.ru)  
**Стек фронтенда:** Vue 3 + TypeScript + Tailwind CSS + Vite + Vue Router  
**Разработчик:** Mark Frost  
**Deadlines:** Нормоконтроль 5 июня, защита ВКР 15–18 июня  

---

## Содержание

1. [Обзор текущего состояния](#1-обзор-текущего-состояния)
2. [Настройка тестовой инфраструктуры](#2-настройка-тестовой-инфраструктуры)
3. [Unit-тесты компонентов (Vitest + Vue Test Utils)](#3-unit-тесты-компонентов)
4. [Интеграционные тесты страниц](#4-интеграционные-тесты-страниц)
5. [E2E тесты (Playwright)](#5-e2e-тесты-playwright)
6. [Визуальное регрессионное тестирование](#6-визуальное-регрессионное-тестирование)
7. [Responsive / Adaptive тестирование](#7-responsive--adaptive-тестирование)
8. [Accessibility тестирование](#8-accessibility-тестирование)
9. [Производительность фронтенда](#9-производительность-фронтенда)
10. [Приоритизация по этапам и срокам](#10-приоритизация-по-этапам-и-срокам)
11. [Сводная таблица трудозатрат](#11-сводная-таблица-трудозатрат)
12. [Рекомендации по внедрению](#12-рекомендации-по-внедрению)

---

## 1. Обзор текущего состояния

### 1.1 Состав фронтенда

| Компонент | Файл | Строк | Сложность |
|-----------|------|-------|-----------|
| **App.vue** | Корневой компонент | 142 | Средняя (роутинг, навигация, dark mode, mobile menu) |
| **HomeView.vue** | Главная страница | 250+ | Средняя (hero, категории, CTA) |
| **CatalogView.vue** | Каталог компонентов | 170+ | Высокая (поиск, фильтрация, пагинация) |
| **ConstructorView.vue** | Конструктор стека | 350+ | **Очень высокая** (выбор компонентов, профили, диагностика, генерация) |
| **StacksView.vue** | Готовые сборки | ~70 | Низкая |
| **ComponentView.vue** | Детальная страница компонента | 550+ | **Очень высокая** (табы, отчёт безопасности, граф зависимостей) |
| **SecurityReportView.vue** | Отчёт безопасности | 167 | Высокая (ScoreBadge, SeverityBar, CveTable, DependencyGraph) |
| **NotFoundView.vue** | 404 страница | 23 | Низкая |

**UI-компоненты (12):**
- `AppIcon.vue` (217 строк) — SVG-иконки, 30+ вариантов
- `ComponentCard.vue` (120 строк) — карточка компонента, скачивание, ConfigWizard
- `ConfigWizard.vue` (168 строк) — модальное окно настройки портов/env
- `Footer.vue` (64 строки) — подвал с навигацией
- `SkeletonGrid.vue` (33 строки) — заглушка загрузки
- `SourceBadge.vue` (22 строки) — бейдж источника
- `StackCard.vue` (79 строк) — карточка готовой сборки
- `CveTable.vue` (154 строки) — таблица CVE с поиском и сортировкой
- `DependencyGraph.vue` (63 строки) — граф зависимостей SBOM
- `ScoreBadge.vue` (29 строк) — бейдж скоринга
- `SecuritySummary.vue` (93 строки) — сводка безопасности
- `SeverityBar.vue` (48 строк) — шкала severity

**Composables:** `useApi.ts` (13 API методов), `useSecurityReport.ts` (загрузка отчёта)

**API эндпоинты (backend FastAPI):**
- `GET /api/categories`
- `GET /api/components?category=&registry_only=`
- `GET /api/stacks`
- `POST /api/generate`
- `GET /api/registry`
- `GET /api/registry/{slug}`
- `POST /api/registry/{slug}/build`
- `GET /api/registry/{slug}/reports`
- `GET /api/registry/{slug}/dockerfile`
- `GET /api/registry/{slug}/manifest`
- `POST /api/constructor/diagnostic`
- `POST /api/constructor`
- `GET /api/constructor/profiles`

### 1.2 Проблемы

- Unit-тестов нет (0)
- E2E тестов нет в текущей кодовой базе (исторически 36 тестов Playwright были, но не настроены)
- Нет accessibility проверок
- Нет тестов адаптивности
- Нет visual regression testing
- Нет drag-and-drop (требование)
- `noUnusedLocals`/`noUnusedParameters` включены в tsconfig — может быть шум при тестах

### 1.3 Инструменты (рекомендуемые)

| Слой | Инструмент | Версия |
|------|-----------|--------|
| Unit-тесты | Vitest + @vue/test-utils + happy-dom | vitest@^2.0 |
| Интеграционные | Vitest + Vue Router testing utilities | — |
| E2E | Playwright | ^1.50 |
| Visual Regression | Playwright Screenshot | built-in |
| Accessibility | axe-core + pa11y | axe-playwright |
| Performance | Lighthouse CI | @lhci/cli |
| Bundle Analysis | vite-bundle-analyzer | rollup-plugin-visualizer |
| Coverage | c8 / istanbul (встроен в Vitest) | — |

---

## 2. Настройка тестовой инфраструктуры

### 2.1 Установка зависимостей

```bash
cd /opt/gosdocker/frontend

# Vitest + Vue Test Utils
npm install -D vitest @vue/test-utils happy-dom jsdom

# Playwright
npm install -D @playwright/test
npx playwright install chromium

# Accessibility
npm install -D @axe-core/playwright

# Bundle analyzer
npm install -D rollup-plugin-visualizer

# Type helpers
npm install -D @vue/tsconfig
```

### 2.2 vitest.config.ts

```ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,js}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.vue', 'src/**/*.ts'],
      exclude: ['src/**/*.test.ts', 'src/**/*.spec.ts', 'src/main.ts'],
    },
    setupFiles: ['src/test/setup.ts'],
  },
})
```

### 2.3 Единый setup-файл

```ts
// src/test/setup.ts
import { config } from '@vue/test-utils'

// Мок роутера, если нужно
// Мок глобальных стилей Tailwind
// Мок API-вызовов по умолчанию
```

### 2.4 Скрипты в package.json

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:a11y": "playwright test --grep @a11y"
  }
}
```

### 2.5 Структура тестов

```
src/
  test/
    setup.ts
    mocks/
      api.ts         # Mock useApi composable
      data.ts        # Mock data (components, stacks, categories)
    unit/
      components/     # Unit-тесты UI-компонентов
      composables/    # Тесты composables
      utils/          # Тесты утилит
    integration/
      views/          # Интеграционные тесты страниц
      router/         # Тесты роутинга
e2e/
  playwright.config.ts
  specs/
    home.spec.ts
    catalog.spec.ts
    constructor.spec.ts
    stacks.spec.ts
    security.spec.ts
  pages/
    HomePage.ts       # Page Object Models
    CatalogPage.ts
    ConstructorPage.ts
  fixtures/
    data.json
```

---

## 3. Unit-тесты компонентов

### 3.1 Pure utility functions (без Vue)

#### `src/utils/security.ts`

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U1 | `calculateSecurityScore()` с нулевыми уязвимостями | score = 100 | P0 |
| U2 | `calculateSecurityScore()` с CRITICAL=1 | score = max(0, 100-15) = 85 | P0 |
| U3 | `calculateSecurityScore()` с HIGH=2 | score = 90 | P0 |
| U4 | `calculateSecurityScore()` с MEDIUM=5, LOW=10 | score = 100-10-5 = 85 | P1 |
| U5 | `calculateSecurityScore()` с очень большими значениями | score не ниже 0 | P1 |
| U6 | `scoreToGrade(90+)` → `'A'` | A | P0 |
| U7 | `scoreToGrade(70-89)` → `'B'` | B | P0 |
| U8 | `scoreToGrade(50-69)` → `'C'` | C | P0 |
| U9 | `scoreToGrade(30-49)` → `'D'` | D | P1 |
| U10 | `scoreToGrade(<30)` → `'E'` | E | P1 |

### 3.2 UI-компоненты

#### AppIcon.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U11 | Рендер с `name="catalog"` | SVG с правильным path | P0 |
| U12 | Рендер с `name="download"` | SVG с правильным path | P0 |
| U13 | Рендер с неизвестным name | Пустой SVG без path | P1 |
| U14 | Кастомный class через props | class передан на внешний SVG | P1 |
| U15 | Все 30+ иконок рендерятся без ошибок | Никаких vue warnings | P2 |

#### SourceBadge.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U16 | `isRegistry=true` | Текст "Из Реестра РФ", иконка щита | P0 |
| U17 | `isRegistry=false` | Текст "Community", иконка GitHub | P0 |
| U18 | Корректные CSS-классы для registry | badge-registry | P1 |
| U19 | Корректные CSS-классы для community | badge-community | P1 |

#### ScoreBadge.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U20 | Рендер grade='A', score=95 | Буква A, число 95 | P0 |
| U21 | Рендер grade='E', score=10 | Буква E, число 10 | P0 |
| U22 | Цвет фона для каждой оценки (A-E) | Правильный bg-* класс | P1 |
| U23 | Неизвестный grade → fallback E | bg-red-500 | P1 |

#### SeverityBar.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U24 | Пустые severity (все 0) | Общая ширина 0, все сегменты невидны | P1 |
| U25 | Только CRITICAL=5 | Красный сегмент 100% | P0 |
| U26 | Равномерное распределение | Пропорциональные ширины | P1 |
| U27 | Легенда severity отображается | 5 элементов с правильными label | P1 |

#### CveTable.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U28 | Рендер с пустым массивом уязвимостей | Empty state "Уязвимостей не найдено" | P0 |
| U29 | Рендер с 3 уязвимостями | 3 строки в таблице | P0 |
| U30 | Фильтр по severity=CRITICAL | Только CRITICAL записи | P0 |
| U31 | Поиск по CVE ID | Фильтрация совпадений | P0 |
| U32 | Сортировка по severity (desc/asc) | Переключение порядка | P1 |
| U33 | Сортировка по пакету (алфавит) | Правильный порядок | P1 |
| U34 | Комбинация поиска + фильтра | Корректное пересечение | P1 |
| U35 | CVE ID кликабельный (ссылка NVD) | `href` на nvd.nist.gov | P1 |
| U36 | Не-CVE ID (не ссылка) | Простой span | P1 |

#### ConfigWizard.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U37 | Открытие модала с компонентом | Заголовок = имя компонента | P0 |
| U38 | Закрытие по кнопке | emit('close') | P0 |
| U39 | Закрытие по overlay click | emit('close') | P0 |
| U40 | Таб портов по умолчанию | Активен таб ports | P0 |
| U41 | Пустые порты → сообщение "Нет настраиваемых портов" | Текст | P1 |
| U42 | Изменение external port | v-model обновляет portEntries | P1 |
| U43 | Переключение на env таб | Активен таб env | P0 |
| U44 | Пустые env → сообщение "Нет переменных окружения" | Текст | P1 |
| U45 | Кнопка download disabled при downloading=true | disabled атрибут | P1 |
| U46 | Ошибка скачивания → отображение error | Текст ошибки на экране | P1 |

#### ComponentCard.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U47 | Рендер всех полей компонента | name, description, version, SourceBadge | P0 |
| U48 | Клик по карточке → router.push | Навигация на /component/:slug | P0 |
| U49 | Кнопка "Скачать Docker образ" | Вызов quickDownload | P0 |
| U50 | Состояние загрузки (downloading=true) | Текст "Подготовка...", спиннер | P1 |
| U51 | Кнопка ConfigWizard → showWizard=true | Рендер ConfigWizard | P0 |
| U52 | is_registry=true → зелёная рамка | border-emerald-* | P1 |
| U53 | registry URL отображается | Ссылка | P1 |

#### StackCard.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U54 | Рендер стека с компонентами | Имя, описание, чипы компонентов | P0 |
| U55 | Стек из реестра → emerald accent | border-emerald-200 | P1 |
| U56 | is_featured=true → бейдж "Избранное" | Жёлтый бейдж | P1 |
| U57 | Скачивание стека | Вызов generateStack | P0 |
| U58 | Состояние загрузки | Текст "Подготовка...", disabled | P1 |

#### SkeletonGrid.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U59 | Рендер с count=6 | 6 skeleton элементов | P0 |
| U60 | Кастомный count (3, 8, 12) | Правильное количество | P1 |

#### Footer.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U61 | Рендер всех секций (brand, links, tech) | 3 колонки | P0 |
| U62 | Текущий год в копирайте | `2026` | P1 |
| U63 | Ссылки навигации ведут на правильные маршруты | RouterLink to={/catalog, /constructor, /stacks} | P1 |

#### SecuritySummary.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U64 | Рендер с отчётом | ScoreBadge, SeverityBar, dep count | P0 |
| U65 | Пустой report (null) | Empty state | P1 |
| U66 | Ошибка загрузки | Оранжевый баннер с error | P0 |
| U67 | Состояние loading | Спиннер | P1 |
| U68 | Ссылка на полный отчёт | router-link на /components/:slug/security | P1 |
| U69 | Pipeline errors → список ошибок | ul с ошибками | P1 |

#### DependencyGraph.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U70 | Пустые зависимости | Empty state "Нет данных" | P1 |
| U71 | Группировка по type | Группы с count | P0 |
| U72 | Развернуть/свернуть группу | toggleGroup переключает expanded | P1 |
| U73 | Рендер зависимостей внутри группы | name + version | P1 |

### 3.3 Composables

#### useApi.ts

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U74 | fetchCategories() | GET /api/categories, возвращает массив | P0 |
| U75 | fetchComponents() без фильтров | GET /api/components | P0 |
| U76 | fetchComponents('database', true) | GET /api/components?category=database&registry_only=true | P0 |
| U77 | fetchReports(slug) → SecurityReport | GET /api/registry/{slug}/reports | P0 |
| U78 | generateStack(slugs, config) | POST /api/generate, возвращает Blob | P0 |
| U79 | constructorGenerate(req) | POST /api/constructor | P1 |
| U80 | constructorDiagnostic(req) | POST /api/constructor/diagnostic | P1 |
| U81 | fetchProfiles() | GET /api/constructor/profiles | P1 |
| U82 | buildComponent(slug) | POST /api/registry/{slug}/build | P1 |
| U83 | Все ошибки API корректно пробрасываются | throw new Error с русским сообщением | P1 |

#### useSecurityReport.ts

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| U84 | load() успешно загружает отчёт | report.value заполнен, loading=false | P0 |
| U85 | load() с ошибкой | error.value установлен, loading=false | P0 |
| U86 | score/computed корректно считает | Использует calculateSecurityScore | P1 |
| U87 | vulnerabilityList из trivy.vulnerabilities | Правильный массив | P1 |

---

## 4. Интеграционные тесты страниц

### 4.1 Роутинг

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I1 | Навигация на / → HomeView | Рендер HomeView | P0 |
| I2 | Навигация на /catalog → CatalogView | Рендер CatalogView | P0 |
| I3 | Навигация на /constructor → ConstructorView | Рендер ConstructorView | P0 |
| I4 | Навигация на /stacks → StacksView | Рендер StacksView | P0 |
| I5 | Навигация на /component/postgres → ComponentView | Рендер с slug=postgres | P0 |
| I6 | Навигация на /security/postgres → SecurityReportView | Рендер с slug=postgres | P0 |
| I7 | Навигация на /nonexistent → NotFoundView | Рендер 404 | P0 |
| I8 | Клик по логотипу → / | Роутер на / | P1 |

### 4.2 HomeView.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I9 | Рендер hero-секции | Заголовок, подзаголовок, CTA | P0 |
| I10 | Категории загружаются из API | Список категорий | P0 |
| I11 | Состояние загрузки категорий | Skeleton/cпиннер | P1 |
| I12 | Ошибка загрузки категорий | Сообщение об ошибке | P1 |
| I13 | Клик по категории → /catalog?category=slug | Навигация | P1 |
| I14 | CTA кнопка "Начать сборку" → /constructor | Навигация | P1 |

### 4.3 CatalogView.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I15 | Загрузка списка компонентов | ComponentCard для каждого | P0 |
| I16 | Поиск по названию | Фильтрация компонентов | P0 |
| I17 | Фильтр по категории | Компоненты только выбранной категории | P0 |
| I18 | Чекбокс "Только из реестра" | registry_only=true | P0 |
| I19 | Пустой результат поиска | Empty state | P1 |
| I20 | Скелетон при загрузке | SkeletonGrid | P1 |
| I21 | Ошибка API | Error state | P1 |
| I22 | Клик по карточке → /component/:slug | Навигация | P1 |

### 4.4 ConstructorView.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I23 | Рендер списка категорий для выбора | Категории из API | P0 |
| I24 | Выбор компонента по категории | Добавление в стек | P0 |
| I25 | Удаление компонента из стека | Удаление | P0 |
| I26 | Выбор security profile | Profile selector | P1 |
| I27 | Кнопка "Сгенерировать" → загрузка ZIP | Вызов constructorGenerate | P0 |
| I28 | Диагностика стека (auto_added) | ConstructorDiagnostic | P1 |
| I29 | Ошибка диагностики | Error state | P1 |
| I30 | Пустой стек → disabled generate | Кнопка недоступна | P1 |
| I31 | Рендер при пустом ответе API | Graceful degradation | P2 |

### 4.5 StacksView.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I32 | Загрузка готовых сборок | Список StackCard | P0 |
| I33 | Пустой список (нет сборок) | Empty state | P1 |
| I34 | Ошибка API | Error state | P1 |

### 4.6 ComponentView.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I35 | Загрузка детальной информации о компоненте | Имя, описание, версия | P0 |
| I36 | Таб "Информация" | Основные поля | P0 |
| I37 | Таб "Безопасность" → SecuritySummary | SecuritySummary рендер | P0 |
| I38 | Таб "Registry Manifest" (если is_registry) | Манифест | P1 |
| I39 | Кнопка "Скачать" для registry компонента | constructorGenerate | P1 |
| I40 | Кнопка "Скачать" для community компонента | generateStack | P1 |
| I41 | Ошибка загрузки компонента | Error state | P1 |
| I42 | Чтение slug из route.params | Правильный slug | P0 |

### 4.7 SecurityReportView.vue

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I43 | Загрузка отчёта | ScoreBadge, SeverityBar, CveTable, DependencyGraph | P0 |
| I44 | Пустой/ошибочный отчёт | "Отчёт не найден" + link | P0 |
| I45 | Экспорт JSON | Скачивание файла | P1 |
| I46 | Печать отчёта | window.print() | P2 |
| I47 | Таб "Уязвимости" | CveTable | P0 |
| I48 | Таб "Граф зависимостей" | DependencyGraph | P1 |
| I49 | Cosign status отображается | signed/не подписан | P1 |

### 4.8 App.vue (Layout)

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| I50 | Навигация (3 ссылки) рендерится | Каталог, Конструктор, Сборки | P0 |
| I51 | Активная ссылка подсвечена | bg-primary-50 | P1 |
| I52 | Toggle dark mode | class 'dark' на html | P0 |
| I53 | Mobile menu открывается/закрывается | Transition | P1 |
| I54 | Route change закрывает mobile menu | mobileMenuOpen=false | P1 |
| I55 | Footer рендерится | 3 колонки | P1 |

---

## 5. E2E тесты (Playwright)

### 5.1 Конфигурация Playwright

```ts
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [['html'], ['list']],
  use: {
    baseURL: process.env.BASE_URL || 'https://gosdocker.ru',
    viewport: { width: 1280, height: 720 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
})
```

### 5.2 Page Object Models

Создать POM для каждой страницы:

```ts
// e2e/pages/HomePage.ts
export class HomePage {
  constructor(public page: Page) {}

  async goto() { await this.page.goto('/') }
  async getCategories() { return this.page.locator('[data-testid=category-card]') }
  async clickCategory(name: string) { ... }
  async clickCTA() { ... }
}
```

Data-testid атрибуты добавить в шаблоны:

```html
<div data-testid="component-card">
<button data-testid="download-btn">
```

### 5.3 E2E сценарии

#### HomePage

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E1 | Главная загружается | Открыть / | Заголовок, категории, CTA видны | P0 |
| E2 | Категории кликабельны | Нажать на категорию | URL /catalog?category=slug | P0 |
| E3 | CTA → Конструктор | Нажать "Начать сборку" | URL /constructor | P1 |

#### Catalog

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E4 | Каталог загружается | Открыть /catalog | Список компонентов | P0 |
| E5 | Поиск по названию | Ввести "postgres" | Отфильтрованный список | P0 |
| E6 | Фильтр категории | Выбрать категорию "Базы данных" | Компоненты только из БД | P0 |
| E7 | Чекбокс "Только реестр" | Включить | registry_only=true | P0 |
| E8 | Клик по карточке | Нажать на карточку | URL /component/:slug | P0 |
| E9 | Скачать компонент | Нажать "Скачать Docker образ" | ZIP скачивается | P0 |
| E10 | Открыть ConfigWizard | Нажать иконку шестерёнки | Модальное окно | P0 |
| E11 | Скачать через ConfigWizard | Настроить порты → Скачать | ZIP скачивается | P1 |
| E12 | Пустой поиск | Ввести "zzzzz_not_exists" | Empty state | P1 |
| E13 | Комбинация фильтров | Поиск + категория + реестр | Корректный фильтр | P1 |

#### Constructor

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E14 | Конструктор загружается | Открыть /constructor | Категории, список компонентов | P0 |
| E15 | Добавить компонент | Выбрать категорию, нажать "В стек" | Компонент в стека | P0 |
| E16 | Удалить компонент из стека | Нажать × на компоненте в стеке | Удалён | P0 |
| E17 | Выбрать security profile | Выбрать из выпадающего списка | Profile выбран | P1 |
| E18 | Сгенерировать и скачать | Добавить компонент + Сгенерировать | ZIP скачивается | P0 |
| E19 | Пустой стек → disabled generate | Не добавлять компоненты | Кнопка неактивна | P1 |

#### Stacks

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E20 | Сборки загружаются | Открыть /stacks | Список сборок | P0 |
| E21 | Скачать сборку | Нажать "Скачать сборку" | ZIP скачивается | P0 |
| E22 | Featured бейдж | Проверить избранные | Бейдж "Избранное" | P1 |

#### Component Detail

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E23 | Страница компонента | Перейти /component/postgres | Информация, табы | P0 |
| E24 | Таб Security | Нажать "Безопасность" | SecuritySummary | P0 |
| E25 | Скачать registry | Нажать "Скачать" | ZIP | P0 |
| E26 | Несуществующий компонент | /component/not-exist | 404 или error | P0 |

#### Security Report

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E27 | Отчёт безопасности | Перейти /security/postgres | ScoreBadge, CveTable | P0 |
| E28 | Фильтр severity | Выбрать CRITICAL | Только CRITICAL | P0 |
| E29 | Поиск CVE | Ввести "CVE-2024" | Фильтрация | P1 |
| E30 | Экспорт JSON | Нажать JSON | Скачивание .json | P1 |
| E31 | Таб "Граф зависимостей" | Нажать | DependencyGraph | P1 |
| E32 | Cosign статус | Проверить | signed/unsinged badge | P1 |

#### Navigation

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E33 | Все навигационные ссылки | Клик по каждой | Корректный URL | P0 |
| E34 | Логотип → Home | Клик на логотип | / | P0 |
| E35 | Dark mode toggle | Нажать moon/sun | class="dark" на html | P0 |
| E36 | 404 страница | /nonexistent | 404 текст, "На главную" | P0 |

#### Полный пользовательский сценарий (Critical Path)

| # | Тест-кейс | Шаги | Ожидание | Приоритет |
|---|-----------|------|----------|-----------|
| E37 | **Happy path: найти → скачать** | / → /catalog → поиск → карточка → скачать | ZIP получен | P0 |
| E38 | **Happy path: конструктор → сборка** | / → /constructor → выбор компонентов → генерация | ZIP получен | P0 |
| E39 | **Happy path: сборка → скачать** | / → /stacks → скачать | ZIP получен | P0 |

---

## 6. Визуальное регрессионное тестирование

### 6.1 Подход

Использовать `playwright screenshot` для захвата key pages в базовом состоянии, затем сравнивать при изменениях.

### 6.2 Тест-кейсы

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| V1 | Скриншот HomeView — полная страница | Соответствие baseline | P1 |
| V2 | Скриншот CatalogView — полная страница | Соответствие baseline | P1 |
| V3 | Скриншот ConstructorView — полная страница | Соответствие baseline | P1 |
| V4 | Скриншот StacksView — полная страница | Соответствие baseline | P1 |
| V5 | Скриншот SecurityReport — полная страница | Соответствие baseline | P1 |
| V6 | Скриншот 404 страницы | Соответствие baseline | P2 |
| V7 | Скриншот ComponentCard (один элемент) | Соответствие baseline | P1 |
| V8 | Скриншот ConfigWizard modal | Соответствие baseline | P1 |
| V9 | Скриншот CveTable — все severity | Соответствие baseline | P2 |
| V10 | Скриншот mobile menu (375px) | Соответствие baseline | P2 |

---

## 7. Responsive / Adaptive тестирование

### 7.1 Viewport sizes

- **Desktop:** 1280×720, 1920×1080
- **Tablet:** 768×1024 (iPad)
- **Mobile:** 375×667 (iPhone SE), 390×844 (iPhone 14)
- **Small mobile:** 320×568 (iPhone 5)

### 7.2 Тест-кейсы

| # | Тест-кейс | Viewport | Ожидание | Приоритет |
|---|-----------|----------|----------|-----------|
| R1 | HomeView — планшет (768px) | 768×1024 | 2 колонки категорий | P1 |
| R2 | HomeView — мобильный (375px) | 375×667 | 1 колонка, скрытый desktop nav | P0 |
| R3 | CatalogView — мобильный | 375×667 | Карточки в 1 колонку, поиск полный | P0 |
| R4 | ConstructorView — мобильный | 375×667 | Вертикальная компоновка | P1 |
| R5 | CveTable — мобильный | 375×667 | Горизонтальный скролл или адаптивная таблица | P1 |
| R6 | Nav — hamburger menu | 375×667 | Mobile menu открывается/закрывается | P0 |
| R7 | Footer — мобильный | 375×667 | 1 колонка | P1 |
| R8 | Все страницы — 320px | 320×568 | Нет горизонтального скролла | P2 |
| R9 | SecurityReport — мобильный | 375×667 | Табы на всю ширину | P1 |
| R10 | ConfigWizard — мобильный | 375×667 | Модал на весь экран | P1 |

---

## 8. Accessibility тестирование

### 8.1 Инструменты

- `@axe-core/playwright` — автоматическая проверка a11y
- Ручная проверка keyboard navigation
- focus management для модальных окон (ConfigWizard)

### 8.2 Тест-кейсы

| # | Тест-кейс | Ожидание | Приоритет |
|---|-----------|----------|-----------|
| A1 | HomeView — axe scan | 0 критических нарушений | P0 |
| A2 | CatalogView — axe scan | 0 критических нарушений | P0 |
| A3 | ConstructorView — axe scan | 0 критических нарушений | P0 |
| A4 | StacksView — axe scan | 0 критических нарушений | P0 |
| A5 | SecurityReportView — axe scan | 0 критических нарушений | P0 |
| A6 | ConfigWizard modal — axe scan | 0 critical violations | P0 |
| A7 | Все картинки имеют alt-текст | Alt присутствует | P1 |
| A8 | Все кнопки доступны с клавиатуры | Tab + Enter/Space | P1 |
| A9 | Focus trap в ConfigWizard | Focus не уходит из модала | P1 |
| A10 | Контраст текста (WCAG AA) | Минимум 4.5:1 | P1 |
| A11 | ARIA labels на иконках | aria-label или aria-hidden | P1 |
| A12 | Skip to main content link | Ссылка в начале body | P2 |
| A13 | Закрытие ConfigWizard по Escape | emit('close') | P1 |

---

## 9. Производительность фронтенда

### 9.1 Lighthouse CI

| # | Метрика | Целевое значение | Приоритет |
|---|---------|------------------|-----------|
| L1 | Performance score | ≥ 90 | P1 |
| L2 | Accessibility score | ≥ 90 | P0 |
| L3 | Best Practices score | ≥ 90 | P1 |
| L4 | SEO score | ≥ 90 | P2 |
| L5 | Largest Contentful Paint (LCP) | ≤ 2.5s | P1 |
| L6 | First Input Delay (FID) / TBT | ≤ 50ms / ≤ 200ms | P1 |
| L7 | Cumulative Layout Shift (CLS) | ≤ 0.1 | P1 |
| L8 | Speed Index | ≤ 3.0s | P2 |

### 9.2 Bundle Analysis

| # | Метрика | Целевое значение | Приоритет |
|---|---------|------------------|-----------|
| B1 | Total JS bundle size (gzip) | ≤ 150 KB | P1 |
| B2 | Total CSS bundle size (gzip) | ≤ 50 KB | P1 |
| B3 | Vue chunk size | ≤ 100 KB | P1 |
| B4 | Routes lazy-loaded | Да (dynamic import) | P2 |

### 9.3 Lighthouse тесты

| # | Тест-кейс | Приоритет |
|---|-----------|-----------|
| P1 | Lighthouse audit — HomeView (desktop) | P1 |
| P2 | Lighthouse audit — HomeView (mobile) | P1 |
| P3 | Lighthouse audit — CatalogView (desktop) | P1 |
| P4 | Lighthouse audit — ConstructorView (desktop) | P2 |

---

## 10. Приоритизация по этапам и срокам

### Этап 1 (2 июня — до нормоконтроля 5 июня) — MUST HAVE, P0

**Цель:** Минимально жизнеспособное тестирование для нормоконтроля

| Что делать | Трудозатраты | Кто |
|-----------|-------------|-----|
| Настроить Vitest + Vue Test Utils | 1 час | — |
| Написать unit-тесты: `security.ts` (10 тестов) | 30 мин | — |
| Написать unit-тесты: `AppIcon`, `SourceBadge`, `ScoreBadge`, `SeverityBar` (10 тестов) | 1 час | — |
| Написать unit-тесты: `CveTable` (8 тестов, поиск/фильтр/сортировка) | 1.5 часа | — |
| Написать unit-тесты: `useApi` happy path (5 тестов) | 1 час | — |
| Написать E2E: Home + Catalog + Navigation (10 сценариев) | 2 часа | — |
| Написать E2E: Constructor + Stacks + Security (8 сценариев) | 2 часа | — |
| Accessibility: axe-core scan (6 страниц) | 1 час | — |
| **Итого Этап 1:** | ~10 часов | |

### Этап 2 (5–10 июня) — SHOULD HAVE, P1

**Цель:** Расширенное покрытие, регресс и адаптивность

| Что делать | Трудозатраты |
|-----------|-------------|
| Unit-тесты: `ConfigWizard` (10 тестов) | 2 часа |
| Unit-тесты: `ComponentCard` (7 тестов) | 1.5 часа |
| Unit-тесты: `StackCard` (5 тестов) | 1 час |
| Unit-тесты: `SecuritySummary` (6 тестов) | 1 час |
| Unit-тесты: `DependencyGraph` (4 теста) | 1 час |
| Unit-тесты: `SkeletonGrid` (2 теста) | 30 мин |
| Unit-тесты: `Footer` (3 теста) | 30 мин |
| Integration: все страницы (24 теста) | 4 часа |
| E2E: дополнительные сценарии (10 тестов) | 2 часа |
| Visual regression: 8 screenshots | 2 часа |
| Responsive: 10 тестов | 2 часа |
| A11y: keyboard nav + focus trap + contrast | 2 часа |
| **Итого Этап 2:** | ~20 часов |

### Этап 3 (10–15 июня) — NICE TO HAVE, P2

**Цель:** Полное покрытие, производительность

| Что делать | Трудозатраты |
|-----------|-------------|
| Unit-тесты: оставшиеся edge cases (10 тестов) | 2 часа |
| E2E: полные user flows (5 сценариев) | 2 часа |
| Lighthouse CI: 4 аудита | 2 часа |
| Bundle analysis: 4 проверки | 1 час |
| Visual regression: доп. 5 screenshots | 1 час |
| A11y: WCAG полный аудит | 3 часа |
| **Итого Этап 3:** | ~11 часов |

---

## 11. Сводная таблица трудозатрат

| Тип тестирования | # тестов | Трудозатраты (часы) | Этап |
|-----------------|----------|--------------------|------|
| **Unit-тесты компонентов** | 73 | 10 | 1 + 2 |
| — Pure utils (security.ts) | 10 | 0.5 | 1 |
| — AppIcon, SourceBadge, ScoreBadge, SeverityBar | 14 | 1.5 | 1 |
| — CveTable | 9 | 1.5 | 1 |
| — ConfigWizard | 10 | 2 | 2 |
| — ComponentCard, StackCard | 12 | 2.5 | 2 |
| — SecuritySummary, DependencyGraph, Footer, SkeletonGrid | 14 | 3 | 2 |
| — Composable | 14 | 2 | 1 |
| **Интеграционные тесты** | 55 | 4 | 2 |
| **E2E тесты (Playwright)** | 39 | 6 | 1 + 2 |
| **Visual Regression** | 10 | 2 | 2 |
| **Responsive тесты** | 10 | 2 | 2 |
| **Accessibility тесты** | 13 | 3 | 1 + 2 |
| **Производительность** | 12 | 3 | 3 |
| | | | |
| **ИТОГО** | **~212 тестов** | **~41 час** | |

---

## 12. Рекомендации по внедрению

### 12.1 Data-testid атрибуты

Добавить `data-testid` в критические элементы для стабильных E2E-селекторов:

```html
<button data-testid="download-btn">
<div data-testid="component-card">
<input data-testid="search-input">
<div data-testid="cve-table">
```

### 12.2 Mock API

- Использовать `vi.mock()` для `useApi` в unit-тестах
- Для E2E: Playwright route interception (`page.route('**/api/**')`)
- Подготовить JSON fixture для компонентов, категорий, стеков, отчёта безопасности

### 12.3 CI/CD интеграция

- Добавить `npm run test` в pre-commit hook (или pre-push)
- Добавить `npm run test:coverage` и `npm run test:e2e` в GitHub Actions
- Требовать coverage ≥ 60% для новых PR (цель: 40%+ общее)

### 12.4 Покрытие кода (цель)

| Модуль | Цель покрытия |
|--------|--------------|
| src/utils/security.ts | 100% |
| src/composables/useApi.ts | 90%+ |
| src/composables/useSecurityReport.ts | 90%+ |
| UI-компоненты (каждый) | 70%+ |
| Views (интеграционные) | 60%+ |
| **Общее покрытие** | **40%+** |

### 12.5 Быстрый старт (Makefile target)

```makefile
.PHONY: test
test:
	npm run test

.PHONY: test-coverage
test-coverage:
	npm run test:coverage

.PHONY: test-e2e
test-e2e:
	npm run test:e2e

.PHONY: test-all
test-all: test test-e2e test-coverage

.PHONY: test-setup
test-setup:
	npm install -D vitest @vue/test-utils happy-dom jsdom @playwright/test @axe-core/playwright rollup-plugin-visualizer
	npx playwright install chromium
```

### 12.6 Риски и митигации

| Риск | Митигация |
|------|-----------|
| **Deadline нормоконтроля (5 июня)** | Фокус только на P0: unit (security, core components) + E2E (critical paths) + a11y scan |
| **Нет времени на drag-and-drop тесты** | Отложить до Этапа 3, если не реализован DnD |
| **Backend недоступен для E2E** | Использовать Playwright route interception (mock API) |
| **Изменения в UI сломают тесты** | Использовать data-testid, а не CSS-селекторы |
| **Vue warnings в тестах** | Настроить `config.warnHandler` в setup |
| **Tailwind CSS purge в production** | Visual regression тестировать build версию |

### 12.7 Начать с Makefile

```makefile
# test-setup target for quick bootstrap
```

---

## Приложение A: Пример unit-теста (security.ts)

```ts
import { describe, it, expect } from 'vitest'
import { calculateSecurityScore, scoreToGrade } from '../utils/security'

describe('calculateSecurityScore', () => {
  it('returns 100 for zero vulnerabilities', () => {
    expect(calculateSecurityScore({ CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 })).toBe(100)
  })

  it('penalizes CRITICAL * 15', () => {
    expect(calculateSecurityScore({ CRITICAL: 1, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 })).toBe(85)
  })

  it('penalizes HIGH * 5', () => {
    expect(calculateSecurityScore({ CRITICAL: 0, HIGH: 2, MEDIUM: 0, LOW: 0, UNKNOWN: 0 })).toBe(90)
  })

  it('clamps score to minimum 0', () => {
    expect(calculateSecurityScore({ CRITICAL: 100, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 })).toBe(0)
  })
})

describe('scoreToGrade', () => {
  it('returns A for score >= 90', () => { expect(scoreToGrade(95)).toBe('A') })
  it('returns B for 70-89', () => { expect(scoreToGrade(75)).toBe('B') })
  it('returns C for 50-69', () => { expect(scoreToGrade(60)).toBe('C') })
  it('returns D for 30-49', () => { expect(scoreToGrade(40)).toBe('D') })
  it('returns E for < 30', () => { expect(scoreToGrade(10)).toBe('E') })
})
```

## Приложение B: Пример E2E-теста (Playwright)

```ts
import { test, expect } from '@playwright/test'

test.describe('Home Page', () => {
  test('displays hero section and categories', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('GosDocker')
    const categories = page.locator('[data-testid=category-card]')
    await expect(categories.first()).toBeVisible()
    await expect(categories).not.toHaveCount(0)
  })

  test('navigates to catalog on category click', async ({ page }) => {
    await page.goto('/')
    const firstCategory = page.locator('[data-testid=category-card]').first()
    await firstCategory.click()
    await expect(page).toHaveURL(/\/catalog\?category=.+/)
  })
})

test.describe('Security Report', () => {
  test('filters vulnerabilities by severity', async ({ page }) => {
    await page.goto('/security/postgres')
    await page.selectOption('select', 'CRITICAL')
    const rows = page.locator('[data-testid=vuln-row]')
    const count = await rows.count()

    // Verify all shown rows are CRITICAL
    for (let i = 0; i < count; i++) {
      await expect(rows.nth(i).locator('[data-testid=severity-badge]')).toContainText('CRITICAL')
    }
  })
})
```

---

*Документ сгенерирован 2 июня 2026. План является живым документом — обновлять по мере реализации.*
