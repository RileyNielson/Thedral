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
      
      <!-- TAB 1: PERSISTENT SOVEREIGN SCENE CARD -->
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
      </div>

      <!-- TAB 2: TEXTUAL SIGNALS -->
      <div v-if="store.activeInspectorTab === 'telemetry'" class="space-y-4">
        <header class="flex items-start justify-between gap-2">
          <div class="space-y-1">
            <h2 class="text-[11px] font-semibold text-zinc-200">Scene patterns in manuscript context</h2>
            <p class="text-[9px] leading-relaxed text-zinc-500">These are measurable text features, not reader reactions. Comparisons use other scenes in this manuscript, so a difference is descriptive—not a quality judgment.</p>
          </div>
          <button @click="loadManuscriptAnalytics" :disabled="analyticsLoading" class="shrink-0 rounded border border-zinc-700 px-2 py-1 text-[9px] text-zinc-400 hover:text-zinc-200 disabled:opacity-50">
            {{ analyticsLoading ? 'Updating…' : 'Refresh' }}
          </button>
        </header>

        <div v-if="analyticsLoading" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-[10px] text-zinc-500">
          Comparing this scene with the manuscript…
        </div>
        <div v-else-if="analyticsError" class="rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 text-[10px] text-rose-200">
          {{ analyticsError }}
        </div>
        <template v-else-if="selectedSceneAnalytics">
          <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-2">
            <div class="flex items-baseline justify-between gap-2">
              <span class="text-[10px] uppercase tracking-wider text-amber-400">Estimated silent read</span>
              <span class="font-mono text-sm font-semibold text-zinc-100">{{ readTimeRange }}</span>
            </div>
            <p class="text-[9px] text-zinc-500">
              {{ selectedSceneAnalytics.telemetry.words.toLocaleString() }} words · estimated at 200–250 words/minute · scene {{ analyticsPosition }} of {{ manuscriptAnalytics.scenes.length }}
            </p>
            <p class="text-[9px] text-zinc-500">{{ sceneLengthComparison }}</p>
          </div>

          <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-3">
            <div class="text-[10px] uppercase tracking-wider text-amber-400">How this scene is written</div>
            <div v-for="metric in manuscriptPatternComparisons" :key="metric.label" class="space-y-1">
              <div class="flex items-baseline justify-between gap-2 text-[10px]">
                <span class="text-zinc-300">{{ metric.label }}</span>
                <span class="font-mono text-zinc-100">{{ metric.value }}</span>
              </div>
              <p class="text-[9px] text-zinc-500">{{ metric.context }}</p>
            </div>
          </div>

          <div class="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-2">
            <div class="text-[10px] uppercase tracking-wider text-zinc-400">Nearby scene lengths</div>
            <div v-if="previousSceneAnalytics" class="flex justify-between gap-2 text-[9px]">
              <span class="truncate text-zinc-500">Before · {{ previousSceneAnalytics.title }}</span>
              <span class="shrink-0 font-mono text-zinc-300">{{ previousSceneAnalytics.telemetry.words.toLocaleString() }} words</span>
            </div>
            <div class="flex justify-between gap-2 text-[9px]">
              <span class="truncate text-zinc-300">Selected · {{ selectedSceneAnalytics.title }}</span>
              <span class="shrink-0 font-mono text-zinc-100">{{ selectedSceneAnalytics.telemetry.words.toLocaleString() }} words</span>
            </div>
            <div v-if="nextSceneAnalytics" class="flex justify-between gap-2 text-[9px]">
              <span class="truncate text-zinc-500">After · {{ nextSceneAnalytics.title }}</span>
              <span class="shrink-0 font-mono text-zinc-300">{{ nextSceneAnalytics.telemetry.words.toLocaleString() }} words</span>
            </div>
            <p v-if="!previousSceneAnalytics && !nextSceneAnalytics" class="text-[9px] text-zinc-500">This is the only scene in the manuscript.</p>
          </div>

          <details class="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5">
            <summary class="cursor-pointer text-[10px] text-zinc-400 hover:text-zinc-200">Possible filter-word repetitions</summary>
            <p class="my-2 text-[9px] text-zinc-500">Occurrences to review—not automatic errors. Keep any wording that serves the scene.</p>
            <div v-if="Object.keys(selectedSceneAnalytics.telemetry.filters || {}).length" class="space-y-1">
              <div v-for="(count, word) in selectedSceneAnalytics.telemetry.filters" :key="word" class="flex justify-between text-[10px] font-mono">
                <span class="text-zinc-300">{{ word }}</span><span class="text-zinc-500">{{ count }}×</span>
              </div>
            </div>
            <p v-else class="text-[9px] text-zinc-600">No configured filter words found.</p>
          </details>
        </template>
        <div v-else class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-[10px] text-zinc-500">
          Select a scene within a manuscript to compare its patterns.
        </div>
        <p class="text-[9px] leading-relaxed text-zinc-600">The selected scene uses current editor text; comparison scenes use their saved drafts. Actual reader responses and the AI first-read rehearsal are in the Reader tab. Sentence and dialogue patterns cannot tell us what a reader felt or understood.</p>
      </div>

      <!-- TAB 3: SOCRATIC MIRROR & TUTOR -->
      <div v-if="store.activeInspectorTab === 'socratic'" class="space-y-4 flex flex-col h-full">
        <div v-if="store.socraticCritique" class="space-y-2">
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
        
        <div class="pt-3 border-t border-zinc-800 space-y-2 flex-1 overflow-y-auto">
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

      <!-- TAB 4: READER HORIZON -->
      <div v-if="store.activeInspectorTab === 'reader'" class="space-y-4">
        <section class="rounded-xl border border-emerald-900/50 bg-emerald-950/10 p-3 space-y-2">
          <header class="flex items-baseline justify-between gap-2">
            <h2 class="text-[10px] font-bold uppercase tracking-wider text-emerald-300">Actual reader evidence</h2>
            <span class="text-[9px] font-mono text-zinc-500">n={{ readerFeedbackSummary.responseCount }}</span>
          </header>
          <template v-if="readerFeedbackSummary.responseCount">
            <div v-for="group in readerFeedbackSummary.groups" :key="group.revision" class="space-y-1.5 border-t border-emerald-900/40 pt-2">
              <p class="text-[9px] text-zinc-400">{{ group.revision === 'CURRENT' ? 'Current draft' : `Version ${group.revision.toLowerCase()}` }} · n={{ group.entries.length }}</p>
              <p v-if="group.averages" class="text-[9px] leading-relaxed text-emerald-200">{{ group.averages }}</p>
              <blockquote v-for="entry in group.recentResponses" :key="entry.id" class="line-clamp-4 border-l border-emerald-800 pl-2 text-[10px] leading-relaxed text-zinc-300">
                “{{ entry.response }}”
                <footer class="mt-0.5 text-[9px] text-zinc-600">{{ entry.reader_label || 'Reader' }}</footer>
              </blockquote>
            </div>
            <p v-if="readerFeedbackSummary.moreGroups" class="text-[9px] text-zinc-600">More reviewed versions are listed below. Ratings are never averaged across different drafts.</p>
            <p class="text-[9px] text-zinc-600">Small, self-selected responses are useful signals—not representative audience research.</p>
          </template>
          <p v-else class="text-[9px] text-zinc-500">No beta-reader responses recorded for this scene yet. Recorded responses appear here before the AI rehearsal.</p>
        </section>

        <section class="rounded-xl border border-violet-900/50 bg-violet-950/10 p-3 space-y-2.5">
          <header class="space-y-1">
            <div class="flex items-center justify-between gap-2">
              <h2 class="text-[10px] font-bold uppercase tracking-wider text-violet-300">Story underneath · no AI</h2>
              <span v-if="readerStoryLoading" class="text-[9px] text-zinc-500">Following the threads…</span>
            </div>
            <p class="text-[9px] leading-relaxed text-zinc-500">
              {{ readerStoryAnalysis?.disclaimer || 'These are confident predictions of a typical reader’s experience, grounded in the manuscript—not a guarantee that every reader will react the same way.' }}
            </p>
            <p class="text-[9px] leading-relaxed text-zinc-500">
              No AI: ready across the manuscript after import, and refreshes from the live draft after you pause while this tab is open.
            </p>
            <p v-if="readerStoryAnalysis?.lexicon?.available" class="text-[9px] leading-relaxed text-emerald-300/80">
              Local Wiktionary word forms and synonyms are expanding the story cues.
            </p>
            <p v-else class="text-[9px] leading-relaxed text-zinc-600">
              Local Wiktionary word-form expansion is not installed yet.
            </p>
          </header>
          <p v-if="readerStoryError" class="text-[9px] text-rose-300">{{ readerStoryError }}</p>
          <template v-else-if="readerStoryAnalysis">
            <template v-for="group in readerStoryGroups" :key="group.key">
              <article v-for="(insight, index) in group.items" :key="`${group.key}-${index}`" class="rounded-lg border border-zinc-800/80 bg-zinc-950/80 p-2.5 space-y-1.5">
                <div class="flex items-baseline justify-between gap-2">
                  <h3 class="text-[10px] font-semibold text-violet-200">{{ insight.headline }}</h3>
                  <span class="shrink-0 text-[8px] text-zinc-600">{{ insight.confidence }}</span>
                </div>
                <p class="text-[10px] leading-relaxed text-zinc-300">{{ insight.reaction }}</p>
                <div v-if="insight.setup_evidence" class="space-y-0.5">
                  <p class="text-[8px] uppercase tracking-wider text-zinc-600">Earlier · {{ insight.setup_title || 'the setup' }}</p>
                  <button @click="jumpToStoryEvidence(insight.setup_scene_id, insight.setup_evidence)" class="block w-full border-l border-violet-900/70 pl-2 text-left text-[9px] italic text-zinc-400 hover:text-violet-200">“{{ insight.setup_evidence }}”</button>
                </div>
                <div v-if="insight.payoff_evidence || insight.evidence" class="space-y-0.5">
                  <p class="text-[8px] uppercase tracking-wider text-zinc-600">{{ insight.setup_evidence ? 'Here' : `Here · paragraph ${insight.paragraph}` }}</p>
                  <button @click="jumpToStoryEvidence(insight.payoff_scene_id, insight.payoff_evidence || insight.evidence)" class="block w-full border-l border-violet-900/70 pl-2 text-left text-[9px] italic text-zinc-400 hover:text-violet-200">“{{ insight.payoff_evidence || insight.evidence }}”</button>
                </div>
              </article>
            </template>
            <p v-if="!readerStoryGroups.length" class="text-[9px] leading-relaxed text-zinc-500">
              {{ readerStoryAnalysis.summary }} Try giving a question, promise, or clear reversal room on the page; this reader lens only calls out patterns it can point to.
            </p>
          </template>
        </section>

        <div class="flex items-center justify-between">
          <div>
            <span class="text-[11px] text-zinc-400 font-medium">Simulated reader pass</span>
            <p class="text-[9px] text-zinc-600">
              {{ readingMode === 'scene'
                ? 'Only this scene is supplied—no author goal or explanation.'
                : 'The AI receives the most recent preceding manuscript text (up to 3,500 characters), then this scene. No notes or author explanation.'
              }}
              This is a hypothesis, not reader feedback.
            </p>
          </div>
          <button 
            @click="scanHorizon" 
            :disabled="isScanning" 
            class="px-2 py-0.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded text-[10px] font-mono flex items-center gap-1 transition"
          >
            <Sparkles class="w-3 h-3" /> 
            <span>{{ isScanning ? 'Simulating...' : 'Simulate first read (AI)' }}</span>
          </button>
        </div>

        <label class="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 py-2 text-[9px] text-zinc-500">
          <span>Reading context</span>
          <select v-model="readingMode" :disabled="isScanning" class="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-[10px] text-zinc-200 disabled:opacity-60">
            <option value="scene">Scene alone</option>
            <option value="sequential">With preceding scenes</option>
          </select>
        </label>

        <div v-if="simulationHistory.length" class="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
          <div class="flex items-center justify-between gap-2">
            <label class="text-[9px] uppercase tracking-wider text-zinc-500" for="reader-simulation-history">Saved first-read pass</label>
            <span class="text-[9px] text-zinc-500">{{ simulationHistory.length }} distinct simulation(s)</span>
          </div>
          <select id="reader-simulation-history" v-model="selectedSimulationId" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200">
            <option v-for="(simulation, index) in simulationHistory" :key="simulation.id" :value="simulation.id">
              Pass {{ simulationHistory.length - index }} · {{ simulation.reading_mode === 'sequential' ? 'sequential' : 'scene alone' }} · {{ simulation.revision_ref }} · {{ (simulation.created_at || '').split(' ')[0] }} · {{ simulation.source_content_hash.slice(0, 10) }}
            </option>
          </select>
          <template v-if="selectedSimulation">
            <p class="text-[9px] text-zinc-500">
              {{ selectedSimulation.revision_ref === 'CURRENT' ? 'Saved scene content' : selectedSimulation.revision_ref === 'UNSAVED' ? 'Unsaved editor content' : `Saved revision ${selectedSimulation.revision_ref}` }}
              · {{ selectedSimulation.analyzed_scene_characters.toLocaleString() }} of {{ selectedSimulation.source_characters.toLocaleString() }} scene characters
              <template v-if="selectedSimulation.context_characters"> + {{ selectedSimulation.context_characters.toLocaleString() }} prior-context characters</template>
              · {{ selectedSimulation.model_name }} · {{ selectedSimulation.prompt_version }}
            </p>
            <p v-if="selectedSimulation.prompt_version === 'first-read-v4'" class="text-[9px] text-emerald-300">
              Fresh-read pass: {{ selectedSimulation.reading_mode === 'sequential'
                ? `the AI received ${selectedSimulation.context_characters.toLocaleString()} characters of preceding scene text and the current scene, without author-only context.`
                : 'the AI received only the scene excerpt, without author-only context.'
              }}
            </p>
            <p v-else-if="selectedSimulation.prompt_version === 'first-read-v3'" class="text-[9px] text-emerald-300">
              Fresh-read pass: the AI received only the scene excerpt, with no author-provided goal or explanation.
            </p>
            <p v-else-if="selectedSimulation.intended_takeaway" class="text-[9px] text-amber-300">
              This older pass included an author-provided takeaway; run a new pass for an uncued fresh read.
            </p>
            <p v-if="selectedSimulation.reused_from_id" class="text-[9px] text-cyan-300">
              The analyzed excerpt matches an earlier pass; its saved observations were reused to keep feedback stable.
            </p>
            <details class="text-[9px] text-zinc-500">
              <summary class="cursor-pointer hover:text-zinc-300">Show exact manuscript text sent to AI</summary>
              <div v-if="selectedSimulation.reading_context" class="mt-1 space-y-1">
                <p class="text-zinc-600">Preceding context window</p>
                <p class="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-zinc-900 p-2 text-zinc-400">{{ selectedSimulation.reading_context }}</p>
              </div>
              <p class="mt-1 text-zinc-600">Current scene excerpt</p>
              <p class="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-zinc-900 p-2 text-zinc-400">{{ selectedSimulation.analyzed_text }}</p>
            </details>
          </template>
        </div>

        <div v-if="!selectedSimulation" class="rounded-xl border border-dashed border-zinc-700 bg-zinc-950 p-4 text-center">
          <h3 class="text-[11px] font-semibold text-zinc-300">No saved first-read pass for this scene</h3>
          <p class="mt-1 text-[9px] leading-relaxed text-zinc-500">Run the AI rehearsal directly—no setup or author explanation is needed. Each result is saved against its exact scene text so revision comparisons stay grounded.</p>
        </div>

        <section v-if="selectedSimulation" class="rounded-xl border border-cyan-900/50 bg-cyan-950/10 p-3 space-y-3">
          <header class="space-y-1">
            <h3 class="text-[11px] font-bold uppercase tracking-wider text-cyan-300">Estimated reader experience</h3>
            <p class="text-[9px] leading-relaxed text-zinc-500">AI interpretation of likely experience, beat by beat. The 1–5 levels are rough ordinal estimates from the cited text—not measurements, predictions, or a real reader’s emotional state. Each cause explains what in the prose may create the effect.</p>
          </header>
          <div v-for="dimension in readerExperienceDimensions" :key="dimension.key" v-show="readerExperienceItems(dimension.type).length" class="space-y-1.5 border-t border-cyan-900/30 pt-2">
            <h4 class="text-[9px] font-semibold uppercase tracking-wider text-zinc-300">{{ dimension.label }}</h4>
            <article v-for="(item, index) in readerExperienceItems(dimension.type)" :key="`${item.source_excerpt}-${index}`" class="rounded-lg bg-zinc-950/80 p-2.5 space-y-1.5">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <span v-if="item.moment" class="mr-1 text-[8px] uppercase tracking-wider text-zinc-600">{{ item.moment }}</span>
                  <span class="text-[10px] font-medium text-zinc-200">{{ item.narrative_claim }}</span>
                </div>
                <span class="shrink-0 rounded border border-cyan-900/60 px-1.5 py-0.5 text-[8px] font-mono text-cyan-200">
                  {{ readerLevelLabel(item.level) }}
                </span>
              </div>
              <div class="h-1 overflow-hidden rounded bg-zinc-800" :aria-label="`AI estimated level ${item.level} of 5`">
                <div class="h-full rounded bg-cyan-500/70" :style="{ width: `${item.level * 20}%` }"></div>
              </div>
              <p class="text-[9px] leading-relaxed text-zinc-400"><span class="text-zinc-600">Possible driver:</span> {{ item.cause }}</p>
              <blockquote class="border-l border-cyan-900/70 pl-2 text-[9px] italic leading-relaxed text-zinc-500">
                <span v-if="item.evidence_source === 'prior_context'" class="not-italic text-cyan-700">Earlier scene: </span>
                “{{ item.source_excerpt }}”
              </blockquote>
            </article>
          </div>
          <p v-if="!readerExperienceDimensions.some(dimension => readerExperienceItems(dimension.type).length)" class="text-[9px] text-zinc-500">
            This pass has no structured reader-experience estimates. Run a fresh pass to generate emotional, interest, tension, mystery, suspense, connection, confusion, and attention hypotheses.
          </p>
        </section>

        <div v-if="loopSignal.active" class="rounded-lg border border-amber-700/50 bg-amber-950/20 p-3 space-y-1">
          <h3 class="text-[10px] font-bold uppercase tracking-wider text-amber-300">Possible revision loop</h3>
          <p class="text-[10px] leading-relaxed text-zinc-300">
            Similar simulated observations have recurred across {{ loopSignal.revisions_compared }} distinct analyzed excerpts. This is not a quality or progress score.
            Consider pausing, making one deliberate revision experiment—or move on and seek a human read.
          </p>
        </div>

        <div v-if="simulationComparison" class="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-1.5">
          <h3 class="text-[10px] font-bold uppercase tracking-wider text-zinc-300">Compared with {{ simulationComparison.previous.revision_ref }}</h3>
          <p class="text-[9px] text-zinc-500">Exact AI observation wording across text versions—this is not a score of revision quality or proof that the reader experience improved.</p>
          <p class="text-[10px] text-zinc-300">
            {{ simulationComparison.unchanged.length }} observation(s) repeated
            · {{ simulationComparison.newClaims.length }} newly surfaced
            · {{ simulationComparison.removedClaims.length }} no longer surfaced
          </p>
          <div v-if="simulationComparison.newClaims.length" class="text-[9px] text-emerald-300">
            Newly surfaced: {{ simulationComparison.newClaims.join(' · ') }}
          </div>
          <div v-if="simulationComparison.removedClaims.length" class="text-[9px] text-zinc-400">
            No longer surfaced: {{ simulationComparison.removedClaims.join(' · ') }}
          </div>
        </div>
        
        <details v-if="selectedSimulation" class="rounded-xl border border-zinc-800 bg-zinc-950 p-2.5 space-y-2">
          <summary class="cursor-pointer text-[10px] font-semibold text-zinc-400 hover:text-zinc-200">Other first-read observations</summary>
          <section v-for="category in otherObservationCategories" :key="category.type" class="space-y-1 border-t border-zinc-800 pt-2">
            <h4 class="text-[9px] font-semibold uppercase tracking-wider" :class="category.color">{{ category.label }}</h4>
            <article v-for="(item, index) in simulationItems(category.type)" :key="`${item.source_excerpt}-${index}`" class="text-[10px] leading-relaxed text-zinc-300">
              <p>{{ item.narrative_claim }}</p>
              <blockquote v-if="item.source_excerpt" class="border-l border-zinc-700 pl-2 text-[9px] italic text-zinc-500">
                <span v-if="item.evidence_source === 'prior_context'" class="not-italic text-cyan-700">Earlier scene: </span>
                “{{ item.source_excerpt }}”
              </blockquote>
            </article>
            <p v-if="!simulationItems(category.type).length" class="text-[9px] text-zinc-600">No grounded observations surfaced in this category.</p>
          </section>
        </details>

          <section class="p-3 bg-zinc-950 rounded-xl border border-emerald-900/50 space-y-3">
            <header>
              <h3 class="text-[11px] font-bold text-emerald-300">Actual reader feedback</h3>
              <p class="mt-1 text-[9px] text-zinc-500">Optional notes entered by you from beta-reader responses. Stored only in this app's local database; avoid entering identifying details without permission.</p>
            </header>
            <form @submit.prevent="saveReaderFeedback" class="space-y-2">
              <input v-model="feedbackForm.reader_label" maxlength="80" placeholder="Reader label (pseudonym, optional)" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200" />
              <label class="block text-[9px] text-zinc-500">Draft version reviewed
                <select v-model="feedbackForm.revision_ref" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200">
                  <option value="CURRENT">Current draft</option>
                  <option v-for="revision in store.activeNode?.revisions || []" :key="revision.version_num" :value="`V${revision.version_num}`">Saved version v{{ revision.version_num }}</option>
                </select>
              </label>
              <div class="grid grid-cols-2 gap-2">
                <label v-for="rating in feedbackRatings" :key="rating.key" class="text-[9px] text-zinc-500">{{ rating.label }}
                  <select v-model="feedbackForm[rating.key]" class="mt-1 w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200">
                    <option value="">Not rated</option><option v-for="score in [1,2,3,4,5]" :key="score" :value="String(score)">{{ score }} / 5</option>
                  </select>
                </label>
              </div>
              <textarea v-model="feedbackForm.response" rows="3" maxlength="4000" class="w-full rounded border border-zinc-700 bg-zinc-900 p-2 text-[10px] text-zinc-200" placeholder="Where were you confused? What did you expect? What moment stayed with you?" />
              <button type="submit" :disabled="!canSaveFeedback" class="rounded border border-emerald-700/60 bg-emerald-950/30 px-2.5 py-1.5 text-[10px] text-emerald-200 hover:bg-emerald-900/40 disabled:opacity-40">Save reader response</button>
            </form>
            <div v-if="readerFeedback.length" class="space-y-2 border-t border-zinc-800 pt-2">
              <div class="text-[10px] font-semibold text-zinc-300">{{ readerFeedback.length }} response(s), grouped by reviewed draft</div>
              <div v-for="group in readerFeedbackGroups" :key="group.revision" class="rounded border border-zinc-800 p-2">
                <div class="text-[9px] text-zinc-400">{{ group.revision === 'CURRENT' ? 'Current draft' : `Version ${group.revision.toLowerCase()}` }} · n={{ group.entries.length }}</div>
                <div v-if="group.averages" class="mt-1 text-[9px] text-emerald-300">{{ group.averages }}</div>
                <article v-for="entry in group.entries" :key="entry.id" class="mt-2 border-t border-zinc-800 pt-1.5 text-[10px] text-zinc-300">
                  <div class="flex justify-between text-zinc-500"><span>{{ entry.reader_label || 'Reader' }}</span><span>{{ (entry.created_at || '').split(' ')[0] }}</span></div>
                  <p v-if="entry.response" class="mt-1 whitespace-pre-wrap">{{ entry.response }}</p>
                  <button @click="removeReaderFeedback(entry.id)" class="mt-1 text-[9px] text-zinc-600 hover:text-rose-400">Remove response</button>
                </article>
              </div>
            </div>
            <p v-else class="text-[10px] text-zinc-600">No reader responses recorded for this scene.</p>
          </section>
      </div>

      <!-- TAB 5: LENS (Zoomed-in Chapter Spacetime with Live Reading Bead) -->
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

    </div>
  </aside>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../store.js'
