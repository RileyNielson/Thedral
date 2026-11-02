<template>
  <div v-if="store.activeInspectorTab === 'reader'" class="space-y-4">
    <!-- Macro vs. Paragraph-by-Paragraph Toggle -->
    <div class="flex items-center justify-between border-b border-zinc-800 pb-2">
      <div class="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
        <button 
          @click="activeReaderMode = 'paragraphs'" 
          :class="['px-2.5 py-1 rounded text-[10px] font-mono transition flex items-center gap-1', activeReaderMode === 'paragraphs' ? 'bg-zinc-800 text-amber-300 font-bold' : 'text-zinc-500 hover:text-zinc-300']"
        >
          <span>Paragraph Feed</span>
          <span v-if="paragraphDiagnoses.length" class="text-[9px] px-1 rounded bg-zinc-900 border border-zinc-700">{{ paragraphDiagnoses.length }}</span>
        </button>
        <button 
          @click="activeReaderMode = 'story'" 
          :class="['px-2.5 py-1 rounded text-[10px] font-mono transition', activeReaderMode === 'story' ? 'bg-zinc-800 text-violet-300 font-bold' : 'text-zinc-500 hover:text-zinc-300']"
        >
          Story Currents
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

    <!-- VIEW 1: PARAGRAPH-BY-PARAGRAPH BEAT FEED (With Story So Far & Thread Impact) -->
    <section v-if="activeReaderMode === 'paragraphs'" class="space-y-2.5">
      <header class="p-2.5 bg-zinc-950 rounded-xl border border-zinc-800/80 space-y-1">
        <div class="flex items-center justify-between text-[10px] font-mono">
          <span class="font-bold text-amber-400 uppercase tracking-wider">Unfolding Reader Experience</span>
          <span class="text-zinc-500">{{ paragraphDiagnoses.length }} beats</span>
        </div>
        <p class="text-[9px] text-zinc-400 leading-relaxed">
          How each paragraph impacts active threads, reader working memory, and sensory reality.
        </p>
      </header>

      <div class="space-y-2.5 max-h-[68vh] overflow-y-auto pr-1 custom-scrollbar">
        <article 
          v-for="p in paragraphDiagnoses" 
          :key="p.paragraph_index"
          @click="jumpToParagraphBeat(p.paragraph_index)"
          class="p-3 bg-zinc-950/80 border rounded-xl space-y-2 transition cursor-pointer hover:border-zinc-700 shadow-sm"
          :class="[
            p.thread_impact?.action_type === 'SEED' ? 'border-amber-500/50 bg-amber-950/10' :
            p.thread_impact?.action_type === 'ESCALATE' ? 'border-rose-500/50 bg-rose-950/10' :
            p.thread_impact?.action_type === 'PAYOFF' ? 'border-emerald-500/50 bg-emerald-950/10' :
            'border-zinc-800/80'
          ]"
        >
          <!-- Header: Paragraph Number + Headline + Thread Action Badge -->
          <div class="flex items-center justify-between gap-2 border-b border-zinc-800/60 pb-1.5">
            <span class="font-mono text-[9px] px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 font-bold">
              P{{ p.paragraph_index }}
            </span>
            <span class="text-[10px] font-semibold truncate flex-1 text-zinc-200">
              {{ p.headline }}
            </span>
            
            <!-- Thread Impact Badge -->
            <span 
              v-if="p.thread_impact?.action_type === 'SEED'"
              class="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/40"
            >
              🌱 Seeded
            </span>
            <span 
              v-else-if="p.thread_impact?.action_type === 'ESCALATE'"
              class="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/40"
            >
              ⚡ Escalated
            </span>
            <span 
              v-else-if="p.thread_impact?.action_type === 'PAYOFF'"
              class="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/40"
            >
              🎯 Payoff
            </span>
          </div>

          <!-- The Story So Far (Reader's Working Horizon) -->
          <div v-if="p.story_so_far" class="p-2 bg-zinc-900/60 rounded-lg text-[9px] font-mono space-y-1 border border-zinc-800/50">
            <div class="flex justify-between text-zinc-400">
              <span>📍 <strong class="text-zinc-200">{{ p.story_so_far.location }}</strong></span>
              <span class="text-zinc-500">{{ p.story_so_far.active_tension_level }}</span>
            </div>
            <div v-if="p.story_so_far.characters_present?.length" class="text-zinc-400 truncate">
              👥 On stage: <span class="text-zinc-300">{{ p.story_so_far.characters_present.join(', ') }}</span>
            </div>
            <div v-if="p.story_so_far.active_threads?.length" class="text-zinc-400 truncate">
              ⏳ Loom: <span class="text-amber-300/90">{{ p.story_so_far.active_threads.join(' · ') }}</span>
            </div>
          </div>

          <!-- How the Reader Experiences This Paragraph -->
          <p class="text-[10px] text-zinc-300 leading-relaxed font-serif">
            {{ p.reader_experience }}
          </p>

          <!-- Thread Impact Detail -->
          <div v-if="p.thread_impact && p.thread_impact.action_type !== 'MAINTAIN'" class="text-[9px] font-mono text-zinc-400 flex items-center gap-1.5">
            <span class="text-amber-400 font-bold">Impact:</span>
            <span>{{ p.thread_impact.detail }}</span>
          </div>

          <!-- Craft Advisory -->
          <div v-if="p.craft_advisory" class="p-1.5 rounded bg-zinc-900/90 text-[9px] font-mono leading-snug text-zinc-400">
            💡 {{ p.craft_advisory }}
          </div>
        </article>
      </div>
    </section>

    <!-- VIEW 2: STORY CURRENTS (Macro Turns, Threads, Payoffs) -->
    <section v-else class="rounded-xl border border-violet-900/50 bg-violet-950/10 p-3 space-y-2.5">
      <header class="space-y-1">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-[10px] font-bold uppercase tracking-wider text-violet-300 font-mono">Story underneath</h2>
          <span v-if="readerStoryLoading" class="text-[9px] text-zinc-500 font-mono">Analyzing…</span>
        </div>
        <p class="text-[9px] leading-relaxed text-zinc-500">
          Macro narrative pivots, active promises, and speech acts mapped across the scene.
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
      </template>
    </section>

    <!-- Optional Beta-Reader Logs -->
    <details class="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3 space-y-3">
      <summary class="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-zinc-400">
        Beta-Reader Notes & Response Logs
      </summary>
      <section class="p-3 bg-zinc-950 rounded-xl border border-emerald-900/50 space-y-2">
        <header><h3 class="text-[11px] font-bold text-emerald-300">Human Beta-Reader Notes</h3></header>
        <p class="text-[9px] text-zinc-500">Record observations from beta readers to compare with the cognitive simulation.</p>
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
  jumpToStoryEvidence,
  readerStoryAnalysis,
  readerStoryError,
  readerStoryGroups,
  readerStoryLoading,
} = inject('inspectorState')

const activeReaderMode = ref('paragraphs')
const QUIET_LIMIT = 4
const showFullBreakdown = ref(false)

const paragraphDiagnoses = computed(() => {
  return readerStoryAnalysis.value?.paragraph_diagnoses || []
})

const visibleStoryGroups = computed(() => {
  return readerStoryGroups.value || []
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
    out += `### Paragraph-by-Paragraph Experience & Thread Dynamics\n\n`
    for (const p of data.paragraph_diagnoses) {
      out += `• **[P${p.paragraph_index}] ${p.headline}**\n`
      if (p.story_so_far) {
        out += `  *The Story So Far:* In ${p.story_so_far.location} | Cast: ${p.story_so_far.characters_present.join(', ') || 'Alone'} | Active Loom: ${p.story_so_far.active_threads.join(' · ') || 'None'}\n`
      }
      out += `  *Reader Perception:* ${p.reader_experience}\n`
      if (p.thread_impact && p.thread_impact.action_type !== 'MAINTAIN') {
        out += `  *Thread Impact [${p.thread_impact.action_type}]:* ${p.thread_impact.detail}\n`
      }
      if (p.craft_advisory) out += `  *Craft Advice:* ${p.craft_advisory}\n`
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
