<template>
  <aside 
    v-show="!store.isVoidMode" 
    :class="[
      'w-84 border-l bg-zinc-950 md:bg-zinc-900/60 shadow-2xl backdrop-blur-xl flex flex-col transition-all z-20 shrink-0 select-none',
      'fixed inset-y-12 right-0 md:static md:translate-x-0',
      store.modals.mobileInspector ? 'translate-x-0' : 'translate-x-full md:translate-x-0',
      store.isCandlelight ? 'border-amber-900/40 bg-[#120f0c]' : 'border-zinc-800/80'
    ]"
  >
    <!-- 5-Tab Analytical Navigation -->
    <div 
      class="flex border-b text-xs shrink-0 font-mono"
      :class="store.isCandlelight ? 'border-amber-900/40' : 'border-zinc-800'"
    >
      <button 
        @click="store.activeInspectorTab = 'card'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'card' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Card
      </button>
      <button 
        @click="store.activeInspectorTab = 'telemetry'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'telemetry' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Telemetry
      </button>
      <button 
        @click="store.activeInspectorTab = 'socratic'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'socratic' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Socratic
      </button>
      <button 
        @click="store.activeInspectorTab = 'reader'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'reader' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Reader
      </button>
      <button 
        @click="openLensTab" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition flex items-center justify-center gap-1', store.activeInspectorTab === 'lens' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        <Microscope class="w-3 h-3" /> Lens
      </button>
    </div>

    <!-- Empty Inspector State -->
    <div v-if="!store.activeNode?.id" class="flex-1 flex items-center justify-center p-6 text-zinc-600 text-center">
      <p class="text-xs">Select a scene to engage analytical perspectives.</p>
    </div>

    <div v-else class="flex-1 overflow-y-auto p-4 text-xs space-y-5 custom-scrollbar">
      
      <!-- TAB 1: PERSISTENT SOVEREIGN SCENE CARD -->
      <div v-if="store.activeInspectorTab === 'card'" class="space-y-4">
        
        <!-- 4 Sovereign Grounding Fields (Snaps 3D Coordinates) -->
        <div class="grid grid-cols-2 gap-2 font-mono">
          <div>
            <label class="text-[9px] font-bold text-amber-400 uppercase tracking-wider block mb-1">POV Character</label>
            <input 
              v-model="cardData.pov_character" 
              @blur="forceSave" 
              placeholder="e.g. Ellie" 
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none"
            />
          </div>

          <div>
            <label class="text-[9px] font-bold text-amber-400 uppercase tracking-wider block mb-1">Setting / Corridor</label>
            <input 
              v-model="cardData.setting" 
              @blur="forceSave" 
              placeholder="e.g. The Sky Docks" 
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 font-mono">
          <div>
            <label class="text-[9px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">Story Day / Time</label>
            <input 
              v-model="cardData.narrative_time" 
              @blur="forceSave" 
              placeholder="e.g. Day 3.5 or -5 yrs" 
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-cyan-500/50 focus:outline-none"
            />
          </div>

          <div>
            <label class="text-[9px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">Tension Target: {{ cardData.tension_target || 50 }}%</label>
            <input 
              type="range"
              min="0"
              max="100"
              v-model.number="cardData.tension_target" 
              @change="forceSave" 
              class="w-full accent-amber-500 mt-2 cursor-pointer"
            />
          </div>
        </div>

        <div>
          <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Scene Beat Synopsis</label>
          <textarea 
            v-model="store.activeNode.synopsis" 
            @blur="forceSave" 
            rows="4" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition leading-relaxed font-serif" 
            placeholder="What irreversible dramatic shift occurs in this beat?"
          ></textarea>
        </div>

        <div>
          <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Chapter Epigraph / Lore Quote</label>
          <textarea 
            v-model="store.activeNode.epigraph" 
            @blur="forceSave" 
            rows="2" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-300 text-xs italic font-serif focus:border-amber-500/50 focus:outline-none transition" 
            placeholder='"Quote from historical archive..."'
          ></textarea>
        </div>

        <div>
          <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Drafting Status</label>
          <select 
            v-model="store.activeNode.status" 
            @change="forceSave" 
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-300 text-xs focus:outline-none"
          >
            <option value="DRAFT">Draft</option>
            <option value="REVISED">Revised</option>
            <option value="FINAL">Final</option>
          </select>
        </div>

        <div class="pt-3 border-t border-zinc-800 text-zinc-500 space-y-2 text-[11px] font-mono">
          <div class="flex justify-between">
            <span>Scene Words:</span> 
            <span class="text-zinc-200 font-medium">{{ store.activeNode?.word_count || 0 }}</span>
          </div>
          <div class="flex justify-between">
            <span>Node ID:</span> 
            <span class="text-zinc-500 truncate max-w-[150px]">{{ store.activeNode?.id }}</span>
          </div>
        </div>
      </div>

      <!-- TAB 2: TELEMETRY & NEURO-SPECTROMETER -->
      <div v-if="store.activeInspectorTab === 'telemetry'" class="space-y-4">
        <div class="grid grid-cols-2 gap-2 text-center font-mono">
          <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800">
            <div class="text-[10px] text-zinc-500">Cadence StDev</div>
            <div class="text-base font-bold text-amber-400">{{ telemetry.cadence_stdev || 0 }}</div>
          </div>
          <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800">
            <div class="text-[10px] text-zinc-500">Sentence Avg</div>
            <div class="text-base font-bold text-amber-400">{{ telemetry.avg_sentence || 0 }}w</div>
          </div>
        </div>

        <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800 flex items-center justify-between font-mono">
          <div>
            <span class="text-[10px] text-zinc-500 uppercase block">Stakes Elevation (Z)</span>
            <span class="text-xs text-zinc-300">{{ telemetry.slope_diagnosis || 'STABLE_FLOW' }}</span>
          </div>
          <span class="text-base font-bold text-amber-400">{{ telemetry.tension_elevation || 0.35 }}</span>
        </div>

        <!-- Micro Neuro-Narrative Spectrometer -->
        <div class="p-3.5 bg-zinc-950 rounded-xl border border-zinc-800 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-bold uppercase tracking-wider text-amber-400 font-mono flex items-center gap-1.5">
              <Activity class="w-3.5 h-3.5" /> Reader Neuro-Spectrum
            </span>
            <span class="text-[9px] font-mono text-zinc-500">Live Scene Fuel</span>
          </div>

          <div class="space-y-2 font-mono text-[10px]">
            <div>
              <div class="flex justify-between text-rose-400 mb-0.5">
                <span>Adrenaline (Kinetic Survival)</span>
                <span>{{ telemetry.spectrometer?.adrenaline || 25 }}%</span>
              </div>
              <div class="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
                <div class="bg-rose-500 h-full rounded-full transition-all" :style="{ width: (telemetry.spectrometer?.adrenaline || 25) + '%' }"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-purple-400 mb-0.5">
                <span>Oxytocin (Relational Intimacy)</span>
                <span>{{ telemetry.spectrometer?.oxytocin || 25 }}%</span>
              </div>
              <div class="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
                <div class="bg-purple-500 h-full rounded-full transition-all" :style="{ width: (telemetry.spectrometer?.oxytocin || 25) + '%' }"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-cyan-400 mb-0.5">
                <span>Dopamine (Deductive Mystery)</span>
                <span>{{ telemetry.spectrometer?.dopamine || 25 }}%</span>
              </div>
              <div class="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
                <div class="bg-cyan-500 h-full rounded-full transition-all" :style="{ width: (telemetry.spectrometer?.dopamine || 25) + '%' }"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-emerald-400 mb-0.5">
                <span>Serotonin (Aesthetic Immersion)</span>
                <span>{{ telemetry.spectrometer?.serotonin || 25 }}%</span>
              </div>
              <div class="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
                <div class="bg-emerald-500 h-full rounded-full transition-all" :style="{ width: (telemetry.spectrometer?.serotonin || 25) + '%' }"></div>
              </div>
            </div>
          </div>

          <div 
            class="p-2.5 rounded-lg border text-[10px] leading-relaxed font-sans"
            :class="[
              telemetry.spectrometer?.hunger_severity === 'WARNING' 
                ? 'bg-amber-950/30 border-amber-900/60 text-amber-200' 
                : (telemetry.spectrometer?.hunger_severity === 'CAUTION' ? 'bg-cyan-950/30 border-cyan-900/60 text-cyan-200' : 'bg-zinc-900/50 border-zinc-800 text-zinc-400')
            ]"
          >
            <strong>Reader State:</strong> {{ telemetry.spectrometer?.hunger_alert || "Calibrating neurochemical equilibrium..." }}
          </div>
        </div>

        <div>
          <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Filter Verbs Detected</label>
          <div v-if="Object.keys(telemetry.filters || {}).length" class="space-y-1">
            <div 
              v-for="(cnt, v) in telemetry.filters" 
              :key="v" 
              class="flex justify-between bg-zinc-950 px-2.5 py-1 rounded border border-zinc-800/50 font-mono text-[11px]"
            >
              <span class="text-rose-400">{{ v }}</span>
              <span class="text-zinc-500">{{ cnt }}</span>
            </div>
          </div>
          <div v-else class="text-zinc-600 italic">No filter verbs detected. Deep POV intact.</div>
        </div>
      </div>

      <!-- TAB 3: SOCRATIC MIRROR & TUTOR -->
      <div v-if="store.activeInspectorTab === 'socratic'" class="space-y-4 flex flex-col h-full">
        <div v-if="store.socraticCritique" class="space-y-2">
          <div class="p-3.5 bg-zinc-950 rounded-xl border border-amber-500/30 text-zinc-200 leading-relaxed whitespace-pre-line text-xs font-serif shadow-lg">
            {{ store.socraticCritique }}
          </div>
          <div class="flex items-center justify-between text-xs pt-1">
            <span class="text-[10px] text-zinc-500 font-mono">Logged to Vault</span>
            <div class="flex space-x-1.5">
              <button 
                @click="resolveCritique('ADDRESSED')" 
                class="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded text-[11px] font-medium transition"
              >
                ✓ Addressed
              </button>
              <button 
                @click="resolveCritique('DISMISSED')" 
                class="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded text-[11px] transition"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>

        <div v-else class="text-center py-6 border border-dashed border-zinc-800/80 rounded-xl p-4 text-zinc-500">
          <Sparkles class="w-5 h-5 mx-auto mb-2 text-amber-500/50" />
          <p class="text-[11px] mb-3">Highlight text in the editor to run a <b>Line-Critique</b>.</p>
          <div class="border-t border-zinc-800/80 my-3"></div>
          <button 
            @click="elevateMacroScene" 
            class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-amber-400 font-medium rounded-lg text-[10px] uppercase tracking-wider transition w-full"
          >
            Diagnose Entire Scene
          </button>
        </div>

        <div class="pt-4 border-t border-zinc-800">
          <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-2">Ask The Socratic Companion</label>
          <div class="flex gap-2">
            <input 
              v-model="tutorQuestion" 
              @keyup.enter="askTutor" 
              placeholder="e.g. How do I build dread here?" 
              class="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:border-amber-500/50 focus:outline-none transition" 
            />
            <button 
              @click="askTutor" 
              :disabled="isTutorThinking" 
              class="px-2.5 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-xs transition"
            >
              <Loader v-if="isTutorThinking" class="w-3.5 h-3.5 animate-spin" />
              <Send v-else class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        
        <div class="pt-3 border-t border-zinc-800 space-y-2 flex-1 overflow-y-auto">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Editorial Log</span>
            <span class="text-[10px] text-zinc-600 font-mono">{{ store.sceneCritiques?.length || 0 }} total</span>
          </div>
          <div class="space-y-2 pr-1">
            <div 
              v-for="cr in store.sceneCritiques" 
              :key="cr.id" 
              class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/80 text-[11px] space-y-1.5"
            >
              <div class="flex items-center justify-between">
                <span 
                  :class="[
                    'px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase', 
                    cr.status === 'ADDRESSED' 
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                      : (cr.status === 'OPEN' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-zinc-800 text-zinc-500')
                  ]"
                >
                  {{ cr.status }}
                </span>
                <span class="text-[10px] text-zinc-600 font-mono">{{ (cr.created_at || '').split(' ')[0] }}</span>
              </div>
              <div class="text-zinc-400 italic line-clamp-1 font-serif">"{{ cr.passage_text }}"</div>
              <div class="text-zinc-300 line-clamp-3 font-serif leading-snug">{{ cr.critique_text }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 4: READER HORIZON -->
      <div v-if="store.activeInspectorTab === 'reader'" class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-[11px] text-zinc-400 font-medium">Reader Epistemic Horizon</span>
          <button 
            @click="scanHorizon" 
            :disabled="isScanning" 
            class="px-2 py-0.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded text-[10px] font-mono flex items-center gap-1 transition"
          >
            <Sparkles class="w-3 h-3" /> 
            <span>{{ isScanning ? 'Scanning...' : 'Scan Horizon (AI)' }}</span>
          </button>
        </div>
        
        <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800 space-y-1.5">
          <div class="font-bold text-amber-400 uppercase text-[10px] flex items-center justify-between">
            <span class="flex items-center gap-1"><Target class="w-3 h-3" /> Direct Ground Truths</span>
            <span class="font-mono text-zinc-600 text-[9px]">
              {{ store.activeDisclosures?.filter(x => x.disclosure_type === 'DIRECT').length || 0 }}
            </span>
          </div>
          <div class="space-y-1">
            <div 
              v-for="d in (store.activeDisclosures || []).filter(x => x.disclosure_type === 'DIRECT')" 
              :key="d.id" 
              class="text-[11px] text-zinc-300 flex items-start justify-between group"
            >
              <span>• {{ d.narrative_claim }}</span>
              <button @click="deleteDisclosure(d.id)" class="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-rose-400 p-0.5 transition">
                <X class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800 space-y-1.5">
          <div class="font-bold text-cyan-400 uppercase text-[10px] flex items-center justify-between">
            <span class="flex items-center gap-1"><Search class="w-3 h-3" /> Inferred Subtext</span>
            <span class="font-mono text-zinc-600 text-[9px]">
              {{ store.activeDisclosures?.filter(x => x.disclosure_type === 'INFERRED').length || 0 }}
            </span>
          </div>
          <div class="space-y-1">
            <div 
              v-for="d in (store.activeDisclosures || []).filter(x => x.disclosure_type === 'INFERRED')" 
              :key="d.id" 
              class="text-[11px] text-zinc-300 flex items-start justify-between group"
            >
              <div>
                <span>• {{ d.narrative_claim }}</span>
                <div v-if="d.clue_evidence" class="text-[9px] text-cyan-500/80 italic ml-2">↳ "{{ d.clue_evidence }}"</div>
              </div>
              <button @click="deleteDisclosure(d.id)" class="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-rose-400 p-0.5 transition">
                <X class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 5: LENS (Zoomed-in Chapter Spacetime with Live Reading Bead) -->
      <div v-if="store.activeInspectorTab === 'lens'" class="space-y-3 flex flex-col h-full">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5 font-medium text-[11px] text-cyan-400">
            <Microscope class="w-3.5 h-3.5" />
            <span>Chapter Spacetime Topography</span>
          </div>
          <button 
            @click="store.viewMode = 'cosmograph'" 
            class="px-2 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[10px] font-mono flex items-center gap-1 transition"
          >
            <Maximize class="w-3 h-3" /> Full Cosmos
          </button>
        </div>
        
        <p class="text-[10px] text-zinc-500 leading-snug">
          Real-time chapter waveform. Click any node to jump to that beat.
        </p>

        <div class="flex-1 w-full min-h-[300px] bg-zinc-950 rounded-xl border border-zinc-800/80 overflow-hidden relative shadow-inner">
          <div v-if="isLensLoading" class="absolute inset-0 flex items-center justify-center bg-zinc-950/70 z-10">
            <Loader class="w-5 h-5 text-cyan-400 animate-spin" />
          </div>
          <div id="mini-astrolabe-plot" class="w-full h-full"></div>
        </div>
      </div>

    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { Microscope, Sparkles, Loader, Send, Target, Search, Maximize, X, Activity } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

const telemetry = computed(() => store.activeNode?.telemetry || store.telemetry || {})
const tutorQuestion = ref('')
const isTutorThinking = ref(false)
const isScanning = ref(false)
const isLensLoading = ref(false)
let currentManifest = null

// Persistent Scene Card Data Proxy (Stored in SQLite binder_nodes.card_data)
const cardData = computed(() => {
  if (!store.activeNode) return {}
  if (!store.activeNode.card) {
    store.activeNode.card = {
      pov_character: '',
      setting: '',
      narrative_time: '',
      tension_target: 50
    }
  }
  return store.activeNode.card
})

const getPlotly = async () => {
  if (typeof window !== 'undefined' && window.Plotly) return window.Plotly
  try {
    const mod = await import('plotly.js-dist-min')
    return mod.default || mod
  } catch (e) {
    return null
  }
}

// Live Reading Bead Receiver
const handleScrollBeat = async (e) => {
  const beatIdx = e.detail?.beat || 1
  const plotEl = document.getElementById('mini-astrolabe-plot')
  const Plotly = await getPlotly()
  if (!plotEl || !Plotly || !currentManifest || store.activeInspectorTab !== 'lens') return

  const spine = currentManifest.data?.[0]
  if (!spine || !spine.x?.length) return

  const targetIdx = Math.min(beatIdx - 1, spine.x.length - 1)
  const beadX = [spine.x[targetIdx]]
  const beadY = [spine.y[targetIdx]]
  const beadZ = [spine.z[targetIdx]]

  const beadTrace = {
    type: 'scatter3d',
    mode: 'markers',
    name: 'Reading Head',
    x: beadX,
    y: beadY,
    z: beadZ,
    text: [`<b>Current Reading Position</b> (Beat ${beatIdx})`],
    hoverinfo: 'text',
    marker: {
      size: 14,
      symbol: 'circle',
      color: '#22d3ee',
      line: { color: '#ffffff', width: 2 }
    }
  }

  const allTraces = [...currentManifest.data, beadTrace]
  Plotly.react('mini-astrolabe-plot', allTraces, currentManifest.layout, {
    responsive: true,
    displayModeBar: false
  })
}

const renderMiniAstrolabe = async () => {
  const chapterId = store.activeNode?.parent_id
  const sceneId = store.activeNode?.id
  if (!chapterId) return

  isLensLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/narrative/astrolabe?chapter_id=${chapterId}&focus_id=${sceneId}&projection=KINEMATIC&time_mode=narrative`)
    if (!res.ok) throw new Error('Lens endpoint error')
    currentManifest = await res.json()
    
    await nextTick()
    const plotEl = document.getElementById('mini-astrolabe-plot')
    const Plotly = await getPlotly()

    if (plotEl && currentManifest.data && Plotly) {
      if (currentManifest.layout) {
        currentManifest.layout.paper_bgcolor = 'rgba(0,0,0,0)'
        currentManifest.layout.plot_bgcolor = 'rgba(0,0,0,0)'
        currentManifest.layout.margin = { l: 0, r: 0, b: 0, t: 0 }
        currentManifest.layout.showlegend = false
      }

      await Plotly.react('mini-astrolabe-plot', currentManifest.data, currentManifest.layout, { 
        responsive: true, 
        displayModeBar: false 
      })

      plotEl.removeAllListeners?.('plotly_click')
      plotEl.on('plotly_click', async (data) => {
        if (data && data.points && data.points[0]) {
          const cdata = data.points[0].customdata
          if (!cdata) return

          const sceneId = typeof cdata === 'object' ? cdata.scene_id : cdata
          const beatIdx = typeof cdata === 'object' ? cdata.beat_idx : (data.points[0].pointIndex + 1)
          const snippet = typeof cdata === 'object' ? cdata.snippet : ''

          if (sceneId && sceneId !== store.activeNode?.id) {
            await store.loadScene(sceneId)
          }

          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('lens-beat-jump', {
              detail: { beat: beatIdx, snippet: snippet }
            }))
          }, 150)
        }
      })
    }
  } catch(e) {
    console.warn('[Mini Astrolabe Error]', e)
  } finally {
    isLensLoading.value = false
  }
}

const openLensTab = () => {
  store.activeInspectorTab = 'lens'
  nextTick(() => renderMiniAstrolabe())
}

watch(() => [store.activeNode?.id, store.activeInspectorTab], ([newId, tab]) => {
  if (tab === 'lens' && newId) {
    nextTick(() => renderMiniAstrolabe())
  }
})

// Force save persists title, synopsis, content, epigraph, status, AND cardData directly to SQLite
const forceSave = async () => {
  if (!store.activeNode?.id) return
  try {
    await fetch(`${API_BASE}/api/node/${store.activeNode.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        title: store.activeNode.title, 
        synopsis: store.activeNode.synopsis, 
        content: store.activeNode.content, 
        epigraph: store.activeNode.epigraph, 
        status: store.activeNode.status,
        card_data: cardData.value
      })
    })
    window.dispatchEvent(new Event('refresh-tree'))
  } catch (e) {
    showToast('Failed to update scene details.', 'error')
  }
}

