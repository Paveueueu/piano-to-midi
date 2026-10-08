<script setup lang="ts">
import type { Job } from '~/types/api'

const props = defineProps<{ job: Job }>()
const { t } = useI18n()

const startedAt = ref<number | null>(null)
const now = ref(Date.now())
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => { timer = setInterval(() => { now.value = Date.now() }, 1000) })
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

watch(
  () => props.job.status,
  (status) => {
    if (status === 'running' && startedAt.value === null) startedAt.value = Date.now()
  },
  { immediate: true },
)

const remaining = computed(() => {
  const p = props.job.progress
  if (props.job.status !== 'running' || startedAt.value === null || p < 0.15) return null
  const elapsed = (now.value - startedAt.value) / 1000
  return Math.max(1, Math.round((elapsed * (1 - p)) / p))
})
</script>

<template>
  <div class="grid gap-4 rounded-card border border-line bg-surface p-6 shadow-card" role="status" aria-live="polite">
    <p class="truncate font-medium" :title="job.filename">
      {{ job.filename }}
    </p>
    <template v-if="job.status === 'queued'">
      <p class="text-ink-2">
        {{ job.position ? t('job.waiting', { n: job.position }, job.position) : t('job.next') }}
      </p>
      <div class="h-2 overflow-hidden rounded-full bg-surface-2">
        <div class="h-full w-1/4 animate-pulse rounded-full bg-line-strong motion-reduce:animate-none" />
      </div>
    </template>
    <template v-else>
      <p class="text-ink-2">
        {{ t('job.listening') }}
      </p>
      <div class="h-2 overflow-hidden rounded-full bg-surface-2">
        <div class="h-full rounded-full bg-accent transition-[width] duration-700" :style="{ width: `${Math.round(job.progress * 100)}%` }" />
      </div>
      <p class="flex justify-between text-sm tabular-nums text-muted">
        <span>{{ Math.round(job.progress * 100) }}%</span>
        <span v-if="remaining">{{ t('job.remaining', { time: clock(remaining) }) }}</span>
      </p>
    </template>
  </div>
</template>
