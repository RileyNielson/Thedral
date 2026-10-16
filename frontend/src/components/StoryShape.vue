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
      <!-- Controls -->
      <div class="flex flex-wrap items-center gap-3 text-xs">
        <div class="flex rounded-md border border-zinc-800 overflow-hidden">
          <button v-for="s in ['book', 'chapter', 'scene']" :key="s" @click="setScope(s)"
            :class="['px-3 py-1 capitalize', scope === s ? 'bg-amber-500/20 text-amber-300' : 'text-zinc-400 hover:text-white']">{{ s }}</button>
        </div>
        <template v-if="scope !== 'book'">
          <button @click="step(-1)" class="px-2 py-1 border border-zinc-800 rounded text-zinc-300 hover:text-white" aria-label="Previous">‹</button>
          <input type="range" min="0" :max="units.length - 1" v-model.number="index" class="accent-amber-500 w-40 sm:w-64" />
          <button @click="step(1)" class="px-2 py-1 border border-zinc-800 rounded text-zinc-300 hover:text-white" aria-label="Next">›</button>
          <span class="text-zinc-300 truncate max-w-[16rem]">{{ current.title }}</span>
          <span class="text-zinc-600 font-mono">{{ index + 1 }}/{{ units.length }}</span>
        </template>
        <span v-else class="text-zinc-400">Whole book · {{ shape.book.words.toLocaleString() }} words</span>
        <div class="flex-1"></div>
        <button v-if="scope !== 'book'" @click="togglePin" :class="['px-2.5 py-1 rounded border', pinned ? 'border-cyan-500/50 text-cyan-300' : 'border-zinc-800 text-zinc-400 hover:text-white']">
          {{ pinned ? 'Unpin comparison' : 'Pin to compare' }}
        </button>
        <label class="flex items-center gap-1.5 text-zinc-400"><input type="checkbox" v-model="showExtra" class="accent-amber-500" /> More strands</label>
        <label v-if="scope !== 'book'" class="flex items-center gap-1.5 text-zinc-400"><input type="checkbox" v-model="editTarget" class="accent-emerald-500" /> Set target</label>
      </div>

      <div class="grid lg:grid-cols-[minmax(0,420px)_1fr] gap-6">
        <!-- Radar -->
        <div>
          <svg :viewBox="`0 0 ${size} ${size}`" class="w-full touch-none" ref="radarEl">
            <g v-for="r in [0.25, 0.5, 0.75, 1]" :key="r">
              <polygon :points="ring(r)" fill="none" stroke="#27272a" stroke-width="1" />
            </g>
            <g v-for="(st, i) in visible" :key="st.key">
              <line :x1="c" :y1="c" :x2="pt(i, 1).x" :y2="pt(i, 1).y" stroke="#27272a" />
              <text :x="pt(i, 1.13).x" :y="pt(i, 1.13).y" text-anchor="middle" dominant-baseline="middle" font-size="11"
                :fill="activeStrand === st.key ? colorOf(st.key) : '#a1a1aa'" class="cursor-pointer" @click="openEvidence(st.key)">
                {{ st.label }}<tspan v-if="st.confidence === 'low'" fill="#71717a"> *</tspan>
              </text>
            </g>
            <polygon v-if="scope !== 'book'" :points="poly(shape.book.scores)" fill="rgba(113,113,122,0.12)" stroke="#52525b" stroke-dasharray="3 3" />
            <polygon v-if="pinned" :points="poly(pinned.scores)" fill="rgba(34,211,238,0.10)" stroke="#22d3ee" stroke-width="1.5" />
            <polygon v-if="target" :points="poly(target)" fill="none" stroke="#34d399" stroke-width="1.5" stroke-dasharray="5 3" />
            <polygon :points="poly(current.scores)" fill="rgba(245,158,11,0.22)" stroke="#f59e0b" stroke-width="2" />
            <circle v-for="(st, i) in visible" :key="'d' + st.key" :cx="pt(i, (current.scores[st.key] || 0) / 100).x" :cy="pt(i, (current.scores[st.key] || 0) / 100).y"
              r="3.5" :fill="colorOf(st.key)" class="cursor-pointer" @click="openEvidence(st.key)" />
            <g v-if="editTarget && scope !== 'book'">
              <circle v-for="(st, i) in visible" :key="'t' + st.key" :cx="pt(i, ((target || {})[st.key] || 0) / 100).x"
                :cy="pt(i, ((target || {})[st.key] || 0) / 100).y" r="7" fill="#34d399" fill-opacity="0.35" stroke="#34d399" class="cursor-grab"
                @pointerdown.prevent="startDrag($event, i)" />
            </g>
          </svg>
          <p class="text-[10px] text-zinc-500 leading-relaxed">
            Gold is this {{ scope }}; the dashed grey shape is the whole book. {{ shape.method }}
            <span v-if="hasLow"> * Low confidence: word lists catch this strand poorly.</span>
          </p>
        </div>

        <!-- Right column -->
        <div class="space-y-4 min-w-0">
          <div>
            <div class="text-[10px] uppercase tracking-wider font-mono text-zinc-500 mb-2">Strand by strand</div>
            <div class="grid sm:grid-cols-2 gap-x-5 gap-y-1.5">
              <button v-for="st in visible" :key="st.key" @click="openEvidence(st.key)"
                :class="['flex items-center gap-2 text-left text-xs rounded px-1.5 py-1 hover:bg-zinc-900', activeStrand === st.key ? 'bg-zinc-900' : '']">
                <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: colorOf(st.key) }"></span>
                <span class="w-28 truncate text-zinc-300">{{ st.label }}</span>
                <span class="flex-1 h-1.5 bg-zinc-900 rounded overflow-hidden"><span class="block h-full" :style="{ width: (current.scores[st.key] || 0) + '%', background: colorOf(st.key) }"></span></span>
                <span class="w-8 text-right font-mono text-zinc-500">{{ Math.round(current.scores[st.key] || 0) }}</span>
                <span :class="['w-4 text-center', trendClass(st.key)]" :title="trendTitle(st.key)">{{ trendIcon(st.key) }}</span>
              </button>
            </div>
          </div>

          <div v-if="gaps.length" class="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-3 text-xs space-y-1">
            <div class="text-emerald-300 font-medium">Against your target</div>
            <div v-for="g in gaps" :key="g.key" class="text-zinc-300">
              {{ g.label }}: {{ g.diff > 0 ? 'about ' + Math.round(g.diff) + ' above' : 'about ' + Math.round(-g.diff) + ' below' }} target
            </div>
          </div>

          <div v-if="activeStrand" class="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-xs space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-zinc-200 font-medium">Why “{{ labelOf(activeStrand) }}” scored this way</span>
              <button @click="activeStrand = ''" class="text-zinc-500 hover:text-zinc-300"><X class="w-3.5 h-3.5" /></button>
            </div>
            <div v-if="evidenceLoading" class="text-zinc-500">Finding the sentences…</div>
            <div v-else-if="!evidence.length" class="text-zinc-500">No sentences matched this strand here.</div>
            <div v-else class="space-y-2 max-h-64 overflow-y-auto custom-scrollbar pr-1">
              <div v-for="(e, i) in evidence" :key="i" class="border-l-2 pl-2" :style="{ borderColor: colorOf(activeStrand) }">
                <div class="text-[10px] text-zinc-500 mb-0.5 cursor-pointer hover:text-amber-400" @click="openScene(e.scene_id)">{{ e.scene_title }} · {{ e.matches.join(', ') }}</div>
                <div class="text-zinc-300 leading-snug">{{ e.sentence }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Timeline -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <div class="text-[10px] uppercase tracking-wider font-mono text-zinc-500">Across the book (smoothed, scene by scene)</div>
          <div class="text-[10px] text-zinc-600">Click a point to select that scene</div>
        </div>
        <div class="flex flex-wrap gap-1.5 mb-2">
          <button v-for="st in visible" :key="st.key" @click="toggleLine(st.key)"
            :class="['px-2 py-0.5 rounded-full text-[10px] border', lines.has(st.key) ? 'text-zinc-100' : 'text-zinc-600 border-zinc-800']"
            :style="lines.has(st.key) ? { borderColor: colorOf(st.key), background: colorOf(st.key) + '22' } : {}">{{ st.label }}</button>
        </div>
        <svg :viewBox="`0 0 ${tw} ${th}`" class="w-full" preserveAspectRatio="none" style="height: 220px" @click="onTimelineClick">
          <line v-for="g in [0, 25, 50, 75, 100]" :key="g" :x1="pad" :x2="tw - pad" :y1="ty(g)" :y2="ty(g)" stroke="#18181b" />
          <g v-for="b in chapterBounds" :key="b.id">
            <line :x1="tx(b.start)" :x2="tx(b.start)" :y1="pad" :y2="th - pad" stroke="#27272a" stroke-dasharray="2 4" />
          </g>
          <rect v-if="scope !== 'book'" :x="tx(highlight.start) - 2" :y="pad" :width="Math.max(4, tx(highlight.end) - tx(highlight.start) + 4)" :height="th - 2 * pad" fill="rgba(245,158,11,0.10)" />
          <polyline v-for="st in lineStrands" :key="st.key" :points="linePoints(st.key)" fill="none" :stroke="colorOf(st.key)" stroke-width="1.6" vector-effect="non-scaling-stroke" />
        </svg>
        <div class="mt-3">
          <div class="text-[10px] uppercase tracking-wider font-mono text-zinc-500 mb-1">Pacing: share of each scene that is dialogue</div>
          <div class="flex items-end gap-px h-10">
            <div v-for="(s, i) in shape.scenes" :key="s.scene_id" class="flex-1 bg-zinc-800 hover:bg-amber-600 cursor-pointer min-w-px"
              :style="{ height: Math.max(4, (s.pacing.dialogue_share || 0) * 100) + '%', background: unitIndexOfScene(i) === index && scope === 'scene' ? '#f59e0b' : '' }"
              :title="`${s.title}: ${Math.round((s.pacing.dialogue_share || 0) * 100)}% dialogue · ${s.pacing.avg_sentence_words} words/sentence`"
              @click="pickScene(i)"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { Loader, X } from '@lucide/vue'
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
const editTarget = ref(false)
const pinned = ref(null)
const activeStrand = ref('')
const evidence = ref([])
const evidenceLoading = ref(false)
const lines = ref(new Set())
const radarEl = ref(null)
const targetDraft = ref(null)
let dragIndex = -1
let saveTimer = null

const size = 420
const c = size / 2
const radius = 135

const visible = computed(() => (shape.value?.strands || []).filter(s => s.core || showExtra.value))
const hasLow = computed(() => visible.value.some(s => s.confidence === 'low'))
const lineStrands = computed(() => visible.value.filter(s => lines.value.has(s.key)))
const units = computed(() => (scope.value === 'chapter' ? shape.value?.chapters : shape.value?.scenes) || [])
const current = computed(() => {
  if (scope.value === 'book') return { title: 'Whole book', scores: shape.value.book.scores }
  return units.value[Math.min(index.value, units.value.length - 1)] || { title: '', scores: {} }
})
const unitId = computed(() => (scope.value === 'chapter' ? current.value.chapter_id : current.value.scene_id))
const target = computed(() => {
  if (scope.value === 'book') return null
  if (targetDraft.value) return targetDraft.value
  return shape.value?.targets?.[unitId.value] || null
})
const gaps = computed(() => {
  if (!target.value) return []
  return visible.value
    .map(s => ({ key: s.key, label: s.label, diff: (current.value.scores[s.key] || 0) - (target.value[s.key] || 0) }))
    .filter(g => Math.abs(g.diff) >= 15)
    .sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))
    .slice(0, 5)
})

