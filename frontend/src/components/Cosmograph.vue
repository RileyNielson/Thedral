<template>
  <div class="flex-1 flex flex-col bg-zinc-950 overflow-hidden relative h-full select-none">
    
    <!-- Top Control Bar -->
    <div 
      class="h-12 border-b px-4 flex items-center justify-between text-xs z-10 backdrop-blur shrink-0"
      :class="store.isCandlelight ? 'border-amber-900/40 bg-[#120f0c]/90' : 'border-zinc-800/80 bg-zinc-900/50'"
    >
      <!-- 3-Way Mode Navigation Switcher -->
      <div class="flex items-center rounded-lg border border-zinc-800 bg-zinc-950 p-1 shrink-0 font-mono">
        <button 
          @click="activeViewMode = '3d'" 
          :class="['px-2.5 py-1 rounded text-xs transition flex items-center gap-1.5', activeViewMode === '3d' ? 'bg-zinc-800 text-amber-300 font-bold' : 'text-zinc-500 hover:text-white']"
        >
          <Globe class="w-3.5 h-3.5 text-amber-500" /> 3D Spacetime
        </button>
        <button 
          @click="activeViewMode = 'transit'" 
          :class="['px-2.5 py-1 rounded text-xs transition flex items-center gap-1.5', activeViewMode === 'transit' ? 'bg-zinc-800 text-cyan-300 font-bold' : 'text-zinc-500 hover:text-white']"
        >
          <Route class="w-3.5 h-3.5 text-cyan-400" /> Transit Map
        </button>
        <button 
          @click="activeViewMode = 'shape'" 
          :class="['px-2.5 py-1 rounded text-xs transition flex items-center gap-1.5', activeViewMode === 'shape' ? 'bg-zinc-800 text-violet-300 font-bold' : 'text-zinc-500 hover:text-white']"
        >
          <Compass class="w-3.5 h-3.5 text-violet-400" /> Story Shape
        </button>
      </div>

      <!-- 3D Camera Snap Flight Angles -->
      <div v-show="activeViewMode === '3d'" class="hidden md:flex items-center bg-zinc-950 p-1 rounded-lg border border-zinc-800 text-xs font-mono">
        <button @click="snapCamera('3d')" class="px-2.5 py-0.5 rounded text-zinc-400 hover:text-amber-400 transition" title="Isometric 3D">🌐 3D</button>
        <button @click="snapCamera('pacing')" class="px-2.5 py-0.5 rounded text-zinc-400 hover:text-amber-400 transition" title="Side view: Pacing elevation">🏔️ Pacing</button>
        <button @click="snapCamera('map')" class="px-2.5 py-0.5 rounded text-zinc-400 hover:text-amber-400 transition" title="Top-down God's Eye Geography">🗺️ Map</button>
      </div>

      <div class="text-[11px] font-mono text-zinc-500 hidden sm:block">
        100% Deterministic Prose Cartography
      </div>
    </div>

    <!-- VIEW 1: 3D PLOTLY WEBGL MANIFOLD -->
    <div v-show="activeViewMode === '3d'" id="astrolabe-plot" class="flex-1 w-full h-full relative">
      <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-zinc-950/80 z-20">
        <div class="flex flex-col items-center gap-3">
          <Loader class="w-7 h-7 text-amber-500 animate-spin" />
          <span class="text-xs font-mono text-zinc-400">Rendering narrative spacetime…</span>
        </div>
      </div>
    </div>

    <!-- VIEW 2: 2D SUBWAY TRANSIT MATRIX -->
    <div v-if="activeViewMode === 'transit'" class="flex-1 p-6 overflow-auto custom-scrollbar bg-zinc-950">
      <div class="max-w-6xl mx-auto space-y-6">
        <header class="flex items-baseline justify-between border-b border-zinc-800 pb-3">
          <div>
            <h2 class="text-base font-bold text-zinc-100 flex items-center gap-2">
              <Route class="w-5 h-5 text-cyan-400" /> Character Transit Routes
            </h2>
            <p class="text-xs text-zinc-500 font-mono mt-0.5">Automated subway-style route tracking derived from prose mentions</p>
          </div>
          <span class="text-[11px] font-mono text-zinc-500">{{ transitData.characters?.length || 0 }} tracked characters</span>
        </header>

        <!-- Transit Routes Grid -->
        <div class="space-y-4">
          <div 
            v-for="char in transitData.characters" 
            :key="char.id" 
            class="p-4 bg-zinc-900/60 rounded-xl border border-zinc-800 space-y-3 shadow-md"
          >
            <div class="flex items-center justify-between">
              <span class="text-sm font-bold flex items-center gap-2" :style="{ color: char.color }">
                <span class="w-2.5 h-2.5 rounded-full" :style="{ background: char.color }"></span>
                {{ char.name }}
              </span>
              <span class="text-[10px] font-mono text-zinc-500">{{ char.stops.length }} scene appearance(s)</span>
            </div>

            <!-- Route Track -->
            <div class="flex items-center gap-2 overflow-x-auto py-2 custom-scrollbar">
              <template v-for="(stop, sIdx) in char.stops" :key="sIdx">
                <div class="flex items-center gap-1.5 shrink-0 bg-zinc-950 border border-zinc-800 px-2.5 py-1.5 rounded-lg text-xs font-mono">
                  <span class="w-2 h-2 rounded-full" :style="{ background: char.color }"></span>
                  <span class="text-zinc-200">{{ stop.location }}</span>
                  <span class="text-[10px] text-zinc-500">({{ stop.scene_title }})</span>
                </div>
                <span v-if="sIdx < char.stops.length - 1" class="text-zinc-600 font-mono shrink-0">➔</span>
              </template>
            </div>
          </div>

          <div v-if="!transitData.characters?.length" class="text-center py-12 text-zinc-600 text-xs font-serif italic">
            No confirmed character entities detected in scene text yet. Register characters in the Cast directory to see their transit routes.
          </div>
        </div>
      </div>
    </div>

    <!-- VIEW 3: STORY SHAPE -->
    <StoryShape v-if="activeViewMode === 'shape'" />

    <!-- Continuity Jump HUD -->
    <div 
      v-if="store.astrolabeAnomalies?.length && activeViewMode === '3d'" 
      class="absolute bottom-6 right-6 max-w-sm w-full bg-zinc-900/90 border border-rose-800/60 rounded-xl p-4 shadow-2xl backdrop-blur-md z-20 space-y-2.5"
    >
      <div class="flex items-center justify-between text-xs font-bold text-rose-400 border-b border-zinc-800 pb-2">
        <span class="flex items-center gap-1.5">
          <AlertTriangle class="w-4 h-4 text-rose-500" /> 
          Spatial Continuity Prompts ({{ store.astrolabeAnomalies.length }})
        </span>
        <button @click="store.astrolabeAnomalies = []" class="text-zinc-500 hover:text-zinc-300">
          <X class="w-3.5 h-3.5" />
        </button>
      </div>

      <div class="max-h-48 overflow-y-auto space-y-2 text-[11px] text-zinc-300 pr-1 custom-scrollbar">
        <div 
          v-for="(an, i) in store.astrolabeAnomalies" 
          :key="i" 
          @click="an.scene_id ? jumpToAnomaly(an.scene_id, an.entity) : null" 
          class="p-2.5 bg-zinc-950 rounded border border-rose-900/40 hover:border-rose-500/80 hover:bg-rose-950/40 transition cursor-pointer"
          title="Click to jump directly to this paragraph in editor"
        >
          <div class="font-bold text-rose-400 uppercase text-[9px] tracking-wider">{{ an.type }} • {{ an.entity }}</div>
          <div class="leading-snug text-zinc-300 mt-1">{{ an.desc }}</div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { store, showToast } from '../store.js'
