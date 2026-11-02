<template>
  <div v-if="store.activeInspectorTab === 'blueprint' || store.activeInspectorTab === 'card'" class="space-y-4 select-none">
    
    <!-- 4 Grounding Fields -->
    <div class="grid grid-cols-2 gap-2 font-mono">
      <div>
        <label class="text-[9px] font-bold text-amber-400 uppercase tracking-wider block mb-1">POV Character</label>
        <input 
          v-model="cardData.pov_character" 
          @blur="forceSave" 
          placeholder="e.g. Ellie" 
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none"
        />
      </div>

      <div>
        <label class="text-[9px] font-bold text-amber-400 uppercase tracking-wider block mb-1">Setting / Corridor</label>
        <input 
          v-model="cardData.setting" 
          @blur="forceSave" 
          placeholder="e.g. Lower Bailey" 
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none"
        />
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2 font-mono">
      <div>
        <label class="text-[9px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">Story Day / Time</label>
        <input 
          v-model="cardData.narrative_time" 
          @blur="forceSave" 
          placeholder="e.g. Day 1, Morning" 
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-cyan-500/50 focus:outline-none"
        />
      </div>

      <div>
        <label class="text-[9px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">Tension Target: {{ cardData.tension_target || 50 }}%</label>
        <input 
          type="range"
          min="0"
          max="100"
          v-model.number="cardData.tension_target" 
          @change="forceSave" 
          class="w-full accent-amber-500 mt-2 cursor-pointer"
        />
      </div>
    </div>

    <div>
      <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Scene Goal / Objective</label>
      <textarea
        v-model="cardData.scene_goal"
        @blur="forceSave"
        rows="2"
        class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition leading-relaxed font-serif resize-none"
        placeholder="What irreversible shift must this beat accomplish?"
      ></textarea>
    </div>

    <div class="grid grid-cols-2 gap-2 font-mono">
      <div>
        <label class="text-[9px] font-bold text-cyan-400 uppercase tracking-wider block mb-1">Scene Word Target</label>
        <input
          v-model.number="cardData.word_target"
          @blur="forceSave"
          min="0"
          type="number"
          placeholder="500"
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-cyan-500/50 focus:outline-none"
        />
      </div>

      <div>
        <label class="text-[9px] font-bold text-amber-400 uppercase tracking-wider block mb-1">Daily Goal</label>
        <input
          v-model.number="cardData.daily_goal"
          @blur="forceSave"
          min="0"
          type="number"
          placeholder="1200"
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none"
        />
      </div>
    </div>

    <div>
      <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Beat Synopsis</label>
      <textarea 
        v-model="store.activeNode.synopsis" 
        @blur="forceSave" 
        rows="3" 
        class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition leading-relaxed font-serif resize-none" 
        placeholder="Summary of dramatic beats..."
      ></textarea>
    </div>

    <!-- Chapter Dashboard -->
    <div class="pt-3 border-t border-zinc-800 space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Chapter Pace</span>
        <span class="text-[9px] text-amber-300 font-mono">{{ chapterSummary.progress }}%</span>
      </div>

      <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
        <div class="flex items-center justify-between text-[10px] font-mono text-zinc-400">
          <span>{{ chapterSummary.label }}</span>
          <span>{{ chapterSummary.totalWords }} / {{ chapterSummary.target }}w</span>
        </div>
        <div class="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
          <div class="h-full rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 transition-all" :style="{ width: `${chapterSummary.progress}%` }"></div>
        </div>
      </div>
    </div>

    <!-- Revision Vault -->
    <div class="pt-3 border-t border-zinc-800">
      <div class="flex items-center justify-between mb-2">
        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Revision Vault</span>
        <span class="text-[9px] text-zinc-600 font-mono">{{ (store.activeNode?.revisions || []).length }} saved</span>
      </div>
      <div v-if="(store.activeNode?.revisions || []).length" class="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar pr-1">
        <div v-for="rev in (store.activeNode?.revisions || []).slice(0, 5)" :key="rev.version_num" class="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-1.5">
          <div class="min-w-0">
            <span class="text-[10px] text-zinc-200 font-medium">v{{ rev.version_num }}</span>
            <span class="text-[9px] text-zinc-500 font-mono ml-2">{{ formatRevisionTime(rev.created_at) }}</span>
          </div>
          <button @click="restoreRevision(rev.version_num)" class="px-1.5 py-0.5 rounded border border-amber-500/30 bg-amber-500/10 text-[9px] text-amber-300 hover:bg-amber-500/20 transition">Restore</button>
        </div>
      </div>
      <p v-else class="text-[10px] text-zinc-500 italic">No prior snapshots yet.</p>
    </div>

  </div>
</template>

<script setup>
import { inject } from 'vue'
import { store } from '../../store.js'

const {
  cardData,
  chapterSummary,
  forceSave,
  formatRevisionTime,
  restoreRevision,
} = inject('inspectorState')
</script>
