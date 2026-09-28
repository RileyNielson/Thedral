<template>
  <div 
    class="flex-1 overflow-y-auto p-6 md:p-12 custom-scrollbar transition-colors select-none"
    :class="store.isCandlelight ? 'bg-[#0e0c0a] text-amber-100/90' : 'bg-zinc-950 text-zinc-100'"
  >
    <div class="max-w-4xl mx-auto space-y-10">
      
      <!-- Outline Header -->
      <div class="flex items-center justify-between border-b pb-4" :class="store.isCandlelight ? 'border-amber-900/40' : 'border-zinc-800'">
        <div>
          <h2 class="text-2xl md:text-3xl font-bold font-serif flex items-center gap-3" :class="store.isCandlelight ? 'text-amber-300' : 'text-zinc-100'">
            <ListTree class="w-7 h-7 text-amber-500 shrink-0" /> The Living Outline
          </h2>
          <p class="text-xs text-zinc-500 font-mono mt-1">
            Macro dramatic architecture • Live beat synopses
          </p>
        </div>

        <div class="flex items-center gap-3">
          <span v-if="saveNote" class="text-xs font-mono text-amber-400/90 animate-pulse">
            {{ saveNote }}
          </span>
          <button 
            @click="store.viewMode = 'editor'" 
            class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs font-mono transition flex items-center gap-1.5"
          >
            <PenTool class="w-3.5 h-3.5 text-amber-500" /> Return to Editor
          </button>
        </div>
      </div>

      <!-- Empty Hierarchy State -->
      <div v-if="!store.tree?.length" class="text-center py-20 text-zinc-600 space-y-3 font-serif">
        <BookOpen class="w-10 h-10 mx-auto text-zinc-800" />
        <p class="text-sm">No chapters or scenes found to outline.</p>
      </div>

      <!-- Outline Tree Hierarchy -->
      <div class="space-y-12">
        <template v-for="book in store.tree" :key="book.id">
          
          <!-- Book / Volume Section -->
          <div class="space-y-8">
            <div class="flex items-center gap-2 border-b pb-2" :class="store.isCandlelight ? 'border-amber-900/50' : 'border-zinc-800/80'">
              <BookOpen class="w-4 h-4 text-amber-500" />
              <h3 class="text-base font-bold uppercase tracking-wider font-mono text-zinc-300">
                {{ book.title }}
              </h3>
            </div>

            <!-- Chapters -->
            <div 
              v-for="ch in book.children" 
              :key="ch.id" 
              class="space-y-4 rounded-xl p-5 border transition-all"
              :class="store.isCandlelight ? 'bg-[#15110d] border-amber-900/30' : 'bg-zinc-900/40 border-zinc-800/80'"
            >
              <div class="flex items-center justify-between border-b pb-2" :class="store.isCandlelight ? 'border-amber-900/30' : 'border-zinc-800/60'">
                <div class="flex items-center gap-2 font-serif text-lg font-bold text-amber-400">
                  <Folder class="w-4 h-4 text-zinc-500" />
                  <span>{{ ch.title }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <button 
                    @click="addSceneToChapter(ch.id)" 
                    class="px-2 py-1 bg-zinc-800/60 hover:bg-zinc-700 text-zinc-400 hover:text-white rounded text-[11px] font-mono flex items-center gap-1 transition"
                  >
                    <Plus class="w-3 h-3" /> Add Scene
                  </button>
                </div>
              </div>

              <!-- Scenes Container -->
              <div class="pl-2 md:pl-4 space-y-4 border-l-2" :class="store.isCandlelight ? 'border-amber-900/30' : 'border-zinc-800/50'">
                <div 
                  v-for="sc in ch.children" 
                  :key="sc.id" 
                  class="space-y-1.5 p-3 rounded-lg hover:bg-zinc-800/30 transition group"
                >
                  <div class="flex items-center justify-between">
                    <h4 
                      @click="openScene(sc.id)" 
                      class="text-sm font-semibold cursor-pointer hover:text-amber-400 transition flex items-center gap-2"
                      :class="store.activeNode?.id === sc.id ? 'text-amber-300' : 'text-zinc-200'"
                    >
                      <FileText class="w-3.5 h-3.5 text-zinc-500 group-hover:text-amber-400 transition" />
                      <span>{{ sc.title }}</span>
                      <ExternalLink class="w-3 h-3 opacity-0 group-hover:opacity-100 transition text-zinc-500" />
                    </h4>
                    
                    <span class="text-[10px] font-mono text-zinc-500">
                      {{ sc.word_count || 0 }}w
                    </span>
                  </div>

                  <!-- Editable Scene Beat Synopsis -->
                  <textarea 
                    v-model="sc.synopsis" 
                    @input="queueSaveSynopsis(sc)" 
                    rows="2" 
                    class="w-full bg-zinc-950/70 border border-zinc-800/80 rounded-lg p-2.5 text-xs text-zinc-300 focus:border-amber-500/50 resize-none transition outline-none font-serif leading-relaxed" 
                    placeholder="Describe the central dramatic conflict or causal shift in this beat..."
                  ></textarea>
                </div>
              </div>

            </div>
          </div>

        </template>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { store, showToast } from '../store.js'
import { ListTree, PenTool, BookOpen, Folder, Plus, FileText, ExternalLink } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const saveNote = ref('')
let saveTimer = null

const openScene = async (sceneId) => {
  await store.loadScene(sceneId)
  store.viewMode = 'editor'
}

const queueSaveSynopsis = (scene) => {
  saveNote.value = 'Saving beat synopsis...'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/node/${scene.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          synopsis: scene.synopsis
        })
      })
      if (!res.ok) throw new Error('Synopsis save failed')
      
      // If the scene being edited is the active scene in store, sync it
      if (store.activeNode?.id === scene.id) {
        store.activeNode.synopsis = scene.synopsis
      }

      saveNote.value = 'All synopses committed'
      setTimeout(() => { saveNote.value = '' }, 2500)
    } catch(e) {
      saveNote.value = 'Error saving synopsis'
      showToast(e.message, 'error')
    }
  }, 800)
}

const addSceneToChapter = async (chapterId) => {
  try {
    const res = await fetch(`${API_BASE}/api/node`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        parent_id: chapterId,
        node_type: 'SCENE',
        title: 'New Scene'
      })
    })
    if (!res.ok) throw new Error('Could not create scene')
    const data = await res.json()
    await store.fetchTree()
    showToast(`Created scene "${data.title}"`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}
</script>