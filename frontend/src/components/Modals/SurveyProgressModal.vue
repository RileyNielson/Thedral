<template>
  <div class="fixed inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center z-50 p-4">
    <div class="bg-zinc-900 border border-amber-500/40 rounded-2xl max-w-md w-full p-6 text-center space-y-4 shadow-2xl">
      <h3 class="text-base font-bold text-white tracking-wide">Surveying Story Universe</h3>
      <div class="w-full bg-zinc-950 h-3 rounded-full overflow-hidden p-0.5 border border-zinc-800">
        <div class="bg-gradient-to-r from-amber-600 to-amber-400 h-full rounded-full transition-all duration-300" :style="{ width: store.surveyProgress.percent + '%' }"></div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { store } from '../../store.js'
</script>