<template>
  <div class="flex-1 flex flex-col overflow-hidden relative h-full">
    
    <!-- Void Mode Floating HUD -->
    <div v-if="store.isVoidMode" class="absolute bottom-0 left-0 w-full p-6 flex justify-between items-end pointer-events-none z-40">
      <div class="pointer-events-auto opacity-20 hover:opacity-100 transition-opacity duration-500 flex items-center gap-3">
        <span class="text-zinc-500 font-mono text-[10px] bg-zinc-950/70 px-2.5 py-1 rounded border border-zinc-800 backdrop-blur">
          Words: {{ store.activeNode?.word_count || 0 }}
        </span>
        <button @click="store.toggleModal('omnibar', true)" class="px-2.5 py-1 bg-zinc-900/80 border border-zinc-800 hover:border-amber-500/50 text-zinc-400 hover:text-amber-400 rounded text-[10px] font-mono transition flex items-center gap-1.5 backdrop-blur">
          <Search class="w-3 h-3" /> Lore Check (Cmd+K)
        </button>
      </div>

      <div class="pointer-events-auto opacity-20 hover:opacity-100 transition-opacity duration-500">
        <button @click="store.toggleVoidMode()" class="px-3 py-1.5 bg-zinc-900/80 border border-zinc-800 hover:border-rose-500/50 text-zinc-400 hover:text-rose-400 rounded text-xs font-mono transition flex items-center gap-1.5 backdrop-blur">
          <DoorOpen class="w-3.5 h-3.5" /> Exit Void (Esc)
        </button>
      </div>
    </div>

    <!-- Standard Action Sub-Header -->
    <div v-if="store.activeNode?.id && !store.isVoidMode" class="h-9 border-b border-zinc-800/60 bg-zinc-900/40 px-6 flex items-center justify-between text-xs z-10 shrink-0 backdrop-blur-sm">
      <div class="flex items-center gap-4">
        <span class="text-[11px] text-zinc-500 font-mono">
          Words: <strong class="text-zinc-300 font-medium">{{ store.activeNode?.word_count || 0 }}</strong>
        </span>
        <div class="flex items-center gap-2 min-w-[160px]">
          <span class="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">Goal</span>
          <div class="h-1.5 w-24 bg-zinc-800 rounded-full overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 transition-all" :style="{ width: `${goalProgress}%` }"></div>
          </div>
          <span class="text-[10px] font-mono text-zinc-300">{{ Math.min(store.activeNode?.word_count || 0, wordTarget) }}/{{ wordTarget }}</span>
        </div>
        <span v-if="store.saveStatus" class="text-[10px] font-mono tracking-wider uppercase text-zinc-500">
          ● {{ store.saveStatus }}
        </span>
      </div>

      <div class="flex items-center space-x-2">
        <button @click="store.navigateScene(-1)" :disabled="!hasPreviousScene" title="Previous scene (Ctrl/Cmd+Alt+Left)" class="px-2 py-1 bg-zinc-800/80 border border-zinc-700/50 disabled:opacity-30 text-zinc-300 rounded text-xs transition">← Scene</button>
        <button @click="store.navigateScene(1)" :disabled="!hasNextScene" title="Next scene (Ctrl/Cmd+Alt+Right)" class="px-2 py-1 bg-zinc-800/80 border border-zinc-700/50 disabled:opacity-30 text-zinc-300 rounded text-xs transition">Scene →</button>
        
        <button @click="toggleXRay" :class="['px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition border', store.isXRayActive ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-[0_0_10px_rgba(245,158,11,0.15)]' : 'bg-zinc-800/80 border-zinc-700/50 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800']">
          <Eye class="w-3.5 h-3.5" /> <span>Craft X-Ray</span>
        </button>

        <button @click="toggleGutterBadges" :class="['px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition border', showGutterBadges ? 'bg-violet-500/20 text-violet-300 border-violet-500/40' : 'bg-zinc-800/80 border-zinc-700/50 text-zinc-400 hover:text-zinc-200']" title="Toggle Reader Beat Gutter Pins">
          <Compass class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Reader Gutter</span>
        </button>

        <button @click="store.toggleVoidMode()" class="px-2.5 py-1 bg-zinc-800/80 border border-zinc-700/50 hover:bg-zinc-800 text-zinc-300 rounded text-xs font-medium flex items-center gap-1.5 transition">
          <Moon class="w-3.5 h-3.5" /> <span>The Void</span>
        </button>

        <button @click="runMasterTriage" class="px-2.5 py-1 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded text-xs font-medium flex items-center gap-1.5 transition shadow-[0_0_8px_rgba(6,182,212,0.15)]">
          <Wand2 class="w-3.5 h-3.5" /> <span class="hidden md:inline">Triage Draft</span>
        </button>
      </div>
    </div>

    <!-- Craft X-Ray Visual Key Legend Tray -->
    <div v-if="store.isXRayActive && !store.isVoidMode" class="bg-zinc-950/95 border-b border-zinc-800/80 px-6 py-2 flex flex-col sm:flex-row sm:items-center justify-between text-[10px] font-mono gap-2 shrink-0 animate-fade-in">
      <div class="flex items-center gap-1.5 overflow-x-auto">
        <span class="text-zinc-500 uppercase tracking-wider font-bold mr-1">Lens:</span>
        <button @click="activeXRayLens = 'energetics'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'energetics' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">⚡ Energetics</button>
        <button @click="activeXRayLens = 'clutter'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'clutter' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">🔍 Clutter & Filters</button>
        <button @click="activeXRayLens = 'cadence'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'cadence' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">🎵 Cadence</button>
      </div>

      <div class="flex flex-wrap items-center gap-2 text-[9px] text-zinc-400">
        <label class="flex items-center gap-1.5">
          <span>Staccato</span>
          <input v-model.number="xraySettings.staccato_threshold" type="range" min="4" max="12" class="accent-amber-500" @change="refreshXRay" />
          <strong class="text-zinc-200 font-mono">{{ xraySettings.staccato_threshold }}</strong>
        </label>
        <label class="flex items-center gap-1.5">
          <span>Expansive</span>
          <input v-model.number="xraySettings.expansive_threshold" type="range" min="15" max="35" class="accent-cyan-500" @change="refreshXRay" />
          <strong class="text-zinc-200 font-mono">{{ xraySettings.expansive_threshold }}</strong>
        </label>
      </div>
    </div>

    <!-- Active Writing Canvas with Interactive Gutter -->
    <div 
      ref="scrollContainer" 
      @scroll="handleEditorScroll" 
      v-if="store.activeNode?.id" 
      :class="['flex-1 flex flex-col max-w-4xl w-full mx-auto overflow-y-auto custom-scrollbar relative', store.isVoidMode ? 'p-8 md:p-20 mt-6' : 'p-6 md:p-12']"
    >
      <input 
        v-model="store.activeNode.title" 
        @input="queueAutoSave" 
        class="bg-transparent text-2xl md:text-4xl font-serif font-bold tracking-tight border-none focus:outline-none mb-8 placeholder-zinc-700 transition-colors" 
        :class="store.isCandlelight ? 'text-amber-100/90' : 'text-zinc-100'" 
        placeholder="Scene Title..." 
      />
      
      <!-- Formatting Toolbar -->
      <div v-show="!store.isXRayActive && !store.isVoidMode" class="flex items-center gap-1 mb-3 rounded-lg border border-zinc-800 bg-zinc-950/70 p-1 w-fit" role="toolbar">
        <button @mousedown.prevent @click="toggleMark('bold')" :class="['p-2 rounded transition', activeMarks.bold ? 'bg-amber-500/20 text-amber-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white']" title="Bold (Ctrl/Cmd+B)"><Bold class="w-4 h-4" /></button>
        <button @mousedown.prevent @click="toggleMark('italic')" :class="['p-2 rounded transition', activeMarks.italic ? 'bg-amber-500/20 text-amber-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white']" title="Italic (Ctrl/Cmd+I)"><Italic class="w-4 h-4" /></button>
      </div>

      <!-- Main Editor Container (Prose + Live Gutter) -->
      <div class="flex gap-4 relative">
        
        <!-- Live Reader Gutter Badges -->
        <div v-if="showGutterBadges && !store.isVoidMode" class="w-24 shrink-0 space-y-6 pt-1 select-none hidden md:block">
          <div 
            v-for="(diag, idx) in paragraphDiagnoses" 
            :key="idx" 
            @click="jumpToDiagnostic(idx + 1)"
            class="group cursor-pointer rounded-lg border p-1 text-[9px] font-mono leading-tight transition flex items-center gap-1.5 shadow-sm"
            :class="getGutterBadgeClass(diag)"
            :title="diag.reader_experience"
          >
            <span>{{ getGutterIcon(diag) }}</span>
            <span class="truncate">{{ getGutterShortLabel(diag) }}</span>
          </div>
        </div>

        <!-- TipTap WYSIWYG Editor Surface -->
        <div class="flex-1 min-w-0">
          <editor-content 
            v-show="!store.isXRayActive" 
            :editor="editor" 
            class="font-serif text-lg md:text-xl leading-relaxed outline-none min-h-[350px]" 
            :class="store.isCandlelight ? 'text-amber-100/90' : 'text-zinc-200'" 
          />
          
          <!-- Craft X-Ray Overlay -->
          <div v-show="store.isXRayActive" class="prose-canvas font-serif text-lg md:text-xl leading-relaxed space-y-6">
            <div v-if="isXRayLoading" class="py-12 text-center text-xs font-mono text-amber-400 flex items-center justify-center gap-2">
              <RotateCcw class="w-4 h-4 animate-spin" /> Analyzing sentence energetics...
            </div>
            <div v-else>
              <p v-for="(paraBlock, pIdx) in store.xraySentences" :key="pIdx" class="xray-paragraph">
                <span 
                  v-for="(s, sIdx) in paraBlock" 
                  :key="sIdx" 
                  :class="['xray-sentence group relative cursor-pointer', getSentenceLensClass(s)]" 
                  @click="handleXRaySentenceClick(s.text, pIdx + 1)"
                >
                  <span v-if="activeXRayLens === 'clutter' && s.clutter_html" v-html="s.clutter_html"></span>
                  <span v-else>{{ s.text }}</span>{{ ' ' }}
                  <span class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-zinc-950 text-zinc-200 text-[10px] font-mono rounded-lg shadow-2xl border border-zinc-700 z-50 whitespace-nowrap pointer-events-none">
                    {{ getSentenceTooltip(s) }}
                  </span>
                </span>
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="flex-1 flex items-center justify-center overflow-y-auto p-6 select-none">
      <div class="w-full max-w-lg rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6 md:p-8 shadow-xl text-center space-y-4">
        <Feather class="w-10 h-10 text-amber-500/70 mx-auto" />
        <h2 class="text-xl font-serif font-semibold text-zinc-100">Ready to draft</h2>
        <p class="text-sm text-zinc-400 leading-relaxed">Select a scene from the Binder to begin writing, or create a new chapter.</p>
        <button @click="store.createScene()" class="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold text-xs transition">Create Scene</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { Eye, Moon, Wand2, RotateCcw, Feather, Search, DoorOpen, Bold, Italic, Compass } from '@lucide/vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Typography from '@tiptap/extension-typography'

