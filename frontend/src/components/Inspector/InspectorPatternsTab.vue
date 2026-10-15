<template>
  <div v-if="store.activeInspectorTab === 'telemetry'" class="space-y-4">
    <header class="flex items-start justify-between gap-2">
      <div class="space-y-1">
        <h2 class="text-[11px] font-semibold text-zinc-200">Scene patterns in manuscript context</h2>
        <p class="text-[9px] leading-relaxed text-zinc-500">These are measurable text features, not reader reactions. Comparisons use other scenes in this manuscript, so a difference is descriptive—not a quality judgment.</p>
      </div>
      <button @click="loadManuscriptAnalytics" :disabled="analyticsLoading" class="shrink-0 rounded border border-zinc-700 px-2 py-1 text-[9px] text-zinc-400 hover:text-zinc-200 disabled:opacity-50">
        {{ analyticsLoading ? 'Updating…' : 'Refresh' }}
      </button>
    </header>

    <div v-if="analyticsLoading" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-[10px] text-zinc-500">
      Comparing this scene with the manuscript…
    </div>
    <div v-else-if="analyticsError" class="rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 text-[10px] text-rose-200">
      {{ analyticsError }}
    </div>
    <template v-else-if="selectedSceneAnalytics">
      <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-2">
        <div class="flex items-baseline justify-between gap-2">
          <span class="text-[10px] uppercase tracking-wider text-amber-400">Estimated silent read</span>
          <span class="font-mono text-sm font-semibold text-zinc-100">{{ readTimeRange }}</span>
        </div>
        <p class="text-[9px] text-zinc-500">
          {{ selectedSceneAnalytics.telemetry.words.toLocaleString() }} words · estimated at 200–250 words/minute · scene {{ analyticsPosition }} of {{ manuscriptAnalytics.scenes.length }}
        </p>
        <p class="text-[9px] text-zinc-500">{{ sceneLengthComparison }}</p>
      </div>

      <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-3">
        <div class="text-[10px] uppercase tracking-wider text-amber-400">How this scene is written</div>
        <div v-for="metric in manuscriptPatternComparisons" :key="metric.label" class="space-y-1">
          <div class="flex items-baseline justify-between gap-2 text-[10px]">
            <span class="text-zinc-300">{{ metric.label }}</span>
            <span class="font-mono text-zinc-100">{{ metric.value }}</span>
          </div>
          <p class="text-[9px] text-zinc-500">{{ metric.context }}</p>
        </div>
      </div>

      <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-2">
        <div class="text-[10px] uppercase tracking-wider text-zinc-400">Nearby scene lengths</div>
        <div v-if="previousSceneAnalytics" class="flex justify-between gap-2 text-[9px]">
          <span class="truncate text-zinc-500">Before · {{ previousSceneAnalytics.title }}</span>
          <span class="shrink-0 font-mono text-zinc-300">{{ previousSceneAnalytics.telemetry.words.toLocaleString() }} words</span>
        </div>
        <div class="flex justify-between gap-2 text-[9px]">
          <span class="truncate text-zinc-300">Selected · {{ selectedSceneAnalytics.title }}</span>
          <span class="shrink-0 font-mono text-zinc-100">{{ selectedSceneAnalytics.telemetry.words.toLocaleString() }} words</span>
        </div>
        <div v-if="nextSceneAnalytics" class="flex justify-between gap-2 text-[9px]">
          <span class="truncate text-zinc-500">After · {{ nextSceneAnalytics.title }}</span>
          <span class="shrink-0 font-mono text-zinc-300">{{ nextSceneAnalytics.telemetry.words.toLocaleString() }} words</span>
        </div>
        <p v-if="!previousSceneAnalytics && !nextSceneAnalytics" class="text-[9px] text-zinc-500">This is the only scene in the manuscript.</p>
      </div>

      <details class="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5">
        <summary class="cursor-pointer text-[10px] text-zinc-400 hover:text-zinc-200">Possible filter-word repetitions</summary>
        <p class="my-2 text-[9px] text-zinc-500">Occurrences to review—not automatic errors. Keep any wording that serves the scene.</p>
        <div v-if="Object.keys(selectedSceneAnalytics.telemetry.filters || {}).length" class="space-y-1">
          <div v-for="(count, word) in selectedSceneAnalytics.telemetry.filters" :key="word" class="flex justify-between text-[10px] font-mono">
            <span class="text-zinc-300">{{ word }}</span><span class="text-zinc-500">{{ count }}×</span>
          </div>
        </div>
        <p v-else class="text-[9px] text-zinc-600">No configured filter words found.</p>
      </details>
    </template>
    <div v-else class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-[10px] text-zinc-500">
      Select a scene within a manuscript to compare its patterns.
    </div>
    <p class="text-[9px] leading-relaxed text-zinc-600">The selected scene uses current editor text; comparison scenes use their saved drafts. {{ store.aiEnabled ? 'Actual reader responses and the AI first-read rehearsal are in the Reader tab.' : 'Actual reader responses are in the Reader tab.' }} Sentence and dialogue patterns cannot tell us what a reader felt or understood.</p>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'

const {
  analyticsError,
  analyticsLoading,
  analyticsPosition,
  loadManuscriptAnalytics,
  manuscriptAnalytics,
  manuscriptPatternComparisons,
  nextSceneAnalytics,
  previousSceneAnalytics,
  readTimeRange,
  sceneLengthComparison,
  selectedSceneAnalytics
} = inject('inspectorState')
</script>
