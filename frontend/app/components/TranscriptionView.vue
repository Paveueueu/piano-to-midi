<script setup lang="ts">
import type { Job } from '~/types/api'

defineProps<{ job: Job }>()
const { t } = useI18n()
</script>

<template>
  <section class="grid gap-2 rounded-card border border-line bg-surface p-6 shadow-card">
    <h1 class="truncate text-xl font-semibold" :title="job.filename">
      {{ job.filename }}
    </h1>
    <p class="text-ink-2">
      {{ t('result.summary', { notes: job.notes ?? 0, time: clock(job.seconds ?? 0) }) }}
    </p>
  </section>
</template>
