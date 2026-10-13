<template>
  <div 
    v-if="store.modals.cast" 
    class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none"
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-xl w-full p-6 space-y-5 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
      <!-- Modal Header -->
      <div class="flex items-center justify-between border-b border-zinc-800 pb-3 shrink-0">
        <div class="flex items-center gap-3">
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <Users class="w-5 h-5 text-amber-500" /> Cast & Relics Directory
          </h3>
          <span class="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
            {{ displayedEntities.length }} in view
          </span>
        </div>
        <button @click="closeModal" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Quick Registration Tray -->
      <div class="bg-zinc-950/70 border border-zinc-800/80 rounded-xl p-3 shrink-0 space-y-3">
        <div class="text-[10px] font-bold text-amber-400 uppercase tracking-wider font-mono flex items-center gap-1.5">
          <Plus class="w-3.5 h-3.5" /> Track New Entity
        </div>
        <div class="flex gap-2">
          <input 
            v-model="newEntity.name" 
            @keyup.enter="createEntity"
            placeholder="Entity name (e.g. Lord Vael, The Sunstone)..." 
            class="flex-1 bg-zinc-900 border border-zinc-700/60 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:border-amber-500/50 focus:outline-none transition"
          />
          <select 
            v-model="newEntity.entity_type" 
            class="bg-zinc-900 border border-zinc-700/60 rounded px-2 py-1.5 text-xs text-zinc-300 focus:outline-none"
          >
            <option value="CHARACTER">Character</option>
            <option value="LOCATION">Place</option>
            <option value="ITEM">Artifact / Relic</option>
            <option value="FACTION">Group / faction</option>
            <option value="WORLD_TERM">Worldbuilding term</option>
          </select>
          <button 
            @click="createEntity" 
            :disabled="!newEntity.name.trim()"
            class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-zinc-950 font-bold rounded text-xs transition"
          >
            Add
          </button>
        </div>
        <textarea
          v-model="newEntity.aliases"
          rows="2"
          placeholder="Alternate names, one per line (nicknames, titles, former names; optional)"
          class="w-full bg-zinc-900 border border-zinc-700/60 rounded px-2.5 py-1.5 text-[10px] text-zinc-300 focus:border-amber-500/50 focus:outline-none"
        />
      </div>

      <section class="bg-zinc-950/50 border border-zinc-800/80 rounded-xl p-3 shrink-0 space-y-2">
        <div class="flex items-center justify-between gap-2">
          <div>
            <div class="text-[10px] font-bold text-cyan-300 uppercase tracking-wider font-mono">Untracked manuscript names</div>
            <p class="text-[10px] text-zinc-500 mt-1">Recurring capitalized terms are suggestions only. Confirm what each one means.</p>
          </div>
          <button
            @click="findCandidates"
            :disabled="candidateLoading || !store.getBook()?.id"
            class="px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-200 rounded text-[10px] font-bold whitespace-nowrap"
          >
            {{ candidateLoading ? 'Scanning…' : 'Find names' }}
          </button>
        </div>
        <div v-if="candidates.length" class="max-h-40 overflow-y-auto space-y-2 pr-1">
          <article v-for="candidate in candidates" :key="candidate.name" class="rounded-lg border border-zinc-800 bg-zinc-900/70 p-2 space-y-1.5">
            <div class="flex items-center justify-between gap-2">
              <div class="min-w-0">
                <span class="text-xs text-zinc-100 font-semibold">{{ candidate.name }}</span>
                <span class="ml-2 text-[9px] text-zinc-500">{{ candidate.mentions }} mentions · {{ candidate.scene_count }} scenes</span>
              </div>
              <div class="flex items-center gap-1.5">
                <select v-model="candidate.entity_type" class="bg-zinc-950 border border-zinc-700 rounded px-1.5 py-1 text-[10px] text-zinc-300">
                  <option value="" disabled>Choose type</option>
                  <option value="CHARACTER">Character</option>
                  <option value="LOCATION">Place</option>
                  <option value="ITEM">Artifact</option>
                  <option value="FACTION">Group</option>
                  <option value="WORLD_TERM">World term</option>
                </select>
                <button
                  @click="confirmCandidate(candidate)"
                  :disabled="!candidate.entity_type"
                  class="px-2 py-1 bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded text-[10px] font-bold"
                >
                  Track
                </button>
              </div>
            </div>
            <input
              v-model="candidate.aliases"
              placeholder="Aliases, comma-separated (optional)"
              class="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-[10px] text-zinc-300 focus:border-cyan-600 focus:outline-none"
            />
            <p v-if="candidate.examples?.[0]" class="text-[10px] text-zinc-500 italic truncate">{{ candidate.examples[0].excerpt }}</p>
            <p v-if="candidate.in_wiktionary !== null" class="text-[9px] text-zinc-600">
              {{ candidate.in_wiktionary ? 'Found in English Wiktionary' : 'Not found in English Wiktionary' }}
            </p>
          </article>
        </div>
      </section>

      <!-- Filter Bar: Book Scope vs Type -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono shrink-0 border-b border-zinc-800/60 pb-2.5">
        <!-- Scope Filter: Current Book vs Series Canon -->
        <div class="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
          <button 
            @click="scopeFilter = 'BOOK'"
            :class="['px-2 py-0.5 rounded text-[11px] transition', scopeFilter === 'BOOK' ? 'bg-zinc-800 text-amber-400 font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            📖 Active Book
          </button>
          <button 
            @click="scopeFilter = 'SERIES'"
            :class="['px-2 py-0.5 rounded text-[11px] transition', scopeFilter === 'SERIES' ? 'bg-zinc-800 text-amber-400 font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            🌌 Full Series Canon
          </button>
        </div>

        <!-- Type Filter Pills -->
        <div class="flex items-center space-x-1.5 text-[11px]">
          <button 
            @click="typeFilter = 'ALL'"
            :class="['px-2 py-0.5 rounded transition', typeFilter === 'ALL' ? 'text-amber-400 underline font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            All
          </button>
          <button 
            @click="typeFilter = 'CHARACTER'"
            :class="['px-2 py-0.5 rounded transition', typeFilter === 'CHARACTER' ? 'text-amber-400 underline font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            Characters
          </button>
          <button 
            @click="typeFilter = 'ITEM'"
            :class="['px-2 py-0.5 rounded transition', typeFilter === 'ITEM' ? 'text-cyan-400 underline font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            Artifacts
          </button>
          <button
            @click="typeFilter = 'LOCATION'"
            :class="['px-2 py-0.5 rounded transition', typeFilter === 'LOCATION' ? 'text-emerald-400 underline font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            Places
          </button>
          <button
            @click="typeFilter = 'FACTION'"
            :class="['px-2 py-0.5 rounded transition', typeFilter === 'FACTION' ? 'text-violet-400 underline font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            Groups
          </button>
          <button
            @click="typeFilter = 'WORLD_TERM'"
            :class="['px-2 py-0.5 rounded transition', typeFilter === 'WORLD_TERM' ? 'text-sky-400 underline font-bold' : 'text-zinc-500 hover:text-zinc-300']"
          >
            World terms
          </button>
        </div>
      </div>

      <!-- Entity Directory List -->
      <div class="flex-1 overflow-y-auto space-y-2 p-1 custom-scrollbar">
        <div 
          v-for="ent in displayedEntities" 
          :key="ent.entity_id" 
          class="p-3 bg-zinc-950 border border-zinc-800/80 hover:border-zinc-700 rounded-xl flex items-center justify-between transition group"
        >
          <div class="min-w-0 flex-1 mr-3">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-zinc-100 truncate">{{ ent.name }}</span>
              <span 
                :class="[
                  'px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-bold', 
                  ent.entity_type === 'CHARACTER' 
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                    : ent.entity_type === 'LOCATION'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : ent.entity_type === 'FACTION'
                        ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20'
                        : ent.entity_type === 'WORLD_TERM'
                          ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                ]"
              >
                {{ ent.entity_type }}
              </span>
            </div>
            <div v-if="parseAliasList(ent.aliases).length" class="text-[10px] text-zinc-500 truncate mt-0.5 font-mono">
              Also known as: {{ parseAliasList(ent.aliases).join(' · ') }}
            </div>
            <div v-if="editingAliasesId === ent.entity_id" class="mt-2 flex gap-1.5">
              <textarea
                v-model="editingAliases"
                rows="2"
                placeholder="One alternate name per line (nicknames, titles, former names)"
                class="flex-1 bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-[10px] text-zinc-300 focus:border-amber-500/50 focus:outline-none"
              />
              <div class="flex flex-col gap-1">
                <button @click="saveAliases(ent)" class="px-2 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-[10px]">Save</button>
                <button @click="editingAliasesId = null" class="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[10px]">Cancel</button>
              </div>
            </div>
          </div>

          <button
            v-if="editingAliasesId !== ent.entity_id"
            @click="beginEditAliases(ent)"
            title="Edit alternate names"
            class="p-1.5 hover:bg-zinc-800 text-zinc-500 hover:text-amber-400 rounded transition"
          >
            <span class="text-[10px] font-bold">Names</span>
          </button>
          <button 
            @click="deleteEntity(ent.entity_id)" 
            title="Untrack Entity"
            class="p-1.5 hover:bg-zinc-800 text-zinc-600 hover:text-rose-400 rounded transition opacity-40 group-hover:opacity-100"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>

        <div v-if="!displayedEntities.length" class="text-center py-10 text-xs text-zinc-500 italic font-serif">
          {{ scopeFilter === 'BOOK' ? 'No tracked entities active in this manuscript yet. Switch to "Full Series Canon" or add one above.' : 'No entities found in series canon.' }}
        </div>
      </div>

      <!-- Footer -->
      <div class="border-t border-zinc-800 pt-3 flex justify-between items-center shrink-0">
        <span class="text-[10px] text-zinc-500 font-mono">
          {{ scopeFilter === 'BOOK' ? 'Showing entities active in current draft' : 'Showing all series-wide canon' }}
        </span>
        <button 
          @click="closeModal" 
          class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition"
        >
          Done
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { Users, X, Trash2, Plus } from '@lucide/vue'

