<template>
  <div 
    v-if="store.modals.lore" 
    class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none" 
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
      <!-- Modal Header & Audit Action -->
      <div class="flex items-center justify-between border-b border-zinc-800 pb-3 shrink-0">
        <div class="flex items-center gap-4">
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <BookOpenCheck class="w-5 h-5 text-amber-500" /> Living Style Sheet & Canon Rules
          </h3>
          <button 
            @click="auditSceneLore" 
            :disabled="isAuditingLore || !store.activeNode?.content" 
            class="px-3 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg text-[10px] font-bold uppercase transition disabled:opacity-50 flex items-center gap-1.5"
            title="Scan scene for spelling drift against established canon"
          >
            <ShieldCheck class="w-3.5 h-3.5" />
            <span>{{ isAuditingLore ? 'Scanning...' : 'Audit Spelling Drift' }}</span>
          </button>
        </div>
        <button @click="closeModal" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Lore Contradiction & Drift Alert Box with 1-Click Fix -->
      <div 
        v-if="loreDiscrepancies.length" 
        class="bg-amber-950/20 border border-amber-800/50 rounded-xl p-3 shrink-0 space-y-2 max-h-48 overflow-y-auto custom-scrollbar"
      >
        <div class="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between font-mono">
          <span class="flex items-center gap-1.5">
            <AlertCircle class="w-3.5 h-3.5 text-amber-500" /> Canon Spelling Drift Detected ({{ loreDiscrepancies.length }})
          </span>
          <span class="text-zinc-500 text-[9px]">Levenshtein String Verification</span>
        </div>

        <div 
          v-for="(disc, i) in loreDiscrepancies" 
          :key="i" 
          class="p-2.5 bg-zinc-950 rounded border border-amber-900/40 text-xs space-y-2"
        >
          <div class="flex items-center justify-between">
            <div class="font-bold text-zinc-200 font-mono text-[11px]">
              Found: <span class="text-rose-400">"{{ disc.violation }}"</span> ➔ Canon: <span class="text-emerald-400">"{{ disc.rule_broken }}"</span>
            </div>
            <button 
              @click="batchReplaceCanon(disc.violation, disc.rule_broken)"
              class="px-2 py-0.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-mono text-[10px] transition flex items-center gap-1 shadow"
              title="Replace this misspelled term across the entire book"
            >
              <Wand2 class="w-3 h-3" /> Fix Across Manuscript
            </button>
          </div>
          <div class="text-zinc-400 text-[10px] leading-snug">{{ disc.explanation }}</div>
        </div>
      </div>

      <!-- Main Workspace: Form & Directory -->
      <div class="flex gap-4 h-full overflow-hidden">
        
        <!-- Left: Rule Definition Form -->
        <div class="w-1/3 border-r border-zinc-800 pr-4 space-y-3 shrink-0 overflow-y-auto custom-scrollbar">
          <div class="text-xs font-bold text-amber-400 font-mono uppercase text-[10px] tracking-wider mb-2">
            Establish Rule
          </div>

          <input 
            v-model="newLore.term" 
            placeholder="Term (e.g. Aethelgard)" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition" 
          />

          <select 
            v-model="newLore.category" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-300 text-xs focus:outline-none"
          >
            <option value="LORE">World Lore</option>
            <option value="SPELLING">Spelling & Orthography</option>
            <option value="MAGIC">Magic / Technology Rule</option>
          </select>

          <input 
            v-model="newLore.pronunciation" 
            placeholder="Pronunciation (Optional)" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition font-mono" 
          />

          <textarea 
            v-model="newLore.rule_definition" 
            rows="4" 
            placeholder="Define universal law or spelling standard..." 
            class="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition resize-none"
          ></textarea>

          <button 
            @click="saveRule" 
            :disabled="!newLore.term || !newLore.rule_definition"
            class="w-full py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-xs transition shadow"
          >
            Save Canon Rule
          </button>
        </div>

        <!-- Right: Living Rules Directory -->
        <div class="flex-1 overflow-y-auto space-y-2.5 pl-2 custom-scrollbar">
          <div 
            v-for="rule in store.loreRules" 
            :key="rule.term" 
            class="p-3 bg-zinc-950 border border-zinc-800/80 rounded-xl relative group hover:border-zinc-700 transition"
          >
            <button 
              @click="deleteRule(rule.term)" 
              title="Delete Rule"
              class="absolute top-2.5 right-2.5 text-zinc-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition p-0.5"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>

            <div class="flex items-baseline gap-2 mb-1">
              <span class="font-bold text-amber-400 text-sm font-serif">{{ rule.term }}</span>
              <span v-if="rule.pronunciation" class="text-[10px] text-zinc-500 font-mono">
                /{{ rule.pronunciation }}/
              </span>
              <span class="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[9px] uppercase font-bold font-mono">
                {{ rule.category }}
              </span>
            </div>

            <p class="text-xs text-zinc-300 leading-snug">{{ rule.rule_definition }}</p>
          </div>

          <div v-if="!store.loreRules?.length" class="text-center py-12 text-xs text-zinc-500 italic">
            No canon rules established yet. Define universal spellings or lore on the left.
          </div>
        </div>

      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { BookOpenCheck, X, Trash2, ShieldCheck, AlertCircle, Wand2 } from '@lucide/vue'

