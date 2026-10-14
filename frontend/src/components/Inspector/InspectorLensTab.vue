<template>
  <div v-if="store.activeInspectorTab === 'lens'" class="space-y-3 flex flex-col h-full">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5 font-medium text-[11px] text-cyan-400">
        <Microscope class="w-3.5 h-3.5" />
        <span>Chapter Spacetime Topography</span>
      </div>
      <button 
        @click="store.viewMode = 'cosmograph'" 
        class="px-2 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[10px] font-mono flex items-center gap-1 transition"
      >
        <Maximize class="w-3 h-3" /> Full Cosmos
      </button>
    </div>
    
    <p class="text-[10px] text-zinc-500 leading-snug">
      Real-time chapter waveform. Click any node to jump to that beat.
    </p>

    <div class="flex-1 w-full min-h-[300px] bg-zinc-950 rounded-xl border border-zinc-800/80 overflow-hidden relative shadow-inner">
      <div v-if="isLensLoading" class="absolute inset-0 flex items-center justify-center bg-zinc-950/70 z-10">
        <Loader class="w-5 h-5 text-cyan-400 animate-spin" />
      </div>
      <div id="mini-astrolabe-plot" class="w-full h-full"></div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'
import { Microscope, Loader, Maximize } from '@lucide/vue'

const {
  isLensLoading
} = inject('inspectorState')
</script>