const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

const scopeFilter = ref('BOOK')   // 'BOOK' | 'SERIES'
const typeFilter = ref('ALL')
const candidates = ref([])
const candidateLoading = ref(false)
const editingAliasesId = ref(null)
const editingAliases = ref('')

const newEntity = ref({
  name: '',
  entity_type: 'CHARACTER',
  aliases: ''
})

// Returns concatenated prose of all scenes in active book to detect active cast
const activeBookProse = computed(() => {
  const scenes = []
  const visit = (nodes) => {
    for (const node of nodes || []) {
      if (node.node_type === 'SCENE' && node.content) scenes.push(node.content)
      visit(node.children)
    }
  }
  visit(store.getBook()?.children)
  return scenes.join(' ').toLowerCase()
})

const parseAliasList = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value
  try {
    const parsed = JSON.parse(value)
    if (Array.isArray(parsed)) return parsed
    if (parsed && typeof parsed === 'object') {
      return Object.values(parsed).map(alias => typeof alias === 'object' ? alias.name : alias).filter(Boolean)
    }
  } catch {
    // Legacy database rows store aliases as delimited text.
  }
  return value.split(/[,;\n|]+/).map(alias => alias.trim()).filter(Boolean)
}

const textMatchesName = (text, name) => {
  if (!name) return false
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`(?<!\\w)${escaped}(?!\\w)`, 'i').test(text)
}

