<template>
  <div 
    class="fixed inset-0 bg-black/65 backdrop-blur-sm flex items-start justify-center z-[100] p-4 pt-[15vh] select-none"
    @click.self="closeOmnibar"
  >
    <div class="bg-zinc-900 border border-zinc-700/80 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col animate-fade-in">
      
      <!-- Input Header -->
      <div class="flex items-center px-4 py-3.5 border-b border-zinc-800 bg-zinc-950">
        <Search class="w-5 h-5 text-amber-500 mr-3 shrink-0" />
        <input 
          ref="omnibarInput" 
          v-model="query" 
          @input="runSearch" 
          @keydown.down.prevent="navigateResults(1)"
          @keydown.up.prevent="navigateResults(-1)"
          @keydown.enter.prevent="selectCurrentResult"
          @keydown.esc="closeOmnibar"
          class="flex-1 bg-transparent text-lg text-white focus:outline-none placeholder-zinc-500 font-serif" 
          placeholder="Search manuscript, or end with '?' to ask the Librarian..." 
        />
        <span v-if="isLoading" class="text-xs font-mono text-amber-400 animate-pulse ml-2">Searching...</span>
      </div>
      
      <!-- Librarian Socratic Answer Panel -->
      <div v-if="answer" class="p-4 bg-zinc-950/80 border-b border-zinc-800">
        <div class="flex items-start gap-3">
          <BrainCircuit class="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div class="space-y-1">
            <div class="text-[10px] font-bold text-amber-400 uppercase tracking-wider font-mono">The Librarian Says:</div>
            <div class="text-sm text-zinc-200 font-serif leading-relaxed select-text" v-html="answer"></div>
          </div>
        </div>
      </div>
      
      <!-- Results List -->
      <div v-if="results.length" class="max-h-96 overflow-y-auto p-2 space-y-1 custom-scrollbar">
        <div 
          v-for="(res, i) in results" 
          :key="i" 
          @click="handleClick(res)"
          @mouseenter="selectedIndex = i"
          :class="[
            'p-3 rounded-xl cursor-pointer transition border flex items-start gap-3',
            selectedIndex === i 
              ? 'bg-zinc-800 border-amber-500/40 shadow-sm' 
              : 'bg-zinc-900 hover:bg-zinc-800 border-transparent hover:border-zinc-700/50'
          ]"
        >
          <div class="mt-0.5 shrink-0">
            <User v-if="res.type === 'CHARACTER'" class="w-4 h-4 text-amber-400" />
            <Key v-else-if="res.type === 'ITEM'" class="w-4 h-4 text-cyan-400" />
            <BookOpenCheck v-else-if="res.type === 'LORE'" class="w-4 h-4 text-emerald-400" />
            <FileText v-else class="w-4 h-4 text-zinc-400" />
          </div>

          <div class="flex-1 min-w-0">
            <div class="text-sm font-bold text-zinc-200 flex items-center justify-between">
              <span class="truncate">{{ res.title }}</span>
              <span v-if="res.subtitle" class="text-[9px] text-zinc-500 font-mono ml-2 uppercase px-1.5 py-0.2 rounded bg-zinc-800/80 shrink-0">
                {{ res.subtitle }}
              </span>
            </div>
            <div class="text-xs text-zinc-400 font-serif mt-1 line-clamp-2 select-text" v-html="res.preview"></div>
          </div>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-else-if="query && !isLoading" class="p-8 text-center text-sm text-zinc-500 italic font-serif">
        No passages, lore rules, or cast members found matching "{{ query }}".
      </div>

      <!-- Footer Help Tray -->
      <div class="px-4 py-2 bg-zinc-950 border-t border-zinc-800 text-[10px] text-zinc-500 flex justify-between font-mono">
        <span>Use <kbd class="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">↑</kbd> <kbd class="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">↓</kbd> to navigate, <kbd class="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">Enter</kbd> to jump.</span>
        <span>Press <kbd class="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">Esc</kbd> to return.</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { store, showToast } from '../../store.js'
import { Search, BrainCircuit, User, BookOpenCheck, FileText, Key } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const query = ref('')
const results = ref([])
const answer = ref('')
const omnibarInput = ref(null)
const selectedIndex = ref(0)
const isLoading = ref(false)

const closeOmnibar = () => {
  store.toggleModal('omnibar', false)
}

const runSearch = async () => {
  const q = query.value.trim()
  selectedIndex.value = 0

  if (q.length < 2) { 
    results.value = []
    answer.value = ''
    return 
  }

  // Ask Librarian Q&A mode
  if (q.endsWith('?')) {
    answer.value = 'Consulting manuscript archives and causal lore...'
    isLoading.value = true
    try {
      const res = await fetch(`${API_BASE}/api/ask`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ question: q }) 
      })
      if (!res.ok) throw new Error('Librarian endpoint failed')
      const data = await res.json()
      answer.value = data.answer
    } catch(e) { 
      answer.value = 'The Librarian is unreachable at this moment.' 
    } finally {
      isLoading.value = false
    }
    return
  } else { 
    answer.value = '' 
  }
  
  isLoading.value = true
  const combined = []

  try {
    // 1. Scene Text Search
    const sceneRes = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(q)}`)
    if (sceneRes.ok) {
      const sceneData = await sceneRes.json()
      sceneData.forEach(d => combined.push({ 
        type: 'SCENE', 
        title: d.title, 
        subtitle: d.node_type || 'Scene', 
        preview: d.snippet, 
        id: d.node_id 
      }))
    }
  } catch(e) {}

  try {
    // 2. Cast & Artifacts Search
    const entityRes = await fetch(`${API_BASE}/api/entities`)
    if (entityRes.ok) {
      const entities = await entityRes.json()
      entities
        .filter(e => 
          e.name.toLowerCase().includes(q.toLowerCase()) || 
          (e.aliases && e.aliases.toLowerCase().includes(q.toLowerCase()))
        )
        .forEach(e => combined.push({ 
          type: e.entity_type, 
          title: e.name, 
          subtitle: e.role || e.entity_type, 
          preview: `Aliases: ${e.aliases || 'None'} • Status: ${e.status || 'Active'}`, 
          id: null 
        }))
    }
  } catch(e) {}

  // 3. Living Lore Rules Search (from Store Cache)
  if (store.loreRules && store.loreRules.length) {
    const rules = store.loreRules.filter(r => 
      r.term.toLowerCase().includes(q.toLowerCase()) || 
      (r.rule_definition && r.rule_definition.toLowerCase().includes(q.toLowerCase()))
    )
    rules.forEach(r => combined.push({ 
      type: 'LORE', 
      title: r.term, 
      subtitle: r.category || 'World Rule', 
      preview: r.rule_definition, 
      id: null 
    }))
  }

  results.value = combined
  isLoading.value = false
}

const navigateResults = (direction) => {
  if (!results.value.length) return
  selectedIndex.value = (selectedIndex.value + direction + results.value.length) % results.value.length
}

const selectCurrentResult = () => {
  if (results.value.length && results.value[selectedIndex.value]) {
    handleClick(results.value[selectedIndex.value])
  }
}

const handleClick = async (res) => {
  if (res.type === 'SCENE' && res.id) {
    await store.loadScene(res.id)
    store.viewMode = 'editor'
  } else if (res.type === 'CHARACTER' || res.type === 'ITEM') {
    store.toggleModal('cast', true)
  } else if (res.type === 'LORE') {
    store.toggleModal('lore', true)
  }
  closeOmnibar()
}

onMounted(() => {
  nextTick(() => { 
    if (omnibarInput.value) omnibarInput.value.focus() 
  })
})
</script>