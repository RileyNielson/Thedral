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
      
      <!-- 4 Lens Toggle Pills -->
      <div class="flex items-center gap-1.5 overflow-x-auto">
        <span class="text-zinc-500 uppercase tracking-wider font-bold mr-1">Lens:</span>
        <button @click="activeXRayLens = 'energetics'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'energetics' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">⚡ Energetics</button>
        <button @click="activeXRayLens = 'signals'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'signals' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">Selected word cues</button>
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
        <label class="flex items-center gap-1.5">
          <span>Clutter</span>
          <input v-model.number="xraySettings.clutter_sensitivity" type="range" min="1" max="4" class="accent-rose-500" @change="refreshXRay" />
          <strong class="text-zinc-200 font-mono">{{ xraySettings.clutter_sensitivity }}</strong>
        </label>
      </div>

      <!-- Dynamic Lens Legend -->
      <div class="flex items-center gap-3 overflow-x-auto text-[9px] text-zinc-400">
        <!-- 1. Energetics Key -->
        <template v-if="activeXRayLens === 'energetics'">
          <span class="flex items-center gap-1 text-rose-300"><span class="w-2 h-2 rounded-sm bg-rose-500/30 border border-rose-500"></span> Staccato (&lt;9w)</span>
          <span class="flex items-center gap-1 text-amber-300"><span class="w-2 h-2 rounded-sm bg-amber-500/30 border border-amber-500"></span> Turning Hinge</span>
          <span class="flex items-center gap-1 text-emerald-300"><span class="w-2 h-2 rounded-sm bg-emerald-500/30 border border-emerald-500"></span> Lyrical Flow (22w+)</span>
          <span class="flex items-center gap-1 text-zinc-500"><span class="w-2 h-2 rounded-sm border border-zinc-700 bg-transparent"></span> Clean Baseline</span>
        </template>

        <!-- 2. Selected word-cue key -->
        <template v-else-if="activeXRayLens === 'signals'">
          <span class="flex items-center gap-1 text-rose-300"><span class="w-2 h-2 rounded-sm bg-rose-500/40"></span> Action</span>
          <span class="flex items-center gap-1 text-purple-300"><span class="w-2 h-2 rounded-sm bg-purple-500/40"></span> Relational</span>
          <span class="flex items-center gap-1 text-cyan-300"><span class="w-2 h-2 rounded-sm bg-cyan-500/40"></span> Mystery</span>
          <span class="flex items-center gap-1 text-emerald-300"><span class="w-2 h-2 rounded-sm bg-emerald-500/40"></span> Sensory</span>
          <span class="text-zinc-500">Selected lexical cues only; not reader reactions.</span>
        </template>

        <!-- 3. Clutter Key -->
        <template v-else-if="activeXRayLens === 'clutter'">
          <span class="flex items-center gap-1 text-rose-300"><span class="w-2 h-2 rounded-sm bg-rose-500/30 border border-rose-500"></span> Filter Verbs (saw, felt)</span>
          <span class="flex items-center gap-1 text-amber-300"><span class="w-2 h-2 rounded-sm bg-amber-500/30 border border-amber-500"></span> Crutch Words (suddenly)</span>
        </template>

        <!-- 4. Cadence Key -->
        <template v-else-if="activeXRayLens === 'cadence'">
          <span class="flex items-center gap-1 text-rose-300"><span class="w-2 h-2 rounded-sm bg-rose-500/30"></span> Staccato (&lt;9w)</span>
          <span class="flex items-center gap-1 text-zinc-500"><span class="w-2 h-2 rounded-sm border border-zinc-700"></span> Baseline (9-21w)</span>
          <span class="flex items-center gap-1 text-emerald-300"><span class="w-2 h-2 rounded-sm bg-emerald-500/30"></span> Expansive (22w+)</span>
        </template>
      </div>
    </div>

    <!-- Severed Causal Thread Alert Banner -->
    <div v-if="store.activeNode?.severed_threads?.length && !store.isVoidMode" class="bg-rose-950/40 border-b border-rose-900/50 px-6 py-2 flex items-center justify-between text-xs text-rose-300 z-10 shrink-0 font-mono animate-fade-in">
      <div class="flex items-center gap-2">
        <Link2Off class="w-4 h-4 text-rose-400 shrink-0" />
        <span><strong>Severed Causal Thread:</strong> Paragraph anchoring a canonical fact was excised (Entity: {{ store.activeNode.severed_threads[0].entity_id }}).</span>
      </div>
      <button @click="dismissSeveredThreads" class="text-[10px] text-zinc-400 hover:text-white uppercase font-bold px-2 py-0.5 rounded bg-zinc-800">
        Acknowledge
      </button>
    </div>

    <!-- Active Writing Canvas (with Scroll Tracker for the 3D Reading Bead) -->
    <div ref="scrollContainer" @scroll="handleEditorScroll" v-if="store.activeNode?.id" :class="['flex-1 flex flex-col max-w-3xl w-full mx-auto overflow-y-auto custom-scrollbar relative', store.isVoidMode ? 'p-8 md:p-20 mt-6' : 'p-6 md:p-12']">
      <input v-model="store.activeNode.title" @input="queueAutoSave" class="bg-transparent text-2xl md:text-4xl font-serif font-bold tracking-tight border-none focus:outline-none mb-8 placeholder-zinc-700 transition-colors" :class="store.isCandlelight ? 'text-amber-100/90' : 'text-zinc-100'" placeholder="Scene Title..." />
      
      <!-- TipTap Rich Text Surface -->
      <div v-show="!store.isXRayActive" class="flex items-center gap-1 mb-3 rounded-lg border border-zinc-800 bg-zinc-950/70 p-1 w-fit" role="toolbar" aria-label="Text formatting">
        <button @mousedown.prevent @click="toggleMark('bold')" :aria-pressed="activeMarks.bold" aria-label="Bold (Ctrl/Cmd+B)" title="Bold (Ctrl/Cmd+B)" :class="['p-2 rounded transition', activeMarks.bold ? 'bg-amber-500/20 text-amber-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white']">
          <Bold class="w-4 h-4" />
        </button>
        <button @mousedown.prevent @click="toggleMark('italic')" :aria-pressed="activeMarks.italic" aria-label="Italic (Ctrl/Cmd+I)" title="Italic (Ctrl/Cmd+I)" :class="['p-2 rounded transition', activeMarks.italic ? 'bg-amber-500/20 text-amber-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white']">
          <Italic class="w-4 h-4" />
        </button>
        <span class="px-2 text-[9px] text-zinc-600 font-mono">Ctrl/Cmd+B / I</span>
      </div>
      <editor-content v-show="!store.isXRayActive" :editor="editor" class="flex-1 font-serif text-lg md:text-xl leading-relaxed outline-none min-h-[350px]" :class="store.isCandlelight ? 'text-amber-100/90' : 'text-zinc-200'" />
      
      <!-- Multi-Lens Analytical Overlay -->
      <div v-show="store.isXRayActive" class="prose-canvas flex-1 font-serif text-lg md:text-xl leading-relaxed space-y-6">
        <div v-if="isXRayLoading" class="py-12 text-center text-xs font-mono text-amber-400 flex items-center justify-center gap-2">
          <RotateCcw class="w-4 h-4 animate-spin" /> Analyzing prose lens...
        </div>
        <div v-else>
          <p v-for="(paraBlock, pIdx) in store.xraySentences" :key="pIdx" class="xray-paragraph">
            <span v-for="(s, sIdx) in paraBlock" :key="sIdx" :class="['xray-sentence group relative cursor-pointer', getSentenceLensClass(s)]" @click="handleXRaySentenceClick(s.text)">
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
    
    <!-- Empty State -->
    <div v-else class="flex-1 flex items-center justify-center overflow-y-auto p-6 select-none">
      <div class="w-full max-w-lg rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6 md:p-8 shadow-xl">
        <Feather class="w-10 h-10 text-amber-500/70 mb-4" />
        <template v-if="!store.tree?.length">
          <p class="text-[10px] uppercase tracking-[0.2em] text-amber-400 font-mono mb-2">A place to begin</p>
          <h2 class="text-xl font-serif font-semibold text-zinc-100 mb-2">Your next story starts here.</h2>
          <p class="text-sm text-zinc-400 leading-relaxed mb-5">Create a manuscript to get a Binder, your first chapter, and a blank scene ready for drafting—or bring in a draft you already have.</p>
          <div class="space-y-2 mb-6 text-xs text-zinc-400">
            <div class="flex gap-2"><span class="text-amber-400 font-mono">01</span><span>Organize chapters and scenes in the Binder.</span></div>
            <div class="flex gap-2"><span class="text-amber-400 font-mono">02</span><span>Write in the center workspace; your changes save automatically.</span></div>
            <div class="flex gap-2"><span class="text-amber-400 font-mono">03</span><span>Use the Inspector on the right for goals, notes, and craft feedback.</span></div>
          </div>
          <div class="flex flex-wrap gap-2">
            <button @click="store.createManuscript()" class="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold text-xs transition">Create a manuscript</button>
            <button @click="store.toggleModal('import', true)" class="px-4 py-2 rounded-lg border border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 text-xs transition">Import a draft</button>
          </div>
        </template>
        <template v-else>
          <p class="text-[10px] uppercase tracking-[0.2em] text-amber-400 font-mono mb-2">Ready when you are</p>
          <h2 class="text-xl font-serif font-semibold text-zinc-100 mb-2">Choose a scene to start writing.</h2>
          <p class="text-sm text-zinc-400 leading-relaxed">Your projects and chapters are in the Binder on the left. Select a scene to open it here, or use the Binder’s add buttons to create one.</p>
        </template>
      </div>
    </div>

    <!-- Floating Socratic & Entity Toolbar -->
    <div v-if="store.selectedText && !store.isVoidMode" class="absolute bottom-6 left-1/2 -translate-x-1/2 bg-zinc-900/95 border border-amber-500/40 rounded-full px-4 py-2 shadow-2xl flex items-center space-x-2 z-30 backdrop-blur-md animate-fade-in">
      <span class="text-xs text-zinc-300 font-mono truncate max-w-[140px] sm:max-w-[180px] mr-1">"{{ store.selectedText }}"</span>
      <button @click="elevateSelection" title="Consult Socratic Mirror" class="bg-amber-600 hover:bg-amber-500 text-zinc-950 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5 transition shadow"><Sparkles class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Elevate</span></button>
      <button @click="registerSelection('CHARACTER')" title="Track as Character" class="bg-zinc-800 hover:bg-zinc-700 text-amber-300 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1 transition"><UserPlus class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Character</span></button>
      <button @click="registerSelection('ITEM')" title="Track as Artifact" class="bg-zinc-800 hover:bg-zinc-700 text-cyan-300 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1 transition"><Key class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Artifact</span></button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { Eye, Moon, Wand2, RotateCcw, X, Feather, Search, DoorOpen, Sparkles, UserPlus, Key, Link2Off, Bold, Italic } from '@lucide/vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Typography from '@tiptap/extension-typography'

