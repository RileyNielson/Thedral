<template>
  <div 
    class="flex flex-col h-screen w-screen overflow-hidden select-none font-sans transition-colors duration-500"
    :class="[
      store.isCandlelight 
        ? 'bg-[#0c0a09] text-amber-100/90 selection:bg-amber-900/50' 
        : 'bg-zinc-950 text-zinc-100 selection:bg-indigo-900/50'
    ]"
  >
    <!-- Top Global Command & Navigation Bar (Hidden in Void Mode) -->
    <TopNav v-if="!store.isVoidMode" />

    <!-- Main Workspace Container -->
    <div 
      class="flex flex-1 overflow-hidden transition-all duration-300 relative"
      :class="store.isVoidMode ? 'p-0' : 'p-3 gap-3'"
    >
      <!-- Hierarchical Binder Sidebar -->
      <Binder 
        v-if="!store.isVoidMode && !store.binderCollapsed" 
        class="w-64 flex-shrink-0 transition-all duration-300" 
      />

      <!-- Center Work Surface -->
      <main 
        class="flex-1 flex flex-col relative overflow-hidden transition-all duration-300 shadow-2xl"
        :class="[
          store.isVoidMode 
            ? 'rounded-none border-none bg-transparent' 
            : store.isCandlelight 
              ? 'rounded-lg border border-amber-900/30 bg-[#14100c]' 
              : 'rounded-lg border border-zinc-800/80 bg-zinc-900/70 backdrop-blur-sm'
        ]"
      >
        <!-- Distraction-Free Void Mode Floating Exit Control -->
        <div 
          v-if="store.isVoidMode" 
          class="absolute top-4 right-6 z-50 flex items-center gap-3 opacity-20 hover:opacity-100 transition-opacity"
        >
          <span class="text-xs tracking-widest uppercase font-mono text-zinc-500">Void Mode</span>
          <button 
            @click="store.toggleVoidMode()" 
            class="px-2.5 py-1 text-xs rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 font-mono border border-zinc-700/50 transition"
            title="Exit Void Mode (Esc)"
          >
            Esc ✕
          </button>
        </div>

        <!-- 4 Center Viewport Perspectives -->
        <Scriptorium v-if="store.viewMode === 'editor'" />
        <OutlineView v-else-if="store.viewMode === 'outline'" />
        <CorkboardView v-else-if="store.viewMode === 'corkboard'" />
        <Cosmograph v-else-if="store.viewMode === 'cosmograph' || store.viewMode === '3d'" />
      </main>

      <!-- Contextual Analytical Inspector Sidebar -->
      <Inspector 
        v-if="!store.isVoidMode && !store.inspectorCollapsed" 
        class="w-84 flex-shrink-0 transition-all duration-300" 
      />
    </div>

    <!-- Global Toast Notifications Overlay -->
    <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none max-w-sm">
      <TransitionGroup name="toast">
        <div 
          v-for="toast in toasts" 
          :key="toast.id" 
          class="pointer-events-auto px-4 py-3 rounded-lg shadow-lg border text-xs font-mono flex items-center justify-between gap-3 backdrop-blur-md"
          :class="[
            toast.type === 'error' 
              ? 'bg-rose-950/90 text-rose-200 border-rose-800/80' 
              : toast.type === 'success' 
                ? 'bg-emerald-950/90 text-emerald-200 border-emerald-800/80' 
                : 'bg-zinc-900/90 text-zinc-200 border-zinc-700/80'
          ]"
        >
          <span class="break-words leading-relaxed">{{ toast.msg }}</span>
          <button 
            @click="dismissToast(toast.id)" 
            class="text-zinc-400 hover:text-zinc-100 font-bold ml-2 transition"
          >
            ✕
          </button>
        </div>
      </TransitionGroup>
    </div>

    <!-- Modals Layer -->
    <OmnibarModal v-if="store.modals.omnibar" />
    <CastModal v-if="store.modals.cast" />
    <LoreModal v-if="store.modals.lore" />
    <VaultModal v-if="store.modals.vault" />
    <CareerModal v-if="store.modals.career" />
    <ConnectModal v-if="store.modals.connect" />
    <ImportModal v-if="store.modals.import" />

  </div>
</template>

<script setup>
import { onMounted, onUnmounted, defineAsyncComponent, watch } from 'vue'
import { store, toasts } from './store.js'

import TopNav from './components/TopNav.vue'
import Binder from './components/Binder.vue'
import Scriptorium from './components/Scriptorium.vue'
import OutlineView from './components/OutlineView.vue'
import CorkboardView from './components/CorkboardView.vue'
import Cosmograph from './components/Cosmograph.vue'
import Inspector from './components/Inspector.vue'

// Lazy-loaded Modals
const OmnibarModal = defineAsyncComponent(() => import('./components/Modals/OmnibarModal.vue'))
const CastModal = defineAsyncComponent(() => import('./components/Modals/CastModal.vue'))
const LoreModal = defineAsyncComponent(() => import('./components/Modals/LoreModal.vue'))
const VaultModal = defineAsyncComponent(() => import('./components/Modals/VaultModal.vue'))
const CareerModal = defineAsyncComponent(() => import('./components/Modals/CareerModal.vue'))
const ConnectModal = defineAsyncComponent(() => import('./components/Modals/ConnectModal.vue'))
const ImportModal = defineAsyncComponent(() => import('./components/Modals/ImportModal.vue'))

const dismissToast = (id) => {
  const index = toasts.findIndex(t => t.id === id)
  if (index > -1) toasts.splice(index, 1)
}

// Keep body tag in sync for custom candlelight CSS
watch(() => store.isCandlelight, (val) => {
  document.body.classList.toggle('candlelight-mode', val)
})

// Global Hotkey Orchestrator
const handleKeydown = (e) => {
  const isMeta = e.metaKey || e.ctrlKey

  // Cmd/Ctrl + K -> Omnibar
  if (isMeta && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    store.toggleModal('omnibar')
    return
  }

  // Cmd/Ctrl + \ -> Toggle Void Mode
  if (isMeta && e.key === '\\') {
    e.preventDefault()
    store.toggleVoidMode()
    return
  }

  // Cmd/Ctrl + J -> Toggle Craft X-Ray
  if (isMeta && e.key.toLowerCase() === 'j') {
    e.preventDefault()
    store.toggleXRay()
    return
  }

  // Escape key: closes open modal first, otherwise exits Void mode
  if (e.key === 'Escape') {
    const openModalKey = Object.keys(store.modals).find(key => store.modals[key])
    if (openModalKey) {
      store.toggleModal(openModalKey, false)
      return
    }
    if (store.isVoidMode) {
      store.isVoidMode = false
      return
    }
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  
  // Hydrate core trees and registries from backend
  await store.fetchTree()
  store.fetchCast()
  store.fetchLore()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style>
/* Custom Global Transitions for Toast System */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.96);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}

/* Custom Minimalist Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #27272a;
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #3f3f46;
}

/* Circadian Candlelight Theme Rules */
body.candlelight-mode {
  background-color: #0c0a09 !important;
  color: #fef3c7 !important;
}
body.candlelight-mode .custom-scrollbar::-webkit-scrollbar-thumb {
  background: #443224;
}
</style>