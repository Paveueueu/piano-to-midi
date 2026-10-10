<script setup lang="ts">
import type { Source } from '~/composables/usePlayer'

defineProps<{ playing: boolean, position: number, duration: number, source: Source, hasOriginal: boolean }>()
const emit = defineEmits<{ toggle: [], source: [Source] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <button
      type="button"
      class="grid size-11 cursor-pointer place-items-center rounded-full bg-accent text-accent-ink hover:opacity-90"
      :aria-label="playing ? t('player.pause') : t('player.play')"
      @click="emit('toggle')"
    >
      <svg v-if="!playing" viewBox="0 0 24 24" class="size-5" aria-hidden="true"><path fill="currentColor" d="M8 5v14l11-7z" /></svg>
      <svg v-else viewBox="0 0 24 24" class="size-5" aria-hidden="true"><path fill="currentColor" d="M7 5h4v14H7zm6 0h4v14h-4z" /></svg>
    </button>
    <span class="text-sm tabular-nums text-muted">{{ clock(position) }} / {{ clock(duration) }}</span>
    <div role="radiogroup" :aria-label="t('player.listen')" class="ml-auto flex gap-1 rounded-full border border-line p-0.5 text-sm">
      <button
        type="button"
        role="radio"
        :aria-checked="source === 'midi'"
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