import { API_BASE } from '@/api'
import { contentToHtml, htmlToText } from '../editorText.js'

const isXRayLoading = ref(false)
const showGutterBadges = ref(true)
const activeXRayLens = ref('energetics')
const xraySettings = ref({
  staccato_threshold: 9,
  expansive_threshold: 22,
  clutter_sensitivity: 2
})

const wordTarget = computed(() => Number(store.activeNode?.card?.word_target) || 500)
const goalProgress = computed(() => {
  const target = wordTarget.value || 1
  return Math.min(100, Math.round(((Number(store.activeNode?.word_count) || 0) / target) * 100))
})

const paragraphDiagnoses = computed(() => {
  return store.readerStoryCache?.analyses?.find(a => a.scene_id === store.activeNode?.id)?.analysis?.paragraph_diagnoses || []
})

const bookScenes = computed(() => {
  const scenes = []
  const visit = (nodes) => {
    for (const node of nodes || []) {
      if (node.node_type === 'SCENE') scenes.push(node)
      visit(node.children)
    }
  }
  visit(store.getBook()?.children || [])
  return scenes
})

const activeSceneIndex = computed(() => bookScenes.value.findIndex(scene => scene.id === store.activeNode?.id))
const hasPreviousScene = computed(() => bookScenes.value.length > 0 && activeSceneIndex.value > 0)
const hasNextScene = computed(() => bookScenes.value.length > 0 && activeSceneIndex.value < bookScenes.value.length - 1)

