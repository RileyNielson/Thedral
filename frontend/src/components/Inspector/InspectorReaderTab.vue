<template>
  <div v-if="store.activeInspectorTab === 'reader'" class="space-y-4">
    <!-- Macro vs. Paragraph-by-Paragraph Toggle -->
    <div class="flex items-center justify-between border-b border-zinc-800 pb-2">
      <div class="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
        <button 
          @click="activeReaderMode = 'story'" 
          :class="['px-2.5 py-1 rounded text-[10px] font-mono transition', activeReaderMode === 'story' ? 'bg-zinc-800 text-violet-300 font-bold' : 'text-zinc-500 hover:text-zinc-300']"
        >
          Story Currents
        </button>
        <button 
          @click="activeReaderMode = 'paragraphs'" 
          :class="['px-2.5 py-1 rounded text-[10px] font-mono transition flex items-center gap-1', activeReaderMode === 'paragraphs' ? 'bg-zinc-800 text-amber-300 font-bold' : 'text-zinc-500 hover:text-zinc-300']"
        >
          <span>Paragraph Feed</span>
          <span v-if="paragraphDiagnoses.length" class="text-[9px] px-1 rounded bg-zinc-900 border border-zinc-700">{{ paragraphDiagnoses.length }}</span>
        </button>
      </div>

      <button 
        v-if="readerStoryAnalysis" 
        @click="copyReaderReport" 
        class="px-2 py-1 rounded border border-violet-700/60 bg-violet-950/50 text-[9px] font-mono text-violet-200 hover:bg-violet-900/50 transition flex items-center gap-1 shadow-sm"
        title="Copy Markdown report to clipboard"
      >
        <Copy class="w-3 h-3" />
        <span>Copy</span>
      </button>
    </div>

    <!-- VIEW 1: STORY CURRENTS (Macro Turns, Threads, Payoffs) -->
    <section v-if="activeReaderMode === 'story'" class="rounded-xl border border-violet-900/50 bg-violet-950/10 p-3 space-y-2.5">
      <header class="space-y-1">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-[10px] font-bold uppercase tracking-wider text-violet-300 font-mono">Story underneath</h2>
          <span v-if="readerStoryLoading" class="text-[9px] text-zinc-500 font-mono">Analyzing…</span>
        </div>
        <p class="text-[9px] leading-relaxed text-zinc-500">
          Semantic turns, active promises, and character subtext mapped from the text.
        </p>
        <InspectorLexiconStatus />
      </header>

      <p v-if="readerStoryError" class="text-[9px] text-rose-300">{{ readerStoryError }}</p>

      <template v-else-if="readerStoryAnalysis">
        <template v-for="group in visibleStoryGroups" :key="group.key">
          <article 
            v-for="(insight, index) in group.items" 
            :key="`${group.key}-${index}`" 
            class="rounded-lg border border-zinc-800/80 bg-zinc-950/80 p-2.5 space-y-1.5 shadow-sm"
          >
            <div class="flex items-baseline justify-between gap-2">
              <h3 class="text-[10px] font-semibold text-violet-200">{{ insight.headline }}</h3>
              <span class="shrink-0 text-[8px] text-zinc-600 font-mono">{{ insight.confidence }}</span>
            </div>

            <p class="text-[10px] leading-relaxed text-zinc-300">{{ insight.reaction }}</p>

            <div v-if="insight.setup_evidence" class="space-y-0.5">
              <p class="text-[8px] uppercase tracking-wider text-zinc-600 font-mono">
                Earlier · {{ insight.setup_title || 'the setup' }}
              </p>
              <button 
                @click="jumpToStoryEvidence(insight.setup_scene_id, insight.setup_evidence)" 
                class="block w-full border-l border-violet-900/70 pl-2 text-left text-[9px] italic text-zinc-400 hover:text-violet-200 transition"
              >
                “{{ insight.setup_evidence }}”
              </button>
            </div>

            <div v-if="insight.payoff_evidence || insight.evidence" class="space-y-0.5">
              <p class="text-[8px] uppercase tracking-wider text-zinc-600 font-mono">
                {{ insight.setup_evidence ? 'Here' : `Here · paragraph ${insight.paragraph}` }}
              </p>
              <button 
                @click="jumpToStoryEvidence(insight.payoff_scene_id, insight.payoff_evidence || insight.evidence)" 
                class="block w-full border-l border-violet-900/70 pl-2 text-left text-[9px] italic text-zinc-400 hover:text-violet-200 transition"
              >
                “{{ insight.payoff_evidence || insight.evidence }}”
              </button>
            </div>
          </article>
        </template>

        <button 
          v-if="hiddenStoryCount > 0 || (showFullBreakdown && totalStoryCount > 3)" 
          @click="showFullBreakdown = !showFullBreakdown" 
          class="w-full rounded border border-violet-900/50 py-1 text-[10px] text-violet-300 hover:bg-violet-950/30 transition"
        >
          {{ showFullBreakdown ? 'Show fewer' : `Show full breakdown (${hiddenStoryCount} more)` }}
        </button>

        <p v-if="!readerStoryGroups.length" class="text-[9px] leading-relaxed text-zinc-500">
          {{ readerStoryAnalysis.summary }}
        </p>
      </template>
    </section>

    <!-- VIEW 2: PARAGRAPH-BY-PARAGRAPH BEAT FEED (Cuts & Flesh-out) -->
    <section v-else class="space-y-2.5">
      <header class="p-2.5 bg-zinc-950 rounded-xl border border-zinc-800/80 space-y-1">
        <div class="flex items-center justify-between text-[10px] font-mono">
          <span class="font-bold text-amber-400 uppercase tracking-wider">Paragraph Beat Experience</span>
          <span class="text-zinc-500">{{ paragraphDiagnoses.length }} beats</span>
        </div>
        <p class="text-[9px] text-zinc-400 leading-relaxed">
          How words, senses, and concept meanings affect reader attention paragraph by paragraph.
        </p>
      </header>

      <div class="space-y-2 max-h-[68vh] overflow-y-auto pr-1 custom-scrollbar">
        <article 
          v-for="p in paragraphDiagnoses" 
          :key="p.paragraph_index"
          @click="jumpToParagraphBeat(p.paragraph_index)"
          class="p-2.5 bg-zinc-950/80 border rounded-xl space-y-1.5 transition cursor-pointer hover:border-zinc-700"
          :class="[
            p.cognitive_function === 'SEMANTIC_SLACK_ALERT' ? 'border-amber-900/60 bg-amber-950/10' :
            p.cognitive_function === 'WHITE_ROOM_ALERT' ? 'border-rose-900/60 bg-rose-950/10' :
            p.cognitive_function === 'VISCERAL_GROUNDING' ? 'border-emerald-900/50' :
            'border-zinc-800/80'
          ]"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="font-mono text-[9px] px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 font-bold">
              P{{ p.paragraph_index }}
            </span>
            <span class="text-[10px] font-semibold truncate flex-1 text-zinc-200">
              {{ p.headline }}
            </span>
            <span 
              v-if="p.cognitive_function === 'SEMANTIC_SLACK_ALERT'"
              class="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30"
            >
              ✂️ Trim?
            </span>
            <span 
              v-else-if="p.cognitive_function === 'WHITE_ROOM_ALERT'"
              class="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30"
            >
              🔍 Flesh out?
            </span>
          </div>

          <p class="text-[10px] text-zinc-300 leading-relaxed font-serif">
            {{ p.reader_experience }}
          </p>

          <div v-if="p.craft_advisory" class="p-1.5 rounded bg-zinc-900/90 text-[9px] font-mono leading-snug"
            :class="p.cognitive_function.includes('ALERT') ? 'text-amber-300' : 'text-zinc-400'"
          >
            💡 {{ p.craft_advisory }}
          </div>

          <div v-if="p.salient_words?.length" class="flex flex-wrap gap-1 pt-0.5 text-[8px] font-mono text-zinc-500">
            <span class="text-zinc-600">Key words:</span>
            <span v-for="word in p.salient_words" :key="word" class="px-1 rounded bg-zinc-900 text-zinc-400">
              {{ word }}
            </span>
          </div>
        </article>
      </div>
    </section>

    <!-- Optional Human Feedback Drawer -->
    <details class="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3 space-y-3">
      <summary class="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-zinc-400">
        Beta-Reader Notes & Response Logs
      </summary>

      <section class="rounded-xl border border-emerald-900/50 bg-emerald-950/10 p-3 space-y-2">
        <header class="flex items-baseline justify-between gap-2">
          <h2 class="text-[10px] font-bold uppercase tracking-wider text-emerald-300">Actual reader evidence</h2>
          <span class="text-[9px] font-mono text-zinc-500">n={{ readerFeedbackSummary.responseCount }}</span>
        </header>

        <template v-if="readerFeedbackSummary.responseCount">
          <div v-for="group in readerFeedbackSummary.groups" :key="group.revision" class="space-y-1.5 border-t border-emerald-900/40 pt-2">
            <p class="text-[9px] text-zinc-400 font-mono">
              {{ group.revision === 'CURRENT' ? 'Current draft' : `Version ${group.revision.toLowerCase()}` }} · n={{ group.entries.length }}
            </p>
            <p v-if="group.averages" class="text-[9px] leading-relaxed text-emerald-200">{{ group.averages }}</p>
            <blockquote v-for="entry in group.recentResponses" :key="entry.id" class="line-clamp-4 border-l border-emerald-800 pl-2 text-[10px] leading-relaxed text-zinc-300 font-serif">
              “{{ entry.response }}”
              <footer class="mt-0.5 text-[9px] text-zinc-600 font-mono">{{ entry.reader_label || 'Reader' }}</footer>
            </blockquote>
          </div>
        </template>
        <p v-else class="text-[9px] text-zinc-500">
          No human beta-reader responses recorded for this scene yet.
        </p>
      </section>

      <section class="p-3 bg-zinc-950 rounded-xl border border-emerald-900/50 space-y-3">
        <header>
          <h3 class="text-[11px] font-bold text-emerald-300">Log actual reader feedback</h3>
        </header>
        <form @submit.prevent="saveReaderFeedback" class="space-y-2">
          <input v-model="feedbackForm.reader_label" maxlength="80" placeholder="Reader pseudonym (optional)" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200" />
          <textarea v-model="feedbackForm.response" rows="3" maxlength="4000" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200" placeholder="Where did they skim? What did they picture?" />
          <button type="submit" :disabled="!canSaveFeedback" class="rounded border border-emerald-700/60 bg-emerald-950/30 px-2.5 py-1.5 text-[10px] text-emerald-200 hover:bg-emerald-900/40 disabled:opacity-40 transition">
            Save response
          </button>
        </form>
      </section>
    </details>
  </div>
