<template>
  <div 
    v-if="store.modals.connect" 
    class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 select-none" 
    @click.self="closeModal"
  >
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-sm w-full p-6 text-center space-y-5 shadow-2xl animate-fade-in">
      
      <!-- Icon Header -->
      <div class="flex items-center justify-between">
        <div class="w-10 h-10 bg-amber-500/10 text-amber-500 rounded-full flex items-center justify-center border border-amber-500/20">
          <Smartphone class="w-5 h-5" />
        </div>
        <button @click="closeModal" class="text-zinc-500 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Title & Explanation -->
      <div class="text-left space-y-1">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          Mobile PWA Bridge
        </h3>
        <p class="text-xs text-zinc-400 leading-relaxed">
          Ensure your phone is on the same Wi-Fi, then scan this QR code with your camera:
        </p>
      </div>

      <!-- Live Scannable QR Code -->
      <div class="p-4 bg-white rounded-xl mx-auto w-48 h-48 flex items-center justify-center shadow-lg border border-zinc-700">
        <img 
          :src="qrCodeUrl" 
          alt="Scan with camera" 
          class="w-full h-full object-contain"
        />
      </div>

      <!-- LAN URL Display Box -->
      <div class="p-3 bg-zinc-950 rounded-lg font-mono text-amber-400 text-xs select-all border border-zinc-800 flex items-center justify-between gap-2 shadow-inner">
        <span class="truncate">{{ targetUrl }}</span>
        <button 
          @click="copyUrl" 
          title="Copy URL" 
          class="p-1 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 rounded transition shrink-0"
        >
          <Copy class="w-4 h-4" />
        </button>
      </div>

      <!-- Instructions for Fullscreen PWA -->
      <p class="text-[11px] text-zinc-500 font-mono leading-normal">
        💡 <strong>Pro-Tip:</strong> In Safari on your phone, tap <strong>Share</strong> ❯ <strong>Add to Home Screen</strong> to run Thedral as a distraction-free fullscreen app.
      </p>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { store, showToast } from '../../store.js'
import { Smartphone, X, Copy } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const networkInfo = ref({
  local_ip: window.location.hostname || 'localhost',
  port: window.location.port || 5173
})

// Points to the frontend port so your phone loads the UI
const targetUrl = computed(() => {
  const host = (networkInfo.value.local_ip === 'localhost' || networkInfo.value.local_ip === '127.0.0.1')
    ? window.location.hostname
    : networkInfo.value.local_ip
  return `http://${host}:${window.location.port || 5173}`
})

// Zero-dependency SVG QR Code generator endpoint
const qrCodeUrl = computed(() => {
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(targetUrl.value)}`
})

const closeModal = () => {
  store.toggleModal('connect', false)
}

const fetchNetworkInfo = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/network_info`)
    if (res.ok) {
      const data = await res.json()
      if (data.local_ip && data.local_ip !== 'localhost') {
        networkInfo.value.local_ip = data.local_ip
      }
    }
  } catch(e) {
    console.warn('[Thedral Network Info]', e)
  }
}

const copyUrl = async () => {
  try {
    await navigator.clipboard.writeText(targetUrl.value)
    showToast('Mobile URL copied to clipboard!', 'info')
  } catch(e) {
    showToast('Failed to copy', 'error')
  }
}

watch(() => store.modals.connect, (isOpen) => {
  if (isOpen) fetchNetworkInfo()
})

onMounted(() => {
  if (store.modals.connect) fetchNetworkInfo()
})
</script>