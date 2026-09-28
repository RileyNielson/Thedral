<template>
  <div class="flex-1 flex flex-col bg-zinc-950 overflow-hidden relative h-full select-none">
    
    <!-- Top Control Bar -->
    <div 
      class="h-12 border-b px-4 flex items-center justify-between text-xs z-10 backdrop-blur shrink-0"
      :class="store.isCandlelight ? 'border-amber-900/40 bg-[#120f0c]/90' : 'border-zinc-800/80 bg-zinc-900/50'"
    >
      <!-- Spacetime Projections -->
      <div class="flex items-center space-x-1.5 overflow-x-auto py-1 custom-scrollbar">
        <span class="text-zinc-500 font-mono uppercase text-[10px] mr-1 hidden sm:inline">Projections:</span>
        <button 
          @click="setProjection('ALL')" 
          :class="['px-2.5 py-1 rounded-md font-medium text-xs transition', store.projectionMode === 'ALL' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm' : 'text-zinc-400 hover:text-white']"
        >
          All
        </button>
        <button 
          @click="setProjection('KINEMATIC')" 
          :class="['px-2.5 py-1 rounded-md font-medium text-xs transition', store.projectionMode === 'KINEMATIC' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm' : 'text-zinc-400 hover:text-white']"
        >
          Kinematics
        </button>
        <button 
          @click="setProjection('CUSTODY')" 
          :class="['px-2.5 py-1 rounded-md font-medium text-xs transition', store.projectionMode === 'CUSTODY' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm' : 'text-zinc-400 hover:text-white']"
        >
          Custody
        </button>
        <button 
          @click="setProjection('SOMATIC')" 
          :class="['px-2.5 py-1 rounded-md font-medium text-xs transition', store.projectionMode === 'SOMATIC' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm' : 'text-zinc-400 hover:text-white']"
        >
          Health
        </button>
        <button 
          @click="setProjection('SYNAPTIC')" 
          :class="['px-2.5 py-1 rounded-md font-medium text-xs transition', store.projectionMode === 'SYNAPTIC' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' : 'text-zinc-400 hover:text-white']"
        >
          🕸️ Web
        </button>
      </div>

      <!-- Center: Camera Snap Flight Angles -->
      <div class="hidden md:flex items-center bg-zinc-950 p-1 rounded-lg border border-zinc-800 text-xs font-mono">
        <button 
          @click="snapCamera('3d')" 
          class="px-2.5 py-0.5 rounded text-zinc-400 hover:text-amber-400 transition" 
          title="Isometric Spacetime"
        >
          🌐 3D
        </button>
        <button 
          @click="snapCamera('pacing')" 
          class="px-2.5 py-0.5 rounded text-zinc-400 hover:text-amber-400 transition" 
          title="Side View: Tension Mountain Range (Time vs Stakes)"
        >
          🏔️ Pacing
        </button>
        <button 
          @click="snapCamera('map')" 
          class="px-2.5 py-0.5 rounded text-zinc-400 hover:text-amber-400 transition" 
          title="Top-Down View: Geographic Story Map (Time vs Space)"
        >
          🗺️ Map
        </button>
      </div>

      <!-- Chronology & Survey Actions -->
      <div class="flex items-center space-x-2 shrink-0">
        <button 
          @click="toggleTimeMode" 
          class="text-amber-400 hover:text-amber-300 font-mono text-xs flex items-center gap-1.5 border border-zinc-800 bg-zinc-900/60 px-2.5 py-1 rounded transition"
        >
          <Clock class="w-3.5 h-3.5 text-amber-500" />
          <span>{{ store.timeMode === 'chronological' ? 'Story Days' : 'Sequence' }}</span>
        </button>

        <button 
          @click="surveyStory" 
          :disabled="store.surveyProgress.active" 
          class="px-3 py-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded-md flex items-center gap-1.5 transition text-xs shadow"
        >
          <Satellite class="w-3.5 h-3.5" />
          <span>{{ store.surveyProgress.active ? 'Surveying...' : 'Survey (AI)' }}</span>
        </button>
      </div>
    </div>

    <!-- 3D Plotly WebGL Canvas -->
    <div id="astrolabe-plot" class="flex-1 w-full h-full relative">
      <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-zinc-950/80 z-20">
        <div class="flex flex-col items-center gap-3">
          <Loader class="w-7 h-7 text-amber-500 animate-spin" />
          <span class="text-xs font-mono text-zinc-400">Rendering Narrative Spacetime...</span>
        </div>
      </div>
    </div>

    <!-- Continuity Collisions Anomaly HUD -->
    <div 
      v-if="store.astrolabeAnomalies && store.astrolabeAnomalies.length" 
      class="absolute bottom-6 right-6 max-w-sm w-full bg-zinc-900/90 border border-rose-800/60 rounded-xl p-4 shadow-2xl backdrop-blur-md z-20 space-y-2.5 animate-fade-in"
    >
      <div class="flex items-center justify-between text-xs font-bold text-rose-400 border-b border-zinc-800 pb-2">
        <span class="flex items-center gap-1.5">
          <AlertTriangle class="w-4 h-4 text-rose-500" /> 
          Continuity Collisions ({{ store.astrolabeAnomalies.length }})
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
          :class="[
            'p-2.5 bg-zinc-950 rounded border border-rose-900/40 transition', 
            an.scene_id ? 'cursor-pointer hover:border-rose-500/80 hover:bg-rose-950/40' : ''
          ]"
          title="Click to Sniper-Scroll into prose"
        >
          <div class="flex items-center justify-between">
            <div class="font-bold text-rose-400 uppercase text-[9px] tracking-wider flex items-center gap-1">
              <Crosshair class="w-3 h-3 text-rose-400" />
              <span>{{ an.type }} • {{ an.entity }}</span>
            </div>
            <ExternalLink v-if="an.scene_id" class="w-3 h-3 text-rose-500/70" />
          </div>
          <div class="leading-snug text-zinc-300 mt-1">{{ an.desc }}</div>
        </div>
      </div>
    </div>

    <!-- AI Story Universe Survey Modal Overlay -->
    <div 
      v-if="store.surveyProgress.active" 
      class="fixed inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center z-50 p-4"
    >
      <div class="bg-zinc-900 border border-amber-500/40 rounded-2xl max-w-md w-full p-6 text-center space-y-4 shadow-2xl">
        <div class="w-12 h-12 bg-amber-500/10 text-amber-400 rounded-full flex items-center justify-center mx-auto border border-amber-500/30">
          <Satellite class="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h3 class="text-base font-bold text-white tracking-wide">Surveying Story Universe</h3>
          <p class="text-xs text-zinc-400 mt-0.5">Local engine analyzing causal trajectories</p>
        </div>
        
        <div class="space-y-1.5">
          <div class="w-full bg-zinc-950 h-3 rounded-full overflow-hidden p-0.5 border border-zinc-800">
            <div 
              class="bg-gradient-to-r from-amber-600 to-amber-400 h-full rounded-full transition-all duration-300 shadow-[0_0_12px_rgba(245,158,11,0.5)]" 
              :style="{ width: store.surveyProgress.percent + '%' }"
            ></div>
          </div>
          <div class="flex justify-between text-[11px] font-mono text-zinc-500">
            <span>{{ store.surveyProgress.current }} of {{ store.surveyProgress.total }} Scenes</span>
            <span class="text-amber-400 font-bold">{{ store.surveyProgress.percent }}%</span>
          </div>
        </div>

        <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/80 text-left space-y-1">
          <div class="text-[10px] text-zinc-500 uppercase font-mono tracking-wider">Current Beat:</div>
          <div class="text-xs text-zinc-200 font-medium truncate flex items-center gap-1.5">
            <Loader class="w-3.5 h-3.5 animate-spin text-amber-500 shrink-0" />
            <span class="truncate">{{ store.surveyProgress.current_title || 'Analyzing...' }}</span>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-zinc-800/80">
          <span class="text-[11px] text-zinc-500 font-mono">
            Mapped Events: <strong class="text-amber-400">{{ store.surveyProgress.extracted }}</strong>
          </span>
          <button 
            @click="cancelSurvey" 
            class="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs rounded transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { Clock, Satellite, AlertTriangle, ExternalLink, Loader, X, Crosshair } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const isLoading = ref(false)
