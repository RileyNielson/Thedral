import os

frontend_dir = os.path.expanduser("~/Developer/ManuscriptStudio/frontend/src/components")

# ==========================================
# 1. BINDER.VUE
# ==========================================
binder_content = """<template>
  <aside v-show="!store.isVoidMode" class="w-64 border-r border-zinc-800/80 bg-zinc-950 md:bg-zinc-900/60 shadow-2xl backdrop-blur-xl flex flex-col transition-all z-20 shrink-0">
    
    <div class="p-3 border-b border-zinc-800/80 flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-zinc-400 shrink-0">
      <div class="flex items-center gap-2">
        <BookMarked class="w-3.5 h-3.5 text-amber-500" />
        <span>Binder</span>
        <button @click="store.modals.vault = true" class="px-1.5 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-amber-400/90 rounded text-[10px] font-mono flex items-center gap-1 transition">
          <Library class="w-3 h-3" /> Vault
        </button>
      </div>
      <div class="flex space-x-1">
        <button @click="autoTitleScenes" title="Auto-Title Generic Scenes" class="p-1 hover:bg-zinc-800 rounded text-amber-400 hover:text-white"><Sparkles class="w-4 h-4" /></button>
        <button @click="addChapter" title="Add Chapter" class="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white"><FolderPlus class="w-4 h-4" /></button>
        <button @click="addScene" title="Add Scene" class="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white"><FilePlus class="w-4 h-4" /></button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-2 space-y-1 text-sm">
      <template v-for="book in store.tree" :key="book.id">
        <!-- BOOK ROW -->
        <div class="font-bold text-zinc-200 text-xs px-2 py-1.5 flex items-center justify-between group hover:bg-zinc-800/40 rounded cursor-pointer" @click="toggleCollapse(book.id)">
          <div class="flex items-center gap-1.5 truncate flex-1 mr-2" @dblclick.stop="startRename(book, $event)">
            <ChevronRight v-if="isCollapsed(book.id)" class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <ChevronDown v-else class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <BookOpen class="w-3.5 h-3.5 text-amber-500 shrink-0" /> 
            
            <input v-if="editingNodeId === book.id" :id="'rename-' + book.id" v-model="editingTitle" @keyup.enter="saveRename(book)" @blur="saveRename(book)" @click.stop class="bg-zinc-950 text-amber-400 px-1 py-0.5 rounded border border-amber-500 text-xs w-full focus:outline-none" />
            <span v-else class="truncate">{{ book.title }}</span>
          </div>
          <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
            <button @click.stop="startRename(book, $event)" class="p-0.5 hover:text-amber-400 text-zinc-600"><Pencil class="w-3 h-3" /></button>
            <button @click.stop="closeBook(book)" class="p-0.5 hover:text-amber-400 text-zinc-600"><Archive class="w-3.5 h-3.5" /></button>
            <button @click.stop="deleteNode(book)" class="p-0.5 hover:text-rose-400 text-zinc-600"><Trash2 class="w-3.5 h-3.5" /></button>
          </div>
        </div>
        
        <!-- CHAPTERS -->
        <div v-show="!isCollapsed(book.id)" v-for="chapter in book.children" :key="chapter.id" class="ml-2">
          <div class="text-zinc-400 text-xs px-2 py-1.5 font-medium flex items-center justify-between group hover:bg-zinc-800/40 rounded cursor-pointer" @click="toggleCollapse(chapter.id)">
            <div class="flex items-center gap-1.5 truncate flex-1 mr-2" @dblclick.stop="startRename(chapter, $event)">
              <ChevronRight v-if="isCollapsed(chapter.id)" class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
              <ChevronDown v-else class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
              <Folder class="w-3.5 h-3.5 text-zinc-500 shrink-0" /> 
              
              <input v-if="editingNodeId === chapter.id" :id="'rename-' + chapter.id" v-model="editingTitle" @keyup.enter="saveRename(chapter)" @blur="saveRename(chapter)" @click.stop class="bg-zinc-950 text-amber-400 px-1 py-0.5 rounded border border-amber-500 text-xs w-full focus:outline-none" />
              <span v-else class="truncate">{{ chapter.title }}</span>
            </div>
            <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
              <button @click.stop="startRename(chapter, $event)" class="p-0.5 hover:text-amber-400 text-zinc-500"><Pencil class="w-3 h-3" /></button>
              <button @click.stop="addSceneTo(chapter.id)" class="p-0.5 hover:text-white text-zinc-500"><Plus class="w-3 h-3" /></button>
              <button @click.stop="deleteNode(chapter)" class="p-0.5 hover:text-rose-400 text-zinc-600"><Trash2 class="w-3.5 h-3.5" /></button>
            </div>
          </div>

          <!-- SCENES -->
          <div v-show="!isCollapsed(chapter.id)" v-for="scene in chapter.children" :key="scene.id" class="ml-4">
            <div @click="selectNode(scene.id)" :class="['w-full text-left px-2 py-1.5 rounded text-xs flex items-center justify-between group transition cursor-pointer', store.activeNode.id === scene.id ? 'bg-amber-500/10 text-amber-300 font-medium' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200']">
              <div class="flex items-center gap-1.5 truncate flex-1 mr-2" @dblclick.stop="startRename(scene, $event)">
                <FileText class="w-3 h-3 text-zinc-600 shrink-0" /> 
                <input v-if="editingNodeId === scene.id" :id="'rename-' + scene.id" v-model="editingTitle" @keyup.enter="saveRename(scene)" @blur="saveRename(scene)" @click.stop class="bg-zinc-950 text-amber-400 px-1 py-0.5 rounded border border-amber-500 text-xs w-full focus:outline-none" />
                <span v-else class="truncate">{{ scene.title }}</span>
              </div>
              <div class="flex items-center space-x-1.5 opacity-0 group-hover:opacity-100 transition">
                <span class="text-[10px] text-zinc-600 font-mono">{{ scene.word_count || 0 }}w</span>
                <button @click.stop="startRename(scene, $event)" class="p-0.5 hover:text-amber-400 text-zinc-600"><Pencil class="w-3 h-3" /></button>
                <button @click.stop="deleteNode(scene)" class="p-0.5 hover:text-rose-400 text-zinc-600"><Trash2 class="w-3.5 h-3.5" /></button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { BookMarked, Library, Sparkles, FolderPlus, FilePlus, ChevronRight, ChevronDown, BookOpen, Pencil, Archive, Trash2, Folder, Plus, FileText } from 'lucide-vue-next'

const collapsed = ref({})
const isCollapsed = (id) => !!collapsed.value[id]
const toggleCollapse = (id) => collapsed.value[id] = !collapsed.value[id]

const editingNodeId = ref(null)
const editingTitle = ref('')

const fetchTree = async () => {
  try {
    const res = await fetch('/api/tree')
    store.tree = await res.json()
    if (!store.activeNode.id && store.tree[0]?.children[0]?.children[0]) {
      selectNode(store.tree[0].children[0].children[0].id)
    }
  } catch(e) {
    showToast("Error loading Binder.", "error")
  }
}

const selectNode = async (id) => {
  try {
    const res = await fetch(`/api/node/${id}`)
    store.activeNode = await res.json()
    store.editorState.previousWordCount = (store.activeNode.content || '').split(/\s+/).filter(Boolean).length
    store.modals.mobileBinder = false
    
    fetch(`/api/disclosures/scene/${id}`).then(r => r.json()).then(d => store.activeDisclosures = d).catch(()=>{})
    fetch(`/api/critiques/scene/${id}`).then(r => r.json()).then(d => store.sceneCritiques = d).catch(()=>{})
  } catch(e) {
    showToast("Failed to open scene.", "error")
  }
}

onMounted(() => {
  fetchTree()
  window.addEventListener('refresh-tree', fetchTree)
})

const addChapter = async () => {
  const bookId = store.tree[0]?.id
  if (!bookId) return
  await fetch('/api/node', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parent_id: bookId, node_type: 'CHAPTER', title: 'New Chapter' }) })
  fetchTree()
}

const addScene = async () => {
  const chId = store.tree[0]?.children[0]?.id
  if (chId) addSceneTo(chId)
}

const addSceneTo = async (chId) => {
  const res = await fetch('/api/node', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parent_id: chId, node_type: 'SCENE', title: 'New Scene' }) })
  const data = await res.json()
  await fetchTree()
  selectNode(data.id)
}

const startRename = (node, event) => {
  if (event) event.stopPropagation()
  editingNodeId.value = node.id
  editingTitle.value = node.title
  nextTick(() => {
    const el = document.getElementById(`rename-${node.id}`)
    if (el) { el.focus(); el.select() }
  })
}

const saveRename = async (node) => {
  if (!editingNodeId.value) return
  const newTitle = editingTitle.value.trim()
  editingNodeId.value = null
  if (!newTitle || newTitle === node.title) return

  node.title = newTitle
  if (store.activeNode.id === node.id) store.activeNode.title = newTitle
  store.saveStatus = `Renamed to "${newTitle}"`

  try {
    await fetch(`/api/node/${node.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: newTitle }) })
    fetchTree()
  } catch(e) {
    showToast("Rename failed.", "error")
  }
}

const closeBook = async (book) => {
  if (!window.confirm(`Close "${book.title}"?\n\nThis removes it from the active Binder, keeping all data safe in your Vault.`)) return
  await fetch(`/api/vault/${book.id}/toggle`, { method: 'POST' })
  if (store.activeNode.book_id === book.id || store.activeNode.id === book.id) store.activeNode = {}
  fetchTree()
  store.saveStatus = `Closed ${book.title}`
}

const deleteNode = async (node) => {
  const type = node.node_type ? node.node_type.toLowerCase() : 'item'
  if (!window.confirm(`Delete ${type} "${node.title}"? This cannot be undone.`)) return
  try {
    await fetch(`/api/node/${node.id}`, { method: 'DELETE' })
    if (store.activeNode.id === node.id) store.activeNode = {}
    fetchTree()
    store.saveStatus = `Deleted ${node.title}`
  } catch (e) {
    showToast("Delete failed.", "error")
  }
}

const autoTitleScenes = async () => {
  store.saveStatus = 'Local AI generating titles...'
  try {
    const bId = store.tree[0]?.id || null
    const res = await fetch('/api/binder/auto-title-scenes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ book_id: bId }) })
    const data = await res.json()
    store.saveStatus = `Updated ${data.updated_count} scene titles!`
    fetchTree()
  } catch(e) {
    showToast("Auto-titling failed.", "error")
  }
}
</script>"""

