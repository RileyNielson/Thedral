<template>
  <div class="absolute inset-0 top-12 bg-zinc-950 overflow-y-auto custom-scrollbar z-10 select-none">
    <div v-if="loading" class="h-full flex items-center justify-center text-xs font-mono text-zinc-400 gap-2">
      <Loader class="w-4 h-4 animate-spin text-amber-500" /> Measuring story strands…
    </div>
    <div v-else-if="error" class="p-8 text-sm text-rose-400">{{ error }}</div>
    <div v-else-if="!shape || !shape.scenes.length" class="h-full flex items-center justify-center text-sm text-zinc-500 p-8 text-center">
      Open or import a manuscript with scenes to see its story shape.
    </div>
    <div v-else class="p-5 space-y-5 max-w-6xl mx-auto">
      
      <!-- Top Controls -->
      <div class="flex flex-wrap items-center gap-3 text-xs">
        <div class="flex rounded-md border border-zinc-800 overflow-hidden">
          <button v-for="s in ['book', 'chapter', 'scene']" :key="s" @click="setScope(s)"
            :class="['px-3 py-1 capitalize font-mono text-xs', scope === s ? 'bg-amber-500/20 text-amber-300 font-bold' : 'text-zinc-400 hover:text-white']">{{ s }}</button>
        </div>
        <template v-if="scope !== 'book'">
          <button @click="step(-1)" class="px-2 py-1 border border-zinc-800 rounded text-zinc-300 hover:text-white" aria-label="Previous">‹</button>
          <input type="range" min="0" :max="units.length - 1" v-model.number="index" class="accent-amber-500 w-40 sm:w-64" />
          <button @click="step(1)" class="px-2 py-1 border border-zinc-800 rounded text-zinc-300 hover:text-white" aria-label="Next">›</button>
          <span class="text-zinc-300 truncate max-w-[16rem] font-serif font-bold">{{ current.title }}</span>
          <span class="text-zinc-600 font-mono text-[11px]">{{ index + 1 }}/{{ units.length }}</span>
        </template>
        <span v-else class="text-zinc-400 font-mono text-xs">Entire Manuscript · {{ shape.book.words.toLocaleString() }} words</span>
        <div class="flex-1"></div>
        <button v-if="scope !== 'book'" @click="togglePin" :class="['px-2.5 py-1 rounded border font-mono text-xs transition', pinned ? 'border-cyan-500/50 text-cyan-300 bg-cyan-950/20' : 'border-zinc-800 text-zinc-400 hover:text-white']">
          {{ pinned ? 'Unpin' : 'Pin comparison' }}
        </button>
        <label class="flex items-center gap-1.5 text-zinc-400 font-mono text-xs cursor-pointer"><input type="checkbox" v-model="showExtra" class="accent-amber-500" /> More strands</label>
      </div>

      <!-- Non-Prescriptive Descriptive Insights Drawer -->
      <section v-if="shape.insights" class="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
        <div class="flex items-center justify-between border-b border-zinc-800 pb-2">
          <span class="text-[10px] font-bold uppercase tracking-wider text-amber-400 font-mono flex items-center gap-1.5">
            <Compass class="w-3.5 h-3.5" /> Descriptive Narrative Insights (Non-Prescriptive)
          </span>
          <span class="text-[9px] text-zinc-500 font-mono">Telemetry from prose; no formula targets</span>
        </div>

        <div class="grid sm:grid-cols-3 gap-3 text-xs">
          <!-- Primary Narrative Spine -->
          <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/80 space-y-1">
            <div class="text-[9px] font-mono text-zinc-500 uppercase tracking-wider">Dominant Spine:</div>
            <div class="text-zinc-200 font-medium">
              <span v-for="(item, i) in shape.insights.spine" :key="item.key">
                <span :style="{ color: colorOf(item.key) }" class="font-bold">{{ item.label }}</span> ({{ item.score }}%)<span v-if="i < shape.insights.spine.length - 1">, </span>
              </span>
            </div>
          </div>

          <!-- Dynamic Range & Contrast -->
          <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/80 space-y-1">
            <div class="text-[9px] font-mono text-zinc-500 uppercase tracking-wider">Dynamic Contrast:</div>
            <div class="text-zinc-300 text-[11px] leading-snug font-serif">{{ shape.insights.dynamic_range }}</div>
          </div>

          <!-- Pacing Respiration -->
          <div class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/80 space-y-1">
            <div class="text-[9px] font-mono text-zinc-500 uppercase tracking-wider">Pacing Respiration:</div>
            <div class="text-zinc-300 text-[11px] leading-snug font-serif">{{ shape.insights.respiration }}</div>
          </div>
        </div>

        <!-- Transitions / Hand-offs -->
        <div v-if="shape.insights.handoffs?.length" class="flex flex-wrap items-center gap-2 pt-1 text-[10px] font-mono text-zinc-400">
          <span class="text-zinc-500 uppercase tracking-wider">Key Transitions:</span>
          <span v-for="h in shape.insights.handoffs" :key="h" class="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-300">
            {{ h }}
          </span>
        </div>
      </section>

      <!-- Main Visual Grid: Radar & Strand List -->
      <div class="grid lg:grid-cols-[minmax(0,420px)_1fr] gap-6">
        <!-- Relative Radar -->
        <div>
          <svg :viewBox="`0 0 ${size} ${size}`" class="w-full touch-none" ref="radarEl">
            <g v-for="r in [0.25, 0.5, 0.75, 1]" :key="r">
              <polygon :points="ring(r)" fill="none" stroke="#27272a" stroke-width="1" />
            </g>
            <g v-for="(st, i) in visible" :key="st.key">
              <line :x1="c" :y1="c" :x2="pt(i, 1).x" :y2="pt(i, 1).y" stroke="#27272a" />
              <text :x="pt(i, 1.13).x" :y="pt(i, 1.13).y" text-anchor="middle" dominant-baseline="middle" font-size="11"
                :fill="activeStrand === st.key ? colorOf(st.key) : '#a1a1aa'" class="cursor-pointer font-serif" @click="openEvidence(st.key)">
                {{ st.label }}
              </text>
            </g>
            <!-- Whole book baseline (dashed grey) -->
            <polygon v-if="scope !== 'book'" :points="poly(shape.book.scores)" fill="rgba(113,113,122,0.12)" stroke="#52525b" stroke-dasharray="3 3" />
            <!-- Pinned comparison -->
            <polygon v-if="pinned" :points="poly(pinned.scores)" fill="rgba(34,211,238,0.10)" stroke="#22d3ee" stroke-width="1.5" />
            <!-- Active focal scope -->
            <polygon :points="poly(current.scores)" fill="rgba(245,158,11,0.22)" stroke="#f59e0b" stroke-width="2" />
            <circle v-for="(st, i) in visible" :key="'d' + st.key" :cx="pt(i, (current.scores[st.key] || 0) / 100).x" :cy="pt(i, (current.scores[st.key] || 0) / 100).y"
              r="3.5" :fill="colorOf(st.key)" class="cursor-pointer" @click="openEvidence(st.key)" />
          </svg>
          <p class="text-[10px] text-zinc-500 leading-relaxed font-mono mt-2">
            Gold is this {{ scope }}; dashed grey is the full manuscript baseline. Click any strand label to see matching sentences in the text.
          </p>
        </div>

        <!-- Strand Bars & Clickable Evidence Drawer -->
        <div class="space-y-4 min-w-0">
          <div>
            <div class="text-[10px] uppercase tracking-wider font-mono text-zinc-500 mb-2">Active Strands:</div>
            <div class="grid sm:grid-cols-2 gap-x-5 gap-y-1.5">
              <button v-for="st in visible" :key="st.key" @click="openEvidence(st.key)"
                :class="['flex items-center gap-2 text-left text-xs rounded px-2 py-1.5 hover:bg-zinc-900 transition', activeStrand === st.key ? 'bg-zinc-900 border border-zinc-800' : '']">
                <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: colorOf(st.key) }"></span>
                <span class="w-28 truncate text-zinc-300 font-serif">{{ st.label }}</span>
                <span class="flex-1 h-1.5 bg-zinc-950 rounded overflow-hidden border border-zinc-800"><span class="block h-full transition-all" :style="{ width: (current.scores[st.key] || 0) + '%', background: colorOf(st.key) }"></span></span>
                <span class="w-8 text-right font-mono text-zinc-400 text-[11px]">{{ Math.round(current.scores[st.key] || 0) }}%</span>
              </button>
            </div>
          </div>

          <!-- Clicked Evidence Drawer -->
          <div v-if="activeStrand" class="rounded-xl border border-zinc-800 bg-zinc-900/70 p-3 text-xs space-y-2.5 animate-fade-in shadow-xl">
            <div class="flex items-center justify-between border-b border-zinc-800 pb-1.5">
              <span class="text-zinc-200 font-semibold font-serif">Prose Evidence for “{{ labelOf(activeStrand) }}”</span>
              <button @click="activeStrand = ''" class="text-zinc-500 hover:text-zinc-300"><X class="w-3.5 h-3.5" /></button>
            </div>
            <div v-if="evidenceLoading" class="text-zinc-500 font-mono text-xs">Scanning text...</div>
            <div v-else-if="!evidence.length" class="text-zinc-500 italic">No direct keyword markers found in this scope.</div>
            <div v-else class="space-y-2 max-h-60 overflow-y-auto custom-scrollbar pr-1">
              <div v-for="(e, i) in evidence" :key="i" class="border-l-2 pl-2 text-xs" :style="{ borderColor: colorOf(activeStrand) }">
                <div class="text-[10px] text-zinc-500 mb-0.5 cursor-pointer hover:text-amber-400 font-mono" @click="openScene(e.scene_id)">
                  {{ e.scene_title }} · matches: {{ e.matches.join(', ') }}
                </div>
                <div class="text-zinc-300 leading-snug font-serif">“{{ e.sentence }}”</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Manuscript Timeline Wave -->
      <div class="pt-4 border-t border-zinc-800">
        <div class="flex items-center justify-between mb-2">
          <div class="text-[10px] uppercase tracking-wider font-mono text-zinc-500">Continuous Timeline Waveform (Across Manuscript)</div>
          <div class="text-[10px] text-zinc-500 font-mono">Click anywhere to jump to scene</div>
        </div>
        <div class="flex flex-wrap gap-1.5 mb-2">
          <button v-for="st in visible" :key="st.key" @click="toggleLine(st.key)"
            :class="['px-2 py-0.5 rounded-full text-[10px] font-mono border transition', lines.has(st.key) ? 'text-zinc-100 font-bold' : 'text-zinc-600 border-zinc-800']"
            :style="lines.has(st.key) ? { borderColor: colorOf(st.key), background: colorOf(st.key) + '22' } : {}">{{ st.label }}</button>
        </div>
        <svg :viewBox="`0 0 ${tw} ${th}`" class="w-full bg-zinc-950 rounded-xl border border-zinc-800 cursor-pointer" preserveAspectRatio="none" style="height: 180px" @click="onTimelineClick">
          <line v-for="g in [0, 25, 50, 75, 100]" :key="g" :x1="pad" :x2="tw - pad" :y1="ty(g)" :y2="ty(g)" stroke="#18181b" />
          <g v-for="b in chapterBounds" :key="b.id">
            <line :x1="tx(b.start)" :x2="tx(b.start)" :y1="pad" :y2="th - pad" stroke="#27272a" stroke-dasharray="2 4" />
          </g>
          <rect v-if="scope !== 'book'" :x="tx(highlight.start) - 2" :y="pad" :width="Math.max(4, tx(highlight.end) - tx(highlight.start) + 4)" :height="th - 2 * pad" fill="rgba(245,158,11,0.12)" />
          <polyline v-for="st in lineStrands" :key="st.key" :points="linePoints(st.key)" fill="none" :stroke="colorOf(st.key)" stroke-width="1.8" vector-effect="non-scaling-stroke" />
        </svg>

        <!-- Dialogue Pacing Wave -->
        <div class="mt-4">
          <div class="text-[10px] uppercase tracking-wider font-mono text-zinc-500 mb-1">Cadence Rhythm: Dialogue Ratio per Scene</div>
          <div class="flex items-end gap-px h-8 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
            <div v-for="(s, i) in shape.scenes" :key="s.scene_id" class="flex-1 bg-zinc-800 hover:bg-amber-500 cursor-pointer min-w-px rounded-t-sm transition-colors"
              :style="{ height: Math.max(8, (s.pacing.dialogue_share || 0) * 100) + '%', background: unitIndexOfScene(i) === index && scope === 'scene' ? '#f59e0b' : '' }"
              :title="`${s.title}: ${Math.round((s.pacing.dialogue_share || 0) * 100)}% dialogue`"
              @click="pickScene(i)"></div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Loader, X, Compass } from '@lucide/vue'
