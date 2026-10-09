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
        <span v-if="store.saveStatus" class="text-[10px] font-mono tracking-wider uppercase text-zinc-500">
          ● {{ store.saveStatus }}
        </span>
      </div>

      <div class="flex items-center space-x-2">
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

    <!-- Craft X-Ray Legend Tray -->
    <div v-if="store.isXRayActive && !store.isVoidMode" class="bg-zinc-950/95 border-b border-zinc-800/80 px-6 py-2 flex flex-col sm:flex-row sm:items-center justify-between text-[10px] font-mono gap-2 shrink-0 animate-fade-in">
      <div class="flex items-center gap-1.5 overflow-x-auto">
        <span class="text-zinc-500 uppercase tracking-wider font-bold mr-1">Lens:</span>
        <button @click="activeXRayLens = 'energetics'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'energetics' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">⚡ Energetics</button>
        <button @click="activeXRayLens = 'neuro'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'neuro' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">🧬 Neuro-Spectrum</button>
        <button @click="activeXRayLens = 'clutter'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'clutter' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">🔍 Clutter & Filters</button>
        <button @click="activeXRayLens = 'cadence'" :class="['px-2 py-0.5 rounded transition', activeXRayLens === 'cadence' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-zinc-900 text-zinc-400 hover:text-white']">🎵 Cadence</button>
      </div>
    </div>

    <!-- Active Writing Canvas -->
    <div ref="scrollContainer" @scroll="handleEditorScroll" v-if="store.activeNode?.id" :class="['flex-1 flex flex-col max-w-3xl w-full mx-auto overflow-y-auto custom-scrollbar relative', store.isVoidMode ? 'p-8 md:p-20 mt-6' : 'p-6 md:p-12']">
      <input v-model="store.activeNode.title" @input="queueAutoSave" class="bg-transparent text-2xl md:text-4xl font-serif font-bold tracking-tight border-none focus:outline-none mb-8 placeholder-zinc-700 transition-colors" :class="store.isCandlelight ? 'text-amber-100/90' : 'text-zinc-100'" placeholder="Scene Title..." />
      <editor-content v-show="!store.isXRayActive" :editor="editor" class="flex-1 font-serif text-lg md:text-xl leading-relaxed outline-none min-h-[350px]" :class="store.isCandlelight ? 'text-amber-100/90' : 'text-zinc-200'" />
      
      <div v-show="store.isXRayActive" class="prose-canvas flex-1 font-serif text-lg md:text-xl leading-relaxed space-y-6">
        <div v-if="isXRayLoading" class="py-12 text-center text-xs font-mono text-amber-400 flex items-center justify-center gap-2"><RotateCcw class="w-4 h-4 animate-spin" /> Analyzing prose lens...</div>
        <div v-else>
          <p v-for="(paraBlock, pIdx) in store.xraySentences" :key="pIdx" class="xray-paragraph">
            <span v-for="(s, sIdx) in paraBlock" :key="sIdx" :class="['xray-sentence group relative cursor-pointer', getSentenceLensClass(s)]" @click="handleXRaySentenceClick(s.text)">
              <span v-if="activeXRayLens === 'clutter' && s.clutter_html" v-html="s.clutter_html"></span>
              <span v-else>{{ s.text }}</span>{{ ' ' }}
              <span class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-zinc-950 text-zinc-200 text-[10px] font-mono rounded-lg shadow-2xl border border-zinc-700 z-50 whitespace-nowrap pointer-events-none">{{ getSentenceTooltip(s) }}</span>
            </span>
          </p>
        </div>
      </div>
    </div>
    
    <div v-else class="flex-1 flex items-center justify-center text-zinc-600 select-none">
      <div class="text-center space-y-3">
        <Feather class="w-12 h-12 mx-auto text-zinc-800" />
        <p class="text-sm font-sans tracking-wide">Select a scene from the binder to begin crafting.</p>
      </div>
    </div>

    <!-- Floating Socratic Toolbar -->
    <div v-if="store.selectedText && !store.isVoidMode" class="absolute bottom-6 left-1/2 -translate-x-1/2 bg-zinc-900/95 border border-amber-500/40 rounded-full px-4 py-2 shadow-2xl flex items-center space-x-2 z-30 backdrop-blur-md animate-fade-in">
      <span class="text-xs text-zinc-300 font-mono truncate max-w-[140px] sm:max-w-[180px] mr-1">"{{ store.selectedText }}"</span>
      <button @click="elevateSelection" title="Consult Socratic Mirror" class="bg-amber-600 hover:bg-amber-500 text-zinc-950 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5 transition shadow"><Sparkles class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Elevate</span></button>
      <button @click="registerSelection('CHARACTER')" title="Track as Character" class="bg-zinc-800 hover:bg-zinc-700 text-amber-300 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1 transition"><UserPlus class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Character</span></button>
      <button @click="registerSelection('ITEM')" title="Track as Artifact" class="bg-zinc-800 hover:bg-zinc-700 text-cyan-300 text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1 transition"><Key class="w-3.5 h-3.5" /> <span class="hidden sm:inline">Artifact</span></button>
    </div>

  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { Eye, Moon, Wand2, RotateCcw, X, Feather, Search, DoorOpen, Sparkles, UserPlus, Key } from 'lucide-vue-next'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Typography from '@tiptap/extension-typography'

const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

