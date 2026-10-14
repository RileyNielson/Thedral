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
        accept=".docx,.doc,.txt,.md,.rtf,.zip" 
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
            Found in Documents, Desktop, and Downloads:
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
              @click="previewLocalFile(m.path)"
              :disabled="isImporting || isPreviewing"
              class="px-2.5 py-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-[11px] shrink-0 transition shadow"
            >
              {{ isPreviewing && pendingPath === m.path ? 'Preparing...' : 'Preview' }}
            </button>
          </div>
        </div>

        <div v-else class="text-xs text-zinc-500 italic p-4 bg-zinc-950 rounded border border-zinc-800/80 text-center font-serif">
          No .scriv projects or .docx manuscripts found in Documents, Desktop, or Downloads. Paste a path below.
        </div>
      </div>

      <div v-if="importReport" class="rounded-xl border border-zinc-700 bg-zinc-950 p-4 space-y-3 overflow-y-auto custom-scrollbar">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h4 class="text-sm font-semibold text-zinc-100">{{ importComplete ? 'Import complete' : `Preview: ${previewTitle}` }}</h4>
            <p class="text-[10px] text-zinc-500 mt-1">{{ importComplete ? 'Review what was brought into your Binder.' : 'Nothing has been added to your Binder yet.' }}</p>
          </div>
          <button @click="clearPreview" class="text-zinc-500 hover:text-white" aria-label="Clear preview"><X class="w-4 h-4" /></button>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[10px]">
          <div v-for="item in reportItems" :key="item.label" class="rounded bg-zinc-900 px-2.5 py-2">
            <div class="text-zinc-500">{{ item.label }}</div>
            <div class="text-zinc-200 font-mono mt-0.5">{{ item.value }}</div>
          </div>
        </div>
        <p v-if="isAnalyzing" class="text-[10px] text-violet-300">
          Preparing the no-AI reader lens for {{ importReport.scenes || 0 }} scenes…
        </p>
        <p v-else-if="analysisError" class="text-[10px] text-rose-300">
          Manuscript imported, but the reader lens could not be prepared: {{ analysisError }}
        </p>
        <p v-else-if="analyzedSceneCount" class="text-[10px] text-emerald-300">
          No-AI reader lens ready for {{ analyzedSceneCount }} scenes. Open the Reader tab to explore it.
        </p>
        <ul v-if="importReport.warnings?.length" class="space-y-1.5 text-[10px] text-amber-200/90">
          <li v-for="warning in importReport.warnings" :key="warning" class="flex gap-2"><span class="text-amber-400">!</span><span>{{ warning }}</span></li>
        </ul>
        <p v-else class="text-[10px] text-emerald-400">No unsupported structures were detected by this preview.</p>
        <button v-if="!importComplete" @click="confirmImport" :disabled="isImporting" class="w-full rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 px-3 py-2 text-xs font-bold text-zinc-950 transition">
          {{ isImporting ? 'Importing...' : 'Import this manuscript' }}
        </button>
      </div>

      <!-- Path or file import -->
      <div class="border-t border-zinc-800 pt-4 space-y-3 shrink-0">
        <div class="space-y-1.5">
          <label class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider font-mono">Scrivener project or file path</label>
          <form class="flex gap-2" @submit.prevent="previewTypedPath">
            <input
              v-model="typedPath"
              type="text"
              placeholder="~/Desktop/My Novel.scriv"
              class="flex-1 min-w-0 rounded-lg bg-zinc-950 border border-zinc-800 px-2.5 py-1.5 text-xs text-zinc-200 font-mono placeholder-zinc-600 focus:outline-none focus:border-amber-500/60"
            />
            <button type="submit" :disabled="!typedPath.trim() || isImporting || isPreviewing" class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded-lg text-xs transition">Preview</button>
          </form>
          <p class="text-[10px] text-zinc-500">A .scriv project is a folder, so the Browse button can't pick it. Paste its path (drag the folder into this box, or in Finder choose Option-Cmd-C), or upload a ZIP of it.</p>
        </div>
        <div class="flex items-center justify-between">
          <div class="text-xs text-zinc-400">
            <div>Have a file elsewhere on your Mac?</div>
            <div class="text-[10px] text-zinc-500 font-mono">.docx, .txt, .md, .rtf, or a zipped .scriv</div>
            <div class="text-[10px] text-zinc-500 mt-1">Scrivener synopsis, notes, outline cards, and Binder metadata are retained.</div>
          </div>
          <button
            @click="triggerBrowse"
            :disabled="isImporting || isPreviewing"
            class="px-3.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition border border-zinc-700/50"
          >
            <Upload class="w-3.5 h-3.5" /> Browse File...
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { FolderDown, X, RefreshCw, Loader, BookOpen, FileText, Upload } from '@lucide/vue'

import { API_BASE } from '@/api'

