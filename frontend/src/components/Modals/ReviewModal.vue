<template>
  <div v-if="store.modals.review" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[90] p-4" @click.self="close">
    <section class="w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-2xl border border-zinc-700 bg-zinc-900 shadow-2xl flex flex-col" role="dialog" aria-modal="true" aria-labelledby="review-title">
      <header class="flex items-center justify-between border-b border-zinc-800 p-5">
        <div>
          <h2 id="review-title" class="text-base font-bold text-zinc-100">Manuscript review</h2>
          <p class="mt-1 text-xs text-zinc-500">{{ activeBook?.title || 'Choose a manuscript' }} · a checklist, not a quality score</p>
        </div>
        <button @click="close" class="text-zinc-500 hover:text-white" aria-label="Close manuscript review"><X class="w-5 h-5" /></button>
      </header>
      <div class="flex-1 overflow-y-auto p-5 space-y-5">
        <div v-if="!activeBook" class="rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-400">Select a working manuscript in the Binder first.</div>
        <div v-else-if="loading" class="py-12 text-center text-sm text-zinc-400">Gathering manuscript checks…</div>
        <div v-else-if="error" class="rounded-lg border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200">{{ error }}</div>
        <template v-else>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div v-for="metric in metrics" :key="metric.label" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              <div class="text-lg font-semibold text-zinc-100">{{ metric.value.toLocaleString() }}</div>
              <div class="text-[10px] uppercase tracking-wider text-zinc-500">{{ metric.label }}</div>
            </div>
          </div>
          <section class="space-y-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-300">Beta-reader feedback</h3>
            <p class="text-[10px] text-zinc-500">Author-entered responses, grouped by scene and draft version. Averages show the number of ratings behind each measure; they are not a representative reader score.</p>
            <p v-if="!readerFeedbackGroups.length" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-500">No beta-reader responses have been recorded for this manuscript.</p>
            <article v-for="group in readerFeedbackGroups" :key="group.key" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-2">
              <button @click="openScene(group.scene_id, true)" class="text-left text-xs font-semibold text-emerald-300 hover:underline">
                {{ group.chapter_title }} / {{ group.scene_title }} · {{ group.revision_ref === 'CURRENT' ? 'Current draft' : group.revision_ref }}
                <span class="ml-1 text-zinc-500">({{ group.entries.length }} response{{ group.entries.length === 1 ? '' : 's' }})</span>
              </button>
              <p v-if="group.averages.length" class="text-[10px] text-zinc-300">{{ group.averages.join(' · ') }}</p>
              <p v-else class="text-[10px] text-zinc-500">No ratings recorded.</p>
              <div v-for="entry in group.entries.filter(item => item.response)" :key="entry.id" class="border-l border-zinc-700 pl-2 text-[10px] text-zinc-400">
                <span class="text-zinc-500">{{ entry.reader_label || 'Reader' }}:</span> {{ entry.response }}
              </div>
            </article>
          </section>
          <section class="space-y-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-300">Scenes to check</h3>
            <p v-if="!issues.length" class="rounded-lg border border-emerald-900 bg-emerald-950/20 p-3 text-xs text-emerald-300">No empty scenes, missing synopses, or open critique notes found.</p>
            <button v-for="scene in issues" :key="scene.id" @click="openScene(scene.id)" class="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-left hover:border-amber-500/50">
              <div class="flex items-center justify-between gap-3">
                <span class="truncate text-xs font-semibold text-zinc-200">{{ scene.chapter_title }} / {{ scene.title }}</span>
                <span class="shrink-0 text-[10px] text-amber-300">{{ sceneIssueLabels(scene).join(' · ') }}</span>
              </div>
            </button>
          </section>
          <section v-if="proposals.length" class="space-y-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-300">Survey proposals awaiting approval ({{ proposals.length }})</h3>
            <p class="text-[10px] text-zinc-500">AI-extracted details remain suggestions until you approve them. Approval adds them to mapped Cosmograph data.</p>
            <article v-for="proposal in proposals" :key="proposal.proposal_id" class="rounded-lg border border-cyan-900/50 bg-cyan-950/20 p-3 space-y-2">
              <div class="text-xs font-semibold text-cyan-200">{{ proposal.detected_entity_name }} · {{ proposal.entity_type }} · {{ proposal.chapter_title }} / {{ proposal.scene_title }}</div>
              <p class="text-[10px] text-zinc-300">{{ proposal.source_span_text || 'No source excerpt provided.' }}</p>
              <p class="text-[10px] text-zinc-400">Suggested state: {{ JSON.stringify(proposal.proposed_delta) }} · {{ Math.round(proposal.confidence * 100) }}% confidence · {{ proposal.epistemic_tier }}</p>
              <div class="flex gap-3 text-[10px]">
                <button @click="resolveProposal(proposal, 'approve')" class="text-emerald-400 hover:underline">Approve and map</button>
                <button @click="resolveProposal(proposal, 'dismiss')" class="text-zinc-400 hover:underline">Dismiss</button>
                <button @click="openScene(proposal.scene_id)" class="text-amber-400 hover:underline">Review scene</button>
              </div>
            </article>
          </section>
          <section v-if="report.anomalies?.length" class="space-y-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-300">Cosmograph signals</h3>
            <p class="text-[10px] text-zinc-500">These are heuristic continuity flags based on story data. Review each in context; they are not confirmed errors.</p>
            <button v-for="(anomaly, index) in report.anomalies" :key="`${anomaly.scene_id}-${index}`" @click="anomaly.scene_id && openScene(anomaly.scene_id)" class="w-full rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 text-left text-xs text-zinc-300 hover:border-rose-500/50">
              <strong class="text-rose-300">{{ anomaly.type }} · {{ anomaly.entity }}</strong>
              <span class="block mt-1">{{ anomaly.desc }}</span>
            </button>
          </section>
          <section v-else class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-500">
            No Cosmograph signals are available. This does not confirm continuity is error-free.
          </section>
        </template>
      </div>
      <footer class="flex justify-between border-t border-zinc-800 p-4">
        <button @click="loadReport" :disabled="loading || !activeBook" class="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50">Refresh checks</button>
        <button @click="close" class="rounded-lg bg-amber-500 px-4 py-2 text-xs font-bold text-zinc-950 hover:bg-amber-400">Done</button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { X } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const report = ref(null)
