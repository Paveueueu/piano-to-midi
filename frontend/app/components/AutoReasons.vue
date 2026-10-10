<script setup lang="ts">
import type { Reason } from '~/types/api'

const props = defineProps<{ reasons: Reason[] }>()
const { t, locale } = useI18n()

/** Each reason as a sentence; numbers come from the API, words from the locale files. */
const sentences = computed(() =>
  props.reasons.map((r) => {
    const v = r.values
    switch (r.code) {
      case 'noisy_recording':
        return t('auto.noisy', { db: Math.round(Math.abs(Number(v.noise_db))) })
      case 'sensitivity_raised':
        return t('auto.raised', { n: Number(v.notes_changed) }, Number(v.notes_changed))
      case 'sensitivity_lowered':
        return t('auto.lowered', { n: Number(v.notes_changed) }, Number(v.notes_changed))
      case 'steady_rhythm':
        return t('auto.steady', { bpm: Math.round(Number(v.bpm)), grid: String(v.grid) })
      case 'free_rhythm':
        return v.bpm ? t('auto.free', { bpm: Math.round(Number(v.bpm)) }) : t('auto.fewNotes')
      case 'hands_split':
        return t('auto.split', { key: keyName(Number(v.split_key), locale.value) })
      case 'hands_together':
        return t('auto.together')
      case 'sensitivity_default':
        return t('auto.sensitivityKept')
      default:
        return null
    }
  }).filter((s): s is string => s !== null),
)
</script>

<template>
  <ul class="grid gap-1.5 text-sm text-ink-2">
    <li v-for="(s, i) in sentences" :key="i" class="flex gap-2">
      <span class="mt-2 size-1.5 flex-none rounded-full bg-accent" aria-hidden="true" />
      <span>{{ s }}</span>
    </li>
  </ul>
</template>
