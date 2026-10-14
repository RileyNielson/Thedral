import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { store, showToast } from '../../store.js'
import { API_BASE } from '@/api'

export function useInspectorState() {

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
      { key: 'experience-moments', items: analysis.experience_moments || [] },
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
      store.socraticAi = !!data.ai_generated
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

  return {
    analyticsError,
    analyticsLoading,
    analyticsPosition,
    askTutor,
    canSaveFeedback,
    cardData,
    chapterSummary,
    elevateMacroScene,
    feedbackForm,
    feedbackRatings,
    fetchCritiques,
    forceSave,
    formatRevisionTime,
    getPlotly,
    handleScrollBeat,
    isLensLoading,
    isScanning,
    isTutorThinking,
    jumpToStoryEvidence,
    loadManuscriptAnalytics,
    loadReaderFeedback,
    loadReaderSimulations,
    loadReaderStoryAnalysis,
    loopSignal,
    manuscriptAnalytics,
    manuscriptPatternComparisons,
    manuscriptPeers,
    median,
    nextSceneAnalytics,
    openLensTab,
    otherObservationCategories,
    plainSceneContent,
    previousSceneAnalytics,
    readTimeRange,
    readerExperienceDimensions,
    readerExperienceItems,
    readerFeedback,
    readerFeedbackGroups,
    readerFeedbackSummary,
    readerLevelLabel,
    readerStoryAnalysis,
    readerStoryError,
    readerStoryGroups,
    readerStoryLoading,
    readingMode,
    removeReaderFeedback,
    renderMiniAstrolabe,
    resolveCritique,
    restoreRevision,
    revisionComparison,
    saveReaderFeedback,
    scanHorizon,
    sceneLengthComparison,
    scrivenerMetadataFields,
    scrivenerMetadataText,
    selectedRevisionVersion,
    selectedSceneAnalytics,
    selectedSimulation,
    selectedSimulationId,
    simulationComparison,
    simulationHistory,
    simulationItems,
    sprintProgress,
    tutorQuestion,
    writableTarget
  }
}