const displayedEntities = computed(() => {
  let list = store.registeredEntities || []

  // 1. Filter by Type
  if (typeFilter.value !== 'ALL') {
    list = list.filter(e => e.entity_type === typeFilter.value)
  }

  // 2. Filter by Scope: if BOOK, only show if entity appears in the current draft
  if (scopeFilter.value === 'BOOK' && activeBookProse.value) {
    const bookText = activeBookProse.value
    list = list.filter(e => {
      return [e.name, ...parseAliasList(e.aliases)].some(name => textMatchesName(bookText, name))
    })
  }

  return list
})

const closeModal = () => {
  store.toggleModal('cast', false)
}

const fetchEntities = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/entities`)
    if (!res.ok) throw new Error('Could not fetch cast directory')
    store.registeredEntities = await res.json()
  } catch(e) { 
    store.registeredEntities = [] 
  }
}

const createEntity = async () => {
  const name = newEntity.value.name.trim()
  if (!name) return

  try {
    const res = await fetch(`${API_BASE}/api/entities/quick-register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        entity_type: newEntity.value.entity_type,
        aliases: newEntity.value.aliases || ''
      })
    })
    if (!res.ok) throw new Error('Registration failed')
    newEntity.value.name = ''
    newEntity.value.aliases = ''
    await fetchEntities()
    showToast(`Tracked "${name}" (${newEntity.value.entity_type})`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}

const findCandidates = async () => {
  const bookId = store.getBook()?.id
  if (!bookId) return
  candidateLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/entities/candidates/${encodeURIComponent(bookId)}`)
    if (!res.ok) throw new Error('Could not scan manuscript names')
    const data = await res.json()
    candidates.value = (data.candidates || []).map(candidate => ({
      ...candidate,
      aliases: '',
      entity_type: ''
    }))
    showToast(`Found ${candidates.value.length} names to review`, 'info')
  } catch (error) {
    showToast(error.message, 'error')
  } finally {
    candidateLoading.value = false
  }
}

const confirmCandidate = async (candidate) => {
  try {
    const res = await fetch(`${API_BASE}/api/entities/quick-register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: candidate.name,
        entity_type: candidate.entity_type,
        aliases: candidate.aliases || ''
      })
    })
    if (!res.ok) throw new Error((await res.json()).detail || 'Could not track this name')
    candidates.value = candidates.value.filter(item => item.name !== candidate.name)
    await fetchEntities()
    showToast(`Now tracking "${candidate.name}"`, 'info')
  } catch (error) {
    showToast(error.message, 'error')
  }
}

const beginEditAliases = (entity) => {
  editingAliasesId.value = entity.entity_id
  editingAliases.value = parseAliasList(entity.aliases).join('\n')
}

const saveAliases = async (entity) => {
  const aliases = editingAliases.value.split(/\n+/).map(alias => alias.trim()).filter(Boolean)
  try {
    const res = await fetch(`${API_BASE}/api/entities/${encodeURIComponent(entity.entity_id)}/aliases`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aliases })
    })
    if (!res.ok) throw new Error((await res.json()).detail || 'Could not update alternate names')
    editingAliasesId.value = null
    await fetchEntities()
    showToast(`Updated alternate names for "${entity.name}"`, 'info')
  } catch (error) {
    showToast(error.message, 'error')
  }
}

const deleteEntity = async (eid) => {
  try {
    const res = await fetch(`${API_BASE}/api/entities/${eid}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Deletion failed')
    await fetchEntities()
  } catch(e) {
    showToast('Failed to delete entity', 'error')
  }
}

watch(() => store.modals.cast, (newVal) => { 
  if (newVal) fetchEntities() 
})
</script>