<script setup lang="ts">
import type { Arrangement, Job, OptionsInfo } from '~/types/api'

const props = defineProps<{ job: Job }>()
const { t } = useI18n()
const api = useApi()

const info = ref<OptionsInfo | null>(null)
const arrangement = shallowRef<Arrangement | null>(null)
const position = ref(0)

onMounted(async () => {
  info.value = await api.optionsInfo()
  arrangement.value = await api.notes(props.job.id, info.value.defaults)
})
</script>

<template>
  <section class="grid gap-4 rounded-card border border-line bg-surface p-4 shadow-card sm:p-6">
    <div class="grid gap-1">
      <h1 class="truncate text-xl font-semibold" :title="job.filename">
        {{ job.filename }}
      </h1>
      <p class="text-ink-2">
        {{ t('result.summary', { notes: arrangement?.notes.length ?? job.notes ?? 0, time: clock(job.seconds ?? 0) }) }}
      </p>
    </div>
    <PianoRoll v-if="arrangement" :arrangement="arrangement" :position="position" @seek="position = $event" />
    <div v-else class="h-[350px] animate-pulse rounded-xl bg-surface-2 motion-reduce:animate-none" />
  </section>
</template>