import { Microscope, Sparkles, Loader, Send, Maximize, X } from '@lucide/vue'

const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

const manuscriptAnalytics = ref(null)
const analyticsLoading = ref(false)
const analyticsError = ref('')
const readerStoryAnalysis = ref(null)
const readerStoryLoading = ref(false)
const readerStoryError = ref('')
let analyticsRequest = 0
const selectedSceneAnalytics = computed(() =>
  manuscriptAnalytics.value?.scenes.find(scene => scene.scene_id === store.activeNode?.id) || null
)
const previousSceneAnalytics = computed(() => {
  const index = manuscriptAnalytics.value?.selected_index
  return Number.isInteger(index) && index > 0 ? manuscriptAnalytics.value.scenes[index - 1] : null
})
const nextSceneAnalytics = computed(() => {
  const index = manuscriptAnalytics.value?.selected_index
  return Number.isInteger(index) ? manuscriptAnalytics.value.scenes[index + 1] || null : null
})
const analyticsPosition = computed(() => {
  const index = manuscriptAnalytics.value?.selected_index
  return Number.isInteger(index) ? index + 1 : 0
})
const readTimeRange = computed(() => {
  const words = selectedSceneAnalytics.value?.telemetry.words || 0
  if (!words) return 'No text'
  const minMinutes = Math.max(1, Math.ceil(words / 250))
  const maxMinutes = Math.max(1, Math.ceil(words / 200))
  return minMinutes === maxMinutes ? `~${minMinutes} min` : `~${minMinutes}–${maxMinutes} min`
})
const median = values => {
  const sorted = values.filter(Number.isFinite).sort((left, right) => left - right)
  if (!sorted.length) return null
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}
const manuscriptPeers = computed(() =>
  manuscriptAnalytics.value?.scenes.filter(scene => scene.scene_id !== store.activeNode?.id) || []
)
const sceneLengthComparison = computed(() => {
  const words = selectedSceneAnalytics.value?.telemetry.words
  const typical = median(manuscriptPeers.value.map(scene => scene.telemetry.words))
  if (!Number.isFinite(words)) return ''
  if (typical === null) return 'Only scene in this manuscript; no manuscript baseline yet.'
  const delta = Math.round(words - typical)
  const detail = delta === 0 ? 'matches' : `${Math.abs(delta)} words ${delta > 0 ? 'above' : 'below'}`
  return `${detail} the ${Math.round(typical).toLocaleString()}-word median of ${manuscriptPeers.value.length} other scene(s).`
})
const manuscriptPatternComparisons = computed(() => {
  const current = selectedSceneAnalytics.value?.telemetry
  if (!current) return []
  const comparisons = [
    { label: 'Dialogue paragraphs', key: 'dialogue_ratio', suffix: '%', decimals: 1 },
    { label: 'Average sentence length', key: 'avg_sentence', suffix: ' words', decimals: 1 },
    { label: 'Sentence-length variation', key: 'cadence_stdev', suffix: ' words', decimals: 1 }
  ]
  return comparisons.map(metric => {
    const value = current[metric.key] || 0
    const baseline = median(manuscriptPeers.value.map(scene => scene.telemetry[metric.key]))
    let context = 'No other scenes available for comparison.'
    if (baseline !== null) {
      const delta = value - baseline
      const format = number => `${Number(number.toFixed(metric.decimals))}${metric.suffix}`
      context = `${format(value)} here vs ${format(baseline)} median across ${manuscriptPeers.value.length} other scene(s) (${delta > 0 ? '+' : ''}${format(delta)}).`
    }
    return { label: metric.label, value: `${Number(value.toFixed(metric.decimals))}${metric.suffix}`, context }
  })
})
const loadManuscriptAnalytics = async () => {
  const scene = store.activeNode
  const book = scene?.id ? store.findBookForNode(scene.id) : null
  const requestId = ++analyticsRequest
  analyticsError.value = ''
  manuscriptAnalytics.value = null
  if (!scene?.id || scene.node_type !== 'SCENE' || !book) {
    analyticsLoading.value = false
    return
  }
  analyticsLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/analytics/reader-experience/${encodeURIComponent(book.id)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_id: scene.id, content: scene.content || '' })
    })
    if (!response.ok) throw new Error(`Could not compare scene patterns (HTTP ${response.status}).`)
    const result = await response.json()
    if (requestId !== analyticsRequest || store.activeNode?.id !== scene.id) return
    manuscriptAnalytics.value = result
  } catch (error) {
    if (requestId === analyticsRequest && store.activeNode?.id === scene?.id) {
      analyticsError.value = error.message || 'Could not compare scene patterns.'
    }
  } finally {
    if (requestId === analyticsRequest) analyticsLoading.value = false
  }
}
const plainSceneContent = (content = '') => {
  const parsed = new DOMParser().parseFromString(content, 'text/html')
  const paragraphs = Array.from(parsed.body.querySelectorAll('p, li, blockquote'))
    .map(paragraph => paragraph.textContent.trim())
    .filter(Boolean)
  return (paragraphs.length ? paragraphs.join('\n\n') : parsed.body.textContent || '').trim()
}
const tutorQuestion = ref('')
const isTutorThinking = ref(false)
const isScanning = ref(false)
const readingMode = ref('scene')
const isLensLoading = ref(false)
const selectedRevisionVersion = ref(null)
const simulationHistory = ref([])
const selectedSimulationId = ref('')
const loopSignal = ref({ active: false, similarity: null, revisions_compared: 0 })
const readerFeedback = ref([])
const feedbackRatings = [
  { key: 'confusion_rating', label: 'Confusion (1=clear, 5=lost)' },
  { key: 'engagement_rating', label: 'Engagement (1=low, 5=high)' },
  { key: 'tension_rating', label: 'Tension (1=low, 5=high)' },
  { key: 'empathy_rating', label: 'Connection (1=low, 5=high)' }
]
const feedbackForm = reactive({
  reader_label: '',
  revision_ref: 'CURRENT',
  confusion_rating: '',
  engagement_rating: '',
  tension_rating: '',
  empathy_rating: '',
  response: ''
})
const canSaveFeedback = computed(() => Boolean(
  feedbackForm.response.trim() ||
  feedbackRatings.some(rating => feedbackForm[rating.key] !== '')
))
const readerFeedbackGroups = computed(() => {
  const groups = new Map()
  for (const entry of readerFeedback.value) {
    if (!groups.has(entry.revision_ref)) groups.set(entry.revision_ref, [])
    groups.get(entry.revision_ref).push(entry)
  }
  return Array.from(groups, ([revision, entries]) => {
    const ratings = feedbackRatings.map(rating => {
      const values = entries.map(entry => entry[rating.key]).filter(value => value !== null && value !== undefined).map(Number).filter(Number.isFinite)
      if (!values.length) return ''
      const mean = values.reduce((total, value) => total + value, 0) / values.length
      const average = (rating.key === 'confusion_rating' ? 6 - mean : mean).toFixed(1)
      const label = rating.key === 'confusion_rating' ? 'Clarity' : rating.label.split(' (')[0]
      return `${label} ${average}/5 (n=${values.length})`
    }).filter(Boolean)
    return { revision, entries, averages: ratings.join(' · ') }
  })
})
const readerFeedbackSummary = computed(() => {
  const groups = readerFeedbackGroups.value.map(group => ({
    ...group,
    recentResponses: group.entries.filter(entry => entry.response?.trim()).slice(0, 2)
  }))
  return {
    responseCount: readerFeedback.value.length,
    groups: groups.slice(0, 3),
    moreGroups: groups.length > 3
  }
})
const selectedSimulation = computed(() =>
  simulationHistory.value.find(simulation => simulation.id === selectedSimulationId.value)
  || simulationHistory.value[0]
  || null
)
const readerExperienceDimensions = [
  { key: 'emotional-arc', type: 'EMOTIONAL_ARC', label: 'Emotional movement' },
  { key: 'interest', type: 'READER_INTEREST', label: 'Interest and engagement' },
  { key: 'tension', type: 'TENSION', label: 'Tension' },
  { key: 'mystery', type: 'MYSTERY', label: 'Mystery and curiosity' },
  { key: 'suspense', type: 'SUSPENSE', label: 'Suspense and anticipation' },
  { key: 'character-connection', type: 'CHARACTER_CONNECTION', label: 'Character connection' },
  { key: 'confusion', type: 'CONFUSION', label: 'Possible confusion' },
  { key: 'attention', type: 'ATTENTION', label: 'Attention and pacing' }
]
const otherObservationCategories = [
  { type: 'DIRECT', label: 'What may come through clearly', color: 'text-amber-300' },
  { type: 'INFERRED', label: 'Possible inference or reaction', color: 'text-cyan-300' },
  { type: 'DELAYED', label: 'Open questions carried forward', color: 'text-violet-300' },
  { type: 'FRICTION', label: 'Possible confusion or attention breaks', color: 'text-rose-300' },
  { type: 'REVISION_FOCUS', label: 'Optional revision experiments', color: 'text-amber-300' }
]
const simulationItems = type =>
  selectedSimulation.value?.items.filter(item => item.disclosure_type === type) || []