</template>

<script setup>
import InspectorLexiconStatus from './InspectorLexiconStatus.vue'
import { computed, inject, ref } from 'vue'
import { store, showToast } from '../../store.js'
import { Copy } from '@lucide/vue'

const {
  canSaveFeedback,
  feedbackForm,
  jumpToStoryEvidence,
  readerFeedbackSummary,
  readerStoryAnalysis,
  readerStoryError,
  readerStoryGroups,
  readerStoryLoading,
  saveReaderFeedback,
} = inject('inspectorState')

const activeReaderMode = ref('paragraphs') // 'paragraphs' | 'story'
const QUIET_LIMIT = 4
const showFullBreakdown = ref(false)

const paragraphDiagnoses = computed(() => {
  return readerStoryAnalysis.value?.paragraph_diagnoses || []
})

const totalStoryCount = computed(() => readerStoryGroups.value.reduce((sum, group) => sum + group.items.length, 0))
const hiddenStoryCount = computed(() => Math.max(0, totalStoryCount.value - QUIET_LIMIT))

const visibleStoryGroups = computed(() => {
  if (showFullBreakdown.value) return readerStoryGroups.value
  let remaining = QUIET_LIMIT
  const groups = []
  for (const group of readerStoryGroups.value) {
    if (remaining <= 0) break
    groups.push({ ...group, items: group.items.slice(0, remaining) })
    remaining -= group.items.length
  }
  return groups
})

