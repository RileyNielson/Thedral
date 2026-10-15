<template>
  <section class="pt-3 border-t border-zinc-800 space-y-2">
    <div class="flex items-center justify-between gap-2">
      <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Lore in this scene</span>
      <button @click="load" :disabled="loading" class="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-amber-400 rounded text-[10px]">
        {{ loading ? 'Checking…' : 'Find connections' }}
      </button>
    </div>
    <template v-if="result">
      <p class="text-[9px] text-zinc-500">Found by matching your Lore and Cast names in the text.{{ store.aiEnabled ? ' No AI.' : '' }}</p>
      <div>
        <p class="text-[9px] uppercase tracking-wider text-zinc-600">Present here</p>
        <p v-if="!result.present.length" class="text-[10px] text-zinc-600">Nothing from your Lore or Cast is named in this scene.</p>
        <div class="flex flex-wrap gap-1 mt-1">
          <span v-for="item in result.present" :key="item.label || item" class="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-200">{{ item.label || item }}</span>
        </div>
      </div>
      <div v-if="result.dormant.length">
        <p class="text-[9px] uppercase tracking-wider text-zinc-600">Elsewhere in the book, not here</p>
        <div class="flex flex-wrap gap-1 mt-1">
          <span v-for="item in result.dormant" :key="item.label || item" class="px-1.5 py-0.5 rounded border border-zinc-700 text-[10px] text-zinc-400">{{ item.label || item }}</span>
        </div>
      </div>
      <div v-if="result.ai_generated && result.suggestion" class="space-y-1">
        <p class="text-[9px] font-mono uppercase tracking-wider text-amber-400">AI suggestion, based on the lists above</p>
        <p class="p-2 bg-zinc-950 rounded border border-amber-500/30 text-[11px] text-zinc-200 font-serif leading-snug whitespace-pre-line">{{ result.suggestion }}</p>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'

const result = ref(null)
const loading = ref(false)

const load = async () => {
  if (!store.activeNode?.id) return
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/narrative/serendipity/${encodeURIComponent(store.activeNode.id)}`)
    if (!res.ok) throw new Error('Could not check lore connections.')
    result.value = await res.json()
  } catch (err) {
    showToast(err.message, 'error')
  } finally {
    loading.value = false
  }
}

watch(() => store.activeNode?.id, () => { result.value = null })
</script>
