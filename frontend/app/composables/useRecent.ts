/**
 * Recordings sent from this browser, newest first, so the home page can list them.
 * Only ids and file names; the server decides whether a job still exists.
 */
export interface RecentJob {
  id: string
  filename: string
  /** ms since epoch */
  addedAt: number
}

const KEY = 'piano-to-midi:recent'
const MAX = 8

function isRecent(v: unknown): v is RecentJob {
  const r = v as RecentJob
  return typeof r?.id === 'string' && typeof r.filename === 'string' && typeof r.addedAt === 'number'
}

function read(): RecentJob[] {
  try {
    const list: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(list) ? list.filter(isRecent) : []
  }
  catch {
    return []
  }
}

function write(list: RecentJob[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)))
  }
  catch { /* storage blocked or full: the list is a convenience */ }
}

export function useRecent() {
  return {
    list: read,
    add(id: string, filename: string) {
      write([{ id, filename, addedAt: Date.now() }, ...read().filter(r => r.id !== id)])
    },
    remove(id: string) {
      write(read().filter(r => r.id !== id))
    },
  }
}
