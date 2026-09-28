<template>
  <div 
    class="flex-1 overflow-y-auto p-6 md:p-10 custom-scrollbar select-none transition-colors"
    :class="store.isCandlelight ? 'bg-[#0e0c0a] text-amber-100/90' : 'bg-zinc-950 text-zinc-100'"
  >
    <div class="max-w-7xl mx-auto space-y-8">
      
      <!-- Top Bar: Filter & Actions -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4" :class="store.isCandlelight ? 'border-amber-900/40' : 'border-zinc-800'">
        <div>
          <h2 class="text-2xl font-bold font-serif flex items-center gap-2.5" :class="store.isCandlelight ? 'text-amber-300' : 'text-zinc-100'">
            <LayoutGrid class="w-6 h-6 text-amber-500 shrink-0" /> Corkboard Index Cards
          </h2>
          <p class="text-xs text-zinc-500 font-mono mt-0.5">
            {{ totalSceneCount }} scene beats across {{ chapters.length }} chapters
          </p>
        </div>

        <div class="flex items-center space-x-3">
          <!-- Chapter Filter -->
          <div class="flex items-center gap-2 text-xs font-mono">
            <span class="text-zinc-500 hidden md:inline">Chapter:</span>
            <select 
              v-model="selectedChapterId" 
              class="bg-zinc-900 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-amber-500/50"
            >
              <option value="ALL">All Chapters</option>
              <option v-for="ch in chapters" :key="ch.id" :value="ch.id">
                {{ ch.title }}
              </option>
            </select>
          </div>

          <button 
            @click="store.viewMode = 'editor'" 
            class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs font-mono transition flex items-center gap-1.5 border border-zinc-700/50"
          >
            <PenTool class="w-3.5 h-3.5 text-amber-500" /> Write
          </button>
        </div>
      </div>

      <!-- Empty Board Fallback -->
      <div v-if="!cards.length" class="text-center py-20 text-zinc-600 font-serif space-y-2">
        <p class="text-base">No scene index cards match this filter.</p>
        <button 
          v-if="chapters.length" 
          @click="addNewBeat(chapters[0].id)" 
          class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-zinc-950 font-bold rounded-lg text-xs font-mono transition shadow"
        >
          Create First Beat Card
        </button>
      </div>

      <!-- Index Cards Responsive Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-6">
        <div 
          v-for="card in cards" 
          :key="card.id" 
          @click="openScene(card.id)"
          :class="[
            'border rounded-xl p-5 cursor-pointer transition-all shadow-xl flex flex-col justify-between h-64 group relative overflow-hidden',
            store.activeNode?.id === card.id 
              ? 'border-amber-500/80 bg-zinc-900 shadow-[0_0_15px_rgba(245,158,11,0.15)] ring-1 ring-amber-500/40' 
              : store.isCandlelight 
                ? 'bg-[#16120e] border-amber-900/30 hover:border-amber-500/50' 
                : 'bg-zinc-900/80 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900'
          ]"
        >
          <!-- Top Card Meta -->
          <div class="space-y-2">
            <div class="flex items-center justify-between text-xs text-zinc-500 font-mono">
              <span class="truncate max-w-[150px]">{{ card.chapterTitle }}</span>
              <span 
                :class="[
                  'px-2 py-0.5 rounded text-[9px] font-bold font-mono tracking-wider uppercase',
                  card.status === 'FINAL' 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                    : card.status === 'REVISED' 
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                      : 'bg-zinc-800 text-zinc-400'
                ]"
              >
                {{ card.status || 'DRAFT' }}
              </span>
            </div>

            <!-- Scene Title -->
            <h3 class="text-sm font-bold font-serif text-zinc-100 group-hover:text-amber-400 transition line-clamp-1">
              {{ card.title }}
            </h3>

            <!-- Synopsis Preview -->
            <p class="text-xs text-zinc-400 font-serif leading-relaxed line-clamp-4 select-none">
              {{ card.synopsis || 'No beat synopsis recorded for this scene. Click to begin drafting.' }}
            </p>
          </div>

          <!-- Bottom Card Footer -->
          <div class="text-[11px] text-zinc-500 font-mono border-t pt-2 flex items-center justify-between" :class="store.isCandlelight ? 'border-amber-900/30' : 'border-zinc-800/80'">
            <span>{{ card.word_count || 0 }} words</span>
            <span class="text-amber-500/90 group-hover:text-amber-400 transition flex items-center gap-1">
              Draft <ArrowRight class="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </div>
        </div>

        <!-- Add New Beat Card Slot -->
        <div 
          v-if="chapters.length"
          @click="addNewBeat(selectedChapterId === 'ALL' ? chapters[0].id : selectedChapterId)"
          class="border border-dashed rounded-xl p-5 cursor-pointer transition flex flex-col items-center justify-center h-64 text-zinc-600 hover:text-amber-400 hover:border-amber-500/40 hover:bg-zinc-900/30 group"
          :class="store.isCandlelight ? 'border-amber-900/30' : 'border-zinc-800'"
        >
          <div class="w-10 h-10 rounded-full bg-zinc-800/50 group-hover:bg-amber-500/10 flex items-center justify-center mb-2 transition">
            <Plus class="w-5 h-5 text-zinc-500 group-hover:text-amber-400 transition" />
          </div>
          <span class="text-xs font-mono font-medium">Add Scene Beat</span>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, showToast } from '../store.js'
import { LayoutGrid, PenTool, ArrowRight, Plus } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const selectedChapterId = ref('ALL')

// Flatten chapters from all books in tree
const chapters = computed(() => {
  const chList = []
  for (const book of store.tree || []) {
    for (const ch of book.children || []) {
      chList.push(ch)
    }
  }
  return chList
})

// Flatten scene cards matching chapter filter
const cards = computed(() => {
  const result = []
  for (const book of store.tree || []) {
    for (const ch of book.children || []) {
      if (selectedChapterId.value !== 'ALL' && ch.id !== selectedChapterId.value) {
        continue
      }
      for (const sc of ch.children || []) {
        result.push({
          ...sc,
          chapterTitle: ch.title,
          chapterId: ch.id
        })
      }
    }
  }
  return result
})

const totalSceneCount = computed(() => {
  let count = 0
  for (const book of store.tree || []) {
    for (const ch of book.children || []) {
      count += (ch.children || []).length
    }
  }
  return count
})

const openScene = async (sceneId) => {
  await store.loadScene(sceneId)
  store.viewMode = 'editor'
}

const addNewBeat = async (targetChapterId) => {
  if (!targetChapterId) return
  try {
    const res = await fetch(`${API_BASE}/api/node`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        parent_id: targetChapterId,
        node_type: 'SCENE',
        title: 'New Scene Beat'
      })
    })
    if (!res.ok) throw new Error('Scene creation failed')
    const data = await res.json()
    await store.fetchTree()
    await openScene(data.id)
    showToast(`Created "${data.title}"`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}
</script>