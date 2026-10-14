<template>
  <div 
    v-if="store.modals.career" 
    class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none" 
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-zinc-800 pb-3 shrink-0">
        <div class="flex items-center gap-3">
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <Award class="w-5 h-5 text-amber-500" /> Publishing & Career Suite
          </h3>
          <span class="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
            Audible & KDP
          </span>
        </div>
        <button @click="closeModal" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Action Card Grid: 4 Master Publishing Tools -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 shrink-0">
        
        <!-- Tool 1: Manuscript Prose Signals -->
        <div class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-purple-500/50 transition group">
          <div>
            <div class="text-xs font-bold text-purple-400 flex items-center gap-1.5 font-mono">
              <Activity class="w-4 h-4" /> Prose Signals
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              Counts of selected word and sentence patterns—not reader reactions.
            </p>
          </div>
          <button 
            @click="fetchProseSignals"
            :disabled="isLoading"
            class="w-full py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 disabled:opacity-50 font-medium rounded text-xs transition shadow-sm"
          >
            {{ isLoading && outputTitle.includes('Signals') ? 'Counting...' : 'View patterns' }}
          </button>
        </div>

        <!-- Tool 2: Drafting History -->
        <div class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-emerald-500/50 transition group">
          <div>
            <div class="text-xs font-bold text-emerald-400 flex items-center gap-1.5 font-mono">
              <ShieldCheck class="w-4 h-4" /> Drafting History
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              Revision records and a current-text fingerprint; not proof of authorship.
            </p>
          </div>
          <button 
            @click="fetchAuthorshipProof" 
            :disabled="isLoading"
            class="w-full py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 font-medium rounded text-xs text-white transition border border-zinc-700/50"
          >
            {{ isLoading && outputTitle.includes('Drafting History') ? 'Preparing...' : 'View report' }}
          </button>
        </div>

        <!-- Tool 3: Query Synopsis -->
        <div class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-cyan-500/50 transition group">
          <div>
            <div class="text-xs font-bold text-cyan-400 flex items-center gap-1.5 font-mono">
              <FileText class="w-4 h-4" /> Query Synopsis
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              1-page causal plot pitch revealing the ending.
            </p>
          </div>
          <button 
            @click="generateSynopsis" 
            :disabled="isLoading"
            class="w-full py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 font-medium rounded text-xs text-white transition border border-zinc-700/50"
          >
            {{ isLoading && outputTitle.includes('Synopsis') ? 'Compiling...' : 'Generate (AI)' }}
          </button>
        </div>

        <!-- Tool 4: Audiobook Pack -->
        <div class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-amber-500/50 transition group">
          <div>
            <div class="text-xs font-bold text-amber-400 flex items-center gap-1.5 font-mono">
              <Mic class="w-4 h-4" /> Narrator Pack
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              Phonetic lore & vocal acting registers.
            </p>
          </div>
          <a 
            :href="`${API_BASE}/api/publishing/narrator-pack?book_id=${activeBookId}`" 
            download="Narrator_Pronunciation_Pack.md" 
            class="w-full py-1.5 bg-zinc-800 hover:bg-zinc-700 text-center font-medium rounded text-xs text-white block transition border border-zinc-700/50"
          >
            Download .md
          </a>
        </div>

      </div>

      <!-- Output Dossier View -->
      <div v-if="output" class="space-y-2 flex-1 overflow-hidden flex flex-col">
        <div class="flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span class="text-zinc-300 font-semibold">{{ outputTitle }}</span>
          <button 
            @click="copyOutput" 
            class="text-amber-400 hover:underline flex items-center gap-1 transition"
          >
            <Copy class="w-3 h-3" /> {{ copied ? 'Copied!' : 'Copy Text' }}
          </button>
        </div>

        <div class="p-4 bg-zinc-950 rounded-xl border border-zinc-800 text-xs font-mono text-zinc-300 overflow-y-auto whitespace-pre-line select-text flex-1 custom-scrollbar leading-relaxed">
          {{ output }}
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, showToast } from '../../store.js'
import { Award, X, Mic, ShieldCheck, FileText, Copy, Activity } from '@lucide/vue'

