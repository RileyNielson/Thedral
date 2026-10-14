<template>
  <div v-if="store.modals.export" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[90] p-4" @click.self="close">
    <section class="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl space-y-5" role="dialog" aria-modal="true" aria-labelledby="export-title">
      <header class="flex items-start justify-between border-b border-zinc-800 pb-3">
        <div>
          <h2 id="export-title" class="text-base font-bold text-zinc-100">Review manuscript before export</h2>
          <p class="mt-1 text-xs text-zinc-500">{{ activeBook?.title || 'Choose a manuscript' }} · DOCX</p>
        </div>
        <button @click="close" class="text-zinc-500 hover:text-white" aria-label="Close export review"><X class="w-5 h-5" /></button>
      </header>

      <div v-if="!activeBook" class="rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-400">
        Select a working manuscript in the Binder before exporting.
      </div>
      <template v-else>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="text-[11px] text-zinc-400">Author name
            <input v-model="profile.author_name" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2.5 py-2 text-xs text-zinc-100" placeholder="Author name on title page" />
          </label>
          <label class="text-[11px] text-zinc-400">Subtitle
            <input v-model="profile.subtitle" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2.5 py-2 text-xs text-zinc-100" placeholder="Optional subtitle" />
          </label>
        </div>
        <label class="block text-[11px] text-zinc-400">Dedication
          <input v-model="profile.dedication" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2.5 py-2 text-xs text-zinc-100" placeholder="Optional dedication page" />
        </label>
        <section class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-2">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-semibold text-zinc-200">Chapters to include</h3>
            <button @click="toggleAllChapters" class="text-[10px] text-amber-400 hover:underline">{{ selectedChapterIds.length === chapters.length ? 'Select none' : 'Select all' }}</button>
          </div>
          <div v-if="chapters.length" class="max-h-32 overflow-y-auto space-y-1">
            <label v-for="chapter in chapters" :key="chapter.id" class="flex items-center gap-2 text-xs text-zinc-300">
              <input v-model="selectedChapterIds" type="checkbox" :value="chapter.id" class="accent-amber-500" />
              <span>{{ chapter.title }}</span>
            </label>
          </div>
          <p v-else class="text-xs text-zinc-500">No chapters are available in this manuscript.</p>
        </section>
        <div class="grid grid-cols-3 gap-2 text-center">
          <div v-for="status in statusSummary" :key="status.label" class="rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-3">
            <div class="text-lg font-semibold text-zinc-100">{{ status.count }}</div>
            <div class="text-[9px] uppercase tracking-wider text-zinc-500">{{ status.label }}</div>
          </div>
        </div>
        <div class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-400 space-y-1">
          <div class="flex justify-between"><span>Included scenes</span><span class="font-mono text-zinc-200">{{ includedScenes.length }}</span></div>
          <div class="flex justify-between"><span>Included words</span><span class="font-mono text-zinc-200">{{ includedWords.toLocaleString() }}</span></div>
        </div>
        <div v-if="!includedScenes.length" class="rounded-lg border border-amber-700/50 bg-amber-950/30 p-3 text-[11px] text-amber-200">Select chapters containing scenes to export.</div>
        <div v-else-if="emptyScenes.length" class="rounded-lg border border-amber-700/50 bg-amber-950/30 p-3 text-[11px] text-amber-200">
          <strong>{{ emptyScenes.length }} included scene(s) have no draft text:</strong>
          <span class="ml-1">{{ emptySceneTitles }}</span>
        </div>
        <p v-else class="text-[11px] text-emerald-400">Every included scene has draft text. Draft and Revised scenes can still be exported.</p>
        <details class="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
          <summary class="cursor-pointer text-xs font-semibold text-zinc-300">Preview included content</summary>
          <div class="mt-3 space-y-2 text-xs">
            <div v-for="chapter in selectedChapters" :key="chapter.id" class="border-t border-zinc-800 pt-2">
              <div class="font-semibold text-zinc-200">{{ chapter.title }}</div>
              <p v-for="scene in chapter.children?.filter(node => node.node_type === 'SCENE')" :key="scene.id" class="mt-1 text-zinc-400">
                <strong class="text-zinc-300">{{ scene.title }}:</strong> {{ previewText(scene.content) || scene.synopsis || 'No draft text' }}
              </p>
            </div>
          </div>
        </details>
        <section class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-2">
          <div class="flex items-center justify-between"><h3 class="text-xs font-semibold text-zinc-200">Recent exports</h3><button @click="loadHistory" class="text-[10px] text-amber-400 hover:underline">Refresh</button></div>
          <p v-if="!history.length" class="text-[10px] text-zinc-500">No saved exports yet.</p>
          <div v-for="item in history" :key="item.id" class="flex items-center justify-between gap-3 border-t border-zinc-800 pt-2 text-[10px]">
            <span class="truncate text-zinc-300">{{ item.filename }} · {{ item.word_count.toLocaleString() }} words · {{ item.created_at }}</span>
            <a :href="`${API_BASE}/api/publishing/exports/${item.id}/download`" class="shrink-0 text-amber-400 hover:underline">Download</a>
          </div>
        </section>
        <footer class="flex flex-wrap justify-end gap-2">
          <button @click="close" class="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800">Keep writing</button>
          <button @click="openQueryPackage" class="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800">Query package…</button>
          <button @click="saveSettings" :disabled="isExporting" class="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800">Save settings</button>
          <button @click="exportDocument" :disabled="!activeBook || !includedScenes.length || isExporting" class="rounded-lg bg-amber-500 px-4 py-2 text-xs font-bold text-zinc-950 hover:bg-amber-400 disabled:opacity-50">
            {{ isExporting ? 'Saving…' : 'Export DOCX' }}
          </button>
        </footer>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { X } from '@lucide/vue'