import { Globe, AlertTriangle, Loader, X, Route, Compass } from '@lucide/vue'

import { API_BASE } from '@/api'
import StoryShape from './StoryShape.vue'

const activeViewMode = ref('3d') // '3d' | 'transit' | 'shape'
const isLoading = ref(false)
const transitData = ref({})
let resizeObserver = null

const getPlotly = async () => {
  if (typeof window !== 'undefined' && window.Plotly) return window.Plotly
  try {
    const mod = await import('plotly.js-dist-min')
    return mod.default || mod
  } catch {
    return null
  }
}

const snapCamera = async (mode) => {
  const plotEl = document.getElementById('astrolabe-plot')
  const Plotly = await getPlotly()
  if (!plotEl || !Plotly) return

  let eye = { x: 0.1, y: -2.3, z: 1.0 }
  if (mode === 'pacing') eye = { x: 0.0, y: -3.2, z: 0.0 }
  else if (mode === 'map') eye = { x: 0.0, y: 0.0, z: 3.2 }

  Plotly.relayout(plotEl, { 'scene.camera.eye': eye })
}

const renderAstrolabe = async () => {
  isLoading.value = true
  try {
    const bId = store.activeBookId || ''
    const res = await fetch(`${API_BASE}/api/narrative/astrolabe?book_id=${encodeURIComponent(bId)}&projection=ALL&time_mode=narrative`)
    if (!res.ok) throw new Error('Astrolabe server error')
    const manifest = await res.json()
    
    store.astrolabeAnomalies = manifest.anomalies || []
    transitData.value = manifest.transit_matrix || {}

    await nextTick()
    const plotEl = document.getElementById('astrolabe-plot')
    const Plotly = await getPlotly()

    if (plotEl && manifest.data && Plotly) {
      if (manifest.layout) {
        manifest.layout.paper_bgcolor = 'rgba(0,0,0,0)'
        manifest.layout.plot_bgcolor = 'rgba(0,0,0,0)'
        manifest.layout.autosize = true
        manifest.layout.margin = { l: 0, r: 0, b: 0, t: 0 }
      }

      await Plotly.react('astrolabe-plot', manifest.data, manifest.layout, {
        responsive: true,
        displayModeBar: false
      })

      plotEl.removeAllListeners?.('plotly_click')
      plotEl.on('plotly_click', (data) => {
        if (data && data.points && data.points[0]) {
          const sid = data.points[0].customdata
          if (sid) {
            store.loadScene(sid)
            store.viewMode = 'editor'
          }
        }
      })
    }
  } catch (err) {
    showToast(`Astrolabe: ${err.message}`, 'error')
  } finally {
    isLoading.value = false
  }
}

const jumpToAnomaly = async (sceneId, entityName) => {
  if (!sceneId) return
  await store.loadScene(sceneId)
  store.viewMode = 'editor'
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('sniper-scroll', { detail: { text: entityName } }))
  }, 200)
}

watch(activeViewMode, async (mode) => {
  if (mode === '3d') {
    await nextTick()
    const Plotly = await getPlotly()
    const el = document.getElementById('astrolabe-plot')
    if (Plotly && el && el.data) Plotly.Plots.resize(el)
  }
})

watch(() => store.activeBookId, () => {
  renderAstrolabe()
})

onMounted(() => {
  renderAstrolabe()
  const plotEl = document.getElementById('astrolabe-plot')
  if (plotEl && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(async () => {
      const Plotly = await getPlotly()
      if (Plotly) Plotly.Plots.resize(plotEl)
    })
    resizeObserver.observe(plotEl)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
})
</script>
