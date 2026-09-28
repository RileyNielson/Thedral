<template>
  <div 
    v-if="store.modals.career" 
    class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none" 
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-xl w-full p-6 space-y-6 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
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

      <!-- Action Card Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 shrink-0">
        
        <!-- Tool 1: Audiobook Pack -->
        <div class="p-4 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-zinc-700 transition">
          <div>
            <div class="text-xs font-bold text-amber-400 flex items-center gap-1.5 font-mono">
              <Mic class="w-4 h-4" /> Audiobook Pack
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              Pronunciation guide & character acting registers.
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

        <!-- Tool 2: Authorship Certificate -->
        <div class="p-4 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-zinc-700 transition">
          <div>
            <div class="text-xs font-bold text-emerald-400 flex items-center gap-1.5 font-mono">
              <ShieldCheck class="w-4 h-4" /> Authorship Proof
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              Cryptographic audit trail proving organic human drafting.
            </p>
          </div>
          <button 
            @click="fetchAuthorshipProof" 
            :disabled="isLoading"
            class="w-full py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 font-medium rounded text-xs text-white transition border border-zinc-700/50"
          >
            View Certificate
          </button>
        </div>

        <!-- Tool 3: Query Synopsis -->
        <div class="p-4 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2 flex flex-col justify-between hover:border-zinc-700 transition">
          <div>
            <div class="text-xs font-bold text-cyan-400 flex items-center gap-1.5 font-mono">
              <FileText class="w-4 h-4" /> Query Synopsis
            </div>
            <p class="text-[10px] text-zinc-500 mt-1 leading-snug">
              1-page causal agent pitch with full ending reveal.
            </p>
          </div>
          <button 
            @click="generateSynopsis" 
            :disabled="isLoading"
            class="w-full py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 font-medium rounded text-xs text-white transition border border-zinc-700/50"
          >
            {{ isLoading ? 'Compiling...' : 'Generate' }}
          </button>
        </div>

      </div>

      <!-- Output Dossier View -->
      <div v-if="output" class="space-y-2 flex-1 overflow-hidden flex flex-col">
        <div class="flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>{{ outputTitle }}</span>
          <button 
            @click="copyOutput" 
            class="text-amber-400 hover:underline flex items-center gap-1"
          >
            <Copy class="w-3 h-3" /> {{ copied ? 'Copied!' : 'Copy Text' }}
          </button>
        </div>

        <div class="p-3.5 bg-zinc-950 rounded-xl border border-zinc-800 text-xs font-mono text-zinc-300 overflow-y-auto whitespace-pre-line select-text flex-1 custom-scrollbar leading-relaxed">
          {{ output }}
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, showToast } from '../../store.js'
import { Award, X, Mic, ShieldCheck, FileText, Copy } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

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