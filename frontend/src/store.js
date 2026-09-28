import { reactive } from 'vue'

// Resolves dynamically to your Mac's IP when viewing from a phone
const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

// --- Toast System ---
export const toasts = reactive([])

export const showToast = (msg, type = 'error') => {
  const id = Date.now() + Math.random()
  toasts.push({ id, msg, type })
  setTimeout(() => {
    const idx = toasts.findIndex(t => t.id === id)
    if (idx > -1) toasts.splice(idx, 1)
  }, 5000)
}

// --- Global Reactive Store ---
export const store = reactive({
  // Hierarchy & Active Scene
  tree: [],
  activeNode: null,
  
  // Navigation & Workspace Layout
  viewMode: 'editor', // 'editor' | 'outline' | 'corkboard' | 'cosmograph'
  projectionMode: 'ALL',
  timeMode: 'chronological',
  activeInspectorTab: 'card', // 'card' | 'telemetry' | 'socratic' | 'reader' | 'lens'
  binderCollapsed: false,
  inspectorCollapsed: false,

  // Immersion & Editor Modes
  isVoidMode: false,
  isCandlelight: false,
  isXRayActive: false,
  xraySentences: [],

  // Editor Session State
  saveStatus: '',
  selectedText: '',
  socraticCritique: '',
  activeCritiqueId: null,
  tkMarkers: [],
  editorState: {
    previousWordCount: 0,
    keystrokeRepeatCount: 0,
    lastKeystrokeTime: Date.now()
  },

  // Modals & Panels
  modals: {
    import: false,
    vault: false,
    cast: false,
    career: false,
    connect: false,
    omnibar: false,
    lore: false,
    mobileBinder: false,
    mobileInspector: false
  },

  // Telemetry & Prose Analytics
  telemetry: {
    word_count: 0,
    readability_score: 0,
    pacing_velocity: 0,
    dialogue_ratio: 0,
    passive_ratio: 0,
    sensory_density: 0,
    sentiment_curve: []
  },

  // Socratic Mirror
  socraticMirror: {
    messages: [
      {
        role: 'assistant',
        text: 'The mirror is polished. What structural tension, subtextual tremor, or character dilemma shall we investigate?'
      }
    ],
    isLoading: false,
    critiqueFocus: 'unspoken_subtext'
  },

  // Narrative Horizons & Inferences
  activeDisclosures: [],
  sceneCritiques: [],
  astrolabeAnomalies: [],
  readerHorizon: {
    dramaticIronyGaps: [],
    projectedExpectations: [],
    readerKnownFacts: []
  },

  // Cosmograph Data
  cosmograph: {
    data: {
      nodes: [],
      edges: []
    },
    selectedNodeId: null,
    isLoading: false
  },

  // Registries
  vaultBooks: [],
  registeredEntities: [],
  loreRules: [],

  // Survey Progress
  surveyProgress: {
    active: false,
    current: 0,
    total: 0,
    percent: 0,
    current_title: '',
    extracted: 0
  },

  // ==========================================
  // Store Actions & Backend Bridges
  // ==========================================

  toggleVoidMode() {
    this.isVoidMode = !this.isVoidMode
  },

  toggleCandlelight() {
    this.isCandlelight = !this.isCandlelight
  },

  toggleXRay() {
    this.isXRayActive = !this.isXRayActive
  },

  setInspectorTab(tab) {
    this.activeInspectorTab = tab
    if (this.inspectorCollapsed) {
      this.inspectorCollapsed = false
    }
  },

  toggleModal(modalName, state = null) {
    if (this.modals[modalName] !== undefined) {
      this.modals[modalName] = state !== null ? state : !this.modals[modalName]
    }
  },

  // Fetch Binder Tree (Aligned to /api/tree)
  async fetchTree() {
    try {
      const res = await fetch(`${API_BASE}/api/tree`)
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch binder`)
      const data = await res.json()
      this.tree = data

      // Auto-load first scene if none active
      if (!this.activeNode?.id && this.tree.length > 0) {
        const first = this.findFirstScene(this.tree)
        if (first) await this.loadScene(first.id)
      }
    } catch (err) {
      showToast(err.message, 'error')
    }
  },

  // Correctly detects SCENE nodes from backend
  findFirstScene(nodes) {
    for (const node of nodes) {
      if (node.node_type === 'SCENE' || node.type === 'scene') return node
      if (node.children && node.children.length) {
        const found = this.findFirstScene(node.children)
        if (found) return found
      }
    }
    return null
  },

  // Load Scene (Aligned to /api/node/{id})
  async loadScene(nodeId) {
    if (!nodeId) return
    try {
      const res = await fetch(`${API_BASE}/api/node/${nodeId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load scene`)
      const data = await res.json()

      this.activeNode = data
      this.telemetry = data.telemetry || {}
      this.saveStatus = 'Loaded'

      // Hydrate disclosures and critiques in parallel
      fetch(`${API_BASE}/api/disclosures/scene/${nodeId}`)
        .then(r => r.json())
        .then(d => { this.activeDisclosures = d })
        .catch(() => {})

      fetch(`${API_BASE}/api/critiques/scene/${nodeId}`)
        .then(r => r.json())
        .then(c => { this.sceneCritiques = c })
        .catch(() => {})

      if (this.isXRayActive && data.content) {
        this.fetchXRayAnalysis()
      }
    } catch (err) {
      showToast(err.message, 'error')
    }
  },

  // Commit Scene Content (Aligned to PUT /api/node/{id})
  async saveActiveScene(htmlContent) {
    if (!this.activeNode?.id) return
    this.saveStatus = 'saving'

    try {
      const res = await fetch(`${API_BASE}/api/node/${this.activeNode.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: this.activeNode.title,
          synopsis: this.activeNode.synopsis || '',
          content: htmlContent,
          status: this.activeNode.status || 'DRAFT'
        })
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to persist scene`)
      this.activeNode.content = htmlContent
      this.activeNode.word_count = htmlContent.split(/\s+/).filter(Boolean).length
      this.saveStatus = 'saved'
    } catch (err) {
      this.saveStatus = 'error'
      showToast(err.message, 'error')
    }
  },

  // Craft X-Ray Analysis (Aligned to POST /api/craft/xray)
  async fetchXRayAnalysis() {
    if (!this.activeNode?.content) {
      this.xraySentences = []
      return
    }
    try {
      const res = await fetch(`${API_BASE}/api/craft/xray`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: this.activeNode.content })
      })
      if (!res.ok) return
      const data = await res.json()
      const paras = (this.activeNode.content || '').split("\n\n")
      let sentIdx = 0
      const blocks = []
      for (const p of paras) {
        const pLen = p.trim().length
        let currentBlock = []
        let collectedLen = 0
        while (sentIdx < data.sentences.length && collectedLen < pLen) {
          currentBlock.push(data.sentences[sentIdx])
          collectedLen += data.sentences[sentIdx].text.length + 1
          sentIdx++
        }
        if (currentBlock.length) blocks.push(currentBlock)
      }
      this.xraySentences = blocks.length ? blocks : [data.sentences]
    } catch (err) {
      console.warn('[Thedral X-Ray]', err)
    }
  },

  // Socratic Mirror Query
  async querySocraticMirror(promptText) {
    if (!promptText.trim()) return

    this.socraticMirror.messages.push({ role: 'user', text: promptText })
    this.socraticMirror.isLoading = true

    try {
      const res = await fetch(`${API_BASE}/api/craft/elevate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scene_id: this.activeNode?.id,
          passage: promptText,
          surrounding: this.activeNode?.content || ''
        })
      })

      if (!res.ok) throw new Error('Socratic bridge failed')
      const data = await res.json()
      
      this.socraticMirror.messages.push({
        role: 'assistant',
        text: data.critique
      })
    } catch (err) {
      this.socraticMirror.messages.push({
        role: 'assistant',
        text: `The Socratic lens encountered an error: ${err.message}`
      })
      showToast(err.message, 'error')
    } finally {
      this.socraticMirror.isLoading = false
    }
  },

  // Cosmograph Spacetime (Aligned to /api/narrative/astrolabe)
  async fetchCosmographData() {
    this.cosmograph.isLoading = true
    try {
      const bId = this.activeNode?.book_id || (this.tree[0] && this.tree[0].id) || ''
      const res = await fetch(`${API_BASE}/api/narrative/astrolabe?book_id=${bId}`)
      if (!res.ok) throw new Error('Failed to load narrative spacetime manifold')
      const data = await res.json()
      this.cosmograph.data = data
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      this.cosmograph.isLoading = false
    }
  },

  // Cast Directory (Aligned to /api/entities)
  async fetchCast() {
    try {
      const res = await fetch(`${API_BASE}/api/entities`)
      if (res.ok) {
        this.registeredEntities = await res.json()
      }
    } catch (err) {
      console.warn('[Thedral Cast]', err)
    }
  },

  // Lore Lexicon (Aligned to /api/lore)
  async fetchLore() {
    try {
      const res = await fetch(`${API_BASE}/api/lore`)
      if (res.ok) {
        this.loreRules = await res.json()
      }
    } catch (err) {
      console.warn('[Thedral Lore]', err)
    }
  }
})