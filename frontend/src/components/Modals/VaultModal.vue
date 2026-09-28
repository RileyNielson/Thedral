<template>
  <div 
    v-if="store.modals.vault" 
    class="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none" 
    @click.self="store.modals.vault = false"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-xl w-full p-6 space-y-5 shadow-2xl flex flex-col max-h-[85vh] animate-fade-in">
      
      <!-- Modal Header -->
      <div class="flex items-center justify-between border-b border-zinc-800 pb-3 shrink-0">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <Library class="w-5 h-5 text-amber-500" /> The Library Vault
        </h3>
        <button @click="store.modals.vault = false" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Book List -->
      <div class="max-h-72 overflow-y-auto space-y-2.5 p-1 custom-scrollbar">
        <div 
          v-for="b in store.vaultBooks" 
          :key="b.id" 
          class="p-3.5 bg-zinc-950 border border-zinc-800 rounded-xl flex items-center justify-between group hover:border-zinc-700 transition"
        >
          <div class="truncate mr-4">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-bold text-zinc-100 truncate">{{ b.title }}</span>
              <span 
                :class="[
                  'px-2 py-0.5 rounded text-[10px] font-mono', 
                  b.is_archived ? 'bg-zinc-800 text-zinc-400' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                ]"
              >
                {{ b.is_archived ? 'Archived' : 'Active' }}
              </span>
            </div>

            <div class="text-xs text-zinc-500 font-mono flex gap-3">
              <span>{{ b.chapter_count || 0 }} Chapters</span>
              <span>•</span>
              <span>{{ (b.total_words || 0).toLocaleString() }} Words</span>
            </div>
          </div>

          <div class="flex items-center space-x-2 shrink-0">
            <button 
              @click="toggleBook(b)" 
              :class="[
                'px-3 py-1.5 rounded-lg text-xs font-semibold transition', 
                b.is_archived ? 'bg-amber-600 hover:bg-amber-500 text-zinc-950 font-bold shadow' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
              ]"
            >
              {{ b.is_archived ? 'Open in Binder' : 'Close Book' }}
            </button>
            <button 
              @click="deleteBook(b)" 
              title="Delete Book"
              class="p-1.5 hover:bg-zinc-800 text-zinc-600 hover:text-rose-400 rounded transition opacity-50 group-hover:opacity-100"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div v-if="!store.vaultBooks?.length" class="text-center py-10 text-xs text-zinc-500 italic">
          No manuscripts found in the vault.
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="border-t border-zinc-800 pt-3 flex justify-between items-center text-xs text-zinc-500 font-mono shrink-0">
        <span>Archived manuscripts remain safe on disk.</span>
        <button 
          @click="store.modals.vault = false" 
          class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition"
        >
          Done
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { Library, X, Trash2 } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const fetchVault = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/vault/books`)
    if (res.ok) {
      store.vaultBooks = await res.json()
    }
  } catch(e) {
    store.vaultBooks = []
  }
}

const toggleBook = async (b) => {
  try {
    const res = await fetch(`${API_BASE}/api/vault/${b.id}/toggle`, { method: 'POST' })
    if (!res.ok) throw new Error('Failed to toggle book')
    if (store.activeNode?.book_id === b.id || store.activeNode?.id === b.id) {
      store.activeNode = null
    }
    window.dispatchEvent(new Event('refresh-tree'))
    await fetchVault()
    showToast(`Updated "${b.title}"`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}

const deleteBook = async (b) => {
  if (!window.confirm(`Permanently delete "${b.title}"? This cannot be undone.`)) return
  try {
    const res = await fetch(`${API_BASE}/api/node/${b.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Failed to delete book')
    if (store.activeNode?.book_id === b.id || store.activeNode?.id === b.id) {
      store.activeNode = null
    }
    window.dispatchEvent(new Event('refresh-tree'))
    await fetchVault()
    showToast(`Deleted "${b.title}"`, 'info')
  } catch(e) {
    showToast(e.message, 'error')
  }
}

watch(() => store.modals.vault, (isOpen) => {
  if (isOpen) fetchVault()
})

onMounted(() => {
  fetchVault()
})
</script>