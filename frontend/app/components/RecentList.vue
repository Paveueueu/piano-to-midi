<script setup lang="ts">
import type { Job } from '~/types/api'
import type { RecentJob } from '~/composables/useRecent'
import { ApiError } from '~/composables/useApi'

const { t, locale } = useI18n()
const api = useApi()
const recent = useRecent()

interface Row { entry: RecentJob, job: Job | null }

// Shown only after the first check, so recordings the server has already dropped never flash up.
const rows = ref<Row[] | null>(null)
const now = ref(Date.now())
let timer: ReturnType<typeof setTimeout> | null = null
let ticker: ReturnType<typeof setInterval> | null = null

async function check(list: Row[]) {
  const gone = new Set<string>()
  await Promise.all(list.map(async (row) => {
    try {
      row.job = await api.job(row.entry.id)
    }
    catch (error: unknown) {
      if (error instanceof ApiError && error.reason === 'expired') {
        recent.remove(row.entry.id)
        gone.add(row.entry.id)
      }
    }
  }))
  rows.value = list.filter(r => !gone.has(r.entry.id))
  if (rows.value.some(r => r.job?.status === 'queued' || r.job?.status === 'running')) {
    timer = setTimeout(() => check(rows.value ?? []), 2000)
  }
}

onMounted(() => {
  const entries = recent.list()
  if (entries.length) check(entries.map(entry => ({ entry, job: null })))
  ticker = setInterval(() => { now.value = Date.now() }, 30_000)
})
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
  if (ticker) clearInterval(ticker)
})

function ago(ms: number): string {
  const minutes = Math.floor((now.value - ms) / 60_000)
  if (minutes < 1) return t('recent.justNow')
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  return minutes < 60 ? rtf.format(-minutes, 'minute') : rtf.format(-Math.floor(minutes / 60), 'hour')
}
</script>

<template>
  <section v-if="rows?.length" class="grid gap-3" aria-labelledby="recent-title">
    <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <h2 id="recent-title" class="text-lg font-semibold tracking-tight">
        {{ t('recent.title') }}
      </h2>
      <p class="text-sm text-muted">
        {{ t('recent.note') }}
      </p>
    </div>

    <ul class="divide-y divide-line overflow-hidden rounded-card border border-line bg-surface shadow-card">
      <li v-for="{ entry, job } in rows" :key="entry.id">
        <NuxtLink
          :to="`/jobs/${entry.id}`"
          class="group flex items-center gap-4 px-4 py-3.5 hover:bg-surface-2 focus-visible:outline-offset-[-3px] sm:px-5"
        >
          <div class="grid min-w-0 flex-1 gap-0.5">
            <p class="truncate font-medium" :title="entry.filename">
              {{ entry.filename }}
            </p>
            <p class="flex flex-wrap gap-x-3 text-sm tabular-nums text-muted">
              <template v-if="job?.status === 'done'">
                <span>{{ t('result.notes', { n: job.notes ?? 0 }, job.notes ?? 0) }}</span>
                <span>{{ clock(job.seconds ?? 0) }}</span>
              </template>
              <span v-else-if="job?.status === 'running'" class="flex items-center gap-2 text-ink-2">
                <span class="size-2 animate-pulse rounded-full bg-accent motion-reduce:animate-none" aria-hidden="true" />
                {{ t('recent.running', { n: Math.round(job.progress * 100) }) }}
              </span>
              <span v-else-if="job?.status === 'queued'" class="flex items-center gap-2 text-ink-2">
                <span class="size-2 rounded-full bg-line-strong" aria-hidden="true" />
                {{ t('recent.queued') }}
              </span>
              <span v-else-if="job?.status === 'failed'" class="text-danger">
                {{ t('recent.failed') }}
              </span>
              <span class="sm:hidden">{{ ago(entry.addedAt) }}</span>
            </p>
          </div>
          <span class="hidden flex-none text-sm text-muted sm:block">{{ ago(entry.addedAt) }}</span>
          <svg viewBox="0 0 24 24" class="size-4 flex-none text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-ink" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="m9 6 6 6-6 6" />
          </svg>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
