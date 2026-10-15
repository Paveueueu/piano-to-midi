<script setup lang="ts">
import type { Arrangement } from '~/types/api'

// The canvas only covers the visible area and redraws on scroll: a long piece at a
// useful zoom would exceed the browser's canvas size limit.
const props = defineProps<{ arrangement: Arrangement, position: number }>()
const emit = defineEmits<{ seek: [seconds: number] }>()

const { t, locale } = useI18n()

const KEYBOARD = 44 // px
const AXIS = 20
const PEDAL_LANE = 16
const ROLL_HEIGHT = 300
const OVERVIEW = 28
const IVORY = '#f4f1e8'
const EBONY = '#1c1c21'
const KEY_EDGE = '#c9c4b7'
const KEY_LABEL = '#55555e'

const scroller = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const overview = ref<HTMLCanvasElement | null>(null)
const viewWidth = ref(600)
const scrollLeft = ref(0)
const zoom = ref<number | null>(null) // px per second; null = fit the whole piece
const dragging = ref<number | null>(null) // playhead time while it's being dragged

const duration = computed(() => Math.max(props.arrangement.seconds, 1))
const rollWidth = computed(() => Math.max(1, viewWidth.value - KEYBOARD))
const fitZoom = computed(() => Math.max(4, rollWidth.value / duration.value))
const pxPerSecond = computed(() => zoom.value ?? fitZoom.value)
const contentWidth = computed(() => duration.value * pxPerSecond.value)
const zoomedIn = computed(() => contentWidth.value > rollWidth.value + 1)
const shownPosition = computed(() => dragging.value ?? props.position)

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

function colors() {
  return {
    surface: css('--surface'), surface2: css('--surface-2'), line: css('--line'), lineStrong: css('--line-strong'),
    muted: css('--muted'), accent: css('--accent'), left: css('--hand-left'), ink: css('--ink'),
  }
}

function setup(c: HTMLCanvasElement, width: number, h: number) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  c.width = Math.round(width * dpr)
  c.height = Math.round(h * dpr)
  const g = c.getContext('2d')
  g?.setTransform(dpr, 0, 0, dpr, 0, 0)
  return g
}

function draw() {
  const c = canvas.value
  if (!c) return
  const width = viewWidth.value
  const g = setup(c, width, height)
  if (!g) return

  const col = colors()
  const { low, high } = range.value
  const rowH = rowHeight.value
  const px = pxPerSecond.value
  const x0 = scrollLeft.value // content px at the left edge of the roll area
  const tFrom = x0 / px
  const tTo = (x0 + width - KEYBOARD) / px
  const xOf = (s: number) => KEYBOARD + s * px - x0
  const yOf = (pitch: number) => (high - pitch) * rowH

  g.fillStyle = col.surface
  g.fillRect(0, 0, width, height)

  for (let p = low; p <= high; p++) {
    if (isBlackKey(p)) {
      g.fillStyle = col.surface2
      g.fillRect(KEYBOARD, yOf(p), width - KEYBOARD, rowH)
    }
    if (p % 12 === 0) {
      g.fillStyle = col.line
      g.fillRect(KEYBOARD, yOf(p) + rowH - 1, width - KEYBOARD, 1)
    }
  }

  // Beat lines when the MIDI follows the piece's tempo, otherwise one per second.
  const beat = props.arrangement.bpm !== 120 || props.arrangement.shift ? 60 / props.arrangement.bpm : 1
  const minGap = 14 / px
  const step = beat * Math.max(1, 2 ** Math.ceil(Math.log2(minGap / beat)))
  g.fillStyle = col.line
  for (let s = Math.floor(tFrom / step) * step; s <= tTo; s += step) {
    if (s >= 0) g.fillRect(Math.round(xOf(s)), 0, 1, ROLL_HEIGHT)
  }

  for (const n of props.arrangement.notes) {
    if (n.end < tFrom || n.start > tTo || n.pitch < low || n.pitch > high) continue
    g.globalAlpha = 0.35 + 0.65 * (n.velocity / 127)
    g.fillStyle = n.hand === 'left' ? col.left : col.accent
    g.fillRect(xOf(n.start), yOf(n.pitch) + 0.5, Math.max(2, (n.end - n.start) * px - 1), Math.max(1, rowH - 1))
  }
  g.globalAlpha = 1

  // Pedal lane: sustain full height, soft pedal as a thin line.
  const laneY = ROLL_HEIGHT
  g.fillStyle = col.surface2
  g.fillRect(KEYBOARD, laneY, width - KEYBOARD, PEDAL_LANE)
  for (const p of props.arrangement.pedals) {
    if (p.end < tFrom || p.start > tTo) continue
    g.fillStyle = col.muted
    g.globalAlpha = p.kind === 'sustain' ? 0.55 : 0.9
    const y = p.kind === 'sustain' ? laneY + 3 : laneY + PEDAL_LANE - 3
    g.fillRect(xOf(p.start), y, Math.max(1, (p.end - p.start) * px), p.kind === 'sustain' ? PEDAL_LANE - 7 : 2)
  }
  g.globalAlpha = 1

  g.fillStyle = col.muted
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
  g.fillStyle = col.surface
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
  g.fillStyle = col.lineStrong
  g.fillRect(KEYBOARD - 1, 0, 1, ROLL_HEIGHT)
  g.fillStyle = col.muted
  g.fillText(t('roll.pedal'), 4, laneY + PEDAL_LANE / 2)
}

