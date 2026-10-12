<template>
  <div v-if="store.modals.submission" class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-[90] p-4" @click.self="close">
    <section class="w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl border border-zinc-700 bg-zinc-900 shadow-2xl flex flex-col" role="dialog" aria-modal="true" aria-labelledby="submission-title">
      <header class="flex items-center justify-between border-b border-zinc-800 p-5">
        <div>
          <h2 id="submission-title" class="text-base font-bold text-zinc-100">Submission workspace</h2>
          <p class="mt-1 text-xs text-zinc-500">{{ activeBook?.title || 'Choose a manuscript' }} · stored locally</p>
        </div>
        <button @click="close" class="text-zinc-500 hover:text-white" aria-label="Close submission workspace"><X class="w-5 h-5" /></button>
      </header>
      <div class="flex-1 overflow-y-auto p-5 grid grid-cols-1 lg:grid-cols-2 gap-5">
        <section class="space-y-3">
          <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-300">Query package details</h3>
          <label class="block text-[11px] text-zinc-400">Genre
            <input v-model="profile.genre" class="form-input" placeholder="e.g. Literary fantasy" />
          </label>
          <label class="block text-[11px] text-zinc-400">Logline
            <textarea v-model="profile.logline" rows="2" class="form-input" placeholder="A concise one- or two-sentence pitch" />
          </label>
          <label class="block text-[11px] text-zinc-400">Author bio
            <textarea v-model="profile.author_bio" rows="3" class="form-input" placeholder="A brief professional biography" />
          </label>
          <label class="block text-[11px] text-zinc-400">Query letter / synopsis
            <textarea v-model="profile.query_text" rows="6" class="form-input" placeholder="Paste or draft your query letter and synopsis here" />
          </label>
          <div class="space-y-1">
            <div class="text-[11px] text-zinc-400">Sample scenes (included in the generated text package)</div>
            <label v-for="scene in scenes" :key="scene.id" class="flex items-center gap-2 text-xs text-zinc-300">
              <input v-model="profile.sample_scene_ids" type="checkbox" :value="scene.id" class="accent-amber-500" />
              <span>{{ scene.chapter_title }} / {{ scene.title }}</span>
            </label>
          </div>
          <div class="flex gap-2">
            <button @click="saveProfile" class="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800">Save details</button>
            <button @click="createPackage" class="rounded-lg bg-amber-500 px-3 py-2 text-xs font-bold text-zinc-950 hover:bg-amber-400">Build package</button>
          </div>
        </section>
        <section class="space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-300">Local submission tracker</h3>
            <span class="text-[10px] text-zinc-500">No data is sent to a recipient</span>
          </div>
          <div class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-2">
            <input v-model="submission.recipient" class="form-input" placeholder="Agent, editor, publisher, or venue" />
            <div class="grid grid-cols-2 gap-2">
              <label class="text-[10px] text-zinc-500">Date sent
                <input v-model="submission.sent_at" type="date" class="form-input" />
              </label>
              <label class="text-[10px] text-zinc-500">Response due (optional)
                <input v-model="submission.response_due" type="date" class="form-input" />
              </label>
            </div>
            <textarea v-model="submission.notes" rows="2" class="form-input" placeholder="Notes, requested materials, or follow-up reminder" />
            <button @click="addSubmission" :disabled="!submission.recipient.trim()" class="rounded-lg bg-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-700 disabled:opacity-50">Add submission</button>
          </div>
          <p v-if="!records.length" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-500">No submissions tracked yet.</p>
          <article v-for="record in records" :key="record.id" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-2">
            <div class="flex items-center gap-2">
              <input v-model="record.recipient" class="form-input min-w-0 flex-1 font-semibold" />
              <select v-model="record.status" class="form-input w-32">
                <option v-for="status in statuses" :key="status" :value="status">{{ statusLabel(status) }}</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <label class="text-[10px] text-zinc-500">Sent
                <input v-model="record.sent_at" type="date" class="form-input" />
              </label>
              <label class="text-[10px] text-zinc-500">Response due
                <input v-model="record.response_due" type="date" class="form-input" />
              </label>
            </div>
            <textarea v-model="record.notes" rows="2" class="form-input" placeholder="Notes" />
            <div class="flex justify-between">
              <button @click="updateSubmission(record)" class="text-[10px] text-amber-400 hover:underline">Save changes</button>
              <button @click="deleteSubmission(record.id)" class="text-[10px] text-rose-400 hover:underline">Delete</button>
            </div>
          </article>
        </section>
        <section v-if="packageText" class="lg:col-span-2 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <h3 class="font-semibold text-zinc-200">Package preview</h3>
            <div class="flex gap-3">
              <button @click="copyPackage" class="text-amber-400 hover:underline">Copy</button>
              <button @click="downloadPackage" class="text-amber-400 hover:underline">Download .md</button>
            </div>
          </div>
          <pre class="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-[11px] leading-relaxed text-zinc-300">{{ packageText }}</pre>
        </section>
      </div>
      <footer class="border-t border-zinc-800 p-4 flex justify-between">
        <button @click="close" class="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800">Close</button>
        <button @click="store.toggleModal('career', true); close()" class="text-xs text-zinc-400 hover:text-zinc-200">Publishing tools</button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { X } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const statuses = ['PREPARING', 'SENT', 'REQUESTED', 'REJECTED', 'ACCEPTED', 'WITHDRAWN']