const readerExperienceItems = type => simulationItems(type)
const readerStoryGroups = computed(() => {
  const analysis = readerStoryAnalysis.value
  if (!analysis) return []
  return [
    { key: 'threads', items: analysis.threads || [] },
    { key: 'turns', items: analysis.turns || [] },
    { key: 'emotional-payoffs', items: analysis.emotional_payoffs || [] },
    { key: 'empathy-moments', items: analysis.empathy_moments || [] },
    { key: 'subtext-moments', items: analysis.subtext_moments || [] },
    { key: 'irony-moments', items: analysis.irony_moments || [] },
    { key: 'trust-shifts', items: analysis.trust_shifts || [] }
  ].filter(group => group.items.length)
})
const jumpToStoryEvidence = async (sceneId, text) => {
  if (!text) return
  if (sceneId && sceneId !== store.activeNode?.id) {
    if (!await store.loadScene(sceneId)) return
  }
  store.viewMode = 'editor'
  await nextTick()
  window.dispatchEvent(new CustomEvent('sniper-scroll', { detail: { text } }))
}
const readerLevelLabel = level => {
  const labels = { 1: 'Very low · 1/5', 2: 'Low · 2/5', 3: 'Moderate · 3/5', 4: 'High · 4/5', 5: 'Very high · 5/5' }
  return labels[level] || 'Unrated'
}
const simulationComparison = computed(() => {
  const selectedIndex = simulationHistory.value.findIndex(
    simulation => simulation.id === selectedSimulationId.value
  )
  if (selectedIndex < 0) return null
  const selected = simulationHistory.value[selectedIndex]
  const previous = simulationHistory.value.slice(selectedIndex + 1).find(simulation =>
    simulation.analyzed_content_hash !== selected.analyzed_content_hash
    && simulation.prompt_version === selected.prompt_version
    && simulation.model_name === selected.model_name
    && (simulation.reading_mode || 'scene') === (selected.reading_mode || 'scene')
  )
  if (!previous) return null
  const normalizeClaim = item => `${item.disclosure_type}:${item.narrative_claim}`.trim().toLowerCase().replace(/\s+/g, ' ')
  const currentClaims = new Map(selected.items.map(item => [normalizeClaim(item), item.narrative_claim]))
  const previousClaims = new Map(previous.items.map(item => [normalizeClaim(item), item.narrative_claim]))
  return {
    previous,
    unchanged: [...currentClaims.keys()].filter(claim => previousClaims.has(claim)),
    newClaims: [...currentClaims].filter(([claim]) => !previousClaims.has(claim)).map(([, claim]) => claim),
    removedClaims: [...previousClaims].filter(([claim]) => !currentClaims.has(claim)).map(([, claim]) => claim)
  }
})
let readerFeedbackRequest = 0
let simulationHistoryRequest = 0
let currentManifest = null