const jumpToParagraphBeat = (pNum) => {
  window.dispatchEvent(new CustomEvent('lens-beat-jump', { detail: { beat: pNum } }))
}

const copyReaderReport = async () => {
  if (!readerStoryAnalysis.value) return
  const data = readerStoryAnalysis.value
  const sceneTitle = store.activeNode?.title || 'Current Scene'
  
  let out = `# Beta-Reader Semantic Analysis: ${sceneTitle}\n\n`
  out += `*${data.summary || 'Summary unavailable'}*\n\n`
  
  if (data.paragraph_diagnoses?.length) {
    out += `### Paragraph-by-Paragraph Semantic Experience\n\n`
    for (const p of data.paragraph_diagnoses) {
      out += `• **[P${p.paragraph_index}] ${p.headline}**\n`
      out += `  *Reader Perception:* ${p.reader_experience}\n`
      if (p.craft_advisory) out += `  *Craft Advice:* ${p.craft_advisory}\n`
      if (p.salient_words?.length) out += `  *Anchoring Words:* ${p.salient_words.join(', ')}\n`
      out += `\n`
    }
  }

  const sections = [
    ['Story Turns (Pivots & Reversals)', data.turns],
    ['Story Threads (Promises & Payoffs)', data.threads],
    ['Subtext & Speech Acts', data.subtext_moments],
    ['Dramatic Irony (Secret Knowledge)', data.irony_moments],
    ['Atmosphere, Pacing & Continuity', data.experience_moments]
  ]

  for (const [title, items] of sections) {
    if (!items || !items.length) continue
    out += `### ${title}\n`
    for (const item of items) {
      const pNum = item.paragraph ? `P${item.paragraph}` : ''
      out += `- **${item.headline || item.kind}** ${pNum ? `(${pNum})` : ''}\n`
      if (item.reaction) out += `  *Reader Perception:* ${item.reaction}\n`
      if (item.payoff_evidence || item.evidence) {
        out += `  *Evidence:* "${item.payoff_evidence || item.evidence}"\n`
      }
      out += `\n`
    }
  }

  try {
    await navigator.clipboard.writeText(out)
    showToast('Reader analysis copied to clipboard!', 'success')
  } catch (err) {
    showToast('Could not copy to clipboard. Check browser permissions.', 'error')
  }
}
</script>