import { API_BASE } from '@/api'
const isExporting = ref(false)
const history = ref([])
const openQueryPackage = () => {
  store.toggleModal('export', false)
  store.toggleModal('queryPackage', true)
}
const selectedChapterIds = ref([])
const profile = reactive({
  author_name: '', subtitle: '', dedication: '', genre: '', logline: '',
  author_bio: '', query_text: '', sample_scene_ids: [], included_chapter_ids: null
})

const activeBook = computed(() => store.getBook())
const chapters = computed(() => (activeBook.value?.children || []).filter(node => node.node_type === 'CHAPTER'))
const selectedChapters = computed(() => chapters.value.filter(chapter => selectedChapterIds.value.includes(chapter.id)))
const includedScenes = computed(() => selectedChapters.value.flatMap(chapter => (chapter.children || []).filter(node => node.node_type === 'SCENE')))
const statusSummary = computed(() => [
  { label: 'Draft', count: includedScenes.value.filter(scene => (scene.status || 'DRAFT').toUpperCase() === 'DRAFT').length },
  { label: 'Revised', count: includedScenes.value.filter(scene => (scene.status || '').toUpperCase() === 'REVISED').length },
  { label: 'Final', count: includedScenes.value.filter(scene => (scene.status || '').toUpperCase() === 'FINAL').length }
])
const includedWords = computed(() => includedScenes.value.reduce((total, scene) => total + (Number(scene.word_count) || 0), 0))
const emptyScenes = computed(() => includedScenes.value.filter(scene => !(Number(scene.word_count) > 0)))
const emptySceneTitles = computed(() => emptyScenes.value.slice(0, 4).map(scene => scene.title).join(', ') + (emptyScenes.value.length > 4 ? ', …' : ''))
const close = () => store.toggleModal('export', false)
const previewText = html => (html || '').replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim().slice(0, 280)

const toggleAllChapters = () => {
  selectedChapterIds.value = selectedChapterIds.value.length === chapters.value.length ? [] : chapters.value.map(chapter => chapter.id)
}

const loadHistory = async () => {
  if (!activeBook.value) return
  const response = await fetch(`${API_BASE}/api/publishing/exports/${encodeURIComponent(activeBook.value.id)}`)
  if (!response.ok) throw new Error('Could not load export history.')
  history.value = await response.json()
}

const loadProfile = async () => {
  if (!activeBook.value) return
  try {
    const response = await fetch(`${API_BASE}/api/publishing/profile/${encodeURIComponent(activeBook.value.id)}`)
    if (!response.ok) throw new Error('Could not load export settings.')
    const data = await response.json()
    Object.assign(profile, data)
    if (data.included_chapter_ids === null) {
      selectedChapterIds.value = chapters.value.map(chapter => chapter.id)
    } else {
      selectedChapterIds.value = data.included_chapter_ids.filter(id => chapters.value.some(chapter => chapter.id === id))
    }
    await loadHistory()
  } catch (error) {
    showToast(error.message || 'Could not load export settings.', 'error')
  }
}

const saveProfile = async () => {
  if (!activeBook.value) return
  profile.included_chapter_ids = [...selectedChapterIds.value]
  const response = await fetch(`${API_BASE}/api/publishing/profile/${encodeURIComponent(activeBook.value.id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile)
  })
  if (!response.ok) throw new Error('Could not save export settings.')
  showToast('Export settings saved.', 'info')
}

const saveSettings = async () => {
  try {
    await saveProfile()
  } catch (error) {
    showToast(error.message || 'Could not save export settings.', 'error')
  }
}

const exportDocument = async () => {
  if (!activeBook.value || isExporting.value) return
  isExporting.value = true
  try {
    if (store.flushPendingSave && !(await store.flushPendingSave())) {
      throw new Error('Your latest changes could not be saved. Fix the save issue before exporting.')
    }
    await saveProfile()
    const response = await fetch(`${API_BASE}/api/publishing/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: activeBook.value.id, ...profile, chapter_ids: selectedChapterIds.value })
    })
    if (!response.ok) {
      const details = await response.json().catch(() => ({}))
      throw new Error(details.detail || `Export failed (${response.status}).`)
    }
    const blob = await response.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = response.headers.get('Content-Disposition')?.match(/filename="?([^";]+)"?/)?.[1] || `${activeBook.value.title || 'Manuscript'}.docx`
    document.body.append(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(link.href)
    await loadHistory()
    close()
  } catch (error) {
    showToast(error.message || 'Could not prepare the export.', 'error')
  } finally {
    isExporting.value = false
  }
}

watch(() => activeBook.value?.id, loadProfile, { immediate: true })
</script>
