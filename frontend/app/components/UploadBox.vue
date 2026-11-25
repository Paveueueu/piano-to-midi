<script setup lang="ts">
import type { Limits } from '~/types/api'
import { ApiError } from '~/composables/useApi'

const { t } = useI18n()
const api = useApi()
const recordings = useRecordings()
const recent = useRecent()

const limits = ref<Limits | null>(null)
const dragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const sending = ref('')
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
  sending.value = file.name
  try {
    const job = await api.createJob(file, (f) => { progress.value = f })
    recordings.keep(job.id, file)
    recent.add(job.id, file.name)
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

// dragleave also fires when the pointer moves onto a child; only leaving the box counts.
function onLeave(e: DragEvent) {
  const box = e.currentTarget as HTMLElement
  if (!box.contains(e.relatedTarget as Node | null)) dragging.value = false
}

function onPick(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) send(file)
  ;(e.target as HTMLInputElement).value = ''
}
</script>

<template>
  <div class="grid gap-3">
    <section
      class="relative rounded-card border bg-surface shadow-card transition-colors"
      :class="dragging ? 'border-accent bg-accent/5' : 'border-line'"
      :aria-label="t('upload.drop')"
      @dragenter.prevent="dragging = true"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="onLeave"
      @drop.prevent="onDrop"
    >
      <div v-if="!uploading" class="flex flex-wrap items-center gap-x-5 gap-y-4 px-5 py-6 sm:px-6 sm:py-7">
        <span class="grid size-12 flex-none place-items-center rounded-full bg-surface-2 text-ink-2 ring-1 ring-line" aria-hidden="true">
          <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M4 10v4M8 7v10M12 4v16M16 8v8M20 11v2" />
          </svg>
        </span>
        <div class="grid min-w-48 flex-1 gap-0.5">
          <p class="text-lg font-semibold leading-snug">
            {{ dragging ? t('upload.release') : t('upload.drop') }}
          </p>
          <p class="text-sm text-muted">
            {{ limits
              ? t('upload.limits', { mb: limits.max_upload_mb, minutes: limits.max_audio_minutes })
              : t('upload.formats') }}
          </p>
        </div>
        <button
          type="button"
          class="cursor-pointer rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-bg hover:opacity-85"
          @click="input?.click()"
        >
          {{ t('upload.choose') }}
        </button>
      </div>

      <div v-else class="grid gap-3 px-5 py-6 sm:px-6 sm:py-7" role="status">
        <div class="flex items-baseline justify-between gap-4">
          <div class="grid min-w-0 gap-0.5">
            <p class="truncate text-lg font-semibold leading-snug" :title="sending">
              {{ sending }}
            </p>
            <p class="text-sm text-muted">
              {{ t('upload.sending') }}
            </p>
          </div>
          <span class="tabular-nums text-sm text-muted">{{ Math.round(progress * 100) }}%</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div class="h-full rounded-full bg-ink transition-[width]" :style="{ width: `${Math.round(progress * 100)}%` }" />
        </div>
      </div>

      <input
        ref="input"
        type="file"
        accept="audio/*,.mp3,.m4a,.wav,.flac,.ogg,.opus"
        class="sr-only"
        :aria-label="t('upload.choose')"
        @change="onPick"
      >
    </section>
    <p v-if="problem" class="rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger" role="alert">
      {{ t(`errors.${problem}`, { mb: limits?.max_upload_mb ?? 50, minutes: limits?.max_audio_minutes ?? 10 }) }}
    </p>
  </div>
</template>
