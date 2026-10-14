import { reactive } from 'vue'

import { API_BASE } from './api'

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

const contentToPlainText = (content = '') => {
  if (typeof DOMParser === 'undefined') return content.replace(/<[^>]*>/g, ' ')
  const parsed = new DOMParser().parseFromString(content, 'text/html')
  const paragraphs = Array.from(parsed.body.querySelectorAll('p, li, blockquote'))
    .map(paragraph => paragraph.textContent.trim())
    .filter(Boolean)
  return paragraphs.length ? paragraphs.join('\n\n') : parsed.body.textContent || ''
}

// --- Global Reactive Store ---
const savedTheme = typeof window !== 'undefined' ? (window.localStorage.getItem('thedral-theme') || 'midnight') : 'midnight'
const savedRecentScenes = typeof window !== 'undefined'
  ? (() => {
      try { return JSON.parse(window.localStorage.getItem('thedral-recent-scenes') || '[]') } catch { return [] }
    })()
  : []

export const store = reactive({
  // Hierarchy & Active Scene
  tree: [],
  activeNode: null,
  runtimeStatus: null,
  activeBookId: typeof window !== 'undefined' ? (window.localStorage.getItem('thedral-active-book') || '') : '',
  recentSceneIds: Array.isArray(savedRecentScenes) ? savedRecentScenes.filter(id => typeof id === 'string').slice(0, 8) : [],
  flushPendingSave: null,
  
  // Navigation & Workspace Layout
  viewMode: 'editor', // 'editor' | 'outline' | 'corkboard' | 'cosmograph'
  projectionMode: 'ALL',
  timeMode: 'chronological',
  activeInspectorTab: 'card', // 'card' | 'telemetry' | 'socratic' | 'reader' | 'lens'
  binderCollapsed: false,
  inspectorCollapsed: false,

  // Immersion & Editor Modes
  isVoidMode: false,
  isCandlelight: savedTheme === 'candlelight',
  colorScheme: savedTheme,
  isXRayActive: false,
  xraySentences: [],

  // Editor Session State
  saveStatus: '',
  selectedText: '',
  socraticCritique: '',
  socraticAi: false,
  socraticAi: false,
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
    export: false,
    review: false,
    submission: false,
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
  readerStoryCache: null,
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

  setColorScheme(scheme) {
    const allowed = ['midnight', 'candlelight', 'forest', 'violet', 'ocean', 'rose', 'graphite']
    const nextScheme = allowed.includes(scheme) ? scheme : 'midnight'
    this.colorScheme = nextScheme
    this.isCandlelight = nextScheme === 'candlelight'
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('thedral-theme', nextScheme)
    }
  },

  toggleCandlelight() {
    this.setColorScheme(this.isCandlelight ? 'midnight' : 'candlelight')
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

  setActiveBook(bookId) {
    this.activeBookId = bookId || ''
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('thedral-active-book', this.activeBookId)
    }
  },

  getBook(bookId = this.activeBookId) {
    return this.tree.find(book => book.id === bookId) || null
  },

  findBookForNode(nodeId, books = this.tree) {
    for (const book of books || []) {
      if (book.id === nodeId) return book
      const containsNode = (nodes) => (nodes || []).some(node =>
        node.id === nodeId || containsNode(node.children)
      )
      if (containsNode(book.children)) return book
    }
    return null
  },

  getRecentScenes() {
    const byId = new Map()
    const visit = (nodes) => {
      for (const node of nodes || []) {
        if (node.node_type === 'SCENE') byId.set(node.id, node)
        visit(node.children)
      }
    }
    visit(this.tree)
    return this.recentSceneIds.map(id => byId.get(id)).filter(Boolean)
  },

  async createScene() {
    let book = this.getBook()
    if (!book) {
      showToast('Choose or create a manuscript before adding a scene.', 'info')
      return
    }
    try {
      let chapter = book.children?.find(node => node.node_type === 'CHAPTER')
      if (!chapter) {
        const chapterResponse = await fetch(`${API_BASE}/api/node`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parent_id: book.id, node_type: 'CHAPTER', title: 'Chapter 1' })
        })
        if (!chapterResponse.ok) throw new Error(`HTTP ${chapterResponse.status}: Failed to create chapter`)
        chapter = await chapterResponse.json()
      }
      const response = await fetch(`${API_BASE}/api/node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_id: chapter.id, node_type: 'SCENE', title: 'New Scene' })
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to create scene`)
      const scene = await response.json()
      await this.fetchTree()
      await this.loadScene(scene.id)
      this.viewMode = 'editor'
    } catch (err) {
      showToast(err.message || 'Failed to create scene.', 'error')
    }
  },

  async navigateScene(direction) {
    const scenes = []
    const visit = (nodes) => {
      for (const node of nodes || []) {
        if (node.node_type === 'SCENE') scenes.push(node)
        visit(node.children)
      }
    }
    visit(this.getBook()?.children || [])
    const index = scenes.findIndex(scene => scene.id === this.activeNode?.id)
    const target = index < 0
      ? (direction > 0 ? scenes[0] : scenes[scenes.length - 1])
      : scenes[index + direction]
    if (target) return this.loadScene(target.id)
    return false
  },

  // Fetch Binder Tree (Aligned to /api/tree)
  async fetchTree() {
    try {
      const res = await fetch(`${API_BASE}/api/tree`)
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch binder`)
      const data = await res.json()
      this.tree = data

      const bookIds = new Set(this.tree.map(book => book.id))
      if (!bookIds.has(this.activeBookId)) {
        const rememberedBook = typeof window !== 'undefined' ? window.localStorage.getItem('thedral-active-book') : ''
        this.setActiveBook(bookIds.has(rememberedBook) ? rememberedBook : (this.tree[0]?.id || ''))
      }

      if (!this.activeNode?.id && this.tree.length > 0) {
        const scenes = this.getRecentScenes()
        const lastScene = scenes[0] || this.findFirstScene([this.getBook()].filter(Boolean))
        if (lastScene) await this.loadScene(lastScene.id)
      }
    } catch (err) {
      showToast(err.message, 'error')
    }
  },

  async createManuscript() {
    const createNode = async (payload) => {
      const res = await fetch(`${API_BASE}/api/node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to create ${payload.node_type.toLowerCase()}`)
      return res.json()
    }

    try {
      const book = await createNode({ node_type: 'BOOK', title: 'Manuscript' })
      const chapter = await createNode({ parent_id: book.id, node_type: 'CHAPTER', title: 'Chapter 1' })
      const scene = await createNode({ parent_id: chapter.id, node_type: 'SCENE', title: 'Scene 1' })
      this.setActiveBook(book.id)
      await this.fetchTree()
      const loaded = await this.loadScene(scene.id)
      if (!loaded) return
      this.viewMode = 'editor'
    } catch (err) {
      showToast(err.message || 'Failed to create manuscript.', 'error')
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
    if (!nodeId) return false
    try {
      if (this.activeNode?.id && this.activeNode.id !== nodeId && this.flushPendingSave) {
        const saved = await this.flushPendingSave()
        if (!saved) return false
      }
      const res = await fetch(`${API_BASE}/api/node/${nodeId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load scene`)
      const data = await res.json()

      this.activeNode = data
      const book = this.findBookForNode(nodeId)
      if (book) this.setActiveBook(book.id)
      this.recentSceneIds = [nodeId, ...this.recentSceneIds.filter(id => id !== nodeId)].slice(0, 8)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('thedral-recent-scenes', JSON.stringify(this.recentSceneIds))
      }
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
      return true
    } catch (err) {
      showToast(err.message, 'error')
      return false
    }
  },

  // Commit Scene Content (Aligned to PUT /api/node/{id})
  async saveActiveScene(htmlContent) {
    if (!this.activeNode?.id) return false
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
      this.activeNode.word_count = contentToPlainText(htmlContent).split(/\s+/).filter(Boolean).length
      this.readerStoryCache = null
      this.saveStatus = 'saved'
      return true
    } catch (err) {
      this.saveStatus = 'error'
      showToast(err.message, 'error')
      return false
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
        body: JSON.stringify({ text: contentToPlainText(this.activeNode.content) })
      })
      if (!res.ok) return
      const data = await res.json()
      const paras = contentToPlainText(this.activeNode.content).split(/\n{2,}/)
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
          surrounding: contentToPlainText(this.activeNode?.content || '')
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
  async fetchRuntimeStatus() {
    try {
      const response = await fetch(`${API_BASE}/api/health`)
      if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to fetch runtime status`)
      this.runtimeStatus = await response.json()
    } catch (err) {
      console.warn('[Thedral Runtime Status]', err)
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