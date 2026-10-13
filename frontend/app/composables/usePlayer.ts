import type { Arrangement, Note } from '~/types/api'

export type Source = 'midi' | 'original'

const LOOKAHEAD = 0.3 // seconds of notes scheduled ahead
const TICK_MS = 60

/** Plays the arrangement as MIDI (a small synth) or as the original recording, at the same position. */
export function usePlayer(arrangement: Ref<Arrangement | null>, originalUrl: string | null) {
  const source = ref<Source>('midi')
  const playing = ref(false)
  const position = ref(0)

  let ctx: AudioContext | null = null
  let master: GainNode | null = null
  let audio: HTMLAudioElement | null = null
  let startedAt = 0 // ctx time when playback (re)started
  let startedFrom = 0 // arrangement time at that moment
  let scheduledUntil = 0
  let timer: ReturnType<typeof setInterval> | null = null
  let frame = 0
  let voices: { stop: (at: number) => void }[] = []

  // While playing, the sustain pedal keeps released notes sounding until it lifts.
  const notes = computed<Note[]>(() => {
    const a = arrangement.value
    if (!a) return []
    const sustain = a.pedals.filter(p => p.kind === 'sustain')
    return a.notes
      .map((n) => {
        const pedal = sustain.find(p => p.start <= n.end && n.end < p.end)
        return pedal ? { ...n, end: pedal.end } : n
      })
      .sort((x, y) => x.start - y.start)
  })

  function ensureContext() {
    if (ctx) return
    ctx = new AudioContext()
    const compressor = ctx.createDynamicsCompressor()
    master = ctx.createGain()
    master.gain.value = 0.9
    master.connect(compressor).connect(ctx.destination)
  }

  function voice(n: Note, when: number, until: number) {
    if (!ctx || !master) return
    const f0 = 440 * 2 ** ((n.pitch - 69) / 12)
    const peak = 0.1 * (n.velocity / 127) ** 1.5
    const ring = 0.4 + (2.5 * (108 - n.pitch)) / 88 // low strings ring longer
    const env = ctx.createGain()
    env.gain.setValueAtTime(0, when)
    env.gain.linearRampToValueAtTime(peak, when + 0.006)
    env.gain.setTargetAtTime(0, when + 0.006, ring)
    env.connect(master)
    const oscillators = [1, 2, 3, 4].map((k, i) => {
      const osc = ctx!.createOscillator()
      const g = ctx!.createGain()
      osc.frequency.value = f0 * k * (1 + 0.0004 * k * k) // slightly stretched, as piano strings are
      g.gain.value = [1, 0.45, 0.2, 0.1][i]!
      osc.connect(g).connect(env)
      osc.start(when)
      return osc
    })
    const release = (at: number) => {
      env.gain.cancelScheduledValues(at)
      env.gain.setTargetAtTime(0, at, 0.06)
      oscillators.forEach(o => o.stop(at + 0.5))
    }
    release(Math.max(until, when + 0.05))
    voices.push({
      stop: (at: number) => {
        // Drop notes that haven't started: releasing them at their start would play them at full gain.
        if (at < when) {
          env.disconnect()
          oscillators.forEach(o => o.stop(at))
          return
        }
        release(at)
      },
    })
  }

  function schedule() {
    if (!ctx) return
    const now = startedFrom + (ctx.currentTime - startedAt)
    const horizon = now + LOOKAHEAD
    for (const n of notes.value) {
      if (n.start >= horizon) break
      if (n.start >= scheduledUntil) voice(n, startedAt + (n.start - startedFrom), startedAt + (n.end - startedFrom))
    }
    scheduledUntil = horizon
  }

  function tick() {
    const end = arrangement.value?.seconds ?? 0
    if (source.value === 'original' && audio) {
      position.value = audio.currentTime + (arrangement.value?.shift ?? 0)
    }
    else if (ctx) {
      position.value = startedFrom + (ctx.currentTime - startedAt)
    }
    if (position.value >= end) {
      pause()
      position.value = end
      return
    }
    frame = requestAnimationFrame(tick)
  }

  async function play() {
    if (playing.value || !arrangement.value) return
    if (position.value >= arrangement.value.seconds - 0.05) position.value = 0
    if (source.value === 'original' && originalUrl) {
      audio ??= new Audio(originalUrl)
      audio.currentTime = Math.max(0, position.value - arrangement.value.shift)
      await audio.play()
    }
    else {
      ensureContext()
      await ctx!.resume()
      startedAt = ctx!.currentTime + 0.05
      startedFrom = position.value
      scheduledUntil = position.value
      schedule()
      timer = setInterval(schedule, TICK_MS)
    }
    playing.value = true
    frame = requestAnimationFrame(tick)
  }

  function pause() {
    playing.value = false
    cancelAnimationFrame(frame)
    if (timer) clearInterval(timer)
    timer = null
    audio?.pause()
    if (ctx) voices.forEach(v => v.stop(ctx!.currentTime))
    voices = []
  }

  function seek(seconds: number) {
    const wasPlaying = playing.value
    pause()
    position.value = Math.max(0, seconds)
    if (wasPlaying) play()
  }

  function setSource(next: Source) {
    if (next === 'original' && !originalUrl) return
    const wasPlaying = playing.value
    pause()
    source.value = next
    if (wasPlaying) play()
  }

  onBeforeUnmount(() => {
    pause()
    ctx?.close()
  })

  return { source, playing, position, play, pause, seek, setSource, hasOriginal: originalUrl !== null }
}