const angle = (i) => (-Math.PI / 2) + (2 * Math.PI * i) / Math.max(1, visible.value.length)
const pt = (i, f) => ({ x: c + Math.cos(angle(i)) * radius * f, y: c + Math.sin(angle(i)) * radius * f })
const ring = (f) => visible.value.map((_, i) => `${pt(i, f).x},${pt(i, f).y}`).join(' ')
const poly = (scores) => visible.value.map((s, i) => { const p = pt(i, (scores?.[s.key] || 0) / 100); return `${p.x},${p.y}` }).join(' ')

const labelOf = (k) => (shape.value?.strands || []).find(s => s.key === k)?.label || k

// Timeline geometry
const tw = 1000, th = 220, pad = 10
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

const trendIcon = (k) => ({ rising: '↗', fading: '↘', flat: '→' }[shape.value?.trends?.[k]?.direction] || '→')
const trendClass = (k) => ({ rising: 'text-emerald-400', fading: 'text-rose-400' }[shape.value?.trends?.[k]?.direction] || 'text-zinc-600')
const trendTitle = (k) => {
  const t = shape.value?.trends?.[k]
  if (!t) return ''
  const unit = shape.value.chapters.length >= 3 ? 'chapter' : 'scene'
  return `${t.direction} across the book (peaks at ${unit} ${t.peak_index + 1})`
}