const scrollContainer = ref(null)
let editor = null
let scrollThrottle = null
let hasPendingSave = false
let savePromise = null
const activeMarks = ref({ bold: false, italic: false })

const updateActiveMarks = () => {
  if (!editor) return
  activeMarks.value = { bold: editor.isActive('bold'), italic: editor.isActive('italic') }
}

const toggleMark = (mark) => {
  if (!editor) return
  editor.chain().focus()[mark]().run()
  updateActiveMarks()
}

const toggleGutterBadges = () => {
  showGutterBadges.value = !showGutterBadges.value
}

// Gutter Badge Helpers
const getGutterIcon = (diag) => {
  switch (diag.cognitive_function) {
    case 'KINETIC_ACTION': return '⚡'
    case 'VISCERAL_GROUNDING': return '🏛️'
    case 'SOCIAL_HIERARCHY': return '⚖️'
    case 'SPATIAL_BLUEPRINT': return '🏰'
    case 'INTERIOR_STAKES': return '🧠'
    case 'DIALOGUE_SUBTEXT': return '💬'
    case 'RESOLVE_CLIMAX': return '⚔️'
    case 'CONTINGENCY_HOOK': return '🪝'
    case 'STACCATO_PULSE': return '💓'
    case 'SEMANTIC_SLACK_ALERT': return '✂️'
    case 'WHITE_ROOM_ALERT': return '🔍'
    default: return '●'
  }
}

