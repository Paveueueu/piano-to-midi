/* What the API sends (backend/src/pianotomidi/api.py, options.py). */

export type JobStatus = 'queued' | 'running' | 'done' | 'failed'

export interface Job {
  id: string
  filename: string
  status: JobStatus
  progress: number
  /** jobs waiting ahead of this one; null when not waiting */
  position: number | null
  /** why it failed: too_long, not_audio, empty, silent, internal */
  error: string | null
  seconds: number | null
  notes: number | null
  pedals: number | null
  /** Auto settings are ready */
  auto: boolean
}

export interface Options {
  min_confidence: number
  min_note_ms: number
  lowest_key: number
  highest_key: number
  velocity: 'as_played' | 'compressed' | 'fixed'
  fixed_velocity: number
  pedal: 'controller' | 'held_notes' | 'none'
  tempo: 'real_time' | 'detected'
  bpm: number | null
  grid: 'off' | '1/8' | '1/16' | '1/32'
  quantize_strength: number
  hands: 'one_track' | 'split'
  split_key: number | null
}

export type Hand = 'right' | 'left'

export interface Note {
  start: number
  end: number
  pitch: number
  velocity: number
  confidence: number
  hand: Hand | null
}

export interface Pedal {
  start: number
  end: number
  kind: 'sustain' | 'soft'
  value: number
}

export interface Arrangement {
  seconds: number
  /** tempo written into the MIDI file */
  bpm: number
  /** seconds every event was moved so beats land on bar lines */
  shift: number
  detected_bpm: number | null
  split_key: number | null
  notes: Note[]
  pedals: Pedal[]
}

export interface Reason {
  code: string
  values: Record<string, number | string | null>
}

export interface AutoSettings {
  changes: Partial<Options>
  options: Options
  reasons: Reason[]
}

export interface Preset {
  id: string
  changes: Partial<Options>
  options: Options
}

export interface OptionsInfo {
  defaults: Options
  presets: Preset[]
}

export interface Limits {
  max_upload_mb: number
  max_audio_minutes: number
}
