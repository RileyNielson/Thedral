import { reactive } from 'vue'
import { API_BASE } from '@/api'

export const toasts = reactive([])

export const showToast = (msg, type = 'info') => {
  const id = Date.now() + Math.random()
  toasts.push({ id, msg, type })
  setTimeout(() => {
    const idx = toasts.findIndex(t => t.id === id)
    if (idx > -1) toasts.splice(idx, 1)
  }, 4000)
}

export const store = reactive({
  tree: [],
  activeBookId: null,
  activeNode: null,
  viewMode: 'editor', // 'editor' | 'outline' | 'corkboard' | 'cosmograph' | '3d'
  isVoidMode: false,
  isCandlelight: false,
  colorScheme: 'midnight',
  isXRayActive: false,
  activeInspectorTab: 'blueprint', // 'blueprint' | 'prose' | 'reader'
  selectedText: '',
  saveStatus: 'Ready',
  recentSceneIds: [],

  // Living Reader & Diagnostic State
  readerStoryCache: null,
  currentParagraphDiagnoses: [],
  xraySentences: [],
  loreRules: [],
  registeredEntities: [],
  astrolabeAnomalies: [],
  flushPendingSave: null,

  modals: {
    omnibar: false,
    cast: false,
    lore: false,
    vault: false,
    import: false,
    export: false,
    review: false,
    queryPackage: false,
    mobileBinder: false,
    mobileInspector: false
  },

  toggleModal(modalName, state = null) {
    if (state !== null) {
      this.modals[modalName] = state
    } else {
      this.modals[modalName] = !this.modals[modalName]
    }
  },

  toggleVoidMode() {
    this.isVoidMode = !this.isVoidMode
  },

  setColorScheme(scheme) {
    this.colorScheme = scheme
    this.isCandlelight = scheme === 'candlelight'
  },

  setActiveBook(bookId) {
    this.activeBookId = bookId
  },

  getBook() {
    return this.tree.find(b => b.id === this.activeBookId) || this.tree[0] || null
  },

  findBookForNode(nodeId) {
    for (const b of this.tree) {
      if (b.id === nodeId) return b
      for (const ch of b.children || []) {
        if (ch.id === nodeId) return b
        for (const sc of ch.children || []) {
          if (sc.id === nodeId) return b
        }
      }
    }
    return null
  },

  async fetchTree() {
    try {
      const res = await fetch(`${API_BASE}/api/tree`)
      if (res.ok) {
        this.tree = await res.json()
        if (!this.activeBookId && this.tree.length > 0) {
          this.activeBookId = this.tree[0].id
        }
      }
    } catch (e) {
      this.tree = []
    }
  },

  async loadScene(sceneId) {
    if (!sceneId) return false
    try {
      const res = await fetch(`${API_BASE}/api/node/${sceneId}`)
      if (!res.ok) throw new Error('Could not load scene')
      this.activeNode = await res.json()
      
      const book = this.findBookForNode(sceneId)
      if (book) this.activeBookId = book.id

      if (!this.recentSceneIds.includes(sceneId)) {
        this.recentSceneIds.unshift(sceneId)
        if (this.recentSceneIds.length > 8) this.recentSceneIds.pop()
      }

      // Immediately fetch real-time paragraph diagnoses for this scene
      this.fetchSceneReaderAnalysis(sceneId, this.activeNode.content)
      return true
    } catch (e) {
      showToast(e.message, 'error')
      return false
    }
  },

  async createScene() {
    const chapterId = this.getBook()?.children?.find(n => n.node_type === 'CHAPTER')?.id
    if (!chapterId) {
      showToast('Create a chapter in the Binder first.', 'info')
      return
    }
    try {
      const res = await fetch(`${API_BASE}/api/node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_id: chapterId, node_type: 'SCENE', title: 'New Scene' })
      })
      if (!res.ok) throw new Error('Could not create scene')
      const data = await res.json()
      await this.fetchTree()
      await this.loadScene(data.id)
      this.viewMode = 'editor'
    } catch (e) {
      showToast(e.message, 'error')
    }
  },

  async navigateScene(direction) {
    const scenes = []
    const visit = (nodes) => {
      for (const n of nodes || []) {
        if (n.node_type === 'SCENE') scenes.push(n)
        visit(n.children)
      }
    }
    visit(this.getBook()?.children)
    const currentIdx = scenes.findIndex(s => s.id === this.activeNode?.id)
    if (currentIdx === -1) return
    const nextIdx = currentIdx + direction
    if (nextIdx >= 0 && nextIdx < scenes.length) {
      await this.loadScene(scenes[nextIdx].id)
    }
  },

  // Real-Time Live Reader Analysis Trigger
  async fetchSceneReaderAnalysis(sceneId, content) {
    const bId = this.activeBookId
    if (!bId || !sceneId) return
    try {
      const res = await fetch(`${API_BASE}/api/analytics/reader-story/${encodeURIComponent(bId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: sceneId, content: content || '' })
      })
      if (res.ok) {
        const data = await res.json()
        this.currentParagraphDiagnoses = data.paragraph_diagnoses || []
        // Broadcast to InspectorReaderTab
        window.dispatchEvent(new CustomEvent('reader-story-updated', { detail: data }))
      }
    } catch {}
  },

  async fetchCast() {
    try {
      const res = await fetch(`${API_BASE}/api/entities`)
      if (res.ok) this.registeredEntities = await res.json()
    } catch {}
  },

  async fetchLore() {
    try {
      const res = await fetch(`${API_BASE}/api/lore`)
      if (res.ok) this.loreRules = await res.json()
    } catch {}
  }
})
