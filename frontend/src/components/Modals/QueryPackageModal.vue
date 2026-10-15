<template>
  <div v-if="store.modals.queryPackage" class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-[90] p-4" @click.self="close">
    <section class="w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl border border-zinc-700 bg-zinc-900 shadow-2xl flex flex-col" role="dialog" aria-modal="true" aria-labelledby="query-package-title">
      <header class="flex items-center justify-between border-b border-zinc-800 p-5">
        <div>
          <h2 id="query-package-title" class="text-base font-bold text-zinc-100">Query package</h2>
          <p class="mt-1 text-xs text-zinc-500">{{ activeBook?.title || 'Choose a manuscript' }} · stored locally</p>
        </div>
        <button @click="close" class="text-zinc-500 hover:text-white" aria-label="Close query package"><X class="w-5 h-5" /></button>
      </header>
      <div class="flex-1 overflow-y-auto p-5 grid grid-cols-1 gap-5">
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
          <label class="block text-[11px] text-zinc-400">
            <span class="flex items-center justify-between">
              <span>Query letter / synopsis</span>
              <button v-if="store.aiEnabled" type="button" @click.prevent="draftSynopsis" :disabled="isDrafting" class="text-[10px] text-amber-400 hover:underline disabled:opacity-50">{{ isDrafting ? 'Drafting…' : 'Draft from scene summaries (AI, optional)' }}</button>
            </span>
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
        <section v-if="packageText" class="space-y-2">
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
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { X } from '@lucide/vue'

import { API_BASE } from '@/api'
const activeBook = computed(() => store.getBook())
const profile = reactive({ author_name: '', genre: '', logline: '', author_bio: '', query_text: '', sample_scene_ids: [] })
const isDrafting = ref(false)
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
    const response = await fetch(`${API_BASE}/api/publishing/profile/${encodeURIComponent(activeBook.value.id)}`)
    if (!response.ok) throw new Error('Could not load query package details.')
    Object.assign(profile, await response.json())
  } catch (error) {
    showToast(error.message || 'Could not load query package details.', 'error')
  }
}

// Optional AI helper: drafts a synopsis from the scene summaries; the author edits it before use.
const draftSynopsis = async () => {
  if (!activeBook.value) return
  isDrafting.value = true
  try {
    const response = await fetch(`${API_BASE}/api/publishing/synopsis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book_id: activeBook.value.id })
    })
    const data = await response.json()
    if (!response.ok) throw new Error('Synopsis drafting failed.')
    if (!data.ai_generated) {
      showToast(data.synopsis, 'info')
      return
    }
    const note = '[AI-drafted from your scene summaries. Edit before sending.]\n\n'
    profile.query_text = profile.query_text ? `${profile.query_text}\n\n${note}${data.synopsis}` : `${note}${data.synopsis}`
  } catch (error) {
    showToast(error.message, 'error')
  } finally {
    isDrafting.value = false
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
  link.download = `${(activeBook.value?.title || 'query-package').replace(/[^a-z0-9_-]+/gi, '_')}_query_package.md`
  link.click()
  URL.revokeObjectURL(link.href)
}

const close = () => store.toggleModal('queryPackage', false)

watch(() => [store.modals.queryPackage, activeBook.value?.id], ([open]) => { if (open) loadWorkspace() }, { immediate: true })
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