const isXRayLoading = ref(false)
const activeXRayLens = ref('energetics')
const scrollContainer = ref(null)
let editor = null
let scrollThrottle = null

const textToHtml = (text) => {
  if (!text) return ''
  return text.split(/\n\n+/).map(p => `<p>${p.trim()}</p>`).join('')
}

const htmlToText = (html) => {
  if (!html) return ''
  let text = html.replace(/<\/p>\s*<p>/gi, '\n\n')
  text = text.replace(/<[^>]*>?/gm, '')
  return text.trim()
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
    content: textToHtml(store.activeNode?.content) || '',
    extensions: [
      StarterKit, 
      Typography, 
      Placeholder.configure({ placeholder: 'Lay down the first sentence...' })
    ],
    editorProps: { attributes: { class: 'ProseMirror outline-none prose-canvas focus:outline-none min-h-[300px]' } },
    onUpdate: () => {
      const text = htmlToText(editor.getHTML())
      if (!store.activeNode) return
      store.activeNode.content = text
      store.activeNode.word_count = text.split(/\s+/).filter(Boolean).length
      queueAutoSave()
    },
    onSelectionUpdate: () => {
      syncSelectionFromEditor()
    }
  })
}

watch(() => store.activeNode?.id, async (newId) => {
  if (newId) {
    store.xraySentences = []
    if (!editor) {
      initEditor()
    } else {
      const currentText = htmlToText(editor.getHTML())
      if (currentText !== store.activeNode.content) {
        editor.commands.setContent(textToHtml(store.activeNode.content) || '')
      }
    }
    if (store.isXRayActive && store.activeNode?.content) {
      await fetchXRayAnalysis()
    }
  }
})

let saveTimeout = null
const queueAutoSave = () => {
  store.saveStatus = 'Saving...'
  clearTimeout(saveTimeout)
  saveTimeout = setTimeout(async () => {
    if (!store.activeNode?.id) return
    try {
      const rawText = htmlToText(editor.getHTML())
      await fetch(`${API_BASE}/api/node/${store.activeNode.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: store.activeNode.title,
          synopsis: store.activeNode.synopsis || '',
          content: rawText,
          status: store.activeNode.status || 'DRAFT'
        })
      })
      store.saveStatus = 'Saved'
      window.dispatchEvent(new Event('refresh-tree'))
    } catch(e) { 
      store.saveStatus = 'Error'
      showToast('Save failed', 'error') 
    }
  }, 1200)
}

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
      body: JSON.stringify({ text: store.activeNode.content }) 
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
  } else if (activeXRayLens.value === 'neuro') {
    const nType = s.neuro_type || ''
    switch (nType) {
      case 'ADRENALINE': return 'xray-adrenaline'
      case 'OXYTOCIN': return 'xray-oxytocin'
      case 'DOPAMINE': return 'xray-dopamine'
      case 'SEROTONIN': return 'xray-serotonin'
      default: return 'text-zinc-300'
    }
  } else if (activeXRayLens.value === 'cadence') {
    const words = s.words || (s.text ? s.text.split(' ').length : 12)
    if (words <= 8) return 'xray-escalator'
    if (words >= 22) return 'xray-resolver'
    return 'text-zinc-300'
  } else if (activeXRayLens.value === 'clutter') {
    return s.has_clutter ? 'bg-zinc-900/60' : 'text-zinc-300'
  }
  return 'text-zinc-300'
}

const getSentenceTooltip = (s) => {
  if (activeXRayLens.value === 'energetics') return s.energetics_reason || s.reason
  if (activeXRayLens.value === 'neuro') return s.neuro_reason
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
        surrounding: store.activeNode?.content || '', 
        scene_id: store.activeNode?.id 
      }) 
    })
    if (!res.ok) throw new Error('Elevation failed')
    const data = await res.json()
    store.socraticCritique = data.critique
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
      if (editor) editor.commands.setContent(textToHtml(data.formatted_text))
      store.activeNode.content = data.formatted_text
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
})

onBeforeUnmount(() => { 
  if (editor) editor.destroy() 
  window.removeEventListener('sniper-scroll', handleSniperScroll)
  window.removeEventListener('lens-beat-jump', handleLensBeatJump)
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
.xray-adrenaline { background-color: rgba(239, 68, 68, 0.25); color: #fca5a5; border-bottom: 2px solid rgba(239, 68, 68, 0.8); }
.xray-oxytocin { background-color: rgba(168, 85, 247, 0.25); color: #d8b4fe; border-bottom: 2px solid rgba(168, 85, 247, 0.8); }
.xray-dopamine { background-color: rgba(6, 182, 212, 0.25); color: #67e8f9; border-bottom: 2px solid rgba(6, 182, 212, 0.8); }
.xray-serotonin { background-color: rgba(16, 185, 129, 0.25); color: #6ee7b7; border-bottom: 2px solid rgba(16, 185, 129, 0.8); }
.clutter-filter { background-color: rgba(244, 63, 94, 0.35); color: #fda4af; border-bottom: 2px solid #f43f5e; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
.clutter-crutch { background-color: rgba(245, 158, 11, 0.35); color: #fde68a; border-bottom: 2px solid #f59e0b; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
.pulse-beat { background-color: rgba(34, 211, 238, 0.22) !important; border-left: 3px solid #22d3ee !important; padding-left: 8px !important; border-radius: 4px; transition: all 0.5s ease; }
</style>
