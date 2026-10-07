import type { Arrangement, AutoSettings, Job, Limits, Options, OptionsInfo } from '~/types/api'

/** Non-2xx answer with the backend's short reason code. */
export class ApiError extends Error {
  constructor(public status: number, public reason: string) {
    super(reason)
  }
}

/** Settings as query parameters; empty values (auto-chosen bpm, split key) are left out. */
export function optionsQuery(options: Options): Record<string, string> {
  const query: Record<string, string> = {}
  for (const [key, value] of Object.entries(options)) {
    if (value !== null && value !== undefined) query[key] = String(value)
  }
  return query
}

export function useApi() {
  const base = useRuntimeConfig().public.apiBase

  async function get<T>(path: string, query?: Record<string, string>): Promise<T> {
    try {
      return await $fetch<T>(path, { baseURL: base, query })
    }
    catch (error: unknown) {
      throw toApiError(error)
    }
  }

  /** XHR, because fetch can't report upload progress. */
  function createJob(file: File, onProgress: (fraction: number) => void): Promise<Job> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${base}/jobs`)
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded / e.total)
      }
      xhr.onload = () => {
        if (xhr.status === 202) {
          resolve(JSON.parse(xhr.responseText) as Job)
          return
        }
        let reason = 'internal'
        try {
          reason = (JSON.parse(xhr.responseText) as { detail?: string }).detail ?? reason
        }
        catch { /* not JSON */ }
        reject(new ApiError(xhr.status, reason))
      }
      xhr.onerror = () => reject(new ApiError(0, 'network'))
      const form = new FormData()
      form.append('file', file)
      xhr.send(form)
    })
  }

  return {
    limits: () => get<Limits>('/limits'),
    optionsInfo: () => get<OptionsInfo>('/options'),
    job: (id: string) => get<Job>(`/jobs/${id}`),
    notes: (id: string, options: Options) => get<Arrangement>(`/jobs/${id}/notes`, optionsQuery(options)),
    auto: (id: string) => get<AutoSettings>(`/jobs/${id}/auto`),
    midiUrl: (id: string, options: Options) =>
      `${base}/jobs/${id}/midi?${new URLSearchParams(optionsQuery(options)).toString()}`,
    deleteJob: async (id: string) => {
      try {
        await $fetch(`/jobs/${id}`, { baseURL: base, method: 'DELETE' })
      }
      catch (error: unknown) {
        throw toApiError(error)
      }
    },
    createJob,
  }
}

function toApiError(error: unknown): ApiError {
  const e = error as { statusCode?: number, data?: { detail?: unknown } }
  const detail = typeof e.data?.detail === 'string' ? e.data.detail : null
  if (!e.statusCode) return new ApiError(0, 'network')
  return new ApiError(e.statusCode, detail ?? (e.statusCode === 404 ? 'expired' : 'internal'))
}
