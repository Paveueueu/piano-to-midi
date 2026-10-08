<script setup lang="ts">
import type { Job } from '~/types/api'
import { ApiError } from '~/composables/useApi'

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const id = computed(() => String(route.params.id))

const job = ref<Job | null>(null)
const problem = ref<string | null>(null)
let timer: ReturnType<typeof setTimeout> | null = null

async function poll() {
  try {
    job.value = await api.job(id.value)
    problem.value = null
  }
  catch (error: unknown) {
    problem.value = error instanceof ApiError ? error.reason : 'internal'
    if (problem.value === 'expired') return
  }
  if (!job.value || job.value.status === 'queued' || job.value.status === 'running') {
    timer = setTimeout(poll, 1000)
  }
}

onMounted(poll)
onBeforeUnmount(() => { if (timer) clearTimeout(timer) })

useSeoMeta({ title: () => (job.value ? `${job.value.filename} – Piano to MIDI` : 'Piano to MIDI') })
</script>

<template>
  <div class="grid gap-6">
    <NuxtLink to="/" class="text-sm text-muted underline decoration-line-strong underline-offset-2 hover:text-ink">
      {{ t('job.another') }}
    </NuxtLink>

    <div v-if="problem && !job" class="grid gap-2 rounded-card border border-line bg-surface p-6" role="alert">
      <p class="font-medium">
        {{ t(`errors.${problem}`, { mb: 50, minutes: 10 }) }}
      </p>
    </div>

    <template v-else-if="job">
      <JobProgress v-if="job.status === 'queued' || job.status === 'running'" :job="job" />

      <div v-else-if="job.status === 'failed'" class="grid gap-2 rounded-card border border-line bg-surface p-6" role="alert">
        <p class="font-medium">
          {{ t('job.failed', { name: job.filename }) }}
        </p>
        <p class="text-ink-2">
          {{ t(`errors.${job.error ?? 'internal'}`, { mb: 50, minutes: 10 }) }}
        </p>
      </div>

      <TranscriptionView v-else :job="job" />
    </template>
  </div>
</template>