import { API_BASE } from '@/api'
import { contentToHtml, htmlToText } from '../editorText.js'

const isXRayLoading = ref(false)
const activeXRayLens = ref('energetics') // 'energetics' | 'signals' | 'clutter' | 'cadence'
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
const hasPreviousScene = computed(() => bookScenes.value.length > 0 && activeSceneIndex.value !== 0)
const hasNextScene = computed(() => bookScenes.value.length > 0 && (activeSceneIndex.value < 0 || activeSceneIndex.value < bookScenes.value.length - 1))
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

const syncSelectionFromEditor = () => {
  if (!editor) return
  const { from, to } = editor.state.selection
  if (from === to) {
    store.selectedText = ''
    return
  }
  const text = editor.state.doc.textBetween(from, to, ' ').trim()
  store.selectedText = text.length > 3 ? text : ''
}

const dismissSeveredThreads = () => {
  if (store.activeNode) {
    store.activeNode.severed_threads = []
  }
}

const handleEditorScroll = () => {
  if (!scrollContainer.value || scrollThrottle) return
  scrollThrottle = setTimeout(() => {
    scrollThrottle = null
    const el = scrollContainer.value
    if (!el) return
    const paragraphs = el.querySelectorAll('.ProseMirror p')
    if (!paragraphs.length) return

    const containerTop = el.getBoundingClientRect().top
    let currentBeat = 1
    paragraphs.forEach((p, idx) => {
      const rect = p.getBoundingClientRect()
      if (rect.top - containerTop <= 160) {
        currentBeat = idx + 1
      }
    })
    window.dispatchEvent(new CustomEvent('editor-scroll-beat', { detail: { beat: currentBeat } }))
  }, 100)
}

