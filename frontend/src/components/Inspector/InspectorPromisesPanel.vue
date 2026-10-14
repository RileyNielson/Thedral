<template>
  <section class="rounded-xl border border-pink-900/40 bg-pink-950/10 p-3 space-y-2">
    <header class="flex items-baseline justify-between gap-2">
      <h3 class="text-[10px] font-mono uppercase tracking-wider text-pink-300">Promises (setups to pay off)</h3>
      <span class="text-[9px] text-zinc-500">{{ openCount }} open</span>
    </header>
    <p class="text-[10px] text-zinc-500 leading-snug">
      Record a setup planted in this scene. Open promises appear as pink wells in the Cosmograph; paid-off ones turn green.
    </p>

    <div class="space-y-1.5">
      <input v-model="form.desc" placeholder="e.g. The locked drawer in Marcus's study" class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-pink-500/50 focus:outline-none" />
      <div class="grid grid-cols-2 gap-1.5">
        <input v-model.number="form.tick" type="number" step="0.5" min="0" placeholder="Payoff day" class="bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:outline-none" />
        <input v-model="form.location" placeholder="Payoff location" class="bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:outline-none" />
      </div>
      <button @click="plant" :disabled="!form.desc.trim() || busy" class="w-full py-1.5 rounded-lg bg-pink-600/80 hover:bg-pink-500 disabled:opacity-40 text-white text-[11px] font-medium transition">
        Plant promise in this scene
      </button>
    </div>

    <ul v-if="promises.length" class="space-y-1.5">
      <li v-for="p in promises" :key="p.id" class="rounded-lg border border-zinc-800 bg-zinc-950/60 p-2 space-y-1">
        <div class="flex items-start justify-between gap-2">
          <span :class="['text-[11px] leading-snug', p.status === 'PAID_OFF' ? 'text-emerald-300 line-through decoration-emerald-700' : p.status === 'DROPPED' ? 'text-zinc-500 line-through' : 'text-zinc-200']">{{ p.promise_desc }}</span>
          <span class="text-[9px] font-mono shrink-0" :class="p.status === 'PAID_OFF' ? 'text-emerald-400' : p.status === 'DROPPED' ? 'text-zinc-500' : 'text-pink-300'">{{ statusLabel(p.status) }}</span>
        </div>
        <div class="text-[9px] text-zinc-500 font-mono">
          Planted: {{ p.planted_scene_title || 'unassigned' }} · Payoff day {{ p.target_tick }}<span v-if="p.target_location"> · {{ p.target_location }}</span>
        </div>
        <div class="flex gap-1.5 text-[10px]">
          <button v-if="p.status !== 'PAID_OFF'" @click="setStatus(p, 'PAID_OFF')" class="px-2 py-0.5 rounded bg-emerald-900/50 text-emerald-300 hover:bg-emerald-800/60">Paid off</button>
          <button v-if="p.status !== 'SEEDED'" @click="setStatus(p, 'SEEDED')" class="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Reopen</button>
          <button v-if="p.status === 'SEEDED'" @click="setStatus(p, 'DROPPED')" class="px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 hover:bg-zinc-700">Drop</button>
          <button @click="remove(p)" class="px-2 py-0.5 rounded bg-zinc-800 text-rose-400 hover:bg-zinc-700 ml-auto">Delete</button>
        </div>
      </li>
    </ul>
    <p v-else class="text-[10px] text-zinc-500">No promises recorded for this manuscript yet.</p>
  </section>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'

const promises = ref([])
const busy = ref(false)
const form = reactive({ desc: '', tick: 5, location: '' })

const bookId = computed(() => (store.activeNode?.id ? store.findBookForNode(store.activeNode.id)?.id : null))
const openCount = computed(() => promises.value.filter(p => p.status === 'SEEDED').length)
const statusLabel = (status) => ({ SEEDED: 'Open', PAID_OFF: 'Paid off', DROPPED: 'Dropped' }[status] || status)

const load = async () => {
  if (!bookId.value) { promises.value = []; return }
  try {
    const res = await fetch(`${API_BASE}/api/narrative/promises?book_id=${encodeURIComponent(bookId.value)}`)
    promises.value = res.ok ? await res.json() : []
  } catch (err) {
    promises.value = []
  }
}

const call = async (url, options, failure) => {
  const res = await fetch(`${API_BASE}${url}`, options)
  if (!res.ok) throw new Error(failure)
  await load()
}

const plant = async () => {
  busy.value = true
  try {
    await call('/api/narrative/promise', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: bookId.value,
        scene_id: store.activeNode?.id,
        promise_desc: form.desc.trim(),
        target_tick: Number(form.tick) || 0,
        target_location: form.location.trim()
      })
    }, 'Could not save the promise.')
    form.desc = ''
    form.location = ''
    showToast('Promise planted.', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  } finally {
    busy.value = false
  }
}

const setStatus = (promise, status) => call(
  `/api/narrative/promises/${promise.id}`,
  { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) },
  'Could not update the promise.'
).catch(err => showToast(err.message, 'error'))

const remove = (promise) => call(
  `/api/narrative/promises/${promise.id}`,
  { method: 'DELETE' },
  'Could not delete the promise.'
).catch(err => showToast(err.message, 'error'))

watch(bookId, load, { immediate: true })
</script>