let evtSource = null
let resizeObserver = null

const getPlotly = async () => {
  if (typeof window !== 'undefined' && window.Plotly) return window.Plotly
  try {
    const mod = await import('plotly.js-dist-min')
    return mod.default || mod
  } catch (e) {
    return null
  }
}

// 4 Camera Snap Flight Angles
const snapCamera = async (mode) => {
  const plotEl = document.getElementById('astrolabe-plot')
  const Plotly = await getPlotly()
  if (!plotEl || !Plotly) return

  let eye = { x: 0.1, y: -2.3, z: 1.0 } // 3D Isometric default
  if (mode === 'pacing') {
    eye = { x: 0.0, y: -3.2, z: 0.0 }   // Flat Side Elevation: Time (X) vs Stakes (Z)
  } else if (mode === 'map') {
    eye = { x: 0.0, y: 0.0, z: 3.2 }   // Top-Down God's Eye: Time (X) vs Space (Y)
  }

  Plotly.relayout(plotEl, {
    'scene.camera.eye': eye
  })
}

const renderAstrolabe = async () => {
  isLoading.value = true
  try {
    const bId = store.activeNode?.book_id || (store.tree[0] && store.tree[0].id) || ''
    const res = await fetch(`${API_BASE}/api/narrative/astrolabe?book_id=${bId}&projection=${store.projectionMode}&time_mode=${store.timeMode}`)
    if (!res.ok) throw new Error('Astrolabe endpoint returned ' + res.status)
    const manifest = await res.json()
    
    store.astrolabeAnomalies = manifest.anomalies || []

    await nextTick()
    const plotEl = document.getElementById('astrolabe-plot')
    const Plotly = await getPlotly()

    if (plotEl && manifest.data && Plotly) {
      if (manifest.layout) {
        manifest.layout.paper_bgcolor = 'rgba(0,0,0,0)'
        manifest.layout.plot_bgcolor = 'rgba(0,0,0,0)'
        manifest.layout.autosize = true
        manifest.layout.margin = manifest.layout.margin || { l: 0, r: 0, b: 0, t: 0 }
      }

      await Plotly.react('astrolabe-plot', manifest.data, manifest.layout, {
        responsive: true,
        displayModeBar: false
      })

      // Clicking a node selects the scene and switches to editor
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
    showToast(`Astrolabe Render: ${err.message}`, 'error')
  } finally {
    isLoading.value = false
  }
}

const setProjection = (proj) => {
  store.projectionMode = proj
  renderAstrolabe()
}

const toggleTimeMode = () => {
  store.timeMode = store.timeMode === 'chronological' ? 'narrative' : 'chronological'
  renderAstrolabe()
}

const surveyStory = async () => {
  const bId = (store.tree[0] && store.tree[0].id) || ''
  store.surveyProgress = {
    active: true,
    current: 0,
    total: 0,
    percent: 0,
    current_title: 'Connecting to local LLM...',
    extracted: 0
  }

  if (window.EventSource) {
    if (evtSource) evtSource.close()
    evtSource = new EventSource(`${API_BASE}/api/narrative/survey-stream?book_id=${bId}`)
    
    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        store.surveyProgress.current = data.current || 0
        store.surveyProgress.total = data.total || 0
        store.surveyProgress.percent = data.percent || 0
        store.surveyProgress.current_title = data.message || ''
        store.surveyProgress.extracted = data.extracted || 0
        
        if (data.done) {
          evtSource.close()
          store.surveyProgress.active = false
          renderAstrolabe()
        }
      } catch (err) {
        console.warn('[Survey Stream Parse Error]', err)
      }
    }

    evtSource.onerror = () => {
      if (evtSource) evtSource.close()
      store.surveyProgress.active = false
    }
  }
}

const cancelSurvey = () => {
  if (evtSource) evtSource.close()
  store.surveyProgress.active = false
}

// Sniper-Scroll: Jumps to scene and fires crosshair highlight in prose
const jumpToAnomaly = async (sceneId, entityName) => {
  if (!sceneId) return
  await store.loadScene(sceneId)
  store.viewMode = 'editor'
  
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('sniper-scroll', {
      detail: { text: entityName }
    }))
  }, 200)
}

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
  if (evtSource) evtSource.close()
  if (resizeObserver) resizeObserver.disconnect()
})
</script>