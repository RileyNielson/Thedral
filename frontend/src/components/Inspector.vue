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
    <!-- 5-Tab Analytical Navigation -->
    <div 
      class="flex border-b text-xs shrink-0 font-mono"
      :class="store.isCandlelight ? 'border-amber-900/40' : 'border-zinc-800'"
    >
      <button 
        @click="store.activeInspectorTab = 'card'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'card' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Card
      </button>
      <button 
        @click="store.activeInspectorTab = 'telemetry'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'telemetry' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Patterns
      </button>
      <button 
        @click="store.activeInspectorTab = 'socratic'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'socratic' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Socratic
      </button>
      <button 
        @click="store.activeInspectorTab = 'reader'" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition', store.activeInspectorTab === 'reader' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        Reader
      </button>
      <button 
        @click="openLensTab" 
        :class="['flex-1 py-2.5 font-medium border-b-2 text-center transition flex items-center justify-center gap-1', store.activeInspectorTab === 'lens' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-zinc-500 hover:text-zinc-300']"
      >
        <Microscope class="w-3 h-3" /> Lens
      </button>
    </div>

    <!-- Empty Inspector State -->
    <div v-if="!store.activeNode?.id" class="flex-1 flex items-center justify-center p-6 text-zinc-600 text-center">
      <p class="text-xs">Select a scene to engage analytical perspectives.</p>
    </div>

    <div v-else class="flex-1 overflow-y-auto p-4 text-xs space-y-5 custom-scrollbar">
      <InspectorCardTab />
      <InspectorPatternsTab />
      <InspectorSocraticTab />
      <InspectorReaderTab />
      <InspectorLensTab />
    </div>
  </aside>
</template>

<script setup>
import { provide } from 'vue'
import { store } from '../store.js'
import { Microscope } from '@lucide/vue'
import { useInspectorState } from './Inspector/useInspectorState.js'
import InspectorCardTab from './Inspector/InspectorCardTab.vue'
import InspectorPatternsTab from './Inspector/InspectorPatternsTab.vue'
import InspectorSocraticTab from './Inspector/InspectorSocraticTab.vue'
import InspectorReaderTab from './Inspector/InspectorReaderTab.vue'
import InspectorLensTab from './Inspector/InspectorLensTab.vue'

const inspectorState = useInspectorState()
provide('inspectorState', inspectorState)
const { openLensTab } = inspectorState
</script>
