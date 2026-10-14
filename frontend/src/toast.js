import { reactive } from 'vue'

// --- Toast System ---
export const toasts = reactive([])

export const showToast = (msg, type = 'error') => {
  const id = Date.now() + Math.random()
  toasts.push({ id, msg, type })
  setTimeout(() => {
    const idx = toasts.findIndex(t => t.id === id)
    if (idx > -1) toasts.splice(idx, 1)
  }, 5000)
}
