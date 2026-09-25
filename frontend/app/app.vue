<script setup lang="ts">
const { t, locale, locales, setLocale } = useI18n()
const head = useLocaleHead()

useHead(() => ({ htmlAttrs: { lang: head.value.htmlAttrs?.lang } }))
useSeoMeta({ title: () => t('meta.title'), description: () => t('meta.description') })
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <header class="app-wrap flex items-center justify-between py-5">
      <NuxtLink to="/" class="text-lg font-semibold tracking-tight">
        Piano to MIDI
      </NuxtLink>
      <div class="flex gap-1 text-sm" role="group" :aria-label="t('lang.label')">
        <button
          v-for="l in locales"
          :key="l.code"
          type="button"
          class="cursor-pointer rounded-full px-2.5 py-1 uppercase tracking-wide"
          :class="l.code === locale ? 'bg-ink text-bg' : 'text-muted hover:text-ink'"
          :aria-pressed="l.code === locale"
          :lang="l.language"
          :title="l.name"
          @click="setLocale(l.code)"
        >
          {{ l.code }}
        </button>
      </div>
    </header>

    <main class="app-wrap flex-1 pb-16 pt-4 sm:pt-8">
      <NuxtPage />
    </main>

    <footer class="app-wrap grid gap-1 border-t border-line py-6 text-sm text-muted">
      <p>{{ t('footer.privacy') }}</p>
      <p>{{ t('footer.model') }}</p>
    </footer>
  </div>
</template>