const activeBook = computed(() => store.getBook())
const profile = reactive({ author_name: '', genre: '', logline: '', author_bio: '', query_text: '', sample_scene_ids: [] })
const submission = reactive({ recipient: '', sent_at: new Date().toISOString().slice(0, 10), response_due: '', notes: '' })
const records = ref([])
const packageText = ref('')
const scenes = computed(() => {
  const result = []
  for (const chapter of activeBook.value?.children || []) {
    if (chapter.node_type !== 'CHAPTER') continue
    for (const scene of chapter.children || []) {
      if (scene.node_type === 'SCENE') result.push({ ...scene, chapter_title: chapter.title })
    }
  }
  return result
})

const loadWorkspace = async () => {
  if (!activeBook.value) return
  try {
    const [profileResponse, recordsResponse] = await Promise.all([
      fetch(`${API_BASE}/api/publishing/profile/${encodeURIComponent(activeBook.value.id)}`),
      fetch(`${API_BASE}/api/publishing/submissions/${encodeURIComponent(activeBook.value.id)}`)
    ])
    if (!profileResponse.ok || !recordsResponse.ok) throw new Error('Could not load submission workspace.')
    Object.assign(profile, await profileResponse.json())
    records.value = await recordsResponse.json()
  } catch (error) {
    showToast(error.message || 'Could not load submission workspace.', 'error')
  }
}

const saveProfile = async () => {
  if (!activeBook.value) return
  const existingResponse = await fetch(`${API_BASE}/api/publishing/profile/${encodeURIComponent(activeBook.value.id)}`)
  if (!existingResponse.ok) throw new Error('Could not load saved publishing settings.')
  const existing = await existingResponse.json()
  const response = await fetch(`${API_BASE}/api/publishing/profile/${encodeURIComponent(activeBook.value.id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...existing, ...profile, sample_scene_ids: profile.sample_scene_ids })
  })
  if (!response.ok) throw new Error('Could not save submission package details.')
  showToast('Submission details saved locally.', 'info')
}

const createPackage = async () => {
  try {
    await saveProfile()
    const wordCount = scenes.value.reduce((total, scene) => total + (Number(scene.word_count) || 0), 0)
    const parts = [
      `# ${activeBook.value?.title || 'Untitled manuscript'}`,
      `**Author:** ${profile.author_name || 'Not supplied'}`,
      `**Genre:** ${profile.genre || 'Not supplied'}`,
      `**Word count:** ${wordCount.toLocaleString()}`,
      '',
      '## Logline',
      profile.logline || 'Not supplied',
      '',
      '## Query letter / Synopsis',
      profile.query_text || 'Not supplied',
      '',
      '## About the author',
      profile.author_bio || 'Not supplied'
    ]
    for (const id of profile.sample_scene_ids) {
      const scene = scenes.value.find(item => item.id === id)
      if (scene) parts.push('', `## Sample: ${scene.title}`, `_${scene.chapter_title}_`, '', plainText(scene.content) || '[No scene draft text]')
    }
    packageText.value = parts.join('\n')
  } catch (error) {
    showToast(error.message || 'Could not prepare submission package.', 'error')
  }
}

const plainText = html => (html || '').replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n\n').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').trim()
const copyPackage = async () => {
  try {
    await navigator.clipboard.writeText(packageText.value)
    showToast('Package copied to clipboard.', 'info')
  } catch {
    showToast('Could not copy package text.', 'error')
  }
}
const downloadPackage = () => {
  const blob = new Blob([packageText.value], { type: 'text/markdown;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${(activeBook.value?.title || 'submission-package').replace(/[^a-z0-9_-]+/gi, '_')}_submission.md`
  link.click()
  URL.revokeObjectURL(link.href)
}

const addSubmission = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/publishing/submissions/${encodeURIComponent(activeBook.value.id)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(submission)
    })
    if (!response.ok) throw new Error((await response.json()).detail || 'Could not add submission record.')
    Object.assign(submission, { recipient: '', response_due: '', notes: '' })
    await loadWorkspace()
    showToast('Submission added.', 'info')
  } catch (error) {
    showToast(error.message || 'Could not add submission.', 'error')
  }
}
const updateSubmission = async record => {
  try {
    const response = await fetch(`${API_BASE}/api/publishing/submissions/${encodeURIComponent(record.id)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient: record.recipient, sent_at: record.sent_at, status: record.status, response_due: record.response_due, notes: record.notes })
    })
    if (!response.ok) throw new Error((await response.json()).detail || 'Could not save submission record.')
    showToast('Submission updated.', 'info')
  } catch (error) {
    showToast(error.message || 'Could not update submission.', 'error')
  }
}
const deleteSubmission = async id => {
  try {
    const response = await fetch(`${API_BASE}/api/publishing/submissions/${encodeURIComponent(id)}`, { method: 'DELETE' })
    if (!response.ok) throw new Error('Could not delete submission record.')
    records.value = records.value.filter(record => record.id !== id)
  } catch (error) {
    showToast(error.message || 'Could not delete submission.', 'error')
  }
}
const statusLabel = status => status.charAt(0) + status.slice(1).toLowerCase()
const close = () => store.toggleModal('submission', false)

watch(() => activeBook.value?.id, loadWorkspace, { immediate: true })
</script>

<style scoped>
.form-input {
  width: 100%;
  margin-top: 0.25rem;
  border: 1px solid #3f3f46;
  border-radius: 0.25rem;
  background: #09090b;
  padding: 0.5rem 0.625rem;
  color: #f4f4f5;
  font-size: 0.75rem;
  line-height: 1rem;
}

.form-input:focus {
  border-color: #f59e0b;
  outline: none;
}
</style>
