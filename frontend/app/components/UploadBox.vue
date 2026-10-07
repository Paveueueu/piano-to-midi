<script setup lang="ts">
import type { Limits } from '~/types/api'
import { ApiError } from '~/composables/useApi'

const { t } = useI18n()
const api = useApi()
const recordings = useRecordings()

const limits = ref<Limits | null>(null)
const dragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const problem = ref<string | null>(null)
const input = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  try {
    limits.value = await api.limits()
  }
  catch {
    problem.value = 'network'
  }
})

const AUDIO_EXTENSIONS = ['mp3', 'm4a', 'aac', 'wav', 'flac', 'ogg', 'opus', 'webm', 'aiff', 'aif', 'wma']

function looksLikeAudio(file: File): boolean {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  return file.type.startsWith('audio/') || AUDIO_EXTENSIONS.includes(extension)
}

async function send(file: File) {
  problem.value = null
  if (!looksLikeAudio(file)) {
    problem.value = 'not_audio'
    return
  }
  if (limits.value && file.size > limits.value.max_upload_mb * 1024 * 1024) {
    problem.value = 'too_large'
    return
  }
  uploading.value = true
  progress.value = 0
  try {
    const job = await api.createJob(file, (f) => { progress.value = f })
    recordings.keep(job.id, file)
    await navigateTo(`/jobs/${job.id}`)
  }
  catch (error: unknown) {
    problem.value = error instanceof ApiError ? error.reason : 'internal'
  }
  finally {
    uploading.value = false
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file && !uploading.value) send(file)
}

function onPick(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) send(file)
  ;(e.target as HTMLInputElement).value = ''
}
</script>

<template>
  <div class="grid gap-3">
    <div
      class="grid place-items-center gap-3 rounded-card border-2 border-dashed px-6 py-12 text-center transition-colors"
      :class="dragging ? 'border-accent bg-accent/5' : 'border-line-strong bg-surface'"
      @dragenter.prevent="dragging = true"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <svg viewBox="0 0 24 24" class="size-10 text-accent" aria-hidden="true">
        <path fill="currentColor" d="M12 3a1 1 0 0 1 1 1v9.6l3.3-3.3 1.4 1.4L12 17.4l-5.7-5.7 1.4-1.4 3.3 3.3V4a1 1 0 0 1 1-1zM5 19h14v2H5z" transform="rotate(180 12 12)" />
      </svg>
      <template v-if="!uploading">
        <p class="text-lg font-medium">
          {{ t('upload.drop') }}
        </p>
        <button
          type="button"
          class="cursor-pointer rounded-full bg-accent px-5 py-2.5 font-medium text-accent-ink hover:opacity-90"
          @click="input?.click()"
        >
          {{ t('upload.choose') }}
        </button>
        <p class="text-sm text-muted">
          {{ limits
            ? t('upload.limits', { mb: limits.max_upload_mb, minutes: limits.max_audio_minutes })
            : t('upload.formats') }}
        </p>
      </template>
      <div v-else class="grid w-full max-w-sm gap-2" role="status">
        <p class="font-medium">
          {{ t('upload.sending') }}
        </p>
        <div class="h-2 overflow-hidden rounded-full bg-surface-2">
          <div class="h-full rounded-full bg-accent transition-[width]" :style="{ width: `${Math.round(progress * 100)}%` }" />
        </div>
        <p class="text-sm tabular-nums text-muted">
          {{ Math.round(progress * 100) }}%
        </p>
      </div>
      <input
        ref="input"
        type="file"
        accept="audio/*,.mp3,.m4a,.wav,.flac,.ogg,.opus"
        class="sr-only"
        :aria-label="t('upload.choose')"
        @change="onPick"
      >
    </div>
    <p v-if="problem" class="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger" role="alert">
      {{ t(`errors.${problem}`, { mb: limits?.max_upload_mb ?? 50, minutes: limits?.max_audio_minutes ?? 10 }) }}
    </p>
  </div>
</template>