watch(() => store.activeNode?.id, () => {
  selectedRevisionVersion.value = null
  simulationHistory.value = []
  selectedSimulationId.value = ''
  loopSignal.value = { active: false, similarity: null, revisions_compared: 0 }
  Object.assign(feedbackForm, {
    reader_label: '', revision_ref: 'CURRENT', confusion_rating: '',
    engagement_rating: '', tension_rating: '', empathy_rating: '', response: ''
  })
  loadReaderFeedback()
  loadReaderSimulations()
})
let readerStoryRequest = 0
let readerStoryTimer
watch(() => [store.activeNode?.id, store.activeNode?.content, store.activeInspectorTab], ([, , tab]) => {
  if (tab !== 'reader') return
  clearTimeout(readerStoryTimer)
  readerStoryTimer = setTimeout(loadReaderStoryAnalysis, 350)
})
watch(() => [store.activeNode?.id, store.activeInspectorTab], ([, tab]) => {
  if (tab === 'telemetry') loadManuscriptAnalytics()
})

// Persistent Scene Card Data Proxy (Stored in SQLite binder_nodes.card_data)
const cardData = computed(() => {
  if (!store.activeNode) return {}
  if (!store.activeNode.card) {
    store.activeNode.card = {
      pov_character: '',
      setting: '',
      narrative_time: '',
      tension_target: 50,
      scene_goal: '',
      word_target: 500,
      daily_goal: 1200
    }
  }

  store.activeNode.card.scene_goal ??= ''
  store.activeNode.card.word_target ??= 500
  store.activeNode.card.daily_goal ??= 1200
  return store.activeNode.card
})

