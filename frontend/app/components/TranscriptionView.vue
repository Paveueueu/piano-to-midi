<script setup lang="ts">
import type { Arrangement, AutoSettings, Job, Options, OptionsInfo } from '~/types/api'

const props = defineProps<{ job: Job }>()
const { t } = useI18n()
const api = useApi()

const info = ref<OptionsInfo | null>(null)
const auto = ref<AutoSettings | null>(null)
const options = ref<Options | null>(null)
const base = computed(() => auto.value?.options ?? info.value?.defaults ?? null)
const arrangement = shallowRef<Arrangement | null>(null)
const loading = ref(false)
const recordings = useRecordings()
const player = usePlayer(arrangement, recordings.url(props.job.id))

const midiUrl = computed(() => (options.value ? api.midiUrl(props.job.id, options.value) : null))
const noteCount = computed(() => arrangement.value?.notes.length ?? props.job.notes ?? 0)
const confirming = ref(false)
const deleting = ref(false)

async function remove() {
  deleting.value = true
  player.pause()
  try {
    await api.deleteJob(props.job.id)
  }
  catch { /* already gone */ }
  recordings.forget(props.job.id)
  await navigateTo('/')
}

onMounted(async () => {
  info.value = await api.optionsInfo()
  if (props.job.auto) {
    try {
      auto.value = await api.auto(props.job.id)
    }
    catch { /* Auto is optional */ }
  }
  options.value = { ...base.value! }
})

// Debounce setting changes; pause playback and show a spinner until the new notes arrive.
const SETTLE_MS = 150
const MIN_SPINNER_MS = 400
let pending: ReturnType<typeof setTimeout> | null = null
let latest = 0
let resume = false
let spinnerSince = 0

watch(options, (o) => {
  if (!o) return
  const first = !arrangement.value
  if (player.playing.value) {
    resume = true
    player.pause()
  }
  if (!loading.value) spinnerSince = performance.now()
  loading.value = true
  if (pending) clearTimeout(pending)
  pending = setTimeout(async () => {
    const ticket = ++latest
    let result: Arrangement | null = null
    try {
      result = await api.notes(props.job.id, o)
    }
    catch { /* keep the notes shown */ }
    if (!first) await new Promise(r => setTimeout(r, Math.max(0, MIN_SPINNER_MS - (performance.now() - spinnerSince))))
    if (ticket !== latest) return
    if (result) arrangement.value = result
    loading.value = false
    if (resume) {
      resume = false
      await nextTick()
      player.play()
    }
  }, first ? 0 : SETTLE_MS)
}, { deep: true })

function toggle() {
  if (player.playing.value) player.pause()
  else if (!loading.value) player.play()
}
</script>

<template>
  <section class="grid gap-5 rounded-card border border-line bg-surface p-4 shadow-card sm:p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="grid min-w-0 gap-0.5">
        <h1 class="truncate text-xl font-semibold" :title="job.filename">
          {{ job.filename }}
        </h1>
        <p class="flex flex-wrap gap-x-3 text-sm text-muted">
          <span>{{ t('result.notes', { n: noteCount }, noteCount) }}</span>
          <span>{{ clock(job.seconds ?? 0) }}</span>
          <span v-if="arrangement?.detected_bpm">{{ t('result.tempo', { bpm: Math.round(arrangement.detected_bpm) }) }}</span>
        </p>
      </div>
      <a
        v-if="midiUrl"
        :href="midiUrl"
        class="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 font-medium text-accent-ink hover:opacity-90"
        :class="loading ? 'pointer-events-none opacity-60' : ''"
        :aria-disabled="loading"
      >
        <svg viewBox="0 0 24 24" class="size-5" aria-hidden="true"><path fill="currentColor" d="M12 3a1 1 0 0 1 1 1v9.6l3.3-3.3 1.4 1.4L12 17.4l-5.7-5.7 1.4-1.4 3.3 3.3V4a1 1 0 0 1 1-1zM5 19h14v2H5z" /></svg>
        {{ t('result.download') }}
      </a>
    </div>

    <div class="relative">
      <PianoRoll v-if="arrangement" :arrangement="arrangement" :position="player.position.value" @seek="player.seek" />
      <div v-else class="h-[370px] animate-pulse rounded-xl bg-surface-2 motion-reduce:animate-none" />
      <div
        v-if="arrangement && loading"
        class="pointer-events-none absolute inset-x-0 bottom-0 top-9 grid place-items-center rounded-xl bg-surface/50"
        role="status"
      >
        <span class="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-sm shadow-card">
          <svg viewBox="0 0 24 24" class="size-4 animate-spin text-accent motion-reduce:animate-none" aria-hidden="true">
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-opacity="0.25" stroke-width="3" />
            <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
          </svg>
          {{ t('result.updating') }}
        </span>
      </div>
    </div>

    <PlayerBar
      v-if="arrangement"
      :playing="player.playing.value"
      :busy="loading"
      :position="player.position.value"
      :duration="arrangement.seconds"
      :source="player.source.value"
      :has-original="player.hasOriginal"
      @toggle="toggle"
      @restart="player.seek(0)"
      @source="player.setSource"
    />

    <SettingsPanel v-if="base && options" v-model:options="options" :base="base" :arrangement="arrangement" />

    <div class="flex flex-wrap items-center gap-2 border-t border-line pt-4 text-sm">
      <button v-if="!confirming" type="button" class="cursor-pointer text-muted underline decoration-line-strong underline-offset-2 hover:text-danger" @click="confirming = true">
        {{ t('result.delete') }}
      </button>
      <template v-else>
        <span>{{ t('result.confirmDelete') }}</span>
        <button type="button" class="cursor-pointer rounded-full bg-danger px-3 py-1.5 text-bg disabled:opacity-50" :disabled="deleting" @click="remove">
          {{ t('result.yesDelete') }}
        </button>
        <button type="button" class="cursor-pointer rounded-full border border-line px-3 py-1.5" @click="confirming = false">
          {{ t('result.cancel') }}
        </button>
      </template>
    </div>
  </section>
</template>