const handleSniperScroll = (e) => {
  const target = e.detail?.text
  if (!target || !editor) return

  let foundPos = null
  editor.state.doc.descendants((node, pos) => {
    if (foundPos !== null) return false
    if (node.isText) {
      const matchIdx = node.text.toLowerCase().indexOf(target.toLowerCase())
      if (matchIdx !== -1) {
        foundPos = pos + matchIdx
      }
    }
  })

  if (foundPos !== null) {
    editor.commands.focus()
    editor.commands.setTextSelection({ from: foundPos, to: foundPos + target.length })
    editor.view.dom.scrollIntoView({ behavior: 'smooth', block: 'center' })
    showToast(`🎯 Sniper-Scroll locked onto "${target}"`, 'info')
  }
}

const handleLensBeatJump = (e) => {
  const beatIdx = e.detail?.beat || 1
  const snippet = e.detail?.snippet || ''
  if (!scrollContainer.value) return

  const paragraphs = scrollContainer.value.querySelectorAll('.ProseMirror p')
  const targetP = paragraphs[beatIdx - 1]

  if (targetP) {
    targetP.scrollIntoView({ behavior: 'smooth', block: 'center' })
    targetP.classList.add('pulse-beat')
    setTimeout(() => { targetP.classList.remove('pulse-beat') }, 2200)
    showToast(`📍 Focused on Beat ${beatIdx}`, 'info')
  } else if (snippet) {
    handleSniperScroll({ detail: { text: snippet.substring(0, 30) } })
  }
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
    onSelectionUpdate: () => {
      syncSelectionFromEditor()
      updateActiveMarks()
    },
    onTransaction: () => {
      updateActiveMarks()
    }
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
  if (savePromise) {
    const inFlight = savePromise
    const saved = await inFlight
    if (!saved) return false
    if (!hasPendingSave) return true
  }
  const node = store.activeNode
  if (!node?.id || !hasPendingSave) return true
  const snapshot = {
    id: node.id,
    title: node.title,
    synopsis: node.synopsis || '',
    content: editor?.getHTML() || '',
    status: node.status || 'DRAFT',
    wordCount: node.word_count
  }
  hasPendingSave = false
  store.saveStatus = 'Saving...'
  const request = (async () => {
    try {
      const response = await fetch(`${API_BASE}/api/node/${snapshot.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: snapshot.title,
          synopsis: snapshot.synopsis,
          content: snapshot.content,
          status: snapshot.status
        })
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}: Save failed`)
      const treeNode = store.getBook()?.children?.flatMap(chapter => chapter.children || []).find(scene => scene.id === snapshot.id)
      if (treeNode) {
        treeNode.title = snapshot.title
        treeNode.word_count = snapshot.wordCount
      }
      store.saveStatus = 'Saved'
      window.dispatchEvent(new Event('refresh-tree'))
      return true
    } catch(e) { 
      hasPendingSave = true
      store.saveStatus = 'Save failed'
      showToast(`Save failed: ${e.message}`, 'error')
      return false
    }
  })()
  savePromise = request
  const saved = await request
  if (savePromise === request) savePromise = null
  if (saved && hasPendingSave) {
    clearTimeout(saveTimeout)
    return persistActiveScene()
  }
  return saved
}