const scrivenerMetadataText = computed(() => JSON.stringify(cardData.value.scrivener?.metadata || {}, null, 2))
const scrivenerMetadataFields = computed(() => {
  const metadata = cardData.value.scrivener?.metadata || {}
  const preferred = ['status', 'label', 'keywords', 'custommetadata', 'includeincompile']
  const formatValue = (value) => {
    if (value === null || value === undefined || value === '') return ''
    if (Array.isArray(value)) return value.map(formatValue).filter(Boolean).join(', ')
    if (typeof value === 'object') {
      const text = value['#text']
      const attributes = value['@attributes']
      if (text !== undefined) return String(text)
      if (attributes && Object.keys(attributes).length) return Object.entries(attributes).map(([key, item]) => `${key}: ${item}`).join(', ')
      return Object.entries(value).map(([key, item]) => `${key}: ${formatValue(item)}`).join('; ')
    }
    return String(value)
  }
  return Object.entries(metadata)
    .map(([key, value]) => ({
      label: key.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_-]/g, ' ').replace(/\b\w/g, character => character.toUpperCase()),
      value: formatValue(value)
    }))
    .filter(field => field.value)
    .sort((left, right) => {
      const leftRank = preferred.indexOf(left.label.replace(/\s/g, '').toLowerCase())
      const rightRank = preferred.indexOf(right.label.replace(/\s/g, '').toLowerCase())
      return (leftRank < 0 ? preferred.length : leftRank) - (rightRank < 0 ? preferred.length : rightRank)
    })
})