import { store, showToast } from '../store.js'
import { API_BASE } from '@/api'

const COLORS = {
  action: '#ef4444', conflict: '#f97316', romance: '#ec4899', mystery: '#06b6d4', suspense: '#a855f7', adventure: '#10b981',
  growth: '#eab308', emotion: '#60a5fa', danger: '#dc2626', humor: '#facc15', dread: '#6366f1', loss: '#94a3b8',
  betrayal: '#c026d3', hope: '#4ade80', intrigue: '#d97706', lore: '#2dd4bf',
}
const colorOf = (k) => COLORS[k] || '#a1a1aa'

const loading = ref(false)
const error = ref('')
const shape = ref(null)
const scope = ref('chapter')
const index = ref(0)
const showExtra = ref(false)
const pinned = ref(null)
const activeStrand = ref('')
const evidence = ref([])
const evidenceLoading = ref(false)
const lines = ref(new Set(['action', 'mystery', 'suspense', 'emotion']))
const radarEl = ref(null)

const size = 420
const c = size / 2
const radius = 135

const visible = computed(() => (shape.value?.strands || []).filter(s => s.core || showExtra.value))
const lineStrands = computed(() => visible.value.filter(s => lines.value.has(s.key)))
const units = computed(() => (scope.value === 'chapter' ? shape.value?.chapters : shape.value?.scenes) || [])
const current = computed(() => {
  if (scope.value === 'book') return { title: 'Entire Manuscript', scores: shape.value.book.scores }
  return units.value[Math.min(index.value, units.value.length - 1)] || { title: '', scores: {} }
})

