<template>
  <aside v-show="!store.isVoidMode" class="w-64 border-r bg-zinc-950 md:bg-zinc-900/60 shadow-2xl backdrop-blur-xl flex flex-col transition-all z-20 shrink-0 select-none" :class="store.isCandlelight ? 'border-amber-900/40 bg-[#120f0c]' : 'border-zinc-800/80'">
    <div class="p-3 border-b flex items-center justify-between text-xs font-semibold uppercase tracking-wider shrink-0" :class="store.isCandlelight ? 'border-amber-900/40 text-amber-300/80' : 'border-zinc-800/80 text-zinc-400'">
      <div class="flex items-center gap-2">
        <BookMarked class="w-3.5 h-3.5 text-amber-500" />
        <span>Binder</span>
        <button @click="store.toggleModal('vault', true)" class="px-1.5 py-0.5 bg-zinc-800/80 hover:bg-zinc-700 text-amber-400/90 rounded text-[10px] font-mono flex items-center gap-1 transition border border-zinc-700/50">
          <Library class="w-3 h-3" /> Bookcase
        </button>
      </div>
      <div class="flex items-center space-x-1">
        <button @click="autoTitleScenes" title="Auto-Title Generic Scenes via Local Llama" class="p-1 hover:bg-zinc-800 rounded text-amber-400 hover:text-amber-300 transition"><Sparkles class="w-4 h-4" /></button>
        <button @click="addChapter" title="Add Chapter" class="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white transition"><FolderPlus class="w-4 h-4" /></button>
        <button @click="addScene" title="Add Scene" class="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white transition"><FilePlus class="w-4 h-4" /></button>
      </div>
    </div>
    <div v-if="store.tree.length" class="px-3 py-2 border-b border-zinc-800/70">
      <label class="block text-[9px] uppercase tracking-wider text-zinc-500 mb-1" for="active-manuscript">Working manuscript</label>
      <select id="active-manuscript" :value="store.activeBookId" @change="store.setActiveBook($event.target.value)" class="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-[11px] text-zinc-300 focus:outline-none focus:border-amber-500/50">
        <option v-for="book in store.tree" :key="book.id" :value="book.id">{{ book.title }}</option>
      </select>
    </div>
    <div class="flex-1 overflow-y-auto p-2 space-y-1 text-sm custom-scrollbar">
      <div v-if="!store.tree || store.tree.length === 0" class="py-12 px-4 text-center text-zinc-600 space-y-3">
        <BookOpen class="w-8 h-8 mx-auto text-zinc-800" />
        <p class="text-xs">No manuscripts loaded.</p>
        <button @click="store.createManuscript()" class="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs rounded transition">Create Manuscript</button>
      </div>
      <template v-for="book in store.tree" :key="book.id">
        <div class="font-bold text-zinc-200 text-xs px-2 py-1.5 flex items-center justify-between group hover:bg-zinc-800/40 rounded cursor-pointer transition-colors" @click="store.setActiveBook(book.id); toggleCollapse(book.id)">
          <div class="flex items-center gap-1.5 truncate flex-1 mr-2" @dblclick.stop="startRename(book, $event)">
            <ChevronRight v-if="isCollapsed(book.id)" class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <ChevronDown v-else class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <BookOpen class="w-3.5 h-3.5 text-amber-500 shrink-0" /> 
            <input v-if="editingNodeId === book.id" :id="'rename-' + book.id" v-model="editingTitle" @keyup.enter="saveRename(book)" @blur="saveRename(book)" @click.stop class="bg-zinc-950 text-amber-400 px-1 py-0.5 rounded border border-amber-500 text-xs w-full focus:outline-none font-sans" />
            <span v-else class="truncate tracking-wide">{{ book.title }}</span>
          </div>
          <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
            <button @click.stop="startRename(book, $event)" title="Rename" class="p-0.5 hover:text-amber-400 text-zinc-600 transition"><Pencil class="w-3 h-3" /></button>
            <button @click.stop="checkInBook(book)" title="Check in to Bookcase" class="p-0.5 hover:text-amber-400 text-zinc-600 transition"><Archive class="w-3.5 h-3.5" /></button>
            <button @click.stop="deleteNode(book)" title="Delete" class="p-0.5 hover:text-rose-400 text-zinc-600 transition"><Trash2 class="w-3.5 h-3.5" /></button>
          </div>
        </div>
        <div v-show="!isCollapsed(book.id)" v-for="chapter in book.children" :key="chapter.id" class="ml-2">
          <div class="text-zinc-400 text-xs px-2 py-1.5 font-medium flex items-center justify-between group hover:bg-zinc-800/40 rounded cursor-pointer transition-colors" @click="toggleCollapse(chapter.id)">
            <div class="flex items-center gap-1.5 truncate flex-1 mr-2" @dblclick.stop="startRename(chapter, $event)">
              <ChevronRight v-if="isCollapsed(chapter.id)" class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
              <ChevronDown v-else class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
              <Folder class="w-3.5 h-3.5 text-zinc-500 shrink-0" /> 
              <input v-if="editingNodeId === chapter.id" :id="'rename-' + chapter.id" v-model="editingTitle" @keyup.enter="saveRename(chapter)" @blur="saveRename(chapter)" @click.stop class="bg-zinc-950 text-amber-400 px-1 py-0.5 rounded border border-amber-500 text-xs w-full focus:outline-none font-sans" />
              <span v-else class="truncate">{{ chapter.title }}</span>
            </div>
            <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
              <button @click.stop="startRename(chapter, $event)" title="Rename" class="p-0.5 hover:text-amber-400 text-zinc-500 transition"><Pencil class="w-3 h-3" /></button>
              <button @click.stop="addSceneTo(chapter.id)" title="Add Scene" class="p-0.5 hover:text-white text-zinc-500 transition"><Plus class="w-3 h-3" /></button>
              <button @click.stop="deleteNode(chapter)" title="Delete" class="p-0.5 hover:text-rose-400 text-zinc-600 transition"><Trash2 class="w-3.5 h-3.5" /></button>
            </div>
          </div>
          <div v-show="!isCollapsed(chapter.id)" v-for="scene in chapter.children" :key="scene.id" class="ml-4">
            <div @click="selectNode(scene.id)" :class="['w-full text-left px-2 py-1.5 rounded text-xs flex items-center justify-between group transition cursor-pointer', store.activeNode?.id === scene.id ? 'bg-amber-500/15 text-amber-300 font-medium border border-amber-500/30' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 border border-transparent']">
              <div class="flex items-center gap-1.5 truncate flex-1 mr-2" @dblclick.stop="startRename(scene, $event)">
                <FileText class="w-3 h-3 text-zinc-500 shrink-0" /> 
                <input v-if="editingNodeId === scene.id" :id="'rename-' + scene.id" v-model="editingTitle" @keyup.enter="saveRename(scene)" @blur="saveRename(scene)" @click.stop class="bg-zinc-950 text-amber-400 px-1 py-0.5 rounded border border-amber-500 text-xs w-full focus:outline-none font-sans" />
                <span v-else class="truncate">{{ scene.title }}</span>
              </div>
              <div class="flex items-center space-x-1.5 opacity-0 group-hover:opacity-100 transition">
                <span class="text-[10px] text-zinc-500 font-mono">{{ scene.word_count || 0 }}w</span>
                <button @click.stop="startRename(scene, $event)" title="Rename" class="p-0.5 hover:text-amber-400 text-zinc-500 transition"><Pencil class="w-3 h-3" /></button>
                <button @click.stop="deleteNode(scene)" title="Delete" class="p-0.5 hover:text-rose-400 text-zinc-600 transition"><Trash2 class="w-3.5 h-3.5" /></button>
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