const writableTarget = computed(() => Math.max(Number(cardData.value.word_target) || 0, Number(store.activeNode?.word_count) || 0))
const sprintProgress = computed(() => {
  const target = writableTarget.value || 1
  return Math.min(100, Math.round(((Number(store.activeNode?.word_count) || 0) / target) * 100))
})

const chapterSummary = computed(() => {
  if (!store.activeNode) {
    return { label: 'Chapter', target: 0, totalWords: 0, sceneCount: 0, completedScenes: 0, avgSceneWords: 0, remainingWords: 0, progress: 0, sceneBreakdown: [] }
  }

  const chapterId = store.activeNode.parent_id || (store.activeNode.node_type === 'CHAPTER' ? store.activeNode.id : null)
  if (!chapterId) {
    return { label: 'Chapter', target: Math.max(Number(cardData.value.word_target) || 0, Number(store.activeNode?.word_count) || 0), totalWords: Number(store.activeNode?.word_count) || 0, sceneCount: 1, completedScenes: 1, avgSceneWords: Number(store.activeNode?.word_count) || 0, remainingWords: 0, progress: 100, sceneBreakdown: [{ id: store.activeNode.id, title: store.activeNode.title, words: Number(store.activeNode?.word_count) || 0, target: Math.max(Number(cardData.value.word_target) || 0, Number(store.activeNode?.word_count) || 0) }] }
  }

  const getNodeList = (nodes = []) => {
    const all = []
    for (const node of nodes) {
      all.push(node)
      if (Array.isArray(node.children)) {
        all.push(...getNodeList(node.children))
      }
    }
    return all
  }

  const chapterNode = getNodeList(store.tree).find(node => node.id === chapterId)
  const scenes = []
  const walk = (nodes = []) => {
    for (const node of nodes) {
      if (node.id === chapterId) {
        for (const child of (node.children || [])) {
          if (child.node_type === 'SCENE') scenes.push(child)
          if (Array.isArray(child.children)) walk([child])
        }
      }
      if (node.parent_id === chapterId && node.node_type === 'SCENE') {
        scenes.push(node)
      }
    }
  }
  walk(store.tree)

  const uniqueScenes = scenes.filter((scene, idx, arr) => arr.findIndex(item => item.id === scene.id) === idx)
  let totalWords = 0
  let completedScenes = 0
  const sceneBreakdown = uniqueScenes.map(scene => {
    const words = Number(scene.word_count) || 0
    const target = Number(scene.card?.word_target) || Number(scene.card_data && JSON.parse(scene.card_data || '{}')?.word_target) || 500
    totalWords += words
    if (words >= target) completedScenes += 1
    return {
      id: scene.id,
      title: scene.title,
      words,
      target
    }
  }).sort((a, b) => b.words - a.words)

  const chapterTarget = Math.max(
    Number(chapterNode?.card?.chapter_word_target) ||
    Number(chapterNode?.card?.word_target) ||
    4000,
    totalWords || 3000
  )
  const progress = Math.min(100, Math.round((totalWords / chapterTarget) * 100))

  return {
    label: chapterNode?.title || 'Chapter',
    target: chapterTarget,
    totalWords,
    sceneCount: sceneBreakdown.length || 1,
    completedScenes,
    avgSceneWords: sceneBreakdown.length ? Math.round(totalWords / sceneBreakdown.length) : 0,
    remainingWords: Math.max(0, chapterTarget - totalWords),
    progress,
    sceneBreakdown: sceneBreakdown.slice(0, 4)
  }
})