const angle = (i) => (-Math.PI / 2) + (2 * Math.PI * i) / Math.max(1, visible.value.length)
const pt = (i, f) => ({ x: c + Math.cos(angle(i)) * radius * f, y: c + Math.sin(angle(i)) * radius * f })
const ring = (f) => visible.value.map((_, i) => `${pt(i, f).x},${pt(i, f).y}`).join(' ')
const poly = (scores) => visible.value.map((s, i) => { const p = pt(i, (scores?.[s.key] || 0) / 100); return `${p.x},${p.y}` }).join(' ')

const labelOf = (k) => (shape.value?.strands || []).find(s => s.key === k)?.label || k

// Timeline geometry
const tw = 1000, th = 180, pad = 10
const sceneCount = computed(() => shape.value?.scenes.length || 1)
const tx = (i) => pad + (sceneCount.value <= 1 ? 0 : (i / (sceneCount.value - 1)) * (tw - 2 * pad))
const ty = (v) => th - pad - (v / 100) * (th - 2 * pad)
const smooth = (values) => {
  const w = Math.max(1, Math.min(5, Math.round(values.length / 25) * 2 + 1))
  const half = Math.floor(w / 2)
  return values.map((_, i) => {
    const slice = values.slice(Math.max(0, i - half), i + half + 1)
    return slice.reduce((a, b) => a + b, 0) / slice.length
  })
}
const linePoints = (key) => smooth(shape.value.scenes.map(s => s.scores[key] || 0)).map((v, i) => `${tx(i)},${ty(v)}`).join(' ')
const chapterBounds = computed(() => {
  const out = []
  let last = null
  shape.value?.scenes.forEach((s, i) => { if (s.chapter_id !== last) { out.push({ id: s.chapter_id, start: i }); last = s.chapter_id } })
  return out
})
const highlight = computed(() => {
  const scenes = shape.value?.scenes || []
  if (scope.value === 'scene') return { start: index.value, end: index.value }
  const ids = scenes.map((s, i) => (s.chapter_id === current.value.chapter_id ? i : -1)).filter(i => i >= 0)
  return { start: ids[0] ?? 0, end: ids[ids.length - 1] ?? 0 }
})
const unitIndexOfScene = (i) => i

