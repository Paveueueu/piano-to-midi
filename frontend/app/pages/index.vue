<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <div class="grid gap-8">
    <section class="grid gap-4">
      <h1 class="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        {{ t('app.tagline') }}
      </h1>
      <p class="max-w-2xl text-lg text-ink-2">
        {{ t('app.lead') }}
      </p>
    </section>

    <UploadBox />
  </div>
</template>