const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

const collapsed = ref({})
const isCollapsed = (id) => !!collapsed.value[id]
const toggleCollapse = (id) => { collapsed.value[id] = !collapsed.value[id] }

const editingNodeId = ref(null)
const editingTitle = ref('')

const fetchTree = async () => { await store.fetchTree() }

const selectNode = async (id) => {
  if (!id) return
  if (await store.loadScene(id)) {
    store.viewMode = 'editor'
    store.modals.mobileBinder = false
  }
}

const addChapter = async () => {
  const bookId = store.activeBookId
  if (!bookId) {
    showToast('Create or select a manuscript first.', 'info')
    return
  }
  try {
    const response = await fetch(`${API_BASE}/api/node`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parent_id: bookId, node_type: 'CHAPTER', title: 'New Chapter' }) })
    if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to create chapter`)
    collapsed.value[bookId] = false
    await fetchTree()
  } catch (e) { showToast(e.message, "error") }
}

const addScene = async () => {
  if (!store.getBook()) {
    showToast('Create or select a manuscript first.', 'info')
    return
  }
  const chapterId = store.getBook()?.children?.find(node => node.node_type === 'CHAPTER')?.id
  if (chapterId) { addSceneTo(chapterId) } else { showToast("Create a chapter first.", "info") }
}

const addSceneTo = async (chId) => {
  try {
    const res = await fetch(`${API_BASE}/api/node`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parent_id: chId, node_type: 'SCENE', title: 'New Scene' }) })
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to create scene`)
    const data = await res.json()
    await fetchTree()
    await selectNode(data.id)
  } catch (e) { showToast(e.message, "error") }
}

