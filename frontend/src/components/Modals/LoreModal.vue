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
            <BookOpenCheck class="w-5 h-5 text-amber-500" /> Living Style Sheet & Lore
          </h3>
          <button 
            @click="auditSceneLore" 
            :disabled="isAuditingLore || !store.activeNode?.content" 
            class="px-3 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg text-[10px] font-bold uppercase transition disabled:opacity-50 flex items-center gap-1.5"
            title="Scan active scene for lore contradictions"
          >
            <ShieldAlert class="w-3.5 h-3.5" />
            <span>{{ isAuditingLore ? 'Auditing...' : 'Audit Scene' }}</span>
          </button>
        </div>
        <button @click="closeModal" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Lore Contradiction Alert Box -->
      <div 
        v-if="loreDiscrepancies.length" 
        class="bg-rose-950/40 border border-rose-900/50 rounded-xl p-3 shrink-0 space-y-2 max-h-40 overflow-y-auto custom-scrollbar"
      >
        <div class="text-[10px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5 font-mono">
          <AlertCircle class="w-3.5 h-3.5" /> Lore Contradictions Detected ({{ loreDiscrepancies.length }})
        </div>
        <div 
          v-for="(disc, i) in loreDiscrepancies" 
          :key="i" 
          class="p-2.5 bg-zinc-950 rounded border border-rose-900/40 text-xs space-y-1"
        >
          <div class="font-bold text-rose-300 font-mono text-[11px]">Rule Broken: {{ disc.rule_broken }}</div>
          <div class="text-zinc-400 italic line-clamp-2 font-serif">"{{ disc.violation }}"</div>
          <div class="text-zinc-300 leading-snug">{{ disc.explanation }}</div>
        </div>
      </div>

      <!-- Main Workspace: Form & Directory -->
      <div class="flex gap-4 h-full overflow-hidden">
        
        <!-- Left: Rule Definition Form -->
        <div class="w-1/3 border-r border-zinc-800 pr-4 space-y-3 shrink-0 overflow-y-auto custom-scrollbar">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-amber-400 font-mono uppercase text-[10px] tracking-wider">Establish Rule</span>
            <button 
              @click="extractLoreFromScene" 
              :disabled="isExtractingLore || !store.activeNode?.content" 
              class="px-2 py-0.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 rounded border border-amber-500/30 text-[9px] font-bold uppercase transition disabled:opacity-50 flex items-center gap-1"
              title="Extract terms from active scene draft"
            >
              <Sparkles class="w-3 h-3" />
              <span>{{ isExtractingLore ? 'Scanning...' : 'Extract' }}</span>
            </button>
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
            <option value="MAGIC">Magic / Physics Rule</option>
          </select>

          <input 
            v-model="newLore.pronunciation" 
            placeholder="Pronunciation (Optional)" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition font-mono" 
          />

          <textarea 
            v-model="newLore.rule_definition" 
            rows="4" 
            placeholder="Define universal law or fact..." 
            class="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition resize-none"
          ></textarea>

          <button 
            @click="saveRule" 
            :disabled="!newLore.term || !newLore.rule_definition"
            class="w-full py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-xs transition shadow"
          >
            Save Rule
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
              <span class="font-bold text-amber-400 text-sm">{{ rule.term }}</span>
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
            No lore rules established. Define canon on the left or extract from your scene.
          </div>
        </div>

      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { BookOpenCheck, X, Trash2, ShieldAlert, AlertCircle, Sparkles } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const newLore = ref({
  term: '',
  category: 'LORE',
  rule_definition: '',
  pronunciation: ''
})

const isExtractingLore = ref(false)
const isAuditingLore = ref(false)
const loreDiscrepancies = ref([])

const closeModal = () => {
  store.toggleModal('lore', false)
}

const fetchLore = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/lore`)
    if (!res.ok) throw new Error('Failed to load lore')
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
    showToast('World law committed to canon.', 'info')
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

const extractLoreFromScene = async () => {
  if (!store.activeNode?.content) return
  isExtractingLore.value = true
  try {
    const res = await fetch(`${API_BASE}/api/lore/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_text: store.activeNode.content })
    })
    if (!res.ok) throw new Error('Lore extraction failed')
    const data = await res.json()
    if (data.proposed_lore && data.proposed_lore.length > 0) {
      const suggestion = data.proposed_lore[0]
      newLore.value = {
        term: suggestion.term,
        category: suggestion.category || 'LORE',
        rule_definition: suggestion.rule_definition,
        pronunciation: suggestion.pronunciation || ''
      }
      showToast(`Suggested: "${suggestion.term}"`, 'info')
    } else {
      showToast('No new entities or laws detected in this scene.', 'info')
    }
  } catch(e) {
    showToast(e.message, 'error')
  } finally {
    isExtractingLore.value = false
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
      showToast('Lore audit clean! No contradictions found.', 'info')
    }
  } catch(e) {
    showToast(e.message, 'error')
  } finally {
    isAuditingLore.value = false
  }
}

watch(() => store.modals.lore, (newVal) => { 
  if (newVal) fetchLore() 
})
</script>