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
        
        <!-- Tool 1: Reader Genome (Macro Audience DNA) -->
        <div class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-purple-500/50 transition group">
          <div>
            <div class="text-xs font-bold text-purple-400 flex items-center gap-1.5 font-mono">
              <Dna class="w-4 h-4" /> Reader Genome
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              Macro neurochemical DNA & literary author comps.
            </p>
          </div>
          <button 
            @click="fetchReaderGenome" 
            :disabled="isLoading"
            class="w-full py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 disabled:opacity-50 font-medium rounded text-xs transition shadow-sm"
          >
            {{ isLoading && outputTitle.includes('Genome') ? 'Analyzing...' : 'Analyze DNA' }}
          </button>
        </div>

        <!-- Tool 2: Authorship Certificate -->
        <div class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-emerald-500/50 transition group">
          <div>
            <div class="text-xs font-bold text-emerald-400 flex items-center gap-1.5 font-mono">
              <ShieldCheck class="w-4 h-4" /> Authorship Proof
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              SHA-256 certificate proving organic human drafting.
            </p>
          </div>
          <button 
            @click="fetchAuthorshipProof" 
            :disabled="isLoading"
            class="w-full py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 font-medium rounded text-xs text-white transition border border-zinc-700/50"
          >
            {{ isLoading && outputTitle.includes('Authenticity') ? 'Verifying...' : 'Certificate' }}
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
            {{ isLoading && outputTitle.includes('Synopsis') ? 'Compiling...' : 'Generate' }}
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
import { Award, X, Mic, ShieldCheck, FileText, Copy, Dna } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

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

// 1. Full Manuscript Reader Genome & Market Comps
const fetchReaderGenome = async () => {
  isLoading.value = true
  outputTitle.value = 'Full-Manuscript Reader Genome & Market Comps'
  output.value = 'Running 4-channel neuro-spectrometry across all scenes in manuscript...'

  try {
    const res = await fetch(`${API_BASE}/api/publishing/genome?book_id=${activeBookId.value}`)
    if (!res.ok) throw new Error('Genome calculation failed')
    const data = await res.json()

    let report = `🧬 FULL MANUSCRIPT READER GENOME (${data.total_words.toLocaleString()} words)\n`
    report += `=================================================================\n\n`
    report += `NEUROCHEMICAL COMPOSITION OF YOUR PROSE:\n`
    report += `• 🔴 Adrenaline (Kinetic Survival):     ${data.spectrum.adrenaline}%\n`
    report += `• 🟣 Oxytocin (Relational Intimacy):    ${data.spectrum.oxytocin}%\n`
    report += `• 🔵 Dopamine (Deductive Mystery):      ${data.spectrum.dopamine}%\n`
    report += `• 🟢 Serotonin (Aesthetic Immersion):   ${data.spectrum.serotonin}%\n\n`
    report += `AUDIENCE PSYCHOLOGICAL DIAGNOSIS:\n`
    report += `↳ ${data.spectrum.hunger_alert}\n\n`
    report += `TOP 3 LITERARY COMPS (CALCULATED BY PROSE DNA):\n`
    for (const c of data.comps) {
      report += `★ ${c.author} (${c.match_pct}% Match)\n  "${c.description}"\n\n`
    }

    output.value = report
  } catch(e) {
    output.value = 'Error analyzing reader genome.'
    showToast(e.message, 'error')
  } finally {
    isLoading.value = false
  }
}

// 2. Cryptographic Authorship Proof
const fetchAuthorshipProof = async () => {
  isLoading.value = true
  outputTitle.value = 'Cryptographic Authenticity Certificate'
  output.value = 'Calculating thermodynamic entropy and revision velocity from SQLite ledger...'
  
  try {
    const res = await fetch(`${API_BASE}/api/publishing/authorship-proof?book_id=${activeBookId.value}`)
    if (!res.ok) throw new Error('Proof generation failed')
    const data = await res.json()
    output.value = data.certificate_text
  } catch(e) { 
    output.value = 'Error generating authorship proof certificate.'
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
    output.value = data.synopsis
  } catch(e) { 
    output.value = 'Error generating industry query synopsis.'
    showToast(e.message, 'error') 
  } finally {
    isLoading.value = false
  }
}
</script>