<template>
  <div class="text-[9px] leading-relaxed">
    <p v-if="status?.available" class="text-emerald-300/80">
      Wiktionary is installed: word forms and synonyms widen the story cues. (CC BY-SA 4.0)
    </p>
    <div v-else class="space-y-1">
      <p class="text-zinc-500">
        Wiktionary is not installed, so the reader uses its built-in vocabulary only. A one-time download of about 400 MB adds synonyms and word forms.
      </p>
      <button v-if="!downloading" @click="start" class="rounded border border-violet-700/60 px-2 py-0.5 text-violet-300 hover:bg-violet-900/30">Download Wiktionary</button>
      <p v-else class="text-amber-300">Downloading and preparing… this can take a few minutes. You can keep writing.</p>
      <p v-if="status?.download?.state === 'failed'" class="text-rose-300">Download failed: {{ status.download.error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { store } from '../../store.js'
import { API_BASE } from '@/api'

const status = ref(null)
const downloading = computed(() => status.value?.download?.state === 'running')
let timer

const load = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/lexicon/status`)
    status.value = res.ok ? await res.json() : null
  } catch {
    status.value = null
  }
  if (downloading.value) timer = setTimeout(load, 4000)
  else if (status.value?.available) store.readerStoryCache = null
}

const start = async () => {
  await fetch(`${API_BASE}/api/lexicon/download`, { method: 'POST' }).catch(() => {})
  clearTimeout(timer)
  load()
}

onMounted(load)
onBeforeUnmount(() => clearTimeout(timer))
</script>
