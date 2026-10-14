import { reactive } from 'vue'

import { showToast, toasts } from './toast.js'
import { storeActions } from './storeActions.js'

export { showToast, toasts }

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
  }
})

Object.assign(store, storeActions)