import { API_BASE } from '@/api'

const newLore = ref({
  term: '',
  category: 'LORE',
  rule_definition: '',
  pronunciation: ''
})

const isAuditingLore = ref(false)
const loreDiscrepancies = ref([])

const closeModal = () => {
  store.toggleModal('lore', false)
  loreDiscrepancies.value = []
}

const fetchLore = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/lore`)
    if (!res.ok) throw new Error('Failed to load style sheet')
    store.loreRules = await res.json()
  } catch(e) { 
    store.loreRules = [] 
  }
}

const saveRule = async () => {
  if (!newLore.value.term.trim() || !newLore.value.rule_definition.trim()) return

  try {
    const res = await fetch(`${API_BASE}/api/lore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newLore.value)
    })
    if (!res.ok) throw new Error('Failed to persist rule')
    newLore.value = { term: '', category: 'LORE', rule_definition: '', pronunciation: '' }
    await fetchLore()
    showToast('Canon rule committed to style sheet.', 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}

const deleteRule = async (term) => {
  try {
    const res = await fetch(`${API_BASE}/api/lore/${encodeURIComponent(term)}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Deletion failed')
    await fetchLore()
  } catch(e) {
    showToast('Failed to delete rule', 'error')
  }
}

const auditSceneLore = async () => {
  if (!store.activeNode?.content) return
  isAuditingLore.value = true
  loreDiscrepancies.value = []
  try {
    const res = await fetch(`${API_BASE}/api/lore/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_text: store.activeNode.content })
    })
    if (!res.ok) throw new Error('Audit engine failure')
    const data = await res.json()
    loreDiscrepancies.value = data.discrepancies || []
    if (loreDiscrepancies.value.length === 0) {
      showToast('All words in scene match canonical style sheet.', 'info')
    }
  } catch(e) {
    showToast(e.message, 'error')
  } finally {
    isAuditingLore.value = false
  }
}

const batchReplaceCanon = async (searchTerm, replaceTerm) => {
  if (!window.confirm(`Replace all occurrences of "${searchTerm}" with "${replaceTerm}" across the entire book?\n\nSnapshots will be archived in the Revision Vault.`)) return

  try {
    const res = await fetch(`${API_BASE}/api/lore/batch-replace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        search_term: searchTerm,
        replace_term: replaceTerm,
        book_id: store.activeBookId || null
      })
    })
    if (!res.ok) throw new Error('Batch replacement failed')
    const data = await res.json()
    showToast(`Replaced ${data.occurrences_replaced} occurrence(s) across ${data.scenes_modified} scene(s).`, 'success')
    
    // Refresh editor if active scene was modified
    if (store.activeNode?.id) {
      await store.loadScene(store.activeNode.id)
    }
    // Remove fixed discrepancy from list
    loreDiscrepancies.value = loreDiscrepancies.value.filter(d => d.violation !== searchTerm)
  } catch(e) {
    showToast(e.message, 'error')
  }
}

watch(() => store.modals.lore, (newVal) => { 
  if (newVal) fetchLore() 
})
</script>