const getGutterShortLabel = (diag) => {
  switch (diag.cognitive_function) {
    case 'KINETIC_ACTION': return 'Action'
    case 'VISCERAL_GROUNDING': return 'Sensory'
    case 'SOCIAL_HIERARCHY': return 'Status'
    case 'SPATIAL_BLUEPRINT': return 'Layout'
    case 'INTERIOR_STAKES': return 'Stakes'
    case 'DIALOGUE_SUBTEXT': return 'Dialogue'
    case 'RESOLVE_CLIMAX': return 'Resolve'
    case 'CONTINGENCY_HOOK': return 'Hook'
    case 'STACCATO_PULSE': return 'Pulse'
    case 'SEMANTIC_SLACK_ALERT': return 'Trim?'
    case 'WHITE_ROOM_ALERT': return 'Anchor?'
    default: return 'Flow'
  }
}

const getGutterBadgeClass = (diag) => {
  switch (diag.cognitive_function) {
    case 'SEMANTIC_SLACK_ALERT': return 'bg-amber-950/40 text-amber-300 border-amber-900/60 hover:bg-amber-900/60'
    case 'WHITE_ROOM_ALERT': return 'bg-rose-950/40 text-rose-300 border-rose-900/60 hover:bg-rose-900/60'
    case 'VISCERAL_GROUNDING': return 'bg-emerald-950/40 text-emerald-300 border-emerald-900/60 hover:bg-emerald-900/60'
    case 'KINETIC_ACTION': return 'bg-cyan-950/40 text-cyan-300 border-cyan-900/60 hover:bg-cyan-900/60'
    case 'SOCIAL_HIERARCHY': return 'bg-purple-950/40 text-purple-300 border-purple-900/60 hover:bg-purple-900/60'
    default: return 'bg-zinc-950/80 text-zinc-400 border-zinc-800 hover:border-zinc-700 hover:text-zinc-200'
  }
}

// Two-way synchronization: click gutter badge to highlight paragraph in inspector
const jumpToDiagnostic = (pNum) => {
  store.activeInspectorTab = 'reader'
  window.dispatchEvent(new CustomEvent('lens-beat-jump', { detail: { beat: pNum } }))
}

const handleXRaySentenceClick = (text, pNum) => {
  store.selectedText = text
  store.activeInspectorTab = 'reader'
  window.dispatchEvent(new CustomEvent('lens-beat-jump', { detail: { beat: pNum } }))
}

const initEditor = () => {
  if (editor) editor.destroy()
  
  editor = new Editor({
    content: contentToHtml(store.activeNode?.content) || '',
    extensions: [
      StarterKit, 
      Typography, 
      Placeholder.configure({ placeholder: 'Lay down the first sentence...' })
    ],
    editorProps: { attributes: { class: 'ProseMirror outline-none prose-canvas focus:outline-none min-h-[300px]' } },
    onUpdate: () => {
      const serialized = editor.getHTML()
      const text = htmlToText(serialized)
      if (!store.activeNode) return
      store.activeNode.content = serialized
      store.activeNode.word_count = text.split(/\s+/).filter(Boolean).length
      queueAutoSave()
    },
    onSelectionUpdate: () => updateActiveMarks(),
    onTransaction: () => updateActiveMarks()
  })
}

watch(() => store.activeNode?.id, async (newId) => {
  if (newId) {
    store.xraySentences = []
    if (!editor) {
      initEditor()
    } else {
      const currentHtml = editor.getHTML()
      const storedHtml = contentToHtml(store.activeNode.content)
      if (currentHtml !== storedHtml) {
        editor.commands.setContent(storedHtml || '')
      }
    }
    if (store.isXRayActive && store.activeNode?.content) {
      await fetchXRayAnalysis()
    }
  }
})

let saveTimeout = null
const queueAutoSave = () => {
  hasPendingSave = true
  store.saveStatus = 'Saving...'
  clearTimeout(saveTimeout)
  saveTimeout = setTimeout(persistActiveScene, 1200)
}