const fileInput = ref(null)
const typedPath = ref('')
const localManuscripts = ref([])
const isDiscovering = ref(false)
const isImporting = ref(false)
const isAnalyzing = ref(false)
const analyzedSceneCount = ref(0)
const analysisError = ref('')
const isPreviewing = ref(false)
const pendingPath = ref('')
const pendingFile = ref(null)
const importReport = ref(null)
const previewTitle = ref('')
const importComplete = ref(false)
const reportItems = computed(() => {
  const report = importReport.value || {}
  return [
    { label: 'Chapters', value: report.chapters ?? 0 },
    { label: 'Scenes', value: report.scenes ?? 0 },
    { label: 'Outline-only cards', value: report.outline_only ?? 0 },
    { label: 'Words', value: report.words ?? 0 },
    { label: 'Formatted paragraphs', value: report.formatted_paragraphs ?? 0 },
    { label: 'Notes / synopses', value: `${report.notes ?? 0} / ${report.synopses ?? 0}` },
    { label: 'Characters', value: report.characters ?? 0 },
    { label: 'Locations', value: report.locations ?? 0 },
    { label: 'Lore entries', value: report.lore ?? 0 }
  ]
})

const closeModal = () => {
  store.toggleModal('import', false)
}

const triggerBrowse = () => {
  if (fileInput.value) fileInput.value.click()
}

const clearPreview = () => {
  pendingPath.value = ''
  pendingFile.value = null
  importReport.value = null
  previewTitle.value = ''
  importComplete.value = false
  analyzedSceneCount.value = 0
  analysisError.value = ''
}

const readResponse = async (response, fallback) => {
  let data = {}
  try {
    data = await response.json()
  } catch {
    if (!response.ok) throw new Error(`${fallback} (server error ${response.status})`)
  }
  if (!response.ok) throw new Error(data.detail || data.message || fallback)
  return data
}

const friendlyError = (e) =>
  e instanceof TypeError
    ? 'Could not reach the Thedral server. Make sure the launcher window is still open, then reload this page.'
    : e.message

const previewTypedPath = () => previewLocalFile(typedPath.value.trim())

const previewLocalFile = async (path) => {
  clearPreview()
  isPreviewing.value = true
  pendingPath.value = path
  try {
    const response = await fetch(`${API_BASE}/api/import/preview/local-path`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    const data = await readResponse(response, 'Import preview failed')
    previewTitle.value = data.title
    importReport.value = data.report
  } catch (e) {
    pendingPath.value = ''
    showToast(`Preview Error: ${friendlyError(e)}`, 'error')
  } finally {
    isPreviewing.value = false
  }
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

const confirmImport = async () => {
  if (!pendingPath.value && !pendingFile.value) return
  isImporting.value = true
  store.saveStatus = 'Importing manuscript...'
  try {
    let response
    if (pendingPath.value) {
      response = await fetch(`${API_BASE}/api/import/local-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: pendingPath.value })
      })
    } else {
      const fd = new FormData()
      fd.append('file', pendingFile.value)
      response = await fetch(`${API_BASE}/api/import/upload`, { method: 'POST', body: fd })
    }
    const data = await readResponse(response, 'Import failed')
    if (data.status === 'success') {
      importReport.value = data.report || importReport.value
      importComplete.value = true
      store.readerStoryCache = null
      window.dispatchEvent(new Event('refresh-tree'))
      await store.fetchTree()
      if (data.first_scene_id) {
        await store.loadScene(data.first_scene_id)
      }
      store.viewMode = 'editor'
      showToast('Manuscript imported into Binder!', 'success')
      const book = data.first_scene_id ? store.findBookForNode(data.first_scene_id) : null
      if (book) {
        isAnalyzing.value = true
        analysisError.value = ''
        store.saveStatus = 'Preparing no-AI reader lens...'
        try {
          const analysisResponse = await fetch(
            `${API_BASE}/api/analytics/reader-story/${encodeURIComponent(book.id)}/all`
          )
          const analysis = await readResponse(analysisResponse, 'Reader analysis failed')
          store.readerStoryCache = analysis
          analyzedSceneCount.value = analysis.scene_count
          store.activeInspectorTab = 'reader'
        } catch (error) {
          analysisError.value = error.message || 'Could not prepare the reader lens.'
          showToast(`Manuscript imported, but reader analysis failed: ${analysisError.value}`, 'error')
        } finally {
          isAnalyzing.value = false
        }
      }
    }
  } catch (e) {
    showToast(`Import Error: ${friendlyError(e)}`, 'error')
  } finally {
    isImporting.value = false
    store.saveStatus = 'Ready'
  }
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  clearPreview()
  isPreviewing.value = true
  pendingFile.value = file
  store.saveStatus = `Preparing preview for ${file.name}...`
  const fd = new FormData()
  fd.append('file', file)

  try {
    const res = await fetch(`${API_BASE}/api/import/preview/upload`, {
      method: 'POST',
      body: fd
    })
    const data = await readResponse(res, 'Upload preview failed')
    previewTitle.value = data.title
    importReport.value = data.report
  } catch (e) {
    pendingFile.value = null
    showToast(`Preview Error: ${friendlyError(e)}`, 'error')
  } finally {
    isPreviewing.value = false
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