import { API_BASE } from '@/api'

const output = ref('')
const outputTitle = ref('')
const isLoading = ref(false)
const copied = ref(false)

const activeBookId = computed(() => {
  return store.activeNode?.book_id || (store.tree[0] && store.tree[0].id) || ''
})

const closeModal = () => {
  store.toggleModal('career', false)
}

const copyOutput = async () => {
  if (!output.value) return
  try {
    await navigator.clipboard.writeText(output.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
    showToast('Copied to clipboard!', 'info')
  } catch(e) {
    showToast('Failed to copy', 'error')
  }
}

// 1. Full manuscript prose-pattern summary
const fetchProseSignals = async () => {
  isLoading.value = true
  outputTitle.value = 'Manuscript Prose Signals'
  output.value = 'Counting selected textual patterns across this manuscript...'

  try {
    const res = await fetch(`${API_BASE}/api/publishing/prose-signals?book_id=${activeBookId.value}`)
    if (!res.ok) throw new Error(`Prose signal analysis failed (HTTP ${res.status}).`)
    const data = await res.json()

    const signals = data.text_signals
    let report = `MANUSCRIPT PROSE SIGNALS (${data.total_words.toLocaleString()} words)\n`
    report += `============================================================\n\n`
    report += `Selected word cues per 1,000 words (cue counts are not reader reactions):\n`
    report += `• Action-related cues: ${signals.signals.action_cues_per_1000_words.count} (${signals.signals.action_cues_per_1000_words.rate}/1,000 words)\n`
    report += `• Relational cues: ${signals.signals.relational_cues_per_1000_words.count} (${signals.signals.relational_cues_per_1000_words.rate}/1,000 words)\n`
    report += `• Mystery-related cues: ${signals.signals.mystery_cues_per_1000_words.count} (${signals.signals.mystery_cues_per_1000_words.rate}/1,000 words)\n`
    report += `• Sensory cues: ${signals.signals.sensory_cues_per_1000_words.count} (${signals.signals.sensory_cues_per_1000_words.rate}/1,000 words)\n\n`
    report += `Text patterns:\n`
    report += `• Dialogue paragraphs: ${signals.patterns.dialogue_paragraph_pct}%\n`
    report += `• Short sentences (8 words or fewer): ${signals.patterns.short_sentence_pct}%\n`
    report += `• Long sentences (22 words or more): ${signals.patterns.long_sentence_pct}%\n`
    report += `• Question marks per 1,000 words: ${signals.patterns.question_marks_per_1000_words}\n\n`
    report += `LIMITS: ${signals.limitations}\n`

    output.value = report
  } catch(e) {
    output.value = 'Error analyzing manuscript prose signals.'
    showToast(e.message, 'error')
  } finally {
    isLoading.value = false
  }
}

// 2. Drafting history report
const fetchAuthorshipProof = async () => {
  isLoading.value = true
  outputTitle.value = 'Drafting History Report'
  output.value = 'Preparing recorded revisions and current-text fingerprint...'
  
  try {
    const res = await fetch(`${API_BASE}/api/publishing/drafting-history?book_id=${encodeURIComponent(activeBookId.value)}`)
    if (!res.ok) throw new Error('Drafting history report failed')
    const data = await res.json()
    output.value = data.report_text
  } catch(e) { 
    output.value = 'Error generating drafting history report.'
    showToast(e.message, 'error') 
  } finally {
    isLoading.value = false
  }
}

// 3. 1-Page Query Synopsis
const generateSynopsis = async () => {
  isLoading.value = true
  outputTitle.value = '1-Page Industry Query Synopsis'
  output.value = 'Distilling causal plot spine and character dilemmas through local Llama...'

  try {
    const res = await fetch(`${API_BASE}/api/publishing/synopsis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: activeBookId.value })
    })
    if (!res.ok) throw new Error('Synopsis compilation failed')
    const data = await res.json()
    output.value = (data.ai_generated ? '[AI-generated from your scene summaries]\n\n' : '') + data.synopsis
  } catch(e) { 
    output.value = 'Error generating industry query synopsis.'
    showToast(e.message, 'error') 
  } finally {
    isLoading.value = false
  }
}
</script>