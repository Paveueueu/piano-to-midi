<script setup lang="ts">
import type { Arrangement } from '~/types/api'

/*
 * The canvas is only as wide as what's on screen and redraws the visible stretch while
 * scrolling: a ten-minute piece at a useful zoom would be tens of thousands of pixels wide,
 * more than browsers allow for one canvas.
 */
const props = defineProps<{ arrangement: Arrangement, position: number }>()
const emit = defineEmits<{ seek: [seconds: number] }>()

const { t, locale } = useI18n()

const KEYBOARD = 44 // px
const AXIS = 20
const PEDAL_LANE = 16
const SCROLLBAR = 14 // room under the axis, so the scrollbar doesn't cover the time labels
const ROLL_HEIGHT = 300
const IVORY = '#f4f1e8'
const EBONY = '#1c1c21'
const KEY_EDGE = '#c9c4b7'
const KEY_LABEL = '#55555e'

const scroller = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const viewWidth = ref(600)
const scrollLeft = ref(0)
const zoom = ref<number | null>(null) // px per second; null = fit the whole piece

const duration = computed(() => Math.max(props.arrangement.seconds, 1))
const fitZoom = computed(() => Math.max(4, (viewWidth.value - KEYBOARD) / duration.value))
const pxPerSecond = computed(() => zoom.value ?? fitZoom.value)
const contentWidth = computed(() => duration.value * pxPerSecond.value)

const range = computed(() => {
  const pitches = props.arrangement.notes.map(n => n.pitch)
  if (!pitches.length) return { low: 48, high: 84 }
  return { low: Math.max(21, Math.min(...pitches) - 2), high: Math.min(108, Math.max(...pitches) + 2) }
})
const rowHeight = computed(() => ROLL_HEIGHT / (range.value.high - range.value.low + 1))
const height = ROLL_HEIGHT + PEDAL_LANE + AXIS

function css(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function draw() {
  const c = canvas.value
  if (!c) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const width = viewWidth.value
  c.width = Math.round(width * dpr)
  c.height = Math.round(height * dpr)
  const g = c.getContext('2d')
  if (!g) return
  g.setTransform(dpr, 0, 0, dpr, 0, 0)

  const colors = {
    surface: css('--surface'), surface2: css('--surface-2'), line: css('--line'), lineStrong: css('--line-strong'),
    muted: css('--muted'), accent: css('--accent'), left: css('--hand-left'), ink: css('--ink'),
  }
  const { low, high } = range.value
  const rowH = rowHeight.value
  const px = pxPerSecond.value
  const x0 = scrollLeft.value // content px at the left edge of the roll area
  const tFrom = x0 / px
  const tTo = (x0 + width - KEYBOARD) / px
  const xOf = (s: number) => KEYBOARD + s * px - x0
  const yOf = (pitch: number) => (high - pitch) * rowH

  g.fillStyle = colors.surface
  g.fillRect(0, 0, width, height)

  for (let p = low; p <= high; p++) {
    if (isBlackKey(p)) {
      g.fillStyle = colors.surface2
      g.fillRect(KEYBOARD, yOf(p), width - KEYBOARD, rowH)
    }
    if (p % 12 === 0) {
      g.fillStyle = colors.line
      g.fillRect(KEYBOARD, yOf(p) + rowH - 1, width - KEYBOARD, 1)
    }
  }

  // Beat lines when the MIDI follows the piece's tempo, otherwise one per second.
  const beat = props.arrangement.bpm !== 120 || props.arrangement.shift ? 60 / props.arrangement.bpm : 1
  const minGap = 14 / px
  const step = beat * Math.max(1, 2 ** Math.ceil(Math.log2(minGap / beat)))
  g.fillStyle = colors.line
  for (let s = Math.floor(tFrom / step) * step; s <= tTo; s += step) {
    if (s >= 0) g.fillRect(Math.round(xOf(s)), 0, 1, ROLL_HEIGHT)
  }

  // Notes.
  for (const n of props.arrangement.notes) {
    if (n.end < tFrom || n.start > tTo || n.pitch < low || n.pitch > high) continue
    g.globalAlpha = 0.35 + 0.65 * (n.velocity / 127)
    g.fillStyle = n.hand === 'left' ? colors.left : colors.accent
    const x = xOf(n.start)
    g.fillRect(x, yOf(n.pitch) + 0.5, Math.max(2, (n.end - n.start) * px - 1), Math.max(1, rowH - 1))
  }
  g.globalAlpha = 1

  // Pedal lane: sustain full height, soft pedal as a thin line.
  const laneY = ROLL_HEIGHT
  g.fillStyle = colors.surface2
  g.fillRect(KEYBOARD, laneY, width - KEYBOARD, PEDAL_LANE)
  for (const p of props.arrangement.pedals) {
    if (p.end < tFrom || p.start > tTo) continue
    g.fillStyle = colors.muted
    g.globalAlpha = p.kind === 'sustain' ? 0.55 : 0.9
    const y = p.kind === 'sustain' ? laneY + 3 : laneY + PEDAL_LANE - 3
    g.fillRect(xOf(p.start), y, Math.max(1, (p.end - p.start) * px), p.kind === 'sustain' ? PEDAL_LANE - 7 : 2)
  }
  g.globalAlpha = 1

  g.fillStyle = colors.muted
  g.font = '11px Geist, system-ui, sans-serif'
  g.textBaseline = 'middle'
  const labelEvery = [1, 2, 5, 10, 15, 30, 60, 120].find(s => s * px >= 60) ?? 300
  for (let s = Math.floor(tFrom / labelEvery) * labelEvery; s <= tTo; s += labelEvery) {
    if (s < 0) continue
    const x = xOf(s)
    g.fillRect(Math.round(x), ROLL_HEIGHT + PEDAL_LANE, 1, 4)
    g.fillText(clock(s), x + 3, ROLL_HEIGHT + PEDAL_LANE + AXIS / 2 + 2)
  }

  // Keyboard last, so notes scroll under it.
  g.fillStyle = colors.surface
  g.fillRect(0, 0, KEYBOARD, height)
  g.fillStyle = IVORY
  g.fillRect(0, 0, KEYBOARD, ROLL_HEIGHT)
  for (let p = low; p <= high; p++) {
    if (p % 12 === 0 || p % 12 === 5) {
      g.fillStyle = KEY_EDGE // the gaps between white keys at C and F
      g.fillRect(0, yOf(p) + rowH - 0.5, KEYBOARD, 1)
    }
    if (isBlackKey(p)) {
      g.fillStyle = EBONY
      g.fillRect(0, yOf(p), KEYBOARD * 0.6, rowH)
    }
    if (p % 12 === 0 && rowH * 12 >= 40) {
      g.fillStyle = KEY_LABEL
      g.fillText(keyName(p, locale.value), KEYBOARD * 0.62, yOf(p) + rowH / 2)
    }
  }
  g.fillStyle = colors.lineStrong
  g.fillRect(KEYBOARD - 1, 0, 1, ROLL_HEIGHT)
  g.fillStyle = colors.muted
  g.fillText(t('roll.pedal'), 4, laneY + PEDAL_LANE / 2)
}

let frame = 0
function redraw() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(draw)
}

