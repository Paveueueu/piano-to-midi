/** Piano key names: "C4", "F♯3". Polish names the B natural "H", as Polish musicians do. */
const NAMES = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B']

export function keyName(pitch: number, locale = 'en'): string {
  const name = NAMES[pitch % 12]!
  const octave = Math.floor(pitch / 12) - 1
  return `${locale === 'pl' && name === 'B' ? 'H' : name}${octave}`
}

export function isBlackKey(pitch: number): boolean {
  return [1, 3, 6, 8, 10].includes(pitch % 12)
}

/** "3:07" */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
