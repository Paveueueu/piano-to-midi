<script setup lang="ts">
import type { Arrangement, Options } from '~/types/api'

const props = defineProps<{
  base: Options
  arrangement: Arrangement | null
}>()
const options = defineModel<Options>('options', { required: true })

const { t, locale } = useI18n()

function set<K extends keyof Options>(key: K, value: Options[K]) {
  options.value = { ...options.value, [key]: value }
}

const changed = computed(() =>
  (Object.keys(props.base) as (keyof Options)[]).some(k => options.value[k] !== props.base[k]),
)
function reset() {
  options.value = { ...props.base }
}

const keys = computed(() =>
  Array.from({ length: 88 }, (_, i) => 21 + i).map(p => ({ value: p, label: keyName(p, locale.value) })),
)
const splitKeys = computed(() => keys.value.filter(k => k.value >= 43 && k.value <= 76))

const bpmShown = computed(() => options.value.bpm ?? props.arrangement?.detected_bpm ?? null)
function scaleBpm(factor: number) {
  if (bpmShown.value) set('bpm', Math.min(260, Math.max(30, Math.round(bpmShown.value * factor * 10) / 10)))
}

const onGrid = computed(() => options.value.tempo === 'detected' || options.value.grid !== 'off')
</script>

<template>
  <div class="grid gap-4">
    <details class="rounded-xl border border-line">
      <summary class="cursor-pointer px-4 py-3 text-sm font-medium">
        {{ t('settings.advanced') }}
      </summary>

      <div class="grid items-start gap-5 border-t border-line p-4 sm:grid-cols-2">
        <label class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.sensitivity') }}</span>
          <input
            type="range" min="-2" max="3" step="0.5" class="accent-[var(--accent)]"
            :value="-options.min_confidence + 1"
            @input="set('min_confidence', -Number(($event.target as HTMLInputElement).value) + 1)"
          >
          <span class="flex justify-between text-xs text-muted"><span>{{ t('settings.fewer') }}</span><span>{{ t('settings.more') }}</span></span>
        </label>

        <label class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.shortest', { ms: options.min_note_ms }) }}</span>
          <input
            type="range" min="0" max="200" step="10" class="accent-[var(--accent)]"
            :value="options.min_note_ms"
            @input="set('min_note_ms', Number(($event.target as HTMLInputElement).value))"
          >
        </label>

        <div class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.range') }}</span>
          <div class="flex items-center gap-2 text-sm">
            <select class="rounded-lg border border-line bg-surface px-2 py-1" :aria-label="t('settings.lowest')" :value="options.lowest_key" @change="set('lowest_key', Number(($event.target as HTMLSelectElement).value))">
              <option v-for="k in keys" :key="k.value" :value="k.value">
                {{ k.label }}
              </option>
            </select>
            <span class="text-muted">–</span>
            <select class="rounded-lg border border-line bg-surface px-2 py-1" :aria-label="t('settings.highest')" :value="options.highest_key" @change="set('highest_key', Number(($event.target as HTMLSelectElement).value))">
              <option v-for="k in keys" :key="k.value" :value="k.value">
                {{ k.label }}
              </option>
            </select>
          </div>
        </div>

        <div class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.dynamics') }}</span>
          <ChoiceGroup
            :model-value="options.velocity"
            :label="t('settings.dynamics')"
            :choices="[
              { value: 'as_played', label: t('settings.velocity.as_played') },
              { value: 'compressed', label: t('settings.velocity.compressed') },
              { value: 'fixed', label: t('settings.velocity.fixed') },
            ]"
            @update:model-value="set('velocity', $event)"
          />
          <input
            v-if="options.velocity === 'fixed'"
            type="range" min="1" max="127" class="accent-[var(--accent)]" :aria-label="t('settings.velocity.fixed')"
            :value="options.fixed_velocity"
            @input="set('fixed_velocity', Number(($event.target as HTMLInputElement).value))"
          >
        </div>

        <div class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.pedal') }}</span>
          <ChoiceGroup
            :model-value="options.pedal"
            :label="t('settings.pedal')"
            :choices="[
              { value: 'controller', label: t('settings.pedalMode.controller') },
              { value: 'held_notes', label: t('settings.pedalMode.held_notes') },
              { value: 'none', label: t('settings.pedalMode.none') },
            ]"
            @update:model-value="set('pedal', $event)"
          />
        </div>

        <div class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.timing') }}</span>
          <ChoiceGroup
            :model-value="options.tempo"
            :label="t('settings.timing')"
            :choices="[
              { value: 'real_time', label: t('settings.tempo.real_time') },
              { value: 'detected', label: t('settings.tempo.detected') },
            ]"
            @update:model-value="set('tempo', $event)"
          />
          <div v-if="onGrid" class="flex items-center gap-2 text-sm">
            <input
              type="number" min="30" max="260" step="0.1" class="w-20 rounded-lg border border-line bg-surface px-2 py-1 tabular-nums"
              :aria-label="t('settings.bpm')" :value="bpmShown ?? ''"
              @change="set('bpm', Number(($event.target as HTMLInputElement).value) || null)"
            >
            <span class="text-muted">BPM</span>
            <button type="button" class="cursor-pointer rounded-full border border-line px-2 py-0.5 hover:bg-surface-2" @click="scaleBpm(0.5)">
              ½×
            </button>
            <button type="button" class="cursor-pointer rounded-full border border-line px-2 py-0.5 hover:bg-surface-2" @click="scaleBpm(2)">
              2×
            </button>
          </div>
        </div>

        <div class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.grid') }}</span>
          <ChoiceGroup
            :model-value="options.grid"
            :label="t('settings.grid')"
            :choices="[
              { value: 'off', label: t('settings.gridOff') },
              { value: '1/8', label: '1/8' },
              { value: '1/16', label: '1/16' },
              { value: '1/32', label: '1/32' },
            ]"
            @update:model-value="set('grid', $event)"
          />
          <label v-if="options.grid !== 'off'" class="grid gap-1 text-sm">
            <span class="text-muted">{{ t('settings.strength', { n: options.quantize_strength }) }}</span>
            <input
              type="range" min="0" max="100" step="5" class="accent-[var(--accent)]"
              :value="options.quantize_strength"
              @input="set('quantize_strength', Number(($event.target as HTMLInputElement).value))"
            >
          </label>
        </div>

        <div class="grid gap-1.5">
          <span class="text-sm font-medium">{{ t('settings.hands') }}</span>
          <ChoiceGroup
            :model-value="options.hands"
            :label="t('settings.hands')"
            :choices="[
              { value: 'one_track', label: t('settings.handsMode.one_track') },
              { value: 'split', label: t('settings.handsMode.split') },
            ]"
            @update:model-value="set('hands', $event)"
          />
          <select
            v-if="options.hands === 'split'"
            class="w-fit rounded-lg border border-line bg-surface px-2 py-1 text-sm" :aria-label="t('settings.splitAt')"
            :value="options.split_key ?? ''"
            @change="set('split_key', ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
          >
            <option value="">
              {{ t('settings.splitAuto', { key: arrangement?.split_key ? keyName(arrangement.split_key, locale) : '…' }) }}
            </option>
            <option v-for="k in splitKeys" :key="k.value" :value="k.value">
              {{ t('settings.splitFrom', { key: k.label }) }}
            </option>
          </select>
        </div>

        <button
          v-if="changed"
          type="button"
          class="w-fit cursor-pointer rounded-full border border-line px-3 py-1 text-sm hover:bg-surface-2 sm:col-span-2"
          @click="reset"
        >
          {{ t('settings.reset') }}
        </button>
      </div>
    </details>
  </div>
</template>
