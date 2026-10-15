<template>
  <div v-if="store.activeInspectorTab === 'socratic'" class="space-y-4 flex flex-col h-full">
    <template v-if="store.aiEnabled">
    <div v-if="store.socraticCritique" class="space-y-2">
      <div class="text-[9px] font-mono uppercase tracking-wider" :class="store.socraticAi ? 'text-amber-400' : 'text-zinc-500'">
        {{ store.socraticAi ? 'AI-generated mirror, grounded in text observations computed without AI' : 'No AI involved' }}
      </div>
      <div class="p-3.5 bg-zinc-950 rounded-xl border border-amber-500/30 text-zinc-200 leading-relaxed whitespace-pre-line text-xs font-serif shadow-lg">
        {{ store.socraticCritique }}
      </div>
      <div class="flex items-center justify-between text-xs pt-1">
        <span class="text-[10px] text-zinc-500 font-mono">Logged to Bookcase</span>
        <div class="flex space-x-1.5">
          <button 
            @click="resolveCritique('ADDRESSED')" 
            class="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded text-[11px] font-medium transition"
          >
            ✓ Addressed
          </button>
          <button 
            @click="resolveCritique('DISMISSED')" 
            class="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded text-[11px] transition"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-6 border border-dashed border-zinc-800/80 rounded-xl p-4 text-zinc-500">
      <Sparkles class="w-5 h-5 mx-auto mb-2 text-amber-500/50" />
      <p class="text-[11px] mb-3">Highlight text in the editor to run a <b>Line-Critique</b>.</p>
      <div class="border-t border-zinc-800/80 my-3"></div>
      <button 
        @click="elevateMacroScene" 
        class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-amber-400 font-medium rounded-lg text-[10px] uppercase tracking-wider transition w-full"
      >
        Diagnose Entire Scene
      </button>
    </div>

    <div class="pt-4 border-t border-zinc-800">
      <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-2">Ask The Socratic Companion</label>
      <div class="flex gap-2">
        <input 
          v-model="tutorQuestion" 
          @keyup.enter="askTutor" 
          placeholder="e.g. How do I build dread here?" 
          class="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:border-amber-500/50 focus:outline-none transition" 
        />
        <button 
          @click="askTutor" 
          :disabled="isTutorThinking" 
          class="px-2.5 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-xs transition"
        >
          <Loader v-if="isTutorThinking" class="w-3.5 h-3.5 animate-spin" />
          <Send v-else class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
    
    </template>

    <InspectorLoreLinks />

    <div v-if="store.aiEnabled" class="pt-3 border-t border-zinc-800 space-y-2 flex-1 overflow-y-auto">
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Editorial Log</span>
        <span class="text-[10px] text-zinc-600 font-mono">{{ store.sceneCritiques?.length || 0 }} total</span>
      </div>
      <div class="space-y-2 pr-1">
        <div 
          v-for="cr in store.sceneCritiques" 
          :key="cr.id" 
          class="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800/80 text-[11px] space-y-1.5"
        >
          <div class="flex items-center justify-between">
            <span 
              :class="[
                'px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase', 
                cr.status === 'ADDRESSED' 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : (cr.status === 'OPEN' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-zinc-800 text-zinc-500')
              ]"
            >
              {{ cr.status }}
            </span>
            <span class="text-[10px] text-zinc-600 font-mono">{{ (cr.created_at || '').split(' ')[0] }}</span>
          </div>
          <div class="text-zinc-400 italic line-clamp-1 font-serif">"{{ cr.passage_text }}"</div>
          <div class="text-zinc-300 line-clamp-3 font-serif leading-snug">{{ cr.critique_text }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import InspectorLoreLinks from './InspectorLoreLinks.vue'
import { inject } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'
import { Sparkles, Loader, Send } from '@lucide/vue'

const {
  askTutor,
  elevateMacroScene,
  isTutorThinking,
  resolveCritique,
  tutorQuestion
} = inject('inspectorState')
</script>
