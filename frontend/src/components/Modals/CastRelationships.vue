<template>
  <section class="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3 space-y-2 shrink-0">
    <header class="flex items-baseline justify-between gap-2">
      <h3 class="text-[10px] font-mono uppercase tracking-wider text-zinc-400">Relationships</h3>
      <span class="text-[9px] text-zinc-600">{{ connections.length }} recorded</span>
    </header>

    <div v-if="entities.length >= 2" class="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-1.5 items-center">
      <select v-model="form.source" class="bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-zinc-200">
        <option value="">Who…</option>
        <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.name }}</option>
      </select>
      <select v-model="form.type" class="bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-amber-300">
        <option v-for="t in types" :key="t" :value="t">{{ label(t) }}</option>
      </select>
      <select v-model="form.target" class="bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-zinc-200">
        <option value="">…whom</option>
        <option v-for="e in entities" :key="e.entity_id" :value="e.entity_id">{{ e.name }}</option>
      </select>
      <input v-model="form.description" placeholder="Note (optional)" class="sm:col-span-2 bg-zinc-900 border border-zinc-800 rounded p-1.5 text-[11px] text-zinc-200" />
      <button @click="add" :disabled="!form.source || !form.target || form.source === form.target" class="py-1.5 rounded bg-amber-600/80 hover:bg-amber-500 disabled:opacity-40 text-white text-[11px] font-medium">Add</button>
    </div>
    <p v-else class="text-[10px] text-zinc-500">Track at least two cast members to record how they relate.</p>

    <ul v-if="connections.length" class="space-y-1 max-h-36 overflow-y-auto">
      <li v-for="r in connections" :key="r.rel_id" class="flex items-center justify-between gap-2 text-[11px] bg-zinc-900/70 border border-zinc-800 rounded px-2 py-1">
        <span class="min-w-0 truncate text-zinc-200">
          {{ r.source_name }} <span class="text-amber-300 font-mono">{{ label(r.rel_type) }}</span> {{ r.target_name }}
          <span v-if="r.description" class="text-zinc-500"> — {{ r.description }}</span>
        </span>
        <button @click="remove(r)" class="text-zinc-600 hover:text-rose-400 shrink-0" title="Remove relationship">✕</button>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'

const types = ['ALLIED', 'HOSTILE', 'FAMILY', 'ROMANTIC', 'MENTOR_OF', 'RIVAL', 'KNOWS_SECRET', 'DEBT_TO', 'ANCESTOR_OF']
const connections = ref([])
const form = reactive({ source: '', target: '', type: 'ALLIED', description: '' })
const entities = computed(() => store.registeredEntities.filter(e => e.entity_type === 'CHARACTER' || e.entity_type === 'FACTION'))
const label = (type) => type.toLowerCase().replace(/_/g, ' ')

const load = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/narrative/connections`)
    connections.value = res.ok ? await res.json() : []
  } catch (err) {
    connections.value = []
  }
}

const add = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/narrative/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: form.source, target_id: form.target, rel_type: form.type, description: form.description })
    })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Could not save the relationship.')
    form.description = ''
    await load()
  } catch (err) {
    showToast(err.message, 'error')
  }
}

const remove = async (relationship) => {
  try {
    const res = await fetch(`${API_BASE}/api/narrative/connections/${encodeURIComponent(relationship.rel_id)}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Could not remove the relationship.')
    await load()
  } catch (err) {
    showToast(err.message, 'error')
  }
}

watch(() => [store.modals.cast, store.registeredEntities.length], ([open]) => { if (open) load() }, { immediate: true })
</script>