const flushPendingSave = async () => {
  clearTimeout(saveTimeout)
  return persistActiveScene()
}

const warnBeforeLeaving = (event) => {
  if (!hasPendingSave && !savePromise) return
  event.preventDefault()
  event.returnValue = ''
}

store.flushPendingSave = flushPendingSave
onBeforeUnmount(async () => {
  await flushPendingSave()
  if (store.flushPendingSave === flushPendingSave) store.flushPendingSave = null
})

const fetchXRayAnalysis = async () => {
  if (!store.activeNode?.content) {
    store.xraySentences = []
    return
  }
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
    if (data.paragraphs && data.paragraphs.length > 0) {
      store.xraySentences = data.paragraphs
    } else if (data.sentences && data.sentences.length > 0) {
      store.xraySentences = [data.sentences]
    } else {
      store.xraySentences = []
    }
  } catch(e) { 
    showToast(e.message, 'error') 
  } finally {
    isXRayLoading.value = false
  }
}

const refreshXRay = async () => {
  if (store.isXRayActive) {
    await fetchXRayAnalysis()
  }
}

const toggleXRay = async () => {
  store.isXRayActive = !store.isXRayActive
  if (store.isXRayActive) {
    await fetchXRayAnalysis()
  } else {
    store.xraySentences = []
  }
}

