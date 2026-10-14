<template>
  <div v-if="store.activeInspectorTab === 'card'" class="space-y-4">
    
    <!-- 4 Sovereign Grounding Fields (Snaps 3D Coordinates) -->
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
          placeholder="e.g. The Sky Docks" 
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
          placeholder="e.g. Day 3.5 or -5 yrs" 
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
        rows="3"
        class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition leading-relaxed font-serif"
        placeholder="What must this beat accomplish?"
      ></textarea>
    </div>

    <details v-if="cardData.scrivener" class="rounded-lg border border-zinc-800 bg-zinc-950">
      <summary class="cursor-pointer px-2.5 py-2 text-[10px] font-mono text-zinc-400 hover:text-zinc-200">
        Preserved Scrivener details
      </summary>
      <div class="px-2.5 pb-2.5 space-y-2">
        <div v-if="cardData.scrivener.source_path?.length" class="text-[9px] text-zinc-500 font-mono break-words">
          <span class="text-zinc-400">Source path:</span> {{ cardData.scrivener.source_path.join(' / ') }}
        </div>
        <div v-if="scrivenerMetadataFields.length" class="space-y-1.5">
          <div v-for="field in scrivenerMetadataFields" :key="field.label" class="text-[10px] leading-relaxed">
            <span class="text-zinc-500">{{ field.label }}:</span>
            <span class="text-zinc-300 ml-1 break-words">{{ field.value }}</span>
          </div>
        </div>
        <details v-if="scrivenerMetadataText !== '{}'" class="rounded border border-zinc-800/80">
          <summary class="cursor-pointer px-2 py-1.5 text-[9px] text-zinc-500 hover:text-zinc-300">View complete source metadata</summary>
          <pre class="max-h-40 overflow-auto rounded bg-zinc-900 p-2 text-[9px] leading-relaxed text-zinc-400 whitespace-pre-wrap break-words custom-scrollbar">{{ scrivenerMetadataText }}</pre>
        </details>
        <div v-for="(fileText, fileName) in (cardData.scrivener.external_files || {})" :key="fileName" class="rounded bg-zinc-900 p-2">
          <div class="text-[9px] uppercase tracking-wider text-amber-400/80 mb-1">{{ fileName }}</div>
          <p class="max-h-32 overflow-auto text-[10px] text-zinc-300 whitespace-pre-wrap break-words custom-scrollbar">{{ fileText }}</p>
        </div>
      </div>
    </details>

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

    <div class="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
      <div class="flex items-center justify-between text-[10px] font-mono">
        <span class="text-zinc-500">Writer Sprint</span>
        <span class="text-amber-300">{{ sprintProgress }}%</span>
      </div>
      <div class="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
        <div class="h-full rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 transition-all" :style="{ width: `${sprintProgress}%` }"></div>
      </div>
      <div class="flex items-center justify-between text-[9px] text-zinc-400 font-mono">
        <span>{{ store.activeNode?.word_count || 0 }} words</span>
        <span>{{ writableTarget }} target</span>
      </div>
    </div>

    <div v-if="chapterSummary?.sceneCount" class="rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-2.5 space-y-2">
      <div class="flex items-center justify-between text-[10px] font-mono text-cyan-300">
        <span>{{ chapterSummary.label }}</span>
        <span>{{ chapterSummary.progress }}%</span>
      </div>
      <div class="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
        <div class="h-full rounded-full bg-gradient-to-r from-cyan-500 via-sky-500 to-indigo-500 transition-all" :style="{ width: `${chapterSummary.progress}%` }"></div>
      </div>
      <div class="grid grid-cols-2 gap-2 text-[9px] font-mono text-zinc-300">
        <div class="rounded bg-zinc-950/70 p-1.5">
          <div class="text-zinc-500">Words</div>
          <div class="text-sm text-cyan-300 font-bold">{{ chapterSummary.totalWords }}</div>
        </div>
        <div class="rounded bg-zinc-950/70 p-1.5">
          <div class="text-zinc-500">Target</div>
          <div class="text-sm text-cyan-300 font-bold">{{ chapterSummary.target }}</div>
        </div>
        <div class="rounded bg-zinc-950/70 p-1.5">
          <div class="text-zinc-500">Scenes</div>
          <div class="text-sm text-cyan-300 font-bold">{{ chapterSummary.completedScenes }}/{{ chapterSummary.sceneCount }}</div>
        </div>
        <div class="rounded bg-zinc-950/70 p-1.5">
          <div class="text-zinc-500">Avg</div>
          <div class="text-sm text-cyan-300 font-bold">{{ chapterSummary.avgSceneWords }}</div>
        </div>
      </div>
      <div v-if="chapterSummary.sceneBreakdown.length" class="space-y-1">
        <div v-for="scene in chapterSummary.sceneBreakdown" :key="scene.id" class="flex items-center justify-between text-[9px] font-mono text-zinc-300">
          <span class="truncate pr-2">{{ scene.title }}</span>
          <span>{{ scene.words }}/{{ scene.target }}</span>
        </div>
      </div>
    </div>

    <div>
      <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Scene Beat Synopsis</label>
      <textarea 
        v-model="store.activeNode.synopsis" 
        @blur="forceSave" 
        rows="4" 
        class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-200 text-xs focus:border-amber-500/50 focus:outline-none transition leading-relaxed font-serif" 
        placeholder="What irreversible dramatic shift occurs in this beat?"
      ></textarea>
    </div>

    <div>
      <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Chapter Epigraph / Lore Quote</label>
      <textarea 
        v-model="store.activeNode.epigraph" 
        @blur="forceSave" 
        rows="2" 
        class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-300 text-xs italic font-serif focus:border-amber-500/50 focus:outline-none transition" 
        placeholder='"Quote from historical archive..."'
      ></textarea>
    </div>

    <div>
      <label class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider block mb-1">Drafting Status</label>
      <select 
        v-model="store.activeNode.status" 
        @change="forceSave" 
        class="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-zinc-300 text-xs focus:outline-none"
      >
        <option value="DRAFT">Draft</option>
        <option value="REVISED">Revised</option>
        <option value="FINAL">Final</option>
      </select>
    </div>

    <div class="pt-3 border-t border-zinc-800 text-zinc-500 space-y-2 text-[11px] font-mono">
      <div class="flex justify-between">
        <span>Scene Words:</span> 
        <span class="text-zinc-200 font-medium">{{ store.activeNode?.word_count || 0 }}</span>
      </div>
      <div class="flex justify-between">
        <span>Node ID:</span> 
        <span class="text-zinc-500 truncate max-w-[150px]">{{ store.activeNode?.id }}</span>
      </div>
    </div>

    <div class="pt-3 border-t border-zinc-800">
      <div class="flex items-center justify-between mb-2">
        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Chapter Dashboard</span>
        <span class="text-[9px] text-amber-300 font-mono">{{ chapterSummary.progress }}%</span>
      </div>

      <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
        <div class="flex items-center justify-between text-[10px] font-mono text-zinc-400">
          <span>{{ chapterSummary.label }}</span>
          <span>{{ chapterSummary.totalWords }} / {{ chapterSummary.target }}</span>
        </div>
        <div class="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
          <div class="h-full rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 transition-all" :style="{ width: `${chapterSummary.progress}%` }"></div>
        </div>
        <div class="grid grid-cols-2 gap-2 text-[9px] font-mono text-zinc-400">
          <div class="rounded bg-zinc-900/80 p-2">
            <div class="text-zinc-500">Scenes</div>
            <div class="mt-1 text-zinc-200 text-[11px]">{{ chapterSummary.sceneCount }}</div>
          </div>
          <div class="rounded bg-zinc-900/80 p-2">
            <div class="text-zinc-500">Avg scene</div>
            <div class="mt-1 text-zinc-200 text-[11px]">{{ chapterSummary.avgSceneWords }}w</div>
          </div>
          <div class="rounded bg-zinc-900/80 p-2">
            <div class="text-zinc-500">Completed</div>
            <div class="mt-1 text-zinc-200 text-[11px]">{{ chapterSummary.completedScenes }}</div>
          </div>
          <div class="rounded bg-zinc-900/80 p-2">
            <div class="text-zinc-500">Remaining</div>
            <div class="mt-1 text-zinc-200 text-[11px]">{{ chapterSummary.remainingWords }}w</div>
          </div>
        </div>
      </div>

      <div v-if="chapterSummary.sceneBreakdown.length" class="mt-3 space-y-2">
        <div class="text-[9px] uppercase tracking-wider font-mono text-zinc-500">Scene pace</div>
        <div v-for="beat in chapterSummary.sceneBreakdown" :key="beat.id" class="rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-1.5">
          <div class="flex items-center justify-between text-[9px] text-zinc-400 font-mono">
            <span class="truncate pr-2">{{ beat.title }}</span>
            <span>{{ beat.words }}w</span>
          </div>
          <div class="mt-1 h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
            <div class="h-full rounded-full bg-amber-500/80" :style="{ width: `${Math.min(100, (beat.words / Math.max(beat.target, 1)) * 100)}%` }"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="pt-3 border-t border-zinc-800">
      <div class="flex items-center justify-between mb-2">
        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono">Revision History</span>
        <span class="text-[9px] text-zinc-600 font-mono">{{ (store.activeNode?.revisions || []).length }} saved</span>
      </div>
      <div v-if="(store.activeNode?.revisions || []).length" class="space-y-2">
        <div v-for="rev in (store.activeNode?.revisions || []).slice(0, 5)" :key="rev.version_num" class="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-1.5">
          <div class="min-w-0">
            <div class="text-[10px] text-zinc-200 font-medium">v{{ rev.version_num }}</div>
            <div class="text-[9px] text-zinc-500 font-mono truncate">{{ formatRevisionTime(rev.created_at) }}</div>
          </div>
          <div class="flex shrink-0 gap-1">
            <button @click="selectedRevisionVersion = rev.version_num" class="px-1.5 py-0.5 rounded border text-[9px] transition" :class="selectedRevisionVersion === rev.version_num ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300' : 'border-zinc-700 text-zinc-400 hover:text-zinc-200'">
              {{ selectedRevisionVersion === rev.version_num ? 'Comparing' : 'Compare' }}
            </button>
            <button @click="restoreRevision(rev.version_num)" class="px-1.5 py-0.5 rounded border border-amber-500/30 bg-amber-500/10 text-[9px] text-amber-300 hover:bg-amber-500/20 transition">Restore</button>
          </div>
        </div>

        <div v-if="revisionComparison" class="rounded-lg border border-zinc-800 bg-zinc-950 p-2 space-y-2">
          <div class="flex items-center justify-between gap-2">
            <div class="min-w-0">
              <div class="text-[10px] font-semibold text-zinc-200">Revision v{{ revisionComparison.versionNum }} vs current</div>
              <div class="text-[9px] font-mono text-zinc-500">{{ revisionComparison.removed }} removed · {{ revisionComparison.added }} added · {{ revisionComparison.wordDelta > 0 ? '+' : '' }}{{ revisionComparison.wordDelta }} words</div>
            </div>
            <button @click="selectedRevisionVersion = null" class="text-[9px] text-zinc-500 hover:text-zinc-200">Close</button>
          </div>
          <p v-if="revisionComparison.isLimited" class="text-[9px] text-amber-300/80">This is a large revision; the comparison shows full versions as removed and added.</p>
          <div class="max-h-64 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
            <div v-for="(part, index) in revisionComparison.parts" :key="`${index}-${part.kind}`" class="rounded px-2 py-1 text-[10px] leading-relaxed font-serif whitespace-pre-wrap break-words" :class="part.kind === 'added' ? 'bg-emerald-950/50 text-emerald-200 border-l-2 border-emerald-500' : part.kind === 'removed' ? 'bg-rose-950/40 text-rose-200 border-l-2 border-rose-500' : 'text-zinc-400'">
              <span v-if="part.kind === 'added'" class="mr-1 font-mono text-emerald-500">+</span>
              <span v-else-if="part.kind === 'removed'" class="mr-1 font-mono text-rose-500">−</span>
              {{ part.text || '(empty paragraph)' }}
            </div>
            <p v-if="!revisionComparison.parts.length" class="text-[10px] text-zinc-500">No content changes since this revision.</p>
          </div>
        </div>
      </div>
      <p v-else class="text-[10px] text-zinc-500">No prior revisions yet.</p>
    </div>
    <InspectorPromisesPanel />
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'
import InspectorPromisesPanel from './InspectorPromisesPanel.vue'

const {
  cardData,
  chapterSummary,
  forceSave,
  formatRevisionTime,
  restoreRevision,
  revisionComparison,
  scrivenerMetadataFields,
  scrivenerMetadataText,
  selectedRevisionVersion,
  sprintProgress,
  writableTarget
} = inject('inspectorState')
</script>