const askTutor = async () => {
  if (!tutorQuestion.value.trim()) return
  isTutorThinking.value = true
  store.socraticCritique = ''
  try {
    const res = await fetch(`${API_BASE}/api/craft/teach`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        question: tutorQuestion.value, 
        context: store.activeNode?.content || '' 
      }) 
    })
    if (!res.ok) throw new Error('Tutor offline')
    const data = await res.json()
    store.socraticCritique = data.lesson
  } catch(e) { 
    showToast(e.message, 'error') 
  } finally {
    isTutorThinking.value = false
    tutorQuestion.value = ''
  }
}

const elevateMacroScene = async () => {
  if (!store.activeNode?.content) return
  store.socraticCritique = 'Analyzing macro structure...'
  try {
    const res = await fetch(`${API_BASE}/api/craft/elevate`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        passage: "[MACRO SCENE DIAGNOSIS] " + store.activeNode.content.substring(0, 3000), 
        surrounding: "Evaluate macro scene structure and character agency.", 
        scene_id: store.activeNode.id 
      }) 
    })
    if (!res.ok) throw new Error('Macro diagnosis failed')
    const data = await res.json()
    store.socraticCritique = data.critique
    store.activeCritiqueId = data.critique_id
    fetchCritiques()
  } catch(e) { 
    showToast(e.message, 'error') 
  }
}