const getSentenceLensClass = (s) => {
  if (!s) return 'text-zinc-300'
  if (activeXRayLens.value === 'energetics') {
    const type = s.energetics_type || s.type || ''
    switch (type) {
      case 'ESCALATOR': return 'xray-escalator'
      case 'RESOLVER': return 'xray-resolver'
      case 'PIVOT': return 'xray-pivot'
      case 'SLACK': return 'xray-slack'
      default: return 'text-zinc-300'
    }
  } else if (activeXRayLens.value === 'signals') {
    const signalType = s.signal_type || ''
    switch (signalType) {
      case 'action_cues': return 'xray-action-cues'
      case 'relational_cues': return 'xray-relational-cues'
      case 'mystery_cues': return 'xray-mystery-cues'
      case 'sensory_cues': return 'xray-sensory-cues'
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

const getSentenceTooltip = (s) => {
  if (activeXRayLens.value === 'energetics') return s.energetics_reason || s.reason
  if (activeXRayLens.value === 'signals') return s.signal_reason
  if (activeXRayLens.value === 'cadence') return s.cadence_reason
  if (activeXRayLens.value === 'clutter') return s.clutter_reason
  return s.reason
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
    const res = await fetch(`${API_BASE}/api/craft/elevate`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        passage: store.selectedText, 
        surrounding: htmlToText(store.activeNode?.content || ''),
        scene_id: store.activeNode?.id 
      }) 
    })
    if (!res.ok) throw new Error('Elevation failed')
    const data = await res.json()
    store.socraticCritique = data.critique
    store.socraticAi = !!data.ai_generated
    store.activeCritiqueId = data.critique_id
    window.dispatchEvent(new Event('refresh-critiques'))
  } catch(e) { 
    showToast(e.message, 'error') 
  }
}

const registerSelection = async (type) => {
  if (!store.selectedText) return
  const name = store.selectedText
  try {
    const res = await fetch(`${API_BASE}/api/entities/quick-register`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ name, entity_type: type }) 
    })
    if (!res.ok) throw new Error('Registration failed')
    store.selectedText = ''
    showToast(`Tracked: "${name}" (${type})`, 'info')
  } catch(e) { 
    showToast(e.message, 'error') 
  }
}

const runMasterTriage = async () => {
  if (!store.activeNode?.id) return
  store.saveStatus = 'Running master cleanse...'
  try {
    const res = await fetch(`${API_BASE}/api/binder/triage-scene/${store.activeNode.id}`, { method: 'POST' })
    if (!res.ok) throw new Error('Triage failed')
    const data = await res.json()
    if (data.status === 'success') {
      if (editor) editor.commands.setContent(contentToHtml(data.formatted_text))
      store.activeNode.content = editor?.getHTML() || data.formatted_text
      let msg = 'Draft Triaged!'
      if (data.new_scenes > 0) msg += ` Splitting ${data.new_scenes} new scenes.`
      store.saveStatus = msg
      showToast(msg, 'info')
      if (data.new_scenes > 0) window.dispatchEvent(new Event('refresh-tree'))
      queueAutoSave()
    }
  } catch(e) { 
    showToast(e.message, 'error') 
  }
}

onMounted(() => { 
  if (store.activeNode?.id) initEditor() 
  window.addEventListener('sniper-scroll', handleSniperScroll)
  window.addEventListener('lens-beat-jump', handleLensBeatJump)
  window.addEventListener('beforeunload', warnBeforeLeaving)
})

onBeforeUnmount(() => { 
  if (editor) editor.destroy() 
  window.removeEventListener('sniper-scroll', handleSniperScroll)
  window.removeEventListener('lens-beat-jump', handleLensBeatJump)
  window.removeEventListener('beforeunload', warnBeforeLeaving)
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
.xray-action-cues { background-color: rgba(239, 68, 68, 0.25); color: #fca5a5; border-bottom: 2px solid rgba(239, 68, 68, 0.8); }
.xray-relational-cues { background-color: rgba(168, 85, 247, 0.25); color: #d8b4fe; border-bottom: 2px solid rgba(168, 85, 247, 0.8); }
.xray-mystery-cues { background-color: rgba(6, 182, 212, 0.25); color: #67e8f9; border-bottom: 2px solid rgba(6, 182, 212, 0.8); }
.xray-sensory-cues { background-color: rgba(16, 185, 129, 0.25); color: #6ee7b7; border-bottom: 2px solid rgba(16, 185, 129, 0.8); }
.clutter-filter { background-color: rgba(244, 63, 94, 0.35); color: #fda4af; border-bottom: 2px solid #f43f5e; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
.clutter-crutch { background-color: rgba(245, 158, 11, 0.35); color: #fde68a; border-bottom: 2px solid #f59e0b; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
.pulse-beat { background-color: rgba(34, 211, 238, 0.22) !important; border-left: 3px solid #22d3ee !important; padding-left: 8px !important; border-radius: 4px; transition: all 0.5s ease; }
</style>
