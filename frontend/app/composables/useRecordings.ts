/** Uploads kept in this tab, to play the original next to the MIDI. Lost on reload. */
const recordings = new Map<string, string>()

export function useRecordings() {
  return {
    keep(jobId: string, file: File) {
      recordings.set(jobId, URL.createObjectURL(file))
    },
    url(jobId: string): string | null {
      return recordings.get(jobId) ?? null
    },
    forget(jobId: string) {
      const url = recordings.get(jobId)
      if (url) URL.revokeObjectURL(url)
      recordings.delete(jobId)
    },
  }
}
