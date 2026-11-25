<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <div class="grid gap-6">
    <div class="grid gap-2">
      <h1 class="text-4xl font-semibold tracking-tight sm:text-5xl">
        {{ t('home.title') }}
      </h1>
      <p class="max-w-2xl text-lg text-ink-2">
        {{ t('home.lead') }}
      </p>
    </div>

    <UploadBox />

    <RecentList class="mt-4" />
  </div>
</template>
