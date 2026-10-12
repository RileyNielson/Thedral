<template>
  <div 
    class="flex flex-col h-screen w-screen overflow-hidden select-none font-sans transition-colors duration-500"
    :class="[
      store.colorScheme === 'candlelight'
        ? 'bg-[#0c0a09] text-amber-100/90 selection:bg-amber-900/50' 
        : store.colorScheme === 'forest'
          ? 'bg-[#07140e] text-emerald-50 selection:bg-emerald-900/50'
          : store.colorScheme === 'violet'
            ? 'bg-[#140d1e] text-violet-50 selection:bg-violet-900/50'
            : 'bg-zinc-950 text-zinc-100 selection:bg-indigo-900/50'
    ]"
  >
    <!-- Top Global Command & Navigation Bar -->
    <TopNav v-if="!store.isVoidMode" />

    <div
      v-if="store.runtimeStatus && !store.isVoidMode"
      class="flex-shrink-0 border-b px-4 py-1.5 text-center text-[10px]"
      :class="store.runtimeStatus.mode === 'LITE'
        ? 'border-amber-900/40 bg-amber-950/30 text-amber-200/80'
        : 'border-emerald-900/40 bg-emerald-950/20 text-emerald-200/70'"
      role="status"
    >
      <template v-if="store.runtimeStatus.mode === 'LITE'">
        Lite mode is active. Writing, organization, and text analysis work locally; AI-assisted features are unavailable.
      </template>
      <template v-else>
        Full mode is active. Local AI features use {{ store.runtimeStatus.model }} and require Ollama to be running.
      </template>
    </div>

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
        <!-- Void Mode Floating Exit Control -->
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

    <!-- ALL 7 MODALS MOUNTED -->
    <OmnibarModal v-if="store.modals.omnibar" />
    <CastModal v-if="store.modals.cast" />
    <LoreModal v-if="store.modals.lore" />
    <VaultModal v-if="store.modals.vault" />
    <CareerModal v-if="store.modals.career" />
    <ConnectModal v-if="store.modals.connect" />
    <ImportModal v-if="store.modals.import" />
    <ExportModal v-if="store.modals.export" />
    <ReviewModal v-if="store.modals.review" />
    <SubmissionModal v-if="store.modals.submission" />

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
const ExportModal = defineAsyncComponent(() => import('./components/Modals/ExportModal.vue'))
const ReviewModal = defineAsyncComponent(() => import('./components/Modals/ReviewModal.vue'))
const SubmissionModal = defineAsyncComponent(() => import('./components/Modals/SubmissionModal.vue'))

const dismissToast = (id) => {
  const index = toasts.findIndex(t => t.id === id)
  if (index > -1) toasts.splice(index, 1)
}

watch(() => store.colorScheme, (theme) => {
  document.body.dataset.theme = theme
  document.body.classList.toggle('candlelight-mode', theme === 'candlelight')
  document.body.classList.toggle('forest-mode', theme === 'forest')
  document.body.classList.toggle('violet-mode', theme === 'violet')
})

const handleKeydown = (e) => {
  const isMeta = e.metaKey || e.ctrlKey

  if (isMeta && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    store.toggleModal('omnibar')
    return
  }

  if (isMeta && e.key === '\\') {
    e.preventDefault()
    store.toggleVoidMode()
    return
  }

  if (isMeta && e.key.toLowerCase() === 'j') {
    e.preventDefault()
    store.toggleXRay()
    return
  }

  if (isMeta && e.key.toLowerCase() === 's') {
    e.preventDefault()
    store.flushPendingSave?.()
    return
  }

  if (isMeta && e.altKey && e.key === 'ArrowLeft') {
    e.preventDefault()
    store.navigateScene(-1)
    return
  }

  if (isMeta && e.altKey && e.key === 'ArrowRight') {
    e.preventDefault()
    store.navigateScene(1)
    return
  }

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
  document.body.dataset.theme = store.colorScheme
  document.body.classList.toggle('candlelight-mode', store.colorScheme === 'candlelight')
  document.body.classList.toggle('forest-mode', store.colorScheme === 'forest')
  document.body.classList.toggle('violet-mode', store.colorScheme === 'violet')
  window.addEventListener('keydown', handleKeydown)
  store.fetchRuntimeStatus()
  await store.fetchTree()
  store.fetchCast()
  store.fetchLore()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style>
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

body[data-theme='midnight'] {
  background-color: #09090f !important;
  color: #e2e8f0 !important;
}

body.candlelight-mode {
  background-color: #0c0a09 !important;
  color: #fef3c7 !important;
}

body.forest-mode {
  background-color: #07140e !important;
  color: #dcfce7 !important;
}

body.violet-mode {
  background-color: #140d1e !important;
  color: #f3e8ff !important;
}

body.candlelight-mode .custom-scrollbar::-webkit-scrollbar-thumb,
body.forest-mode .custom-scrollbar::-webkit-scrollbar-thumb,
body.violet-mode .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.6);
}
</style>