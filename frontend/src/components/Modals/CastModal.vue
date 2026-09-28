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
            {{ store.registeredEntities?.length || 0 }} registered
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
            <option value="ITEM">Artifact / Relic</option>
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

      <!-- Filter Tabs -->
      <div class="flex items-center space-x-2 text-xs font-mono shrink-0">
        <button 
          @click="activeFilter = 'ALL'"
          :class="['px-2.5 py-1 rounded transition', activeFilter === 'ALL' ? 'bg-zinc-800 text-amber-400' : 'text-zinc-500 hover:text-zinc-300']"
        >
          All ({{ store.registeredEntities?.length || 0 }})
        </button>
        <button 
          @click="activeFilter = 'CHARACTER'"
          :class="['px-2.5 py-1 rounded transition', activeFilter === 'CHARACTER' ? 'bg-zinc-800 text-amber-400' : 'text-zinc-500 hover:text-zinc-300']"
        >
          Characters ({{ characterCount }})
        </button>
        <button 
          @click="activeFilter = 'ITEM'"
          :class="['px-2.5 py-1 rounded transition', activeFilter === 'ITEM' ? 'bg-zinc-800 text-cyan-400' : 'text-zinc-500 hover:text-zinc-300']"
        >
          Artifacts ({{ itemCount }})
        </button>
      </div>

      <!-- Entity Directory List -->
      <div class="flex-1 overflow-y-auto space-y-2 p-1 custom-scrollbar">
        <div 
          v-for="ent in filteredEntities" 
          :key="ent.entity_id" 
          class="p-3 bg-zinc-950 border border-zinc-800/80 hover:border-zinc-700 rounded-xl flex items-center justify-between transition group"
        >
          <div class="truncate mr-3">
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
            </div>
            <div v-if="ent.aliases" class="text-[10px] text-zinc-500 truncate mt-0.5 font-mono">
              Aliases: {{ ent.aliases }}
            </div>
          </div>

          <button 
            @click="deleteEntity(ent.entity_id)" 
            title="Untrack Entity"
            class="p-1.5 hover:bg-zinc-800 text-zinc-600 hover:text-rose-400 rounded transition opacity-40 group-hover:opacity-100"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>

        <div v-if="!filteredEntities.length" class="text-center py-10 text-xs text-zinc-500 italic">
          No tracked entities match this perspective.
        </div>
      </div>

      <!-- Footer -->
      <div class="border-t border-zinc-800 pt-3 flex justify-between items-center shrink-0">
        <span class="text-[10px] text-zinc-500 font-mono">Synchronized with 3D Cosmograph</span>
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
import { Users, X, Trash2, Plus } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const activeFilter = ref('ALL')
const newEntity = ref({
  name: '',
  entity_type: 'CHARACTER'
})

const characterCount = computed(() => 
  (store.registeredEntities || []).filter(e => e.entity_type === 'CHARACTER').length
)
const itemCount = computed(() => 
  (store.registeredEntities || []).filter(e => e.entity_type === 'ITEM').length
)

const filteredEntities = computed(() => {
  const list = store.registeredEntities || []
  if (activeFilter.value === 'ALL') return list
  return list.filter(e => e.entity_type === activeFilter.value)
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
        entity_type: newEntity.value.entity_type
      })
    })
    if (!res.ok) throw new Error('Registration failed')
    newEntity.value.name = ''
    await fetchEntities()
    showToast(`Tracked "${name}" (${newEntity.value.entity_type})`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
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