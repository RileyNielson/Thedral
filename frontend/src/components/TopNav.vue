<template>
  <header 
    v-show="!store.isVoidMode" 
    class="h-12 border-b backdrop-blur flex items-center justify-between px-3 md:px-4 z-30 shrink-0 transition-colors select-none"
    :class="store.isCandlelight ? 'border-amber-900/40 bg-[#120f0c]/90' : 'border-zinc-800/80 bg-zinc-900/70'"
  >
    <!-- Left: Branding & Dynamic Breadcrumbs -->
    <div class="flex items-center space-x-2 md:space-x-3">
      <button 
        @click="store.modals.mobileBinder = !store.modals.mobileBinder" 
        class="md:hidden text-zinc-400 hover:text-white p-1"
      >
        <MenuIcon class="w-5 h-5" />
      </button>

      <div class="flex items-center gap-1.5 cursor-pointer" @click="store.viewMode = 'editor'">
        <span class="font-bold text-amber-500 tracking-wider text-xs md:text-sm uppercase flex items-center gap-1.5">
          <Feather class="w-4 h-4" /> <span class="hidden sm:inline">Thedral</span>
        </span>
        <span class="text-[9px] font-mono bg-amber-500/10 text-amber-400/80 px-1 py-0.5 rounded border border-amber-500/20 hidden sm:inline">
          Creare Core
        </span>
      </div>

      <span class="hidden md:inline text-zinc-700">|</span>

      <div v-if="store.recentSceneIds.length" class="relative">
        <button @click="recentOpen = !recentOpen" class="hidden sm:flex items-center gap-1 rounded px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition" aria-label="Open recent scenes">
          <Clock3 class="w-3 h-3" /> Continue
        </button>
        <div v-if="recentOpen" class="absolute left-0 top-full mt-2 w-56 rounded-xl border border-zinc-700/70 bg-zinc-950/95 p-2 shadow-2xl z-50">
          <div class="px-2 pb-1 text-[9px] uppercase tracking-wider text-zinc-500">Recent scenes</div>
          <button v-for="scene in recentScenes" :key="scene.id" @click="openRecentScene(scene.id)" class="w-full rounded-lg px-2 py-1.5 text-left hover:bg-zinc-800 transition">
            <span class="block truncate text-xs text-zinc-200">{{ scene.title }}</span>
            <span class="block truncate text-[9px] text-zinc-500">{{ store.findBookForNode(scene.id)?.title || 'Manuscript' }}</span>
          </button>
          <p v-if="!recentScenes.length" class="px-2 py-2 text-[10px] text-zinc-500">No recent scenes in active manuscripts.</p>
        </div>
      </div>

      <!-- Hierarchy Breadcrumb -->
      <div class="hidden md:flex items-center text-xs text-zinc-400 font-mono gap-1.5">
        <span class="text-zinc-500">{{ store.activeNode?.book_title || "Manuscript" }}</span>
        <span class="text-zinc-700">❯</span>
        <span class="text-zinc-500">{{ store.activeNode?.chapter_title || "Chapter" }}</span>
        <span class="text-zinc-700">❯</span>
        <span class="text-amber-400/90 font-medium truncate max-w-[200px]">
          {{ store.activeNode?.title || "No Scene Selected" }}
        </span>
      </div>
    </div>

    <!-- Center: View Mode Switcher -->
    <div class="hidden lg:flex items-center bg-zinc-950 p-1 rounded-lg border border-zinc-800 text-xs shrink-0 font-mono">
      <button 
        @click="store.viewMode = 'editor'" 
        :class="[
          'px-2.5 py-1 rounded-md font-medium transition flex items-center gap-1.5', 
          store.viewMode === 'editor' ? 'bg-zinc-800 text-amber-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
        ]"
      >
        <PenTool class="w-3.5 h-3.5" /> <span class="hidden md:inline">Write</span>
      </button>
      
      <button 
        @click="store.viewMode = 'outline'" 
        :class="[
          'px-2.5 py-1 rounded-md font-medium transition flex items-center gap-1.5', 
          store.viewMode === 'outline' ? 'bg-zinc-800 text-amber-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
        ]"
      >
        <ListTree class="w-3.5 h-3.5" /> <span class="hidden md:inline">Outline</span>
      </button>

      <button 
        @click="store.viewMode = 'corkboard'" 
        :class="[
          'px-2.5 py-1 rounded-md font-medium transition flex items-center gap-1.5', 
          store.viewMode === 'corkboard' ? 'bg-zinc-800 text-amber-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
        ]"
      >
        <LayoutGrid class="w-3.5 h-3.5" /> <span class="hidden md:inline">Board</span>
      </button>

      <button 
        @click="store.viewMode = 'cosmograph'" 
        :class="[
          'px-2.5 py-1 rounded-md font-semibold transition flex items-center gap-1.5', 
          (store.viewMode === 'cosmograph' || store.viewMode === '3d') ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 shadow-sm' : 'text-zinc-400 hover:text-amber-300'
        ]"
      >
        <Globe class="w-3.5 h-3.5 text-amber-500" /> <span>Cosmograph</span>
      </button>
    </div>

    <!-- Right: Studio Registry & Export Actions -->
    <div class="flex items-center space-x-1.5 md:space-x-2 text-xs">
      <span v-if="store.saveStatus" class="text-zinc-400 text-[11px] font-mono hidden xl:inline">
        ● {{ store.saveStatus }}
      </span>

      <div class="relative">
        <button
          @click="themeMenuOpen = !themeMenuOpen"
          :class="[
            'px-2 py-1 rounded flex items-center gap-1 transition text-xs border',
            store.colorScheme === 'candlelight' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-[0_0_8px_rgba(245,158,11,0.2)]' : 'bg-zinc-800/80 border-zinc-700/50 text-zinc-400 hover:text-white'
          ]"
          title="Choose Color Scheme"
        >
          <Palette class="w-3.5 h-3.5 text-amber-500" />
          <span class="hidden sm:inline">Theme</span>
        </button>

        <div v-if="themeMenuOpen" class="absolute right-0 top-full mt-2 w-40 rounded-xl border border-zinc-700/70 bg-zinc-950/95 p-2 shadow-2xl backdrop-blur-md z-50">
          <div class="text-[10px] uppercase tracking-[0.2em] text-zinc-500 mb-2 px-1">Palette</div>
          <button v-for="option in themeOptions" :key="option.id" @click="applyTheme(option.id)" class="w-full flex items-center justify-between rounded-lg px-2 py-1.5 text-xs text-left transition" :class="store.colorScheme === option.id ? 'bg-zinc-800 text-amber-300' : 'text-zinc-300 hover:bg-zinc-800/80'">
            <span>{{ option.label }}</span>
            <span class="inline-block w-2.5 h-2.5 rounded-full border border-white/20" :style="{ background: option.color }"></span>
          </button>
        </div>
      </div>

      <button 
        @click="store.toggleModal('lore', true)" 
        class="px-2 py-1 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700/50 flex items-center gap-1.5 transition text-xs font-medium" 
        title="Living Lexicon & World Rules"
      >
        <BookOpenCheck class="w-3.5 h-3.5 text-amber-500" /> 
        <span class="hidden sm:inline">Lore</span>
      </button>

      <button 
        @click="store.toggleModal('cast', true)" 
        class="px-2 py-1 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700/50 flex items-center gap-1.5 transition text-xs font-medium" 
        title="Cast & Relics Directory"
      >
        <Users class="w-3.5 h-3.5 text-amber-500" /> 
        <span class="hidden sm:inline">Cast</span>
      </button>

      <button 
        @click="store.toggleModal('career', true)" 
        class="px-2 py-1 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700/50 flex items-center gap-1.5 transition text-xs font-medium"
      >
        <Award class="w-3.5 h-3.5 text-amber-500" /> 
        <span class="hidden sm:inline">Publish</span>
      </button>

      <button
        @click="store.toggleModal('review', true)"
        class="px-2 py-1 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700/50 flex items-center gap-1.5 transition text-xs font-medium"
        title="Manuscript-wide revision and continuity checks"
      >
        <ClipboardCheck class="w-3.5 h-3.5 text-amber-500" />
        <span class="hidden sm:inline">Review</span>
      </button>

      <button 
        @click="store.toggleModal('import', true)" 
        class="px-2 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded flex items-center gap-1 transition font-medium text-xs"
      >
        <Upload class="w-3.5 h-3.5" /> 
        <span class="hidden sm:inline">Import</span>
      </button>

      <button 
        @click="store.toggleModal('connect', true)" 
        class="px-2 py-1 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700/50 flex items-center gap-1 transition text-xs"
      >
        <Smartphone class="w-3.5 h-3.5" /> 
        <span class="hidden lg:inline">Phone</span>
      </button>

      <button
        @click="store.toggleModal('export', true)"
        class="px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-zinc-950 font-bold rounded flex items-center gap-1.5 transition text-xs shadow"
      >
        <Download class="w-3.5 h-3.5" /> 
        <span class="hidden sm:inline">Export</span>
      </button>

      <button 
        @click="store.modals.mobileInspector = !store.modals.mobileInspector" 
        class="md:hidden text-zinc-400 hover:text-white p-1"
      >
        <Sliders class="w-5 h-5" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store } from '../store.js'
import { 
  Menu as MenuIcon, Feather, PenTool, ListTree, LayoutGrid, Globe, Palette,
  BookOpenCheck, Users, Award, Upload, Smartphone, Download, Sliders, Clock3, ClipboardCheck
} from 'lucide-vue-next'

const themeMenuOpen = ref(false)
const recentOpen = ref(false)
const recentScenes = computed(() => store.getRecentScenes())
const themeOptions = [
  { id: 'midnight', label: 'Midnight', color: '#5b5bd6' },
  { id: 'candlelight', label: 'Candlelight', color: '#f59e0b' },
  { id: 'forest', label: 'Forest', color: '#22c55e' },
  { id: 'violet', label: 'Violet', color: '#a78bfa' }
]

const applyTheme = (themeId) => {
  store.setColorScheme(themeId)
  themeMenuOpen.value = false
}

const openRecentScene = async (sceneId) => {
  if (await store.loadScene(sceneId)) {
    store.viewMode = 'editor'
    recentOpen.value = false
  }
}
</script>