const revisionComparison = computed(() => {
  const revisions = store.activeNode?.revisions || []
  const revision = revisions.find(item => item.version_num === selectedRevisionVersion.value)
  if (!revision) return null

  const toParagraphs = (content) => {
    const document = new DOMParser().parseFromString(content || '', 'text/html')
    const blocks = Array.from(document.body.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, pre'))
      .map(element => element.textContent.trim())
      .filter(Boolean)
    if (blocks.length) return blocks
    return (document.body.textContent || '').split(/\n+/).map(text => text.trim()).filter(Boolean)
  }

  const oldParagraphs = toParagraphs(revision.content)
  const currentParagraphs = toParagraphs(store.activeNode?.content)
  const wordCount = paragraphs => (paragraphs.join(' ').match(/\S+/g) || []).length
  const cellCount = oldParagraphs.length * currentParagraphs.length
  let parts = []
  let removed = 0
  let added = 0
  const isLimited = cellCount > 1_000_000

  if (isLimited) {
    parts = [
      ...oldParagraphs.map(text => ({ kind: 'removed', text })),
      ...currentParagraphs.map(text => ({ kind: 'added', text }))
    ]
    removed = oldParagraphs.length
    added = currentParagraphs.length
  } else {
    const width = currentParagraphs.length + 1
    const table = new Uint32Array((oldParagraphs.length + 1) * width)
    for (let oldIndex = oldParagraphs.length - 1; oldIndex >= 0; oldIndex -= 1) {
      for (let currentIndex = currentParagraphs.length - 1; currentIndex >= 0; currentIndex -= 1) {
        const index = oldIndex * width + currentIndex
        table[index] = oldParagraphs[oldIndex] === currentParagraphs[currentIndex]
          ? table[index + width + 1] + 1
          : Math.max(table[index + width], table[index + 1])
      }
    }

    let oldIndex = 0
    let currentIndex = 0
    while (oldIndex < oldParagraphs.length || currentIndex < currentParagraphs.length) {
      if (oldIndex < oldParagraphs.length && currentIndex < currentParagraphs.length && oldParagraphs[oldIndex] === currentParagraphs[currentIndex]) {
        parts.push({ kind: 'same', text: oldParagraphs[oldIndex] })
        oldIndex += 1
        currentIndex += 1
      } else if (oldIndex < oldParagraphs.length && (currentIndex >= currentParagraphs.length || table[(oldIndex + 1) * width + currentIndex] >= table[oldIndex * width + currentIndex + 1])) {
        parts.push({ kind: 'removed', text: oldParagraphs[oldIndex] })
        removed += 1
        oldIndex += 1
      } else {
        parts.push({ kind: 'added', text: currentParagraphs[currentIndex] })
        added += 1
        currentIndex += 1
      }
    }
  }

  return {
    versionNum: revision.version_num,
    parts,
    removed,
    added,
    wordDelta: wordCount(currentParagraphs) - wordCount(oldParagraphs),
    isLimited
  }
})

const getPlotly = async () => {
  if (typeof window !== 'undefined' && window.Plotly) return window.Plotly
  try {
    const mod = await import('plotly.js-dist-min')
    return mod.default || mod
  } catch (e) {
    return null
  }
}

const formatRevisionTime = (value) => {
  if (!value) return 'just now'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  return dt.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

const restoreRevision = async (versionNum) => {
  if (!store.activeNode?.id) return
  if (!window.confirm(`Restore revision v${versionNum}? The current draft will be saved as a new revision first.`)) return
  try {
    const res = await fetch(`${API_BASE}/api/node/${store.activeNode.id}/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version_num: versionNum })
    })
    if (!res.ok) throw new Error(`Restore failed (HTTP ${res.status}).`)
    const loaded = await store.loadScene(store.activeNode.id)
    if (!loaded) throw new Error('Revision was restored, but the scene could not be reloaded.')
    showToast(`Restored revision v${versionNum}`, 'success')
  } catch (e) {
    showToast(e.message || 'Revision restore failed', 'error')
  }
}

// Live Reading Bead Receiver
const handleScrollBeat = async (e) => {
  const beatIdx = e.detail?.beat || 1
  const plotEl = document.getElementById('mini-astrolabe-plot')
  const Plotly = await getPlotly()
  if (!plotEl || !Plotly || !currentManifest || store.activeInspectorTab !== 'lens') return

  const spine = currentManifest.data?.[0]
  if (!spine || !spine.x?.length) return

  const targetIdx = Math.min(beatIdx - 1, spine.x.length - 1)
  const beadX = [spine.x[targetIdx]]
  const beadY = [spine.y[targetIdx]]
  const beadZ = [spine.z[targetIdx]]

  const beadTrace = {
    type: 'scatter3d',
    mode: 'markers',
    name: 'Reading Head',
    x: beadX,
    y: beadY,
    z: beadZ,
    text: [`<b>Current Reading Position</b> (Beat ${beatIdx})`],
    hoverinfo: 'text',
    marker: {
      size: 14,
      symbol: 'circle',
      color: '#22d3ee',
      line: { color: '#ffffff', width: 2 }
    }
  }

  const allTraces = [...currentManifest.data, beadTrace]
  Plotly.react('mini-astrolabe-plot', allTraces, currentManifest.layout, {
    responsive: true,
    displayModeBar: false
  })
}

const renderMiniAstrolabe = async () => {
  const chapterId = store.activeNode?.parent_id
  const sceneId = store.activeNode?.id
  if (!chapterId) return

  isLensLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/narrative/astrolabe?chapter_id=${chapterId}&focus_id=${sceneId}&projection=KINEMATIC&time_mode=narrative`)
    if (!res.ok) throw new Error('Lens endpoint error')
    currentManifest = await res.json()
    
    await nextTick()
    const plotEl = document.getElementById('mini-astrolabe-plot')
    const Plotly = await getPlotly()

    if (plotEl && currentManifest.data && Plotly) {
      if (currentManifest.layout) {
        currentManifest.layout.paper_bgcolor = 'rgba(0,0,0,0)'
        currentManifest.layout.plot_bgcolor = 'rgba(0,0,0,0)'
        currentManifest.layout.margin = { l: 0, r: 0, b: 0, t: 0 }
        currentManifest.layout.showlegend = false
      }

      await Plotly.react('mini-astrolabe-plot', currentManifest.data, currentManifest.layout, { 
        responsive: true, 
        displayModeBar: false 
      })

      plotEl.removeAllListeners?.('plotly_click')
      plotEl.on('plotly_click', async (data) => {
        if (data && data.points && data.points[0]) {
          const cdata = data.points[0].customdata
          if (!cdata) return

          const sceneId = typeof cdata === 'object' ? cdata.scene_id : cdata
          const beatIdx = typeof cdata === 'object' ? cdata.beat_idx : (data.points[0].pointIndex + 1)
          const snippet = typeof cdata === 'object' ? cdata.snippet : ''

          if (sceneId && sceneId !== store.activeNode?.id) {
            await store.loadScene(sceneId)
          }

          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('lens-beat-jump', {
              detail: { beat: beatIdx, snippet: snippet }
            }))
          }, 150)
        }
      })
    }
  } catch(e) {
    console.warn('[Mini Astrolabe Error]', e)
  } finally {
    isLensLoading.value = false
  }
}

const openLensTab = () => {
  store.activeInspectorTab = 'lens'
  nextTick(() => renderMiniAstrolabe())
}

watch(() => [store.activeNode?.id, store.activeInspectorTab], ([newId, tab]) => {
  if (tab === 'lens' && newId) {
    nextTick(() => renderMiniAstrolabe())
  }
})

// Force save persists title, synopsis, content, epigraph, status, AND cardData directly to SQLite
const forceSave = async () => {
  if (!store.activeNode?.id) return
  try {
    if (store.flushPendingSave && !(await store.flushPendingSave())) {
      throw new Error('Draft text could not be saved. Please retry before saving scene details.')
    }
    const response = await fetch(`${API_BASE}/api/node/${store.activeNode.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        title: store.activeNode.title, 
        synopsis: store.activeNode.synopsis, 
        content: store.activeNode.content, 
        epigraph: store.activeNode.epigraph, 
        status: store.activeNode.status,
        card_data: cardData.value
      })
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to update scene details`)
    window.dispatchEvent(new Event('refresh-tree'))
  } catch (e) {
    showToast(e.message || 'Failed to update scene details.', 'error')
  }
}

const askTutor = async () => {
  if (!tutorQuestion.value.trim()) return
  isTutorThinking.value = true
  store.socraticCritique = ''
  try {
    const res = await fetch(`${API_BASE}/api/craft/teach`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        question: tutorQuestion.value, 
        context: plainSceneContent(store.activeNode?.content || '')
      }) 
    })
    if (!res.ok) throw new Error('Tutor offline')
    const data = await res.json()
    store.socraticCritique = data.lesson
  } catch(e) { 
    showToast(e.message, 'error') 
  } finally {
    isTutorThinking.value = false
    tutorQuestion.value = ''
  }
}

const elevateMacroScene = async () => {
  if (!store.activeNode?.content) return
  store.socraticCritique = 'Analyzing macro structure...'
  try {
    const res = await fetch(`${API_BASE}/api/craft/elevate`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        passage: "[MACRO SCENE DIAGNOSIS] " + store.activeNode.content.substring(0, 3000), 
        surrounding: "Evaluate macro scene structure and character agency.", 
        scene_id: store.activeNode.id 
      }) 
    })
    if (!res.ok) throw new Error('Macro diagnosis failed')
    const data = await res.json()
    store.socraticCritique = data.critique
    store.activeCritiqueId = data.critique_id
    fetchCritiques()
  } catch(e) { 
    showToast(e.message, 'error') 
  }
}