const load = async () => {
  const id = store.activeBookId
  shape.value = null
  error.value = ''
  if (!id) return
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/analytics/story-shape/${encodeURIComponent(id)}`)
    if (!res.ok) throw new Error(`The server answered ${res.status}`)
    shape.value = await res.json()
    lines.value = new Set(['action', 'romance', 'mystery', 'suspense'])
    index.value = 0
    pinned.value = null
    targetDraft.value = null
    focusActiveScene()
  } catch (e) {
    error.value = `Could not measure story shape. ${e.message}`
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
  targetDraft.value = null
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
    showToast('Could not load the sentences behind that score.', 'error')
  } finally {
    if (activeStrand.value === requested) evidenceLoading.value = false
  }
}

// Target editing: drag a point on the radar, saved shortly after you let go.
const startDrag = (ev, i) => {
  if (!targetDraft.value) targetDraft.value = { ...(shape.value.targets?.[unitId.value] || {}) }
  dragIndex = i
  window.addEventListener('pointermove', onDrag)
  window.addEventListener('pointerup', endDrag, { once: true })
}
const onDrag = (ev) => {
  const svg = radarEl.value
  if (!svg || dragIndex < 0) return
  const rect = svg.getBoundingClientRect()
  const scale = size / rect.width
  const x = (ev.clientX - rect.left) * scale - c
  const y = (ev.clientY - rect.top) * scale - c
  const a = angle(dragIndex)
  const proj = (x * Math.cos(a) + y * Math.sin(a)) / radius
  targetDraft.value = { ...targetDraft.value, [visible.value[dragIndex].key]: Math.round(Math.max(0, Math.min(1, proj)) * 100) }
}
const endDrag = () => {
  window.removeEventListener('pointermove', onDrag)
  dragIndex = -1
  clearTimeout(saveTimer)
  saveTimer = setTimeout(saveTarget, 300)
}
const saveTarget = async () => {
  if (!targetDraft.value) return
  const id = unitId.value
  const payload = { ...targetDraft.value }
  try {
    const res = await fetch(`${API_BASE}/api/analytics/story-shape/targets/${encodeURIComponent(id)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: store.activeBookId, targets: payload }),
    })
    if (!res.ok) throw new Error(String(res.status))
    shape.value.targets = { ...shape.value.targets, [id]: payload }
    targetDraft.value = null
  } catch (e) {
    showToast(`Could not save the target (${e.message}).`, 'error')
  }
}

watch(() => store.activeBookId, load)
watch(index, () => { targetDraft.value = null; if (activeStrand.value) openEvidence(activeStrand.value) })
onMounted(load)
onBeforeUnmount(() => { window.removeEventListener('pointermove', onDrag); clearTimeout(saveTimer) })
</script>
