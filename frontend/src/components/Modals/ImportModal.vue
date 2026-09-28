<template>
  <div 
    v-if="store.modals.import" 
    class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none" 
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
      <!-- Hidden File Input for Direct Browser Upload -->
      <input 
        type="file" 
        ref="fileInput" 
        @change="handleFileUpload" 
        accept=".docx,.doc,.txt,.md,.zip" 
        class="hidden" 
      />

      <!-- Header -->
      <div class="flex items-center justify-between border-b border-zinc-800 pb-3 shrink-0">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <FolderDown class="w-5 h-5 text-amber-500" /> Import Manuscript
        </h3>
        <button @click="closeModal" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Auto-Discovered Local Manuscripts -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <label class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider font-mono">
            Discovered in ~/Documents:
          </label>
          <button 
            @click="discoverLocal" 
            :disabled="isDiscovering"
            class="text-[10px] text-amber-400 hover:text-amber-300 font-mono transition flex items-center gap-1 disabled:opacity-50"
          >
            <RefreshCw class="w-3 h-3" :class="isDiscovering ? 'animate-spin' : ''" /> Rescan
          </button>
        </div>

        <div v-if="isDiscovering" class="py-8 text-center text-xs text-amber-400 flex items-center justify-center gap-2">
          <Loader class="w-4 h-4 animate-spin" /> Scanning local filesystem...
        </div>

        <div v-else-if="localManuscripts.length" class="max-h-56 overflow-y-auto space-y-1.5 p-1 custom-scrollbar">
          <div 
            v-for="m in localManuscripts" 
            :key="m.path" 
            class="p-2.5 bg-zinc-950 border border-zinc-800/80 hover:border-amber-500/50 rounded-lg flex items-center justify-between transition group"
          >
            <div class="truncate mr-3">
              <div class="text-xs font-semibold text-zinc-200 truncate flex items-center gap-1.5">
                <BookOpen v-if="m.type === 'SCRIVENER'" class="w-3.5 h-3.5 text-amber-500 shrink-0" />
                <FileText v-else class="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span class="truncate">{{ m.title }}</span>
              </div>
              <div class="text-[10px] text-zinc-500 font-mono truncate mt-0.5">{{ m.rel_path }}</div>
            </div>

            <button 
              @click="importLocalFile(m.path)" 
              :disabled="isImporting"
              class="px-2.5 py-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-[11px] shrink-0 transition shadow"
            >
              {{ isImporting ? 'Ingesting...' : 'Import' }}
            </button>
          </div>
        </div>

        <div v-else class="text-xs text-zinc-500 italic p-4 bg-zinc-950 rounded border border-zinc-800/80 text-center font-serif">
          No .scriv projects or .docx manuscripts found in ~/Documents.
        </div>
      </div>

      <!-- File Browser Upload Trigger -->
      <div class="border-t border-zinc-800 pt-4 flex items-center justify-between shrink-0">
        <div class="text-xs text-zinc-400">
          <div>Have a file elsewhere on your Mac?</div>
          <div class="text-[10px] text-zinc-500 font-mono">Supports .docx, .txt, .md, or zipped .scriv</div>
        </div>

        <button 
          @click="triggerBrowse" 
          :disabled="isImporting"
          class="px-3.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition border border-zinc-700/50"
        >
          <Upload class="w-3.5 h-3.5" /> Browse File...
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { FolderDown, X, RefreshCw, Loader, BookOpen, FileText, Upload } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const fileInput = ref(null)
const localManuscripts = ref([])
const isDiscovering = ref(false)
const isImporting = ref(false)

const closeModal = () => {
  store.toggleModal('import', false)
}

const triggerBrowse = () => {
  if (fileInput.value) fileInput.value.click()
}

const discoverLocal = async () => {
  isDiscovering.value = true
  try {
    const res = await fetch(`${API_BASE}/api/import/discover`)
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to discover files`)
    localManuscripts.value = await res.json()
  } catch (e) {
    localManuscripts.value = []
    showToast(e.message, 'error')
  } finally {
    isDiscovering.value = false
  }
}

const importLocalFile = async (path) => {
  isImporting.value = true
  store.saveStatus = 'Importing manuscript...'
  try {
    const res = await fetch(`${API_BASE}/api/import/local-path`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || data.message || 'Import failed on server')
    }

    if (data.status === 'success') {
      window.dispatchEvent(new Event('refresh-tree'))
      await store.fetchTree()
      if (data.first_scene_id) {
        await store.loadScene(data.first_scene_id)
      }
      store.viewMode = 'editor'
      closeModal()
      showToast('Manuscript successfully imported into Binder!', 'success')
    }
  } catch (e) {
    showToast(`Import Error: ${e.message}`, 'error')
  } finally {
    isImporting.value = false
    store.saveStatus = 'Ready'
  }
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  isImporting.value = true
  store.saveStatus = `Uploading ${file.name}...`
  const fd = new FormData()
  fd.append('file', file)

  try {
    const res = await fetch(`${API_BASE}/api/import/upload`, {
      method: 'POST',
      body: fd
    })
    
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || data.message || 'Upload parse failed on server')
    }

    if (data.status === 'success') {
      window.dispatchEvent(new Event('refresh-tree'))
      await store.fetchTree()
      if (data.first_scene_id) {
        await store.loadScene(data.first_scene_id)
      }
      store.viewMode = 'editor'
      closeModal()
      showToast(`Imported ${file.name}`, 'success')
    }
  } catch (e) {
    showToast(`Upload Error: ${e.message}`, 'error')
  } finally {
    isImporting.value = false
    store.saveStatus = 'Ready'
    event.target.value = ''
  }
}

watch(() => store.modals.import, (isOpen) => {
  if (isOpen) discoverLocal()
})

onMounted(() => {
  if (store.modals.import) discoverLocal()
})
</script>