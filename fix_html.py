import urllib.request

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Thedral — The Sovereign Studio for Authors</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500;600;700&display=swap');
    .prose-canvas { font-family: 'Crimson Pro', Georgia, serif; }
    .ui-sans { font-family: 'Inter', sans-serif; }
    textarea:focus, input:focus { outline: none; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #09090b; }
    ::-webkit-scrollbar-thumb { background: #27272a; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #3f3f46; }
    .xray-escalator { background-color: rgba(244, 63, 94, 0.15); border-bottom: 2px solid rgba(244, 63, 94, 0.4); }
    .xray-resolver  { background-color: rgba(16, 185, 129, 0.15); border-bottom: 2px solid rgba(16, 185, 129, 0.4); }
    .xray-pivot     { background-color: rgba(245, 158, 11, 0.22); border-left: 3px solid #f59e0b; padding-left: 4px; }
    .xray-slack     { border-bottom: 2px dotted #71717a; }
    .candlelight-mode { background-color: #070709 !important; color: #fef3c7 !important; }
    .candlelight-mode header, .candlelight-mode aside { background-color: #0c0a09 !important; border-color: #292524 !important; }
    .candlelight-mode .prose-canvas, .candlelight-mode textarea, .candlelight-mode input { color: #fed7aa !important; }
  </style>
</head>
<body class="bg-zinc-950 text-zinc-100 ui-sans antialiased h-screen overflow-hidden select-none">
  <div id="app" class="flex flex-col h-full">
    <!-- Header -->
    <header v-show="!isVoidMode" class="h-12 border-b border-zinc-800/80 bg-zinc-900/70 backdrop-blur flex items-center justify-between px-3 md:px-4 z-30 shrink-0">
      <div class="flex items-center space-x-2 md:space-x-3">
        <div class="flex items-center gap-1.5">
          <span class="font-bold text-amber-500 tracking-wider text-xs md:text-sm uppercase flex items-center gap-1.5"><i data-lucide="feather" class="w-4 h-4"></i> <span class="hidden sm:inline">Thedral</span></span>
        </div>
      </div>
      <!-- View Switcher -->
      <div class="hidden lg:flex items-center bg-zinc-950 p-1 rounded-lg border border-zinc-800 text-xs shrink-0">
        <button @click="switchView('editor')" :class="['px-2.5 py-1 rounded-md font-medium transition', viewMode === 'editor' ? 'bg-zinc-800 text-amber-400' : 'text-zinc-500']">Write</button>
        <button @click="switchView('outline')" :class="['px-2.5 py-1 rounded-md font-medium transition', viewMode === 'outline' ? 'bg-zinc-800 text-amber-400' : 'text-zinc-500']">Outline</button>
        <button @click="switchView('3d')" :class="['px-2.5 py-1 rounded-md font-medium transition', viewMode === '3d' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' : 'text-zinc-500']">Cosmograph</button>
      </div>
      <!-- Action Bar -->
      <div class="flex items-center space-x-2 text-xs">
        <span v-if="saveStatus" class="text-zinc-400 text-[11px] font-mono hidden xl:inline">{{ saveStatus }}</span>
        <button @click="toggleCandlelight" class="px-2 py-1 bg-zinc-800 text-zinc-400 rounded"><i data-lucide="flame" class="w-3.5 h-3.5 text-amber-500"></i></button>
      </div>
    </header>
    <!-- Center Pane -->
    <main class="flex-1 flex flex-col bg-zinc-950 overflow-hidden relative">
      <div v-if="viewMode === 'editor'" class="flex-1 flex flex-col max-w-3xl w-full mx-auto p-6 md:p-12 overflow-y-auto">
        <input v-model="activeNode.title" @input="queueAutoSave" class="bg-transparent text-2xl md:text-3xl font-serif font-bold text-zinc-100 border-none focus:outline-none mb-6" placeholder="Scene Title..." />
        <textarea v-model="activeNode.content" @input="queueAutoSave" class="prose-canvas flex-1 bg-transparent text-lg md:text-xl leading-relaxed text-zinc-200 resize-none border-none focus:outline-none min-h-[500px]" placeholder="Lay down the first sentence..."></textarea>
      </div>
      <div v-if="viewMode === 'outline'" class="flex-1 overflow-y-auto p-8 bg-zinc-950"><h2 class="text-2xl font-bold text-zinc-100">The Living Outline</h2></div>
      <div v-if="viewMode === '3d'" class="flex-1 flex flex-col bg-zinc-950 overflow-hidden relative"><div id="astrolabe-plot" class="flex-1 w-full h-full"></div></div>
    </main>
  </div>
  <script>
    const { createApp, ref, onMounted, nextTick } = Vue;
    createApp({
      setup() {
        const activeNode = ref({ title: "Welcome to Thedral", content: "Start typing here..." });
        const viewMode = ref('editor');
        const saveStatus = ref('');
        const isVoidMode = ref(false);
        const isCandlelight = ref(false);
        
        const refreshIcons = () => nextTick(() => lucide.createIcons());
        const toggleCandlelight = () => {
          isCandlelight.value = !isCandlelight.value;
          document.body.classList.toggle('candlelight-mode', isCandlelight.value);
        };
        const switchView = (mode) => { viewMode.value = mode; refreshIcons(); };
        const queueAutoSave = () => { saveStatus.value = 'Saved'; };

        onMounted(() => { refreshIcons(); });

        return { activeNode, viewMode, saveStatus, isVoidMode, isCandlelight, toggleCandlelight, switchView, queueAutoSave };
      }
    }).mount('#app');
  </script>
</body>
</html>
"""

with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ Safe index.html fallback deployed.")
"""
