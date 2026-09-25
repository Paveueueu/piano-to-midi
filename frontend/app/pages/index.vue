<script setup lang="ts">
const { t } = useI18n()
const config = useRuntimeConfig()

// Placeholder until uploading lands: confirms the web app can reach the API.
const { data, error } = await useFetch<{ status: string }>('/health', {
  baseURL: config.public.apiBase,
  server: false,
})
</script>

<template>
  <section class="grid gap-4">
    <h1 class="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
      {{ t('app.tagline') }}
    </h1>
    <p class="max-w-2xl text-lg text-ink-2">
      {{ t('app.lead') }}
    </p>
    <p class="flex gap-1.5 text-sm" aria-live="polite">
      <span class="text-muted">{{ t('api.label') }}:</span>
      <span v-if="data" class="font-medium text-accent">{{ t('api.ok') }}</span>
      <span v-else-if="error" class="font-medium text-danger">{{ t('api.down') }}</span>
      <span v-else class="text-muted">{{ t('api.checking') }}</span>
    </p>
  </section>
</template>
