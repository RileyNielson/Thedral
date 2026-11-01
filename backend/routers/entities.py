<template>
  <div 
    v-if="store.modals.cast" 
    class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none"
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
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
      </div>

      <!-- Entity Directory List with Expandable Dossiers -->
      <div class="flex-1 overflow-y-auto space-y-2 p-1 custom-scrollbar">
        <div 
          v-for="ent in displayedEntities" 
          :key="ent.entity_id" 
          class="bg-zinc-950 border border-zinc-800/80 rounded-xl overflow-hidden transition"
        >
          <!-- Summary Row -->
          <div class="p-3 flex items-center justify-between hover:bg-zinc-900/40 cursor-pointer" @click="toggleDossier(ent.entity_id)">
            <div class="min-w-0 flex-1 mr-3">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-zinc-100 truncate">{{ ent.name }}</span>
                <span 
                  :class="[
                    'px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-bold', 
                    ent.entity_type === 'CHARACTER' 
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                      : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                  ]"
                >
                  {{ ent.entity_type }}
                </span>
                <span v-if="activeDossier?.entity_id === ent.entity_id" class="text-[9px] text-amber-400 font-mono">
                  ● Dossier Open
                </span>
              </div>
              <div v-if="parseAliasList(ent.aliases).length" class="text-[10px] text-zinc-500 truncate mt-0.5 font-mono">
                Aliases: {{ parseAliasList(ent.aliases).join(' · ') }}
              </div>
            </div>

            <div class="flex items-center space-x-2 shrink-0">
              <button 
                @click.stop="toggleDossier(ent.entity_id)" 
                class="px-2 py-1 rounded bg-zinc-800 text-[10px] font-mono text-zinc-300 hover:text-white transition"
              >
                {{ activeDossier?.entity_id === ent.entity_id ? 'Close' : 'Dossier' }}
              </button>
              <button 
                @click.stop="deleteEntity(ent.entity_id)" 
                class="p-1 hover:bg-zinc-800 text-zinc-600 hover:text-rose-400 rounded transition"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Living Auto-Compiled Dossier Drawer -->
          <div 
            v-if="activeDossier?.entity_id === ent.entity_id" 
            class="p-4 bg-zinc-900/80 border-t border-zinc-800/80 space-y-3 text-xs animate-fade-in"
          >
            <div v-if="isDossierLoading" class="py-4 text-center text-xs font-mono text-zinc-500 flex items-center justify-center gap-2">
              <Loader class="w-3.5 h-3.5 animate-spin text-amber-500" /> Compiling living dossier from manuscript...
            </div>
            
            <template v-else>
              <!-- Timeline Presence -->
              <div class="grid grid-cols-2 gap-2 text-[10px] font-mono">
                <div class="p-2 bg-zinc-950 rounded border border-zinc-800">
                  <div class="text-zinc-500">First Appearance:</div>
                  <div class="text-zinc-200 font-medium truncate mt-0.5">{{ activeDossier.first_appearance }}</div>
                </div>
                <div class="p-2 bg-zinc-950 rounded border border-zinc-800">
                  <div class="text-zinc-500">Presence:</div>
                  <div class="text-zinc-200 font-medium mt-0.5">{{ activeDossier.total_scenes }} Scene(s) across {{ activeDossier.chapters_present.length }} Chapter(s)</div>
                </div>
              </div>

              <!-- Observed Appearance & Traits -->
              <div v-if="activeDossier.traits?.length" class="space-y-1">
                <div class="text-[10px] uppercase font-mono text-amber-400 font-bold">Observed Traits & Sensory Details (From Prose):</div>
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="trait in activeDossier.traits" :key="trait" class="px-2 py-0.5 bg-zinc-950 border border-zinc-800 text-zinc-300 rounded text-[10px]">
                    {{ trait }}
                  </span>
                </div>
              </div>

              <!-- Top Associates -->
              <div v-if="activeDossier.top_associates?.length" class="space-y-1">
                <div class="text-[10px] uppercase font-mono text-zinc-400 font-bold">Frequent Associates:</div>
                <div class="flex flex-wrap gap-2 text-[10px] text-zinc-400">
                  <span v-for="assoc in activeDossier.top_associates" :key="assoc.name">
                    <strong class="text-zinc-200">{{ assoc.name }}</strong> ({{ assoc.shared_scenes }} shared scenes)
                  </span>
                </div>
              </div>

              <!-- Spoken Dialogue -->
              <div class="text-[10px] font-mono text-zinc-500 flex justify-between pt-1 border-t border-zinc-800/80">
                <span>Spoken lines: <strong class="text-zinc-300">{{ activeDossier.dialogue_stats.lines_spoken }}</strong></span>
                <span>Dialogue words: <strong class="text-zinc-300">{{ activeDossier.dialogue_stats.words_spoken }}</strong></span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <CastRelationships />

      <div class="border-t border-zinc-800 pt-3 flex justify-between items-center shrink-0">
        <span class="text-[10px] text-zinc-500 font-mono">100% Deterministic Story Architecture</span>
        <button @click="closeModal" class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition">Done</button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, showToast } from '../../store.js'
import { Users, X, Trash2, Plus, Loader } from '@lucide/vue'

import { API_BASE } from '@/api'
import CastRelationships from './CastRelationships.vue'

const activeDossier = ref(null)
const isDossierLoading = ref(false)

const newEntity = ref({
  name: '',
  entity_type: 'CHARACTER'
})

const parseAliasList = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value
  try {
    const parsed = JSON.parse(value)
    if (Array.isArray(parsed)) return parsed
  } catch {}
  return value.split(/[,;\n|]+/).map(a => a.trim()).filter(Boolean)
}

const displayedEntities = computed(() => store.registeredEntities || [])

const closeModal = () => {
  store.toggleModal('cast', false)
  activeDossier.value = null
}

const toggleDossier = async (entityId) => {
  if (activeDossier.value?.entity_id === entityId) {
    activeDossier.value = null
    return
  }
  isDossierLoading.value = true
  activeDossier.value = { entity_id: entityId }
  try {
    const res = await fetch(`${API_BASE}/api/entities/${encodeURIComponent(entityId)}/dossier`)
    if (!res.ok) throw new Error('Could not compile dossier')
    activeDossier.value = await res.json()
  } catch(e) {
    showToast(e.message, 'error')
    activeDossier.value = null
  } finally {
    isDossierLoading.value = false
  }
}

const createEntity = async () => {
  const name = newEntity.value.name.trim()
  if (!name) return

  try {
    const res = await fetch(`${API_BASE}/api/entities/quick-register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, entity_type: newEntity.value.entity_type })
    })
    if (!res.ok) throw new Error('Registration failed')
    newEntity.value.name = ''
    await store.fetchCast()
    showToast(`Tracked "${name}"`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}

const deleteEntity = async (eid) => {
  try {
    const res = await fetch(`${API_BASE}/api/entities/${eid}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Deletion failed')
    await store.fetchCast()
    if (activeDossier.value?.entity_id === eid) activeDossier.value = null
  } catch(e) {
    showToast('Failed to delete entity', 'error')
  }
}
</script>
