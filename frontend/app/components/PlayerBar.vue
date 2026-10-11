<script setup lang="ts">
import type { Source } from '~/composables/usePlayer'

defineProps<{ playing: boolean, busy: boolean, position: number, duration: number, source: Source, hasOriginal: boolean }>()
const emit = defineEmits<{ toggle: [], restart: [], source: [Source] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <button
      type="button"
      class="grid size-9 cursor-pointer place-items-center rounded-full text-ink-2 hover:bg-surface-2 hover:text-ink"
      :aria-label="t('player.start')"
      :title="t('player.start')"
      @click="emit('restart')"
    >
      <svg viewBox="0 0 24 24" class="size-5" aria-hidden="true"><path fill="currentColor" d="M6 5h2v14H6zm3.5 7L18 18V6z" /></svg>
    </button>
    <button
      type="button"
      class="grid size-11 cursor-pointer place-items-center rounded-full bg-accent text-accent-ink hover:opacity-90 disabled:cursor-wait disabled:opacity-60"
      :aria-label="playing ? t('player.pause') : t('player.play')"
      :disabled="busy && !playing"
      @click="emit('toggle')"
    >
      <svg v-if="!playing" viewBox="0 0 24 24" class="size-5" aria-hidden="true"><path fill="currentColor" d="M8 5v14l11-7z" /></svg>
      <svg v-else viewBox="0 0 24 24" class="size-5" aria-hidden="true"><path fill="currentColor" d="M7 5h4v14H7zm6 0h4v14h-4z" /></svg>
    </button>
    <span class="ml-1 text-sm tabular-nums text-muted">{{ clock(position) }} / {{ clock(duration) }}</span>
    <div role="radiogroup" :aria-label="t('player.listen')" class="ml-auto flex gap-1 rounded-full border border-line p-0.5 text-sm">
      <button
        type="button"
        role="radio"
        :aria-checked="source === 'midi'"
        :title="t('player.midiNote')"
        class="cursor-pointer rounded-full px-3 py-1"
        :class="source === 'midi' ? 'bg-ink text-bg' : 'text-ink-2 hover:text-ink'"
        @click="emit('source', 'midi')"
      >
        MIDI
      </button>
      <button
        type="button"
        role="radio"
        :aria-checked="source === 'original'"
        :disabled="!hasOriginal"
        :title="hasOriginal ? undefined : t('player.noOriginal')"
        class="rounded-full px-3 py-1 disabled:cursor-not-allowed disabled:opacity-40"
        :class="source === 'original' ? 'bg-ink text-bg' : 'cursor-pointer text-ink-2 hover:text-ink'"
        @click="emit('source', 'original')"
      >
        {{ t('player.original') }}
      </button>
    </div>
  </div>
</template>
