<script setup lang="ts">
const { t, locale, locales, setLocale } = useI18n()
const head = useLocaleHead()

useHead(() => ({ htmlAttrs: { lang: head.value.htmlAttrs?.lang } }))
useSeoMeta({ title: () => t('meta.title'), description: () => t('meta.description') })
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <header class="app-wrap flex h-16 items-center justify-between gap-3">
      <NuxtLink to="/" class="text-[15px] font-semibold tracking-tight">
        Piano to MIDI
      </NuxtLink>
      <div class="flex rounded-full border border-line p-0.5 text-xs font-medium" role="group" :aria-label="t('lang.label')">
        <button
          v-for="l in locales"
          :key="l.code"
          type="button"
          class="cursor-pointer rounded-full px-2.5 py-1 uppercase tracking-wide"
          :class="l.code === locale ? 'bg-surface text-ink shadow-card' : 'text-muted hover:text-ink'"
          :aria-pressed="l.code === locale"
          :lang="l.language"
          :title="l.name"
          @click="setLocale(l.code)"
        >
          {{ l.code }}
        </button>
      </div>
    </header>

    <main class="app-wrap flex-1 pb-16 pt-6 sm:pt-10">
      <NuxtPage />
    </main>

    <footer class="app-wrap grid gap-1 border-t border-line py-6 text-sm text-muted">
      <p>{{ t('footer.privacy') }}</p>
      <p>{{ t('footer.model') }}</p>
    </footer>
  </div>
</template>