const load = async () => {
  const id = store.activeBookId
  shape.value = null
  error.value = ''
  if (!id) return
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/analytics/story-shape/${encodeURIComponent(id)}`)
    if (!res.ok) throw new Error(`Server returned ${res.status}`)
    shape.value = await res.json()
    index.value = 0
    pinned.value = null
    focusActiveScene()
  } catch (e) {
    error.value = `Could not measure story shape: ${e.message}`
  } finally {
    loading.value = false
  }
}

const focusActiveScene = () => {
  const sid = store.activeNode?.id
  if (!sid || !shape.value) return
  const i = shape.value.scenes.findIndex(s => s.scene_id === sid)
  if (i < 0) return
  if (scope.value === 'scene') index.value = i
  else if (scope.value === 'chapter') index.value = Math.max(0, shape.value.chapters.findIndex(ch => ch.chapter_id === shape.value.scenes[i].chapter_id))
}

const setScope = (s) => {
  scope.value = s
  index.value = 0
  activeStrand.value = ''
  focusActiveScene()
}
const step = (d) => { index.value = Math.min(units.value.length - 1, Math.max(0, index.value + d)) }
const togglePin = () => { pinned.value = pinned.value ? null : { title: current.value.title, scores: { ...current.value.scores } } }
const toggleLine = (k) => {
  const next = new Set(lines.value)
  next.has(k) ? next.delete(k) : next.add(k)
  lines.value = next
}

const pickScene = (i) => {
  scope.value = 'scene'
  index.value = i
}
const onTimelineClick = (ev) => {
  const rect = ev.currentTarget.getBoundingClientRect()
  const frac = (ev.clientX - rect.left) / rect.width
  const i = Math.round(((frac * tw) - pad) / (tw - 2 * pad) * (sceneCount.value - 1))
  pickScene(Math.min(sceneCount.value - 1, Math.max(0, i)))
}
const openScene = (id) => { if (id) { store.loadScene(id); store.viewMode = 'editor' } }

const evidenceSceneIds = (key) => {
  const scenes = shape.value.scenes
  if (scope.value === 'scene') return [current.value.scene_id]
  if (scope.value === 'chapter') return current.value.scene_ids.slice(0, 8)
  return [...scenes].sort((a, b) => (b.scores[key] || 0) - (a.scores[key] || 0)).slice(0, 3).map(s => s.scene_id)
}

const openEvidence = async (key) => {
  activeStrand.value = key
  evidence.value = []
  evidenceLoading.value = true
  const requested = key
  try {
    const ids = evidenceSceneIds(key)
    const parts = await Promise.all(ids.map(async (sid) => {
      const res = await fetch(`${API_BASE}/api/analytics/story-shape/${encodeURIComponent(store.activeBookId)}/evidence/${encodeURIComponent(sid)}?strand=${encodeURIComponent(key)}`)
      if (!res.ok) return []
      const data = await res.json()
      const title = shape.value.scenes.find(s => s.scene_id === sid)?.title || ''
      return data.evidence.map(e => ({ ...e, scene_id: sid, scene_title: title }))
    }))
    if (activeStrand.value === requested) evidence.value = parts.flat().slice(0, 14)
  } catch {
    showToast('Could not load evidence sentences.', 'error')
  } finally {
    if (activeStrand.value === requested) evidenceLoading.value = false
  }
}

watch(() => store.activeBookId, load)
watch(index, () => { if (activeStrand.value) openEvidence(activeStrand.value) })
onMounted(load)
</script>