const startRename = (node, event) => {
  if (event) event.stopPropagation()
  editingNodeId.value = node.id
  editingTitle.value = node.title
  nextTick(() => { const el = document.getElementById(`rename-${node.id}`); if (el) { el.focus(); el.select() } })
}

const saveRename = async (node) => {
  if (!editingNodeId.value) return
  const newTitle = editingTitle.value.trim()
  editingNodeId.value = null
  if (!newTitle || newTitle === node.title) return
  node.title = newTitle
  if (store.activeNode?.id === node.id) store.activeNode.title = newTitle
  try {
    await fetch(`${API_BASE}/api/node/${node.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: newTitle }) })
    await fetchTree()
  } catch(e) { showToast("Rename failed.", "error") }
}

const checkInBook = async (book) => {
if (!window.confirm(`Check in "${book.title}" to the Bookcase?\n\nIt will be removed from the active Binder and kept safe until you check it out again.`)) return
  try {
    await fetch(`${API_BASE}/api/vault/${book.id}/toggle`, { method: 'POST' })
    if (store.activeNode?.book_id === book.id || store.activeNode?.id === book.id || store.activeNode?.parent_id === book.id) { store.activeNode = null }
    await fetchTree()
} catch (e) { showToast("Could not check in the book.", "error") }
}

const deleteNode = async (node) => {
  const type = node.node_type ? node.node_type.toLowerCase() : 'item'
  if (!window.confirm(`Delete ${type} "${node.title}"? This cannot be undone.`)) return
  try {
    const res = await fetch(`${API_BASE}/api/node/${node.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Delete failed on server')
    // Crucial: Clear active node so it doesn't auto-save and recreate itself
    if (store.activeNode?.id === node.id || store.activeNode?.parent_id === node.id || store.activeNode?.book_id === node.id) {
      store.activeNode = null
    }
    await fetchTree()
    showToast(`Deleted ${node.title}`, 'info')
  } catch (e) { showToast("Delete failed.", "error") }
}

const autoTitleScenes = async () => {
  store.saveStatus = 'Local AI generating titles...'
  try {
    const bId = store.activeBookId || null
    const res = await fetch(`${API_BASE}/api/binder/auto-title-scenes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ book_id: bId }) })
    if (!res.ok) throw new Error('Auto-titling failed')
    await fetchTree()
  } catch(e) { showToast("Auto-titling failed.", "error") }
}

onMounted(() => { fetchTree(); window.addEventListener('refresh-tree', fetchTree) })
</script>