const persistActiveScene = async () => {
  const node = store.activeNode
  if (!node?.id || !hasPendingSave) return true
  hasPendingSave = false
  store.saveStatus = 'Saving...'
  try {
    const res = await fetch(`${API_BASE}/api/node/${node.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: node.title,
        synopsis: node.synopsis || '',
        content: editor?.getHTML() || '',
        status: node.status || 'DRAFT'
      })
    })
    if (!res.ok) throw new Error('Save failed')
    store.saveStatus = 'Saved'
    return true
  } catch(e) {
    hasPendingSave = true
    store.saveStatus = 'Save failed'
    return false
  }
}

const fetchXRayAnalysis = async () => {
  if (!store.activeNode?.content) return
  isXRayLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/craft/xray`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({
        text: htmlToText(store.activeNode.content),
        staccato_threshold: xraySettings.value.staccato_threshold,
        expansive_threshold: xraySettings.value.expansive_threshold,
        clutter_sensitivity: xraySettings.value.clutter_sensitivity
      })
    })
    if (!res.ok) throw new Error('X-Ray extraction failed')
    const data = await res.json()
    store.xraySentences = data.paragraphs || [data.sentences] || []
  } catch(e) { 
    showToast(e.message, 'error') 
  } finally {
    isXRayLoading.value = false
  }
}

const toggleXRay = async () => {
  store.isXRayActive = !store.isXRayActive
  if (store.isXRayActive) await fetchXRayAnalysis()
}

const getSentenceLensClass = (s) => {
  if (!s) return 'text-zinc-300'
  if (activeXRayLens.value === 'energetics') {
    switch (s.energetics_type || s.type || '') {
      case 'ESCALATOR': return 'xray-escalator'
      case 'RESOLVER': return 'xray-resolver'
      case 'PIVOT': return 'xray-pivot'
      case 'SLACK': return 'xray-slack'
      default: return 'text-zinc-300'
    }
  } else if (activeXRayLens.value === 'cadence') {
    const words = s.words || (s.text ? s.text.split(' ').length : 12)
    if (words <= xraySettings.value.staccato_threshold) return 'xray-escalator'
    if (words >= xraySettings.value.expansive_threshold) return 'xray-resolver'
    return 'text-zinc-300'
  } else if (activeXRayLens.value === 'clutter') {
    return s.has_clutter ? 'bg-zinc-900/60' : 'text-zinc-300'
  }
  return 'text-zinc-300'
}

const getSentenceTooltip = (s) => s.energetics_reason || s.reason || ''

const runMasterTriage = async () => {
  if (!store.activeNode?.id) return
  store.saveStatus = 'Cleaning draft...'
  try {
    const res = await fetch(`${API_BASE}/api/binder/triage-scene/${store.activeNode.id}`, { method: 'POST' })
    if (!res.ok) throw new Error('Triage failed')
    const data = await res.json()
    if (data.status === 'success') {
      if (editor) editor.commands.setContent(contentToHtml(data.formatted_text))
      store.activeNode.content = editor?.getHTML() || data.formatted_text
      showToast('Draft cleaned and formatted.', 'info')
      queueAutoSave()
    }
  } catch(e) {
    showToast(e.message, 'error')
  }
}

onMounted(() => {
  if (store.activeNode?.id) initEditor()
})

onBeforeUnmount(() => {
  if (editor) editor.destroy()
})
</script>

<style>
.ProseMirror p { margin-bottom: 1.5em; line-height: 1.85; }
.ProseMirror p.is-editor-empty:first-child::before {
  content: attr(data-placeholder); float: left; color: #52525b; pointer-events: none; height: 0;
}
.xray-paragraph { margin-bottom: 1.5em; line-height: 1.85; }
.xray-sentence { display: inline; padding: 2px 2px; border-radius: 3px; transition: all 0.2s ease; }
.xray-sentence:hover { filter: brightness(1.2); }
.xray-escalator { background-color: rgba(239, 68, 68, 0.2); color: #fca5a5; border-bottom: 2px solid rgba(239, 68, 68, 0.6); }
.xray-resolver { background-color: rgba(16, 185, 129, 0.2); color: #6ee7b7; border-bottom: 2px solid rgba(16, 185, 129, 0.6); }
.xray-pivot { background-color: rgba(245, 158, 11, 0.25); color: #fcd34d; border-bottom: 2px solid rgba(245, 158, 11, 0.7); }
.xray-slack { background-color: rgba(113, 113, 122, 0.2); color: #a1a1aa; text-decoration: underline dotted #71717a; }
.clutter-filter { background-color: rgba(244, 63, 94, 0.35); color: #fda4af; border-bottom: 2px solid #f43f5e; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
.clutter-crutch { background-color: rgba(245, 158, 11, 0.35); color: #fde68a; border-bottom: 2px solid #f59e0b; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
</style>