const fetchCritiques = async () => {
  if (!store.activeNode?.id) return
  try {
    const res = await fetch(`${API_BASE}/api/critiques/scene/${store.activeNode.id}`)
    if (!res.ok) return
    store.sceneCritiques = await res.json()
  } catch (e) {
    console.warn('[Thedral Critiques]', e)
  }
}

const resolveCritique = async (status) => {
  if (store.activeCritiqueId) {
    try {
      await fetch(`${API_BASE}/api/critiques/${store.activeCritiqueId}/status`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ status }) 
      })
    } catch(e) {}
  }
  store.socraticCritique = ''
  store.activeCritiqueId = null
  fetchCritiques()
}

const scanHorizon = async () => {
  if (!store.activeNode?.id || !store.activeNode?.content) return
  const sceneId = store.activeNode.id
  const content = store.activeNode.content
  isScanning.value = true
  try {
    const res = await fetch(`${API_BASE}/api/disclosures/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_id: sceneId,
        text: content,
        reading_mode: readingMode.value
      })
    })
    if (!res.ok) throw new Error(`Scan failed (HTTP ${res.status}).`)
    const data = await res.json()
    if (data.status === 'success') {
      if (store.activeNode?.id === sceneId) {
        await loadReaderSimulations(data.simulation.id)
      }
      if (data.warnings?.length) showToast(data.warnings.join(' '), 'info')
      else if (data.reused) showToast('This exact scene already has a saved fresh-read simulation; showing that result.', 'info')
      else showToast('Fresh-read simulation saved for this exact scene text.', 'info')
    } else {
      throw new Error(data.message || 'Reader simulation did not complete.')
    }
  } catch (e) {
    showToast(e.message || 'Reader simulation failed.', 'error')
  } finally {
    isScanning.value = false
  }
}

const loadReaderSimulations = async (selectedId = '') => {
  const sceneId = store.activeNode?.id
  const requestId = ++simulationHistoryRequest
  if (!sceneId) {
    simulationHistory.value = []
    selectedSimulationId.value = ''
    loopSignal.value = { active: false, similarity: null, revisions_compared: 0 }
    return
  }
  try {
    const response = await fetch(`${API_BASE}/api/reader-simulations/scene/${encodeURIComponent(sceneId)}`)
    if (!response.ok) throw new Error(`Could not load saved reader simulations (HTTP ${response.status}).`)
    const result = await response.json()
    if (requestId !== simulationHistoryRequest || store.activeNode?.id !== sceneId) return
    simulationHistory.value = result.simulations
    loopSignal.value = result.loop_signal
    selectedSimulationId.value = (
      result.simulations.some(simulation => simulation.id === selectedId)
        ? selectedId
        : result.simulations[0]?.id || ''
    )
  } catch (error) {
    if (requestId === simulationHistoryRequest && store.activeNode?.id === sceneId) {
      simulationHistory.value = []
      loopSignal.value = { active: false, similarity: null, revisions_compared: 0 }
      showToast(error.message || 'Could not load saved reader simulations.', 'error')
    }
  }
}

const loadReaderStoryAnalysis = async () => {
  const sceneId = store.activeNode?.id
  const bookId = sceneId ? store.findBookForNode(sceneId)?.id : ''
  const requestId = ++readerStoryRequest
  readerStoryAnalysis.value = null
  readerStoryError.value = ''
  if (!sceneId || !bookId || store.activeInspectorTab !== 'reader') {
    readerStoryLoading.value = false
    return
  }
  const cachedScene = store.readerStoryCache?.book_id === bookId
    ? store.readerStoryCache.analyses?.find(item => item.scene_id === sceneId)
    : null
  if (cachedScene && cachedScene.content === (store.activeNode?.content || '')) {
    readerStoryAnalysis.value = cachedScene.analysis
    readerStoryLoading.value = false
    return
  }
  readerStoryLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/analytics/reader-story/${encodeURIComponent(bookId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_id: sceneId, content: store.activeNode?.content || '' })
    })
    if (!response.ok) throw new Error(`Could not follow story threads (HTTP ${response.status}).`)
    const result = await response.json()
    if (requestId === readerStoryRequest && store.activeNode?.id === sceneId) {
      readerStoryAnalysis.value = result
    }
  } catch (error) {
    if (requestId === readerStoryRequest && store.activeNode?.id === sceneId) {
      readerStoryError.value = error.message || 'Could not follow story threads.'
    }
  } finally {
    if (requestId === readerStoryRequest) readerStoryLoading.value = false
  }
}

const loadReaderFeedback = async () => {
  const sceneId = store.activeNode?.id
  const requestId = ++readerFeedbackRequest
  readerFeedback.value = []
  if (!sceneId) {
    return
  }
  try {
    const response = await fetch(`${API_BASE}/api/reader-feedback/scene/${encodeURIComponent(sceneId)}`)
    if (!response.ok) throw new Error(`Could not load reader feedback (HTTP ${response.status}).`)
    const entries = await response.json()
    if (requestId === readerFeedbackRequest && store.activeNode?.id === sceneId) {
      readerFeedback.value = entries
    }
  } catch (error) {
    if (requestId === readerFeedbackRequest && store.activeNode?.id === sceneId) {
      showToast(error.message || 'Could not load reader feedback.', 'error')
    }
  }
}

const saveReaderFeedback = async () => {
  if (!store.activeNode?.id || !canSaveFeedback.value) return
  try {
    const response = await fetch(`${API_BASE}/api/reader-feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_id: store.activeNode.id,
        revision_ref: feedbackForm.revision_ref,
        reader_label: feedbackForm.reader_label,
        confusion_rating: feedbackForm.confusion_rating ? Number(feedbackForm.confusion_rating) : null,
        engagement_rating: feedbackForm.engagement_rating ? Number(feedbackForm.engagement_rating) : null,
        tension_rating: feedbackForm.tension_rating ? Number(feedbackForm.tension_rating) : null,
        empathy_rating: feedbackForm.empathy_rating ? Number(feedbackForm.empathy_rating) : null,
        response: feedbackForm.response
      })
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail.detail || `Could not save reader response (HTTP ${response.status}).`)
    }
    Object.assign(feedbackForm, {
      reader_label: '', confusion_rating: '', engagement_rating: '',
      tension_rating: '', empathy_rating: '', response: ''
    })
    await loadReaderFeedback()
    showToast('Reader response saved locally.', 'info')
  } catch (error) {
    showToast(error.message || 'Could not save reader response.', 'error')
  }
}

const removeReaderFeedback = async (feedbackId) => {
  try {
    const response = await fetch(`${API_BASE}/api/reader-feedback/${encodeURIComponent(feedbackId)}`, { method: 'DELETE' })
    if (!response.ok) throw new Error(`Could not remove reader response (HTTP ${response.status}).`)
    readerFeedback.value = readerFeedback.value.filter(entry => entry.id !== feedbackId)
  } catch (error) {
    showToast(error.message || 'Could not remove reader response.', 'error')
  }
}

onMounted(() => {
  window.addEventListener('refresh-critiques', fetchCritiques)
  window.addEventListener('editor-scroll-beat', handleScrollBeat)
  if (store.activeNode?.id) {
    loadReaderFeedback()
    loadReaderSimulations()
    if (store.activeInspectorTab === 'reader') loadReaderStoryAnalysis()
  }
  if (store.activeInspectorTab === 'lens') {
    nextTick(() => renderMiniAstrolabe())
  }
})

onBeforeUnmount(() => {
  clearTimeout(readerStoryTimer)
  readerStoryRequest += 1
  window.removeEventListener('editor-scroll-beat', handleScrollBeat)
})
</script>