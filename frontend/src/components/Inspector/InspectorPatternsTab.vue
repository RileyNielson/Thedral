<template>
  <div v-if="store.activeInspectorTab === 'prose' || store.activeInspectorTab === 'telemetry'" class="space-y-4 select-none">
    <header class="flex items-start justify-between gap-2 border-b border-zinc-800 pb-2">
      <div class="space-y-0.5">
        <h2 class="text-[11px] font-semibold text-zinc-200 font-mono">Prose Cadence & Precision</h2>
        <p class="text-[9px] text-zinc-500">Sentence rhythm, repeated word echoes, and dialogue attributions.</p>
      </div>
      <button @click="loadManuscriptAnalytics" :disabled="analyticsLoading" class="shrink-0 rounded border border-zinc-700 px-2 py-0.5 text-[9px] text-zinc-400 hover:text-zinc-200 disabled:opacity-50">
        {{ analyticsLoading ? 'Updating…' : 'Refresh' }}
      </button>
    </header>

    <template v-if="selectedSceneAnalytics">
      <!-- Reading Time -->
      <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-1.5">
        <div class="flex items-baseline justify-between gap-2">
          <span class="text-[10px] uppercase font-mono tracking-wider text-amber-400">Estimated Silent Read</span>
          <span class="font-mono text-sm font-semibold text-zinc-100">{{ readTimeRange }}</span>
        </div>
        <p class="text-[9px] text-zinc-500 font-mono">
          {{ selectedSceneAnalytics.telemetry.words.toLocaleString() }} words · scene {{ analyticsPosition }} of {{ manuscriptAnalytics.scenes.length }}
        </p>
      </div>

      <!-- Dialogue Attribution & Strained Tag Audit -->
      <div class="rounded-xl border border-purple-900/40 bg-purple-950/10 p-3 space-y-2">
        <div class="flex items-center justify-between text-[10px] font-mono">
          <span class="text-purple-300 uppercase tracking-wider font-bold">Dialogue Attributions</span>
          <span class="text-zinc-400">{{ selectedSceneAnalytics.telemetry.dialogue_ratio }}% dialogue</span>
        </div>
        
        <div class="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div class="p-2 bg-zinc-950 rounded border border-zinc-800/80">
            <div class="text-zinc-500">Strained Tags:</div>
            <div class="text-sm font-bold mt-0.5" :class="selectedSceneAnalytics.telemetry.strained_tags_count > 3 ? 'text-amber-400' : 'text-zinc-300'">
              {{ selectedSceneAnalytics.telemetry.strained_tags_count || 0 }}
            </div>
            <div class="text-[8px] text-zinc-600 mt-0.5">hissed, groaned, barked</div>
          </div>

          <div class="p-2 bg-zinc-950 rounded border border-zinc-800/80">
            <div class="text-zinc-500">Passive Voice:</div>
            <div class="text-sm font-bold mt-0.5" :class="selectedSceneAnalytics.telemetry.passive_count > 4 ? 'text-rose-400' : 'text-zinc-300'">
              {{ selectedSceneAnalytics.telemetry.passive_count || 0 }}
            </div>
            <div class="text-[8px] text-zinc-600 mt-0.5">was [verb]ed by</div>
          </div>
        </div>

        <div v-if="selectedSceneAnalytics.telemetry.dialogue_adverbs?.length" class="space-y-1 pt-1 border-t border-purple-900/30">
          <span class="text-[9px] uppercase font-mono text-rose-400 font-bold">Dialogue-Tag Adverbs:</span>
          <div class="flex flex-wrap gap-1">
            <span v-for="adv in selectedSceneAnalytics.telemetry.dialogue_adverbs" :key="adv" class="px-1.5 py-0.5 rounded bg-zinc-900 text-rose-300 border border-rose-900/40 text-[9px]">
              said {{ adv }}
            </span>
          </div>
        </div>
      </div>

      <!-- Word Echoes / Proximity Repetitions -->
      <div v-if="Object.keys(selectedSceneAnalytics.telemetry.echoes || {}).length" class="rounded-xl border border-amber-900/50 bg-amber-950/10 p-3 space-y-2">
        <div class="flex items-center justify-between text-[10px] font-mono">
          <span class="text-amber-300 uppercase tracking-wider font-bold">Proximity Word Echoes</span>
          <span class="text-zinc-500 text-[9px]">Repeated in 2–3 paragraphs</span>
        </div>
        <div class="flex flex-wrap gap-1.5 pt-1">
          <span 
            v-for="(data, word) in selectedSceneAnalytics.telemetry.echoes" 
            :key="word" 
            class="px-2 py-0.5 rounded bg-zinc-950 border border-amber-800/60 text-amber-200 text-[10px] font-mono"
            :title="`Repeated ${data.count} times across paragraphs: ${data.paragraphs.join(', ')}`"
          >
            {{ word }} <strong class="text-amber-400">({{ data.count }}×)</strong>
          </span>
        </div>
      </div>

      <!-- Filter Verbs -->
      <details class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-2">
        <summary class="cursor-pointer text-[10px] font-mono uppercase tracking-wider text-zinc-400 hover:text-zinc-200">
          Filter Words & Sensory Buffers
        </summary>
        <div v-if="Object.keys(selectedSceneAnalytics.telemetry.filters || {}).length" class="space-y-1 pt-1">
          <div v-for="(count, word) in selectedSceneAnalytics.telemetry.filters" :key="word" class="flex justify-between text-[10px] font-mono">
            <span class="text-zinc-300">{{ word }}</span>
            <span class="text-zinc-500">{{ count }}×</span>
          </div>
        </div>
      </details>
    </template>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { store } from '../../store.js'

const {
  analyticsLoading,
  analyticsPosition,
  loadManuscriptAnalytics,
  manuscriptAnalytics,
  readTimeRange,
  selectedSceneAnalytics
} = inject('inspectorState')
</script>