function drawOverview() {
  const c = overview.value
  if (!c) return
  const width = rollWidth.value
  const g = setup(c, width, OVERVIEW)
  if (!g) return
  const col = colors()
  const { low, high } = range.value
  const sx = width / duration.value
  const sy = (OVERVIEW - 6) / (high - low + 1)

  g.fillStyle = col.surface2
  g.fillRect(0, 0, width, OVERVIEW)
  for (const n of props.arrangement.notes) {
    g.globalAlpha = 0.6
    g.fillStyle = n.hand === 'left' ? col.left : col.accent
    g.fillRect(n.start * sx, 3 + (high - n.pitch) * sy, Math.max(1, (n.end - n.start) * sx), Math.max(1, sy))
  }
  g.globalAlpha = 1

  const from = scrollLeft.value / pxPerSecond.value
  const span = rollWidth.value / pxPerSecond.value
  g.strokeStyle = col.ink
  g.lineWidth = 1.5
  g.strokeRect(from * sx + 0.75, 0.75, Math.max(6, span * sx) - 1.5, OVERVIEW - 1.5)
  g.fillStyle = col.ink
  g.fillRect(Math.round(shownPosition.value * sx), 0, 1, OVERVIEW)
}

// At most one draw per frame. Keep a pending one rather than replace it, or playback starves it.
let frame = 0
function redraw() {
  if (frame) return
  frame = requestAnimationFrame(() => {
    frame = 0
    draw()
    if (zoomedIn.value) drawOverview()
  })
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
  stopEdgeScroll()
})

watch(() => [props.arrangement, pxPerSecond.value, scrollLeft.value, viewWidth.value, locale.value], redraw)
watch(shownPosition, () => {
  if (zoomedIn.value) redraw()
})
watch(zoomedIn, () => nextTick(() => {
  scrollTo(aroundPlayhead(scrollLeft.value)) // back to fit: no offset left over
  redraw()
}))

function onScroll() {
  scrollLeft.value = scroller.value?.scrollLeft ?? 0
}

function scrollTo(x: number) {
  const el = scroller.value
  if (!el) return
  el.scrollLeft = Math.max(0, Math.min(contentWidth.value - rollWidth.value, x))
  scrollLeft.value = el.scrollLeft
}

// Follow the playhead while playing; while the overview frame is held, move the frame instead.
watch(() => props.position, (s) => {
  if (dragging.value !== null) return
  if (overviewHeld) {
    scrollTo(aroundPlayhead(overviewWanted))
    return
  }
  const x = s * pxPerSecond.value
  if (x < scrollLeft.value || x > scrollLeft.value + rollWidth.value - 40) scrollTo(x - rollWidth.value * 0.2)
})

const playheadX = computed(() => KEYBOARD + shownPosition.value * pxPerSecond.value - scrollLeft.value)

// Dragging the playhead past an edge scrolls the view, faster the further out.
let pointerX = 0
let edgeTimer: ReturnType<typeof setInterval> | null = null
let edgeTime = 0
function timeAt(clientX: number): number {
  const rect = scroller.value!.getBoundingClientRect()
  const x = clientX - rect.left - KEYBOARD + scrollLeft.value
  return Math.max(0, Math.min(duration.value, x / pxPerSecond.value))
}
function stopEdgeScroll() {
  if (edgeTimer) clearInterval(edgeTimer)
  edgeTimer = null
}
function edgeScroll() {
  const el = scroller.value
  if (dragging.value === null || !el) return stopEdgeScroll()
  const rect = el.getBoundingClientRect()
  const past = pointerX < rect.left + KEYBOARD ? pointerX - rect.left - KEYBOARD : pointerX > rect.right ? pointerX - rect.right : 0
  if (!past) return stopEdgeScroll()
  const now = performance.now()
  const elapsed = Math.min(0.1, (now - edgeTime) / 1000)
  edgeTime = now
  scrollTo(scrollLeft.value + Math.sign(past) * Math.min(3000, 250 + Math.abs(past) * 15) * elapsed)
  dragging.value = timeAt(pointerX)
}
function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  pointerX = e.clientX
  dragging.value = timeAt(pointerX)
}
function onPointerMove(e: PointerEvent) {
  if (dragging.value === null) return
  pointerX = e.clientX
  dragging.value = timeAt(pointerX)
  if (!edgeTimer) {
    edgeTime = performance.now()
    edgeTimer = setInterval(edgeScroll, 16)
  }
}
function onPointerUp() {
  if (dragging.value === null) return
  stopEdgeScroll()
  const seconds = timeAt(pointerX)
  dragging.value = null
  emit('seek', seconds)
}

