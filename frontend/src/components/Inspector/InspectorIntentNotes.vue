<template>
  <section class="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3 space-y-2">
    <header class="flex items-baseline justify-between gap-2">
      <h2 class="text-[10px] font-bold uppercase tracking-wider text-zinc-400">Your intent notes · optional</h2>
      <span class="text-[9px] font-mono text-zinc-600">{{ notes.length }}</span>
    </header>
    <p class="text-[9px] leading-relaxed text-zinc-500">
      Jot what you meant a reader to take from this scene. These are your own notes: they are never used to estimate the reader experience, so the estimates above stay grounded in the text alone.
    </p>

    <div class="space-y-1.5">
      <select v-model="form.type" class="w-full bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-zinc-200">
        <option v-for="t in types" :key="t.value" :value="t.value">{{ t.label }}</option>
      </select>
      <textarea v-model="form.claim" rows="2" maxlength="1000" placeholder="What should the reader take from this?" class="w-full bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-zinc-200 focus:outline-none"></textarea>
      <input v-model="form.excerpt" maxlength="1000" placeholder="Passage that carries it (optional)" class="w-full bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-zinc-200 focus:outline-none" />
      <button @click="add" :disabled="!form.claim.trim() || busy" class="w-full py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 text-zinc-100 text-[11px] font-medium">Save note</button>
    </div>

    <ul v-if="notes.length" class="space-y-1.5">
      <li v-for="n in notes" :key="n.id" class="rounded border border-zinc-800 bg-zinc-900/60 p-2 space-y-0.5">
        <div class="flex items-start justify-between gap-2">
          <span class="text-[9px] font-mono uppercase text-amber-300">{{ typeLabel(n.disclosure_type) }}</span>
          <button @click="remove(n)" class="text-zinc-600 hover:text-rose-400 text-[10px]" title="Delete note">✕</button>
        </div>
        <p class="text-[11px] text-zinc-200 leading-snug">{{ n.narrative_claim }}</p>
        <p v-if="n.source_excerpt" class="border-l border-zinc-700 pl-2 text-[10px] italic text-zinc-500">“{{ n.source_excerpt }}”</p>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'

const types = [
  { value: 'INTENDED', label: 'Intended takeaway' },
  { value: 'DIRECT', label: 'Should be clear' },
  { value: 'INFERRED', label: 'Should be inferred' },
  { value: 'DELAYED', label: 'Should stay open for later' }
]
const notes = ref([])
const busy = ref(false)
const form = reactive({ type: 'INTENDED', claim: '', excerpt: '' })
const typeLabel = (value) => types.find(t => t.value === value)?.label || value

const load = async () => {
  const id = store.activeNode?.id
  if (!id || store.activeNode.node_type !== 'SCENE') { notes.value = []; return }
  try {
    const res = await fetch(`${API_BASE}/api/disclosures/scene/${encodeURIComponent(id)}`)
    const rows = res.ok ? await res.json() : []
    notes.value = Array.isArray(rows) ? rows.filter(row => row.source === 'AUTHOR') : []
  } catch (err) {
    notes.value = []
  }
}

const add = async () => {
  busy.value = true
  try {
    const res = await fetch(`${API_BASE}/api/disclosures/author-note`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_id: store.activeNode.id,
        disclosure_type: form.type,
        narrative_claim: form.claim.trim(),
        source_excerpt: form.excerpt.trim()
      })
    })
    if (!res.ok) throw new Error('Could not save the note.')
    form.claim = ''
    form.excerpt = ''
    await load()
  } catch (err) {
    showToast(err.message, 'error')
  } finally {
    busy.value = false
  }
}

const remove = async (note) => {
  try {
    const res = await fetch(`${API_BASE}/api/disclosures/${note.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Could not delete the note.')
    await load()
  } catch (err) {
    showToast(err.message, 'error')
  }
}

watch(() => store.activeNode?.id, load, { immediate: true })
</script>