const fetchCritiques = async () => {
  if (!store.activeNode?.id) return
  try {
    const res = await fetch(`${API_BASE}/api/critiques/scene/${store.activeNode.id}`)
    if (!res.ok) return
    store.sceneCritiques = await res.json()
  } catch (e) {
    console.warn('[Thedral Critiques]', e)
  }
}

const resolveCritique = async (status) => {
  if (store.activeCritiqueId) {
    try {
      await fetch(`${API_BASE}/api/critiques/${store.activeCritiqueId}/status`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ status }) 
      })
    } catch(e) {}
  }
  store.socraticCritique = ''
  store.activeCritiqueId = null
  fetchCritiques()
}

const scanHorizon = async () => {
  if (!store.activeNode?.id || !store.activeNode?.content) return
  isScanning.value = true
  try {
    const res = await fetch(`${API_BASE}/api/disclosures/scan`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        scene_id: store.activeNode.id, 
        text: store.activeNode.content 
      }) 
    })
    if (!res.ok) throw new Error('Scan failed')
    const data = await res.json()
    if (data.status === 'success') {
      store.activeDisclosures = data.disclosures
    }
  } catch(e) { 
    showToast(e.message, 'error') 
  } finally {
    isScanning.value = false
  }
}

const deleteDisclosure = async (id) => {
  if (!store.activeNode?.id) return
  try {
    await fetch(`${API_BASE}/api/disclosures/${id}`, { method: 'DELETE' })
    const res = await fetch(`${API_BASE}/api/disclosures/scene/${store.activeNode.id}`)
    if (res.ok) store.activeDisclosures = await res.json()
  } catch (e) {
    showToast('Failed to remove disclosure.', 'error')
  }
}

onMounted(() => {
  window.addEventListener('refresh-critiques', fetchCritiques)
  window.addEventListener('editor-scroll-beat', handleScrollBeat)
  if (store.activeInspectorTab === 'lens') {
    nextTick(() => renderMiniAstrolabe())
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('editor-scroll-beat', handleScrollBeat)
})
</script>