let observer: ResizeObserver | null = null
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    if (entry) viewWidth.value = entry.contentRect.width
    redraw()
  })
  if (scroller.value) observer.observe(scroller.value)
  const scheme = window.matchMedia('(prefers-color-scheme: dark)')
  scheme.addEventListener('change', redraw)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  cancelAnimationFrame(frame)
})

watch(() => [props.arrangement, pxPerSecond.value, scrollLeft.value, viewWidth.value, locale.value], redraw)

function onScroll() {
  scrollLeft.value = scroller.value?.scrollLeft ?? 0
}

// Keep the playhead in view while playing.
watch(() => props.position, (s) => {
  const el = scroller.value
  if (!el) return
  const x = s * pxPerSecond.value
  if (x < el.scrollLeft || x > el.scrollLeft + el.clientWidth - KEYBOARD - 40) {
    el.scrollLeft = Math.max(0, x - (el.clientWidth - KEYBOARD) * 0.2)
  }
})

const playheadX = computed(() => KEYBOARD + props.position * pxPerSecond.value - scrollLeft.value)

function onClick(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const x = e.clientX - rect.left
  if (x < KEYBOARD) return
  emit('seek', Math.max(0, Math.min(duration.value, (x - KEYBOARD + scrollLeft.value) / pxPerSecond.value)))
}

function zoomBy(factor: number) {
  const el = scroller.value
  const centre = el ? (el.scrollLeft + (el.clientWidth - KEYBOARD) / 2) / pxPerSecond.value : 0
  zoom.value = Math.min(400, Math.max(fitZoom.value, pxPerSecond.value * factor))
  nextTick(() => {
    if (el) el.scrollLeft = Math.max(0, centre * pxPerSecond.value - (el.clientWidth - KEYBOARD) / 2)
  })
}
</script>

<template>
  <div class="grid gap-2">
    <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
      <p class="text-muted">
        {{ arrangement.split_key !== null ? t('roll.legendHands') : t('roll.legend') }}
      </p>
      <div class="flex gap-1">
        <button type="button" class="size-8 cursor-pointer rounded-full border border-line hover:bg-surface-2" :aria-label="t('roll.zoomOut')" @click="zoomBy(1 / 1.6)">
          −
        </button>
        <button type="button" class="size-8 cursor-pointer rounded-full border border-line hover:bg-surface-2" :aria-label="t('roll.zoomIn')" @click="zoomBy(1.6)">
          +
        </button>
        <button type="button" class="h-8 cursor-pointer whitespace-nowrap rounded-full border border-line px-3 hover:bg-surface-2" @click="zoom = null">
          {{ t('roll.fit') }}
        </button>
      </div>
    </div>
    <div class="relative overflow-hidden rounded-xl border border-line bg-surface" :style="{ height: `${height + SCROLLBAR}px` }">
      <canvas
        ref="canvas"
        class="pointer-events-none absolute inset-0"
        :style="{ width: `${viewWidth}px`, height: `${height}px` }"
        role="img"
        :aria-label="t('roll.label', { notes: arrangement.notes.length, time: clock(arrangement.seconds) })"
      />
      <div
        class="pointer-events-none absolute top-0 w-0.5 bg-ink"
        :style="{ height: `${height - AXIS}px`, transform: `translateX(${playheadX}px)` }"
        :hidden="playheadX < KEYBOARD || playheadX > viewWidth"
      />
      <div ref="scroller" class="absolute inset-0 cursor-crosshair overflow-x-auto overflow-y-hidden" @scroll.passive="onScroll" @click="onClick">
        <div :style="{ width: `${contentWidth + KEYBOARD}px`, height: '1px' }" />
      </div>
    </div>
  </div>
</template>
