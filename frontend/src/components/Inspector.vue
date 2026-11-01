<template>
  <aside 
    v-show="!store.isVoidMode" 
    :class="[
      'w-84 border-l bg-zinc-950 md:bg-zinc-900/60 shadow-2xl backdrop-blur-xl flex flex-col transition-all z-20 shrink-0 select-none',
      'fixed inset-y-12 right-0 md:static md:translate-x-0',
      store.modals.mobileInspector ? 'translate-x-0' : 'translate-x-full md:translate-x-0',
      store.isCandlelight ? 'border-amber-900/40 bg-[#120f0c]' : 'border-zinc-800/80'
    ]"
  >
    <!-- 3-Tab Unified Navigation -->
    <div 
      class="flex border-b text-xs shrink-0 font-mono"
      :class="store.isCandlelight ? 'border-amber-900/40' : 'border-zinc-800'"
    >
      <button 
        @click="store.activeInspectorTab = 'blueprint'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', (store.activeInspectorTab === 'blueprint' || store.activeInspectorTab === 'card') ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Blueprint
      </button>
      <button 
        @click="store.activeInspectorTab = 'prose'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', (store.activeInspectorTab === 'prose' || store.activeInspectorTab === 'telemetry') ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Prose
      </button>
      <button 
        @click="store.activeInspectorTab = 'reader'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'reader' ? 'border-violet-500 text-violet-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Reader
      </button>
    </div>

    <!-- Empty Inspector State -->
    <div v-if="!store.activeNode?.id" class="flex-1 flex items-center justify-center p-6 text-zinc-600 text-center">
      <p class="text-xs">Select a scene to engage analytical perspectives.</p>
    </div>

    <!-- Active Workspace Surface -->
    <div v-else class="flex-1 overflow-y-auto p-4 text-xs space-y-5 custom-scrollbar">
      <InspectorCardTab v-if="store.activeInspectorTab === 'blueprint' || store.activeInspectorTab === 'card'" />
      <InspectorPatternsTab v-if="store.activeInspectorTab === 'prose' || store.activeInspectorTab === 'telemetry'" />
      <InspectorReaderTab v-if="store.activeInspectorTab === 'reader'" />
    </div>
  </aside>
</template>

<script setup>
import { provide } from 'vue'
import { store } from '../store.js'
import { useInspectorState } from './Inspector/useInspectorState.js'
import InspectorCardTab from './Inspector/InspectorCardTab.vue'
import InspectorPatternsTab from './Inspector/InspectorPatternsTab.vue'
import InspectorReaderTab from './Inspector/InspectorReaderTab.vue'

const inspectorState = useInspectorState()
provide('inspectorState', inspectorState)
</script>