const proposals = ref([])
const readerFeedback = ref([])
const loading = ref(false)
const error = ref('')
const activeBook = computed(() => store.getBook())
const metrics = computed(() => [
  { label: 'Scenes', value: report.value?.total_scenes || 0 },
  { label: 'Words', value: report.value?.total_words || 0 },
  { label: 'Draft', value: (report.value?.scenes || []).filter(scene => (scene.status || 'DRAFT').toUpperCase() === 'DRAFT').length },
  { label: 'Revised', value: (report.value?.scenes || []).filter(scene => (scene.status || '').toUpperCase() === 'REVISED').length },
  { label: 'Final', value: (report.value?.scenes || []).filter(scene => (scene.status || '').toUpperCase() === 'FINAL').length },
  { label: 'Empty', value: report.value?.empty_scenes || 0 },
  { label: 'No synopsis', value: report.value?.missing_synopses || 0 },
  { label: 'Open notes', value: report.value?.open_critiques || 0 }
])
const issues = computed(() => (report.value?.scenes || []).filter(scene =>
  !(Number(scene.word_count) > 0) || !(scene.synopsis || '').trim() || Number(scene.open_critiques) > 0
))
const readerFeedbackGroups = computed(() => {
  const groups = new Map()
  for (const entry of readerFeedback.value) {
    const key = `${entry.scene_id}:${entry.revision_ref}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(entry)
  }
  return Array.from(groups, ([key, entries]) => {
    const averages = [
      ['Confusion', 'confusion_rating'],
      ['Engagement', 'engagement_rating'],
      ['Tension', 'tension_rating'],
      ['Connection', 'empathy_rating']
    ].flatMap(([label, field]) => {
      const values = entries.map(entry => entry[field]).filter(Number.isFinite)
      return values.length
        ? [`${label} ${(
          values.reduce((sum, value) => sum + value, 0) / values.length
        ).toFixed(1)}/5 (n=${values.length})`]
        : []
    })
    return { key, entries, averages, ...entries[0] }
  })
})
let reportRequest = 0

const loadReport = async () => {
  const requestId = ++reportRequest
  const bookId = activeBook.value?.id
  if (!activeBook.value) {
    report.value = null
    proposals.value = []
    readerFeedback.value = []
    error.value = ''
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  readerFeedback.value = []
  try {
    const [response, proposalResponse, feedbackResponse] = await Promise.all([
      fetch(`${API_BASE}/api/publishing/review/${encodeURIComponent(bookId)}`),
      fetch(`${API_BASE}/api/narrative/proposals?book_id=${encodeURIComponent(bookId)}`),
      fetch(`${API_BASE}/api/reader-feedback/book/${encodeURIComponent(bookId)}`)
    ])
    if (requestId !== reportRequest || activeBook.value?.id !== bookId) return
    if (!response.ok || !proposalResponse.ok || !feedbackResponse.ok) {
      throw new Error(`Review checks failed (${response.status}/${proposalResponse.status}/${feedbackResponse.status}).`)
    }
    ;[report.value, proposals.value, readerFeedback.value] = await Promise.all([
      response.json(), proposalResponse.json(), feedbackResponse.json()
    ])
  } catch (err) {
    if (requestId === reportRequest && activeBook.value?.id === bookId) {
      error.value = err.message || 'Could not load manuscript review checks.'
    }
  } finally {
    if (requestId === reportRequest) loading.value = false
  }
}

const resolveProposal = async (proposal, action) => {
  try {
    const response = await fetch(`${API_BASE}/api/narrative/proposals/${encodeURIComponent(proposal.proposal_id)}/${action}`, { method: 'POST' })
    if (!response.ok) throw new Error(`Could not ${action} survey proposal.`)
    proposals.value = proposals.value.filter(item => item.proposal_id !== proposal.proposal_id)
    showToast(action === 'approve' ? 'Survey proposal approved and mapped.' : 'Survey proposal dismissed.', 'info')
    if (action === 'approve') await loadReport()
  } catch (err) {
    showToast(err.message || 'Could not update survey proposal.', 'error')
  }
}

const sceneIssueLabels = scene => [
  !(Number(scene.word_count) > 0) ? 'Empty draft' : '',
  !(scene.synopsis || '').trim() ? 'No synopsis' : '',
  Number(scene.open_critiques) > 0 ? `${scene.open_critiques} open note(s)` : ''
].filter(Boolean)

const openScene = async (sceneId, showReaderFeedback = false) => {
  const loaded = await store.loadScene(sceneId)
  if (loaded === false) {
    showToast('Could not open the selected scene.', 'error')
    return
  }
  if (showReaderFeedback) store.setInspectorTab('reader')
  store.viewMode = 'editor'
  close()
}
const close = () => store.toggleModal('review', false)

watch(() => activeBook.value?.id, loadReport, { immediate: true })
</script>