/** Scroll position that keeps the playhead on screen, clear of the follow zone. */
function aroundPlayhead(x: number, playhead = shownPosition.value): number {
  const at = playhead * pxPerSecond.value
  return Math.min(at - 4, Math.max(at - rollWidth.value + 48, x))
}

// Pressing outside the overview frame moves the playhead there and centres the frame.
let grab = 0 // seconds between the pointer and the frame's left edge
let overviewHeld = false
let overviewWanted = 0 // content px the pointer asks for; the playhead may hold it back
function overviewTime(e: PointerEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  return Math.max(0, Math.min(duration.value, ((e.clientX - rect.left) / rect.width) * duration.value))
}
function onOverviewDown(e: PointerEvent) {
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  overviewHeld = true
  const at = overviewTime(e)
  const from = scrollLeft.value / pxPerSecond.value
  const span = rollWidth.value / pxPerSecond.value
  if (at >= from && at <= from + span) {
    grab = at - from
    overviewWanted = scrollLeft.value
    return
  }
  grab = span / 2
  overviewWanted = (at - grab) * pxPerSecond.value
  emit('seek', at)
  scrollTo(aroundPlayhead(overviewWanted, at))
}
function onOverviewMove(e: PointerEvent) {
  if (!overviewHeld) return
  overviewWanted = (overviewTime(e) - grab) * pxPerSecond.value
  scrollTo(aroundPlayhead(overviewWanted))
}
function onOverviewUp() {
  overviewHeld = false
}

function zoomBy(factor: number) {
  const el = scroller.value
  const centre = el ? (el.scrollLeft + rollWidth.value / 2) / pxPerSecond.value : 0
  const next = Math.min(400, Math.max(fitZoom.value, pxPerSecond.value * factor))
  zoom.value = next <= fitZoom.value ? null : next
  nextTick(() => scrollTo(aroundPlayhead(centre * pxPerSecond.value - rollWidth.value / 2)))
}
</script>

<template>
  <div class="grid gap-2">
    <div class="flex items-center justify-end text-xs">
      <div class="flex gap-1">
        <button type="button" class="size-7 cursor-pointer rounded-full border border-line text-sm hover:bg-surface-2" :aria-label="t('roll.zoomOut')" :title="t('roll.zoomOut')" @click="zoomBy(1 / 1.6)">
          −
        </button>
        <button type="button" class="size-7 cursor-pointer rounded-full border border-line text-sm hover:bg-surface-2" :aria-label="t('roll.zoomIn')" :title="t('roll.zoomIn')" @click="zoomBy(1.6)">
          +
        </button>
        <button v-if="zoom !== null" type="button" class="h-7 cursor-pointer whitespace-nowrap rounded-full border border-line px-3 hover:bg-surface-2" @click="zoom = null">
          {{ t('roll.fit') }}
        </button>
      </div>
    </div>
    <div class="relative overflow-hidden rounded-xl border border-line bg-surface" :style="{ height: `${height}px` }">
      <canvas
        ref="canvas"
        class="pointer-events-none absolute inset-0"
        :style="{ width: `${viewWidth}px`, height: `${height}px` }"
        role="img"
        :aria-label="t('roll.label', { notes: arrangement.notes.length, time: clock(arrangement.seconds) })"
      />
      <div
        class="pointer-events-none absolute top-0"
        :style="{ height: `${height - AXIS}px`, transform: `translateX(${playheadX - 1}px)` }"
        :hidden="playheadX < KEYBOARD - 1 || playheadX > viewWidth"
      >
        <div class="h-full w-0.5 bg-ink" />
        <div class="absolute -left-[5px] top-0 size-3 rounded-full bg-ink" />
      </div>
      <div
        ref="scroller"
        class="no-scrollbar absolute inset-0 cursor-pointer touch-pan-y overflow-x-auto overflow-y-hidden"
        @scroll.passive="onScroll"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      >
        <div :style="{ width: `${contentWidth + KEYBOARD}px`, height: '1px' }" />
      </div>
    </div>
    <canvas
      v-if="zoomedIn"
      ref="overview"
      class="cursor-grab touch-none rounded-md active:cursor-grabbing"
      :style="{ width: `${rollWidth}px`, height: `${OVERVIEW}px`, marginLeft: `${KEYBOARD}px` }"
      :aria-label="t('roll.overview')"
      role="scrollbar"
      aria-orientation="horizontal"
      :aria-valuenow="Math.round((scrollLeft / Math.max(1, contentWidth - rollWidth)) * 100)"
      @pointerdown="onOverviewDown"
      @pointermove="onOverviewMove"
      @pointerup="onOverviewUp"
      @pointercancel="onOverviewUp"
    />
  </div>
</template>