with open(os.path.join(frontend_dir, "Binder.vue"), "w", encoding="utf-8") as f:
    f.write(binder_content)


# ==========================================
# 2. SCRIPTORIUM.VUE
# ==========================================
scriptorium_content = """<template>
  <div class="flex-1 flex flex-col overflow-hidden relative h-full">
    
    <!-- The Void HUD -->
    <div v-if="store.isVoidMode" class="absolute bottom-0 left-0 w-full p-6 flex justify-between items-end pointer-events-none z-40">
      <div class="pointer-events-auto opacity-10 hover:opacity-100 transition-opacity duration-500 flex items-center gap-3">
        <span class="text-zinc-500 font-mono text-[10px] bg-zinc-950/50 px-2 py-1 rounded border border-zinc-800">Words: {{ store.activeNode.word_count || 0 }}</span>
        <button @click="store.modals.omnibar = true" class="px-2.5 py-1 bg-zinc-900/80 border border-zinc-800 hover:border-amber-500/50 text-zinc-400 hover:text-amber-400 rounded text-[10px] font-medium transition flex items-center gap-1.5 backdrop-blur"><Search class="w-3 h-3" /> Lore Check (Cmd+K)</button>
      </div>
      <div class="pointer-events-auto opacity-10 hover:opacity-100 transition-opacity duration-500">
        <button @click="store.isVoidMode = false" class="px-3 py-1.5 bg-zinc-900/80 border border-zinc-800 hover:border-rose-500/50 text-zinc-500 hover:text-rose-400 rounded text-xs font-medium transition flex items-center gap-1.5 backdrop-blur"><DoorOpen class="w-3.5 h-3.5" /> Exit Void (Esc)</button>
      </div>
    </div>

    <!-- Scriptorium Toolbar -->
    <div v-if="store.activeNode.id && !store.isVoidMode" class="h-9 border-b border-zinc-800/60 bg-zinc-900/30 px-6 flex items-center justify-between text-xs z-10 shrink-0">
      <span class="text-[11px] text-zinc-500 font-mono">Words: <strong class="text-zinc-300">{{ store.activeNode.word_count || 0 }}</strong></span>
      
      <div class="flex items-center space-x-2">
        <button @click="toggleXRay" :class="['px-2.5 py-0.5 rounded text-xs font-medium flex items-center gap-1 transition', store.isXRayActive ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-zinc-800 text-zinc-400 hover:text-white']">
          <Eye class="w-3.5 h-3.5" /> <span>Craft X-Ray</span>
        </button>
        <button @click="store.isVoidMode = true" class="px-2.5 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-xs font-medium flex items-center gap-1 transition" title="Enter The Void">
          <Moon class="w-3.5 h-3.5" /> <span>The Void</span>
        </button>
        <button @click="runMasterTriage" class="px-2.5 py-0.5 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded text-xs font-medium flex items-center gap-1.5 transition shadow-[0_0_8px_rgba(6,182,212,0.2)]">
          <Wand2 class="w-3.5 h-3.5" /> <span class="hidden md:inline">Triage Draft</span>
        </button>
      </div>
    </div>

    <!-- Micro-Stall Alert -->
    <div v-if="microStallAlert" class="bg-amber-500/10 border-b border-amber-500/30 px-6 py-2 flex items-center justify-between text-xs text-amber-300 z-10 shrink-0">
      <div class="flex items-center gap-2">
        <RotateCcw class="w-4 h-4 text-amber-400 animate-spin" />
        <span><strong>Micro-Stall Detected:</strong> You've rewritten this section 8+ times.</span>
      </div>
      <div class="flex items-center space-x-2">
        <button @click="insertTKProtocol" class="px-2 py-0.5 bg-amber-600 hover:bg-amber-500 text-zinc-950 font-bold rounded text-[11px] transition">Insert [TK] & Advance</button>
        <button @click="microStallAlert = false" class="text-zinc-500 hover:text-white"><X class="w-3.5 h-3.5" /></button>
      </div>
    </div>

    <!-- TK Pending Tasks Panel -->
    <div v-if="store.tkMarkers.length && !store.isVoidMode" class="bg-amber-500/10 border-b border-amber-500/30 p-4 shrink-0 max-h-32 overflow-y-auto z-10">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-amber-400 flex items-center gap-1.5"><ListTodo class="w-4 h-4" /> Pending [TK] Tasks in Scene</span>
        <button @click="store.tkMarkers = []" class="text-zinc-500 hover:text-white"><X class="w-4 h-4" /></button>
      </div>
      <div class="space-y-1">
        <button v-for="(tk, i) in store.tkMarkers" :key="i" @click="jumpToTextOffset(tk.index, tk.text.length)" class="w-full text-left px-3 py-1.5 bg-zinc-950/50 hover:bg-zinc-900 rounded border border-zinc-800/80 text-xs text-zinc-300 font-mono transition flex items-center gap-2">
          <span class="text-amber-500">[{{ i + 1 }}]</span> {{ tk.text }}
        </button>
      </div>
    </div>

    <!-- Editor Canvas -->
    <div v-if="store.activeNode.id" :class="['flex-1 flex flex-col max-w-3xl w-full mx-auto overflow-y-auto', store.isVoidMode ? 'p-8 md:p-16 mt-10' : 'p-6 md:p-12']">
      <input v-model="store.activeNode.title" @input="queueAutoSave"
             class="bg-transparent text-2xl md:text-3xl font-serif font-bold text-zinc-100 border-none focus:outline-none mb-6"
             placeholder="Scene Title..." />
             
      <!-- TipTap Rich Text Editor -->
      <editor-content v-show="!store.isXRayActive" :editor="editor" class="flex-1" @mouseup="handleTextSelection" />
      
      <!-- X-Ray Overlay -->
      <div v-show="store.isXRayActive" class="prose-canvas flex-1 text-lg md:text-xl leading-relaxed space-y-4">
        <div v-for="(p_block, p_idx) in store.xraySentences" :key="p_idx" class="leading-relaxed">
          <span v-for="(s, s_idx) in p_block" :key="s_idx" :class="['inline-block transition px-1 py-0.5 rounded cursor-pointer mr-1 mb-1', getXRayClass(s.type)]" :title="s.reason" @click="handleXRaySentenceClick(s.text)">{{ s.text }}</span>
        </div>
      </div>
    </div>
    
    <div v-else class="flex-1 flex items-center justify-center text-zinc-600">
      <div class="text-center space-y-3">
        <Feather class="w-10 h-10 mx-auto text-zinc-800" />
        <p class="text-sm">Select a scene from the binder.</p>
      </div>
    </div>

    <!-- Floating Socratic Toolbar -->
    <div v-if="store.selectedText && !store.isVoidMode" class="absolute bottom-6 left-1/2 -translate-x-1/2 bg-zinc-900/95 border border-amber-500/40 rounded-full px-4 py-2 shadow-2xl flex items-center space-x-2 z-30 backdrop-blur">
      <span class="text-xs text-zinc-300 font-mono truncate max-w-[120px] sm:max-w-[160px] mr-1">"{{ store.selectedText }}"</span>
      <button @click="elevateSelection" title="Socratic Craft Mirror" class="bg-amber-600 hover:bg-amber-500 text-zinc-950 text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1 transition"><Sparkles class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Elevate</span></button>
      <button @click="registerSelection('CHARACTER')" title="Track as Character" class="bg-zinc-800 hover:bg-zinc-700 text-amber-300 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1 transition"><UserPlus class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Character</span></button>
      <button @click="registerSelection('ITEM')" title="Track as Artifact" class="bg-zinc-800 hover:bg-zinc-700 text-cyan-300 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1 transition"><Key class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Artifact</span></button>
    </div>

  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { store, showToast } from '../store.js'
import { Eye, Moon, Wand2, RotateCcw, X, Feather, Search, DoorOpen, ListTodo, Sparkles, UserPlus, Key } from 'lucide-vue-next'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Typography from '@tiptap/extension-typography'

const microStallAlert = ref(false)
let editor = null

const initEditor = () => {
  if (editor) editor.destroy()
  
  editor = new Editor({
    content: store.activeNode.content || '',
    extensions: [
      StarterKit,
      Typography,
      Placeholder.configure({ placeholder: 'Lay down the first sentence...' })
    ],
    editorProps: { attributes: { class: 'ProseMirror outline-none prose-canvas' } },
    onUpdate: () => {
      // For now, store text directly to prevent heavy HTML saving into SQLite
      const text = editor.getText()
      store.activeNode.content = text
      
      const currentWc = text.split(/\s+/).filter(Boolean).length
      store.activeNode.word_count = currentWc
      
      const now = Date.now()
      if (now - store.editorState.lastKeystrokeTime < 3000) {
        store.editorState.keystrokeRepeatCount++
        if (store.editorState.keystrokeRepeatCount >= 14) microStallAlert.value = true
      } else {
        store.editorState.keystrokeRepeatCount = 0
      }
      store.editorState.lastKeystrokeTime = now
      queueAutoSave()
    }
  })
}

watch(() => store.activeNode.id, () => {
  if (store.activeNode.id) {
    if (!editor) initEditor()
    else {
      // Only set content if it changed to avoid cursor jumps
      if (editor.getText() !== store.activeNode.content) {
        editor.commands.setContent(store.activeNode.content || '')
      }
    }
  }
})

let saveTimeout = null
const queueAutoSave = () => {
  store.saveStatus = 'Saving...'
  clearTimeout(saveTimeout)
  saveTimeout = setTimeout(async () => {
    try {
      await fetch(`/api/node/${store.activeNode.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          title: store.activeNode.title, 
          synopsis: store.activeNode.synopsis, 
          content: store.activeNode.content, 
          epigraph: store.activeNode.epigraph, 
          status: store.activeNode.status 
        })
      })
      store.saveStatus = 'All changes saved'
      
      // Update wordcount in tree silently
      window.dispatchEvent(new Event('refresh-tree'))
    } catch(e) {
      showToast('Save failed', 'error')
    }
  }, 1200)
}

const toggleXRay = async () => {
  store.isXRayActive = !store.isXRayActive
  if (store.isXRayActive && store.activeNode.content) {
    try {
      const res = await fetch('/api/craft/xray', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: store.activeNode.content }) })
      const data = await res.json()
      const paras = (store.activeNode.content || '').split("\n\n")
      let sentIdx = 0; const blocks = []
      for (const p of paras) {
        const pLen = p.trim().length; let currentBlock = []; let collectedLen = 0;
        while (sentIdx < data.sentences.length && collectedLen < pLen) {
          currentBlock.push(data.sentences[sentIdx]); collectedLen += data.sentences[sentIdx].text.length + 1; sentIdx++
        }
        if (currentBlock.length) blocks.push(currentBlock)
      }
      store.xraySentences = blocks.length ? blocks : [data.sentences]
    } catch(e) { showToast('X-Ray failed', 'error') }
  }
}

const getXRayClass = (type) => {
  if (type === 'ESCALATOR') return 'xray-escalator';
  if (type === 'RESOLVER') return 'xray-resolver';
  if (type === 'PIVOT') return 'xray-pivot';
  if (type === 'SLACK') return 'xray-slack';
  return '';
}

const handleTextSelection = () => {
  const sel = window.getSelection().toString().trim()
  store.selectedText = sel.length > 4 ? sel : ''
}

const handleXRaySentenceClick = (text) => {
  store.selectedText = text
  elevateSelection()
}

const elevateSelection = async () => {
  if (!store.selectedText) return
  store.activeInspectorTab = 'socratic'
  store.socraticCritique = ''
  showToast("Consulting Socratic Partner...", "info")
  
  try {
    const res = await fetch('/api/craft/elevate', { 
      method: 'POST', headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ passage: store.selectedText, surrounding: store.activeNode.content, scene_id: store.activeNode.id }) 
    })
    const data = await res.json()
    store.socraticCritique = data.critique
    store.activeCritiqueId = data.critique_id
    // Trigger history refresh
    window.dispatchEvent(new Event('refresh-critiques'))
  } catch(e) { showToast('Elevation failed', 'error') }
}

const registerSelection = async (type) => {
  if (!store.selectedText) return
  const name = store.selectedText
  try {
    await fetch('/api/entities/quick-register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, entity_type: type }) })
    store.selectedText = ''
    showToast(`Tracked: "${name}" (${type})`, 'info')
  } catch(e) { showToast('Failed to register entity', 'error') }
}

const runMasterTriage = async () => {
  if (!store.activeNode.id) return
  store.saveStatus = 'Running master cleanse...'
  try {
    const res = await fetch(`/api/binder/triage-scene/${store.activeNode.id}`, { method: 'POST' })
    const data = await res.json()
    if (data.status === 'success') {
      if (editor) editor.commands.setContent(data.formatted_text)
      store.activeNode.content = data.formatted_text
      
      let msg = 'Draft Triaged!'
      if (data.new_scenes > 0) msg += ` Splitting ${data.new_scenes} new scenes.`
      if (data.tk_count > 0) msg += ` Found ${data.tk_count} [TK] markers.`
      showToast(msg, 'info')
      
      if (data.new_scenes > 0) window.dispatchEvent(new Event('refresh-tree'))
      findTKMarkers()
      queueAutoSave()
    }
  } catch(e) { showToast('Triage failed', 'error') }
}

const insertTKProtocol = () => {
  if (editor) {
    editor.chain().focus().insertContent(' [TK: Intent / Next beat] ').run()
  }
  microStallAlert.value = false
  queueAutoSave()
}

const findTKMarkers = () => {
  const text = store.activeNode.content || ""
  const regex = /\[TK[^\]]*\]/gi
  let match
  const markers = []
  while ((match = regex.exec(text)) !== null) markers.push({ text: match[0], index: match.index })
  store.tkMarkers = markers
}

const jumpToTextOffset = (index, length) => {
  if (editor) {
    editor.commands.focus()
    editor.commands.setTextSelection({ from: index, to: index + length })
    editor.view.dom.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

onMounted(() => {
  if (store.activeNode.id) initEditor()
})

onBeforeUnmount(() => {
  if (editor) editor.destroy()
})
</script>
"""

with open(filepath, "w", encoding="utf-8") as f:
    f.write(scriptorium_content)

print("✅ Scriptorium.vue written successfully.")
