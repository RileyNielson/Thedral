<template>
  <div v-if="store.activeInspectorTab === 'reader'" class="space-y-4">
    <section class="rounded-xl border border-emerald-900/50 bg-emerald-950/10 p-3 space-y-2">
      <header class="flex items-baseline justify-between gap-2">
        <h2 class="text-[10px] font-bold uppercase tracking-wider text-emerald-300">Actual reader evidence</h2>
        <span class="text-[9px] font-mono text-zinc-500">n={{ readerFeedbackSummary.responseCount }}</span>
      </header>
      <template v-if="readerFeedbackSummary.responseCount">
        <div v-for="group in readerFeedbackSummary.groups" :key="group.revision" class="space-y-1.5 border-t border-emerald-900/40 pt-2">
          <p class="text-[9px] text-zinc-400">{{ group.revision === 'CURRENT' ? 'Current draft' : `Version ${group.revision.toLowerCase()}` }} · n={{ group.entries.length }}</p>
          <p v-if="group.averages" class="text-[9px] leading-relaxed text-emerald-200">{{ group.averages }}</p>
          <blockquote v-for="entry in group.recentResponses" :key="entry.id" class="line-clamp-4 border-l border-emerald-800 pl-2 text-[10px] leading-relaxed text-zinc-300">
            “{{ entry.response }}”
            <footer class="mt-0.5 text-[9px] text-zinc-600">{{ entry.reader_label || 'Reader' }}</footer>
          </blockquote>
        </div>
        <p v-if="readerFeedbackSummary.moreGroups" class="text-[9px] text-zinc-600">More reviewed versions are listed below. Ratings are never averaged across different drafts.</p>
        <p class="text-[9px] text-zinc-600">Small, self-selected responses are useful signals—not representative audience research.</p>
      </template>
      <p v-else class="text-[9px] text-zinc-500">No beta-reader responses recorded for this scene yet. Recorded responses appear here before the AI rehearsal.</p>
    </section>

    <section class="rounded-xl border border-violet-900/50 bg-violet-950/10 p-3 space-y-2.5">
      <header class="space-y-1">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-[10px] font-bold uppercase tracking-wider text-violet-300">Story underneath · no AI</h2>
          <span v-if="readerStoryLoading" class="text-[9px] text-zinc-500">Following the threads…</span>
        </div>
        <p class="text-[9px] leading-relaxed text-zinc-500">
          {{ readerStoryAnalysis?.disclaimer || 'These are confident predictions of a typical reader’s experience, grounded in the manuscript—not a guarantee that every reader will react the same way.' }}
        </p>
        <p class="text-[9px] leading-relaxed text-zinc-500">
          No AI: ready across the manuscript after import, and refreshes from the live draft after you pause while this tab is open.
        </p>
        <p v-if="readerStoryAnalysis?.lexicon?.available" class="text-[9px] leading-relaxed text-emerald-300/80">
          Local Wiktionary word forms and synonyms are expanding the story cues.
        </p>
        <p v-else class="text-[9px] leading-relaxed text-zinc-600">
          Local Wiktionary word-form expansion is not installed yet.
        </p>
      </header>
      <p v-if="readerStoryError" class="text-[9px] text-rose-300">{{ readerStoryError }}</p>
      <template v-else-if="readerStoryAnalysis">
        <template v-for="group in readerStoryGroups" :key="group.key">
          <article v-for="(insight, index) in group.items" :key="`${group.key}-${index}`" class="rounded-lg border border-zinc-800/80 bg-zinc-950/80 p-2.5 space-y-1.5">
            <div class="flex items-baseline justify-between gap-2">
              <h3 class="text-[10px] font-semibold text-violet-200">{{ insight.headline }}</h3>
              <span class="shrink-0 text-[8px] text-zinc-600">{{ insight.confidence }}</span>
            </div>
            <p class="text-[10px] leading-relaxed text-zinc-300">{{ insight.reaction }}</p>
            <div v-if="insight.setup_evidence" class="space-y-0.5">
              <p class="text-[8px] uppercase tracking-wider text-zinc-600">Earlier · {{ insight.setup_title || 'the setup' }}</p>
              <button @click="jumpToStoryEvidence(insight.setup_scene_id, insight.setup_evidence)" class="block w-full border-l border-violet-900/70 pl-2 text-left text-[9px] italic text-zinc-400 hover:text-violet-200">“{{ insight.setup_evidence }}”</button>
            </div>
            <div v-if="insight.payoff_evidence || insight.evidence" class="space-y-0.5">
              <p class="text-[8px] uppercase tracking-wider text-zinc-600">{{ insight.setup_evidence ? 'Here' : `Here · paragraph ${insight.paragraph}` }}</p>
              <button @click="jumpToStoryEvidence(insight.payoff_scene_id, insight.payoff_evidence || insight.evidence)" class="block w-full border-l border-violet-900/70 pl-2 text-left text-[9px] italic text-zinc-400 hover:text-violet-200">“{{ insight.payoff_evidence || insight.evidence }}”</button>
            </div>
          </article>
        </template>
        <p v-if="!readerStoryGroups.length" class="text-[9px] leading-relaxed text-zinc-500">
          {{ readerStoryAnalysis.summary }} Try giving a question, promise, or clear reversal room on the page; this reader lens only calls out patterns it can point to.
        </p>
      </template>
    </section>

    <div class="flex items-center justify-between">
      <div>
        <span class="text-[11px] text-zinc-400 font-medium">Simulated reader pass</span>
        <p class="text-[9px] text-zinc-600">
          {{ readingMode === 'scene'
            ? 'Only this scene is supplied—no author goal or explanation.'
            : 'The AI receives the most recent preceding manuscript text (up to 3,500 characters), then this scene. No notes or author explanation.'
          }}
          This is a hypothesis, not reader feedback.
        </p>
      </div>
      <button 
        @click="scanHorizon" 
        :disabled="isScanning" 
        class="px-2 py-0.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded text-[10px] font-mono flex items-center gap-1 transition"
      >
        <Sparkles class="w-3 h-3" /> 
        <span>{{ isScanning ? 'Simulating...' : 'Simulate first read (AI)' }}</span>
      </button>
    </div>

    <label class="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 py-2 text-[9px] text-zinc-500">
      <span>Reading context</span>
      <select v-model="readingMode" :disabled="isScanning" class="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-[10px] text-zinc-200 disabled:opacity-60">
        <option value="scene">Scene alone</option>
        <option value="sequential">With preceding scenes</option>
      </select>
    </label>

    <div v-if="simulationHistory.length" class="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
      <div class="flex items-center justify-between gap-2">
        <label class="text-[9px] uppercase tracking-wider text-zinc-500" for="reader-simulation-history">Saved first-read pass</label>
        <span class="text-[9px] text-zinc-500">{{ simulationHistory.length }} distinct simulation(s)</span>
      </div>
      <select id="reader-simulation-history" v-model="selectedSimulationId" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200">
        <option v-for="(simulation, index) in simulationHistory" :key="simulation.id" :value="simulation.id">
          Pass {{ simulationHistory.length - index }} · {{ simulation.reading_mode === 'sequential' ? 'sequential' : 'scene alone' }} · {{ simulation.revision_ref }} · {{ (simulation.created_at || '').split(' ')[0] }} · {{ simulation.source_content_hash.slice(0, 10) }}
        </option>
      </select>
      <template v-if="selectedSimulation">
        <p class="text-[9px] text-zinc-500">
          {{ selectedSimulation.revision_ref === 'CURRENT' ? 'Saved scene content' : selectedSimulation.revision_ref === 'UNSAVED' ? 'Unsaved editor content' : `Saved revision ${selectedSimulation.revision_ref}` }}
          · {{ selectedSimulation.analyzed_scene_characters.toLocaleString() }} of {{ selectedSimulation.source_characters.toLocaleString() }} scene characters
          <template v-if="selectedSimulation.context_characters"> + {{ selectedSimulation.context_characters.toLocaleString() }} prior-context characters</template>
          · {{ selectedSimulation.model_name }} · {{ selectedSimulation.prompt_version }}
        </p>
        <p v-if="selectedSimulation.prompt_version === 'first-read-v4'" class="text-[9px] text-emerald-300">
          Fresh-read pass: {{ selectedSimulation.reading_mode === 'sequential'
            ? `the AI received ${selectedSimulation.context_characters.toLocaleString()} characters of preceding scene text and the current scene, without author-only context.`
            : 'the AI received only the scene excerpt, without author-only context.'
          }}
        </p>
        <p v-else-if="selectedSimulation.prompt_version === 'first-read-v3'" class="text-[9px] text-emerald-300">
          Fresh-read pass: the AI received only the scene excerpt, with no author-provided goal or explanation.
        </p>
        <p v-else-if="selectedSimulation.intended_takeaway" class="text-[9px] text-amber-300">
          This older pass included an author-provided takeaway; run a new pass for an uncued fresh read.
        </p>
        <p v-if="selectedSimulation.reused_from_id" class="text-[9px] text-cyan-300">
          The analyzed excerpt matches an earlier pass; its saved observations were reused to keep feedback stable.
        </p>
        <details class="text-[9px] text-zinc-500">
          <summary class="cursor-pointer hover:text-zinc-300">Show exact manuscript text sent to AI</summary>
          <div v-if="selectedSimulation.reading_context" class="mt-1 space-y-1">
            <p class="text-zinc-600">Preceding context window</p>
            <p class="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-zinc-900 p-2 text-zinc-400">{{ selectedSimulation.reading_context }}</p>
          </div>
          <p class="mt-1 text-zinc-600">Current scene excerpt</p>
          <p class="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-zinc-900 p-2 text-zinc-400">{{ selectedSimulation.analyzed_text }}</p>
        </details>
      </template>
    </div>

    <div v-if="!selectedSimulation" class="rounded-xl border border-dashed border-zinc-700 bg-zinc-950 p-4 text-center">
      <h3 class="text-[11px] font-semibold text-zinc-300">No saved first-read pass for this scene</h3>
      <p class="mt-1 text-[9px] leading-relaxed text-zinc-500">Run the AI rehearsal directly—no setup or author explanation is needed. Each result is saved against its exact scene text so revision comparisons stay grounded.</p>
    </div>

    <section v-if="selectedSimulation" class="rounded-xl border border-cyan-900/50 bg-cyan-950/10 p-3 space-y-3">
      <header class="space-y-1">
        <h3 class="text-[11px] font-bold uppercase tracking-wider text-cyan-300">Estimated reader experience</h3>
        <p class="text-[9px] leading-relaxed text-zinc-500">AI interpretation of likely experience, beat by beat. The 1–5 levels are rough ordinal estimates from the cited text—not measurements, predictions, or a real reader’s emotional state. Each cause explains what in the prose may create the effect.</p>
      </header>
      <div v-for="dimension in readerExperienceDimensions" :key="dimension.key" v-show="readerExperienceItems(dimension.type).length" class="space-y-1.5 border-t border-cyan-900/30 pt-2">
        <h4 class="text-[9px] font-semibold uppercase tracking-wider text-zinc-300">{{ dimension.label }}</h4>
        <article v-for="(item, index) in readerExperienceItems(dimension.type)" :key="`${item.source_excerpt}-${index}`" class="rounded-lg bg-zinc-950/80 p-2.5 space-y-1.5">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <span v-if="item.moment" class="mr-1 text-[8px] uppercase tracking-wider text-zinc-600">{{ item.moment }}</span>
              <span class="text-[10px] font-medium text-zinc-200">{{ item.narrative_claim }}</span>
            </div>
            <span class="shrink-0 rounded border border-cyan-900/60 px-1.5 py-0.5 text-[8px] font-mono text-cyan-200">
              {{ readerLevelLabel(item.level) }}
            </span>
          </div>
          <div class="h-1 overflow-hidden rounded bg-zinc-800" :aria-label="`AI estimated level ${item.level} of 5`">
            <div class="h-full rounded bg-cyan-500/70" :style="{ width: `${item.level * 20}%` }"></div>
          </div>
          <p class="text-[9px] leading-relaxed text-zinc-400"><span class="text-zinc-600">Possible driver:</span> {{ item.cause }}</p>
          <blockquote class="border-l border-cyan-900/70 pl-2 text-[9px] italic leading-relaxed text-zinc-500">
            <span v-if="item.evidence_source === 'prior_context'" class="not-italic text-cyan-700">Earlier scene: </span>
            “{{ item.source_excerpt }}”
          </blockquote>
        </article>
      </div>
      <p v-if="!readerExperienceDimensions.some(dimension => readerExperienceItems(dimension.type).length)" class="text-[9px] text-zinc-500">
        This pass has no structured reader-experience estimates. Run a fresh pass to generate emotional, interest, tension, mystery, suspense, connection, confusion, and attention hypotheses.
      </p>
    </section>

    <div v-if="loopSignal.active" class="rounded-lg border border-amber-700/50 bg-amber-950/20 p-3 space-y-1">
      <h3 class="text-[10px] font-bold uppercase tracking-wider text-amber-300">Possible revision loop</h3>
      <p class="text-[10px] leading-relaxed text-zinc-300">
        Similar simulated observations have recurred across {{ loopSignal.revisions_compared }} distinct analyzed excerpts. This is not a quality or progress score.
        Consider pausing, making one deliberate revision experiment—or move on and seek a human read.
      </p>
    </div>

    <div v-if="simulationComparison" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-1.5">
      <h3 class="text-[10px] font-bold uppercase tracking-wider text-zinc-300">Compared with {{ simulationComparison.previous.revision_ref }}</h3>
      <p class="text-[9px] text-zinc-500">Exact AI observation wording across text versions—this is not a score of revision quality or proof that the reader experience improved.</p>
      <p class="text-[10px] text-zinc-300">
        {{ simulationComparison.unchanged.length }} observation(s) repeated
        · {{ simulationComparison.newClaims.length }} newly surfaced
        · {{ simulationComparison.removedClaims.length }} no longer surfaced
      </p>
      <div v-if="simulationComparison.newClaims.length" class="text-[9px] text-emerald-300">
        Newly surfaced: {{ simulationComparison.newClaims.join(' · ') }}
      </div>
      <div v-if="simulationComparison.removedClaims.length" class="text-[9px] text-zinc-400">
        No longer surfaced: {{ simulationComparison.removedClaims.join(' · ') }}
      </div>
    </div>
    
    <details v-if="selectedSimulation" class="rounded-xl border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
      <summary class="cursor-pointer text-[10px] font-semibold text-zinc-400 hover:text-zinc-200">Other first-read observations</summary>
      <section v-for="category in otherObservationCategories" :key="category.type" class="space-y-1 border-t border-zinc-800 pt-2">
        <h4 class="text-[9px] font-semibold uppercase tracking-wider" :class="category.color">{{ category.label }}</h4>
        <article v-for="(item, index) in simulationItems(category.type)" :key="`${item.source_excerpt}-${index}`" class="text-[10px] leading-relaxed text-zinc-300">
          <p>{{ item.narrative_claim }}</p>
          <blockquote v-if="item.source_excerpt" class="border-l border-zinc-700 pl-2 text-[9px] italic text-zinc-500">
            <span v-if="item.evidence_source === 'prior_context'" class="not-italic text-cyan-700">Earlier scene: </span>
            “{{ item.source_excerpt }}”
          </blockquote>
        </article>
        <p v-if="!simulationItems(category.type).length" class="text-[9px] text-zinc-600">No grounded observations surfaced in this category.</p>
      </section>
    </details>

      <section class="p-3 bg-zinc-950 rounded-xl border border-emerald-900/50 space-y-3">
        <header>
          <h3 class="text-[11px] font-bold text-emerald-300">Actual reader feedback</h3>
          <p class="mt-1 text-[9px] text-zinc-500">Optional notes entered by you from beta-reader responses. Stored only in this app's local database; avoid entering identifying details without permission.</p>
        </header>
        <form @submit.prevent="saveReaderFeedback" class="space-y-2">
          <input v-model="feedbackForm.reader_label" maxlength="80" placeholder="Reader label (pseudonym, optional)" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200" />
          <label class="block text-[9px] text-zinc-500">Draft version reviewed
            <select v-model="feedbackForm.revision_ref" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200">
              <option value="CURRENT">Current draft</option>
              <option v-for="revision in store.activeNode?.revisions || []" :key="revision.version_num" :value="`V${revision.version_num}`">Saved version v{{ revision.version_num }}</option>
            </select>
          </label>
          <div class="grid grid-cols-2 gap-2">
            <label v-for="rating in feedbackRatings" :key="rating.key" class="text-[9px] text-zinc-500">{{ rating.label }}
              <select v-model="feedbackForm[rating.key]" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200">
                <option value="">Not rated</option><option v-for="score in [1,2,3,4,5]" :key="score" :value="String(score)">{{ score }} / 5</option>
              </select>
            </label>
          </div>
          <textarea v-model="feedbackForm.response" rows="3" maxlength="4000" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200" placeholder="Where were you confused? What did you expect? What moment stayed with you?" />
          <button type="submit" :disabled="!canSaveFeedback" class="rounded border border-emerald-700/60 bg-emerald-950/30 px-2.5 py-1.5 text-[10px] text-emerald-200 hover:bg-emerald-900/40 disabled:opacity-40">Save reader response</button>
        </form>
        <div v-if="readerFeedback.length" class="space-y-2 border-t border-zinc-800 pt-2">
          <div class="text-[10px] font-semibold text-zinc-300">{{ readerFeedback.length }} response(s), grouped by reviewed draft</div>
          <div v-for="group in readerFeedbackGroups" :key="group.revision" class="rounded border border-zinc-800 p-2">
            <div class="text-[9px] text-zinc-400">{{ group.revision === 'CURRENT' ? 'Current draft' : `Version ${group.revision.toLowerCase()}` }} · n={{ group.entries.length }}</div>
            <div v-if="group.averages" class="mt-1 text-[9px] text-emerald-300">{{ group.averages }}</div>
            <article v-for="entry in group.entries" :key="entry.id" class="mt-2 border-t border-zinc-800 pt-1.5 text-[10px] text-zinc-300">
              <div class="flex justify-between text-zinc-500"><span>{{ entry.reader_label || 'Reader' }}</span><span>{{ (entry.created_at || '').split(' ')[0] }}</span></div>
              <p v-if="entry.response" class="mt-1 whitespace-pre-wrap">{{ entry.response }}</p>
              <button @click="removeReaderFeedback(entry.id)" class="mt-1 text-[9px] text-zinc-600 hover:text-rose-400">Remove response</button>
            </article>
          </div>
        </div>
        <p v-else class="text-[10px] text-zinc-600">No reader responses recorded for this scene.</p>
      </section>
    <InspectorIntentNotes />
  </div>
</template>

<script setup>
import InspectorIntentNotes from './InspectorIntentNotes.vue'
import { inject } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'
import { Sparkles } from '@lucide/vue'

const {
  canSaveFeedback,
  feedbackForm,
  feedbackRatings,
  isScanning,
  jumpToStoryEvidence,
  loopSignal,
  otherObservationCategories,
  readerExperienceDimensions,
  readerExperienceItems,
  readerFeedback,
  readerFeedbackGroups,
  readerFeedbackSummary,
  readerLevelLabel,
  readerStoryAnalysis,
  readerStoryError,
  readerStoryGroups,
  readerStoryLoading,
  readingMode,
  removeReaderFeedback,
  saveReaderFeedback,
  scanHorizon,
  selectedSimulation,
  selectedSimulationId,
  simulationComparison,
  simulationHistory,
  simulationItems
} = inject('inspectorState')
</script>
