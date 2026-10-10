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
const player = usePlayer(arrangement, useRecordings().url(props.job.id))

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

// Settings change instantly on the server (the model doesn't run again); a short pause
// avoids a request per slider step.
let pending: ReturnType<typeof setTimeout> | null = null
let latest = 0
watch(options, (o) => {
  if (!o) return
  if (pending) clearTimeout(pending)
  pending = setTimeout(async () => {
    const ticket = ++latest
    loading.value = true
    try {
      const result = await api.notes(props.job.id, o)
      if (ticket === latest) arrangement.value = result
    }
    finally {
      if (ticket === latest) loading.value = false
    }
  }, arrangement.value ? 150 : 0)
}, { deep: true })
</script>

<template>
  <section class="grid gap-5 rounded-card border border-line bg-surface p-4 shadow-card sm:p-6">
    <div class="grid gap-1">
      <h1 class="truncate text-xl font-semibold" :title="job.filename">
        {{ job.filename }}
      </h1>
      <p class="text-ink-2">
        {{ t('result.summary', { notes: arrangement?.notes.length ?? job.notes ?? 0, time: clock(job.seconds ?? 0) }) }}
        <span v-if="arrangement?.detected_bpm" class="text-muted"> – {{ t('result.tempo', { bpm: Math.round(arrangement.detected_bpm) }) }}</span>
      </p>
    </div>

    <div class="relative">
      <PianoRoll v-if="arrangement" :arrangement="arrangement" :position="player.position.value" :class="loading ? 'opacity-70 transition-opacity' : ''" @seek="player.seek" />
      <div v-else class="h-[350px] animate-pulse rounded-xl bg-surface-2 motion-reduce:animate-none" />
    </div>

    <div v-if="arrangement" class="grid gap-1">
      <PlayerBar
        :playing="player.playing.value"
        :position="player.position.value"
        :duration="arrangement.seconds"
        :source="player.source.value"
        :has-original="player.hasOriginal"
        @toggle="player.playing.value ? player.pause() : player.play()"
        @source="player.setSource"
      />
      <p v-if="player.source.value === 'midi'" class="text-xs text-muted">
        {{ t('player.midiNote') }}
      </p>
    </div>

    <SettingsPanel v-if="base && options" v-model:options="options" :base="base" :auto="auto" :arrangement="arrangement" />
  </section>
</template>
