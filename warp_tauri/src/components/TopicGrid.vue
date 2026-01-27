<template>
  <div class="topic-grid" :style="{ '--hue': hueShift }" :class="[`density-${viewDensity}`, orientationClass]">
    <!-- macOS Traffic Lights (only in Tauri) -->
    <div v-if="isTauri" class="traffic-lights" data-tauri-drag-region>
      <button class="traffic-light close" @click="closeWindow" title="Close">
        <svg viewBox="0 0 12 12"><path d="M3.5 3.5l5 5m0-5l-5 5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
      </button>
      <button class="traffic-light minimize" @click="minimizeWindow" title="Minimize">
        <svg viewBox="0 0 12 12"><path d="M2.5 6h7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
      </button>
      <button class="traffic-light maximize" @click="toggleMaximize" title="Maximize">
        <svg viewBox="0 0 12 12"><path d="M3 3h6v6H3z" stroke="currentColor" stroke-width="1" fill="none"/></svg>
      </button>
    </div>

    <!-- Activity Ticker (when there's activity to show) -->
    <div class="activity-ticker" v-if="recentActivity.length > 0 && !globalChatActive">
      <TransitionGroup name="ticker">
        <span v-for="activity in recentActivity.slice(0, 3)" :key="activity.id" class="ticker-item">
          <span class="ticker-icon">{{ activity.icon }}</span>
          <span class="ticker-text">{{ activity.text }}</span>
          <span class="ticker-time">{{ activity.time }}</span>
        </span>
      </TransitionGroup>
    </div>

    <div v-show="!globalChatActive" class="grid-container" ref="gridContainer" :class="`grid-${viewDensity}`">
        <!-- Expanded Project Panel -->
        <Transition name="expand" mode="out-in">
          <ProjectPanel
            v-if="expandedProject"
            :project="expandedProject"
            @close="$emit('collapse-project')"
            @approve-task="handleApproveTask"
            @approve-all="handleApproveAll"
            @open-chat="toggleChatMode(expandedProject.id)"
            @delete-project="handleDeleteProject"
          />
        </Transition>

      <!-- Project Widgets - Compact List Style -->
      <template v-if="!expandedProjectId">
        <div
          v-for="project in filteredProjects"
          :key="project.id"
          class="widget-row"
          :class="getCardClass(project)"
          @click="$emit('expand-project', project.id)"
        >
          <!-- Animated Icon (Apple-style Lottie) -->
          <div class="widget-icon">
            <AnimatedEmoji
              :emoji="project.icon"
              :state="getEmojiState(project)"
              :size="36"
            />
          </div>

          <!-- Main content -->
          <div class="widget-content">
            <div class="widget-title">{{ project.name }}</div>
            <div class="widget-subtitle">{{ getLastActivity(project) }}</div>
          </div>

          <!-- Stats with micro-animations -->
          <div class="widget-stats">
            <!-- Active tasks with pulse -->
            <span class="stat" v-if="project.runningTasks?.length">
              <span class="stat-num active pulse-gentle">{{ project.runningTasks.length }}</span>
              <span class="stat-label">active</span>
            </span>
            <!-- Pending tasks with subtle attention -->
            <span class="stat" v-if="project.suggestedTasks?.length">
              <span class="stat-num count-up">{{ project.suggestedTasks.length }}</span>
              <span class="stat-label">tasks</span>
            </span>
            <!-- Progress ring -->
            <span class="stat progress-stat">
              <svg class="progress-ring" viewBox="0 0 24 24">
                <circle class="progress-ring-bg" cx="12" cy="12" r="10" />
                <circle
                  class="progress-ring-fill"
                  cx="12" cy="12" r="10"
                  :style="{ strokeDashoffset: 63 - (63 * getProgress(project) / 100) }"
                />
              </svg>
              <span class="progress-text">{{ getProgress(project) }}</span>
            </span>
          </div>

          <!-- Quick actions -->
          <div class="widget-actions" @click.stop>
            <button
              v-if="getPendingDecisions(project) > 0"
              class="widget-btn approve"
              @click="quickApprove(project)"
            >
              ✓
            </button>
            <button class="widget-btn" @click="askAboutProject(project)">💬</button>
          </div>
        </div>

        <!-- Add widget -->
        <div class="widget-row add-widget" @click="$emit('add-project')">
          <span class="widget-icon">+</span>
          <div class="widget-content">
            <div class="widget-title add-title">New Project</div>
            <span class="add-hint">Click to create</span>
          </div>
        </div>
      </template>
    </div>

    <!-- Empty state -->
    <div v-if="!filteredProjects.length && !expandedProjectId && !globalChatActive" class="empty">
      <span class="empty-icon">🔍</span>
      <span>No matches for "{{ searchQuery }}"</span>
    </div>

    <!-- Global Chat Area (expands from bottom when active) -->
    <Transition name="chat-expand">
      <div v-if="globalChatActive" class="global-chat-area" ref="globalChatRef">
        <div class="chat-messages">
          <div v-for="msg in globalMessages" :key="msg.id" class="chat-msg" :class="msg.role">
            <div class="msg-content">{{ msg.content }}</div>
            <div v-if="msg.actions && msg.actions.length > 0" class="msg-actions">
              <button
                v-for="(action, idx) in msg.actions"
                :key="idx"
                @click="executeAction(action)"
                class="action-btn"
              >
                {{ action.label }}
              </button>
            </div>
          </div>
          <div v-if="globalThinking" class="chat-msg assistant">
            <div class="msg-content thinking">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
          <div v-if="!globalMessages.length && !globalThinking" class="chat-welcome">
            <div class="welcome-icon">🤖</div>
            <div class="welcome-text">Ask me anything</div>
            <div class="welcome-hints">
              <button @click="setGlobalInput('What can you help me with?')">What can you help me with?</button>
              <button @click="setGlobalInput('Show my progress')">Show my progress</button>
              <button @click="setGlobalInput('Daily brief')">Daily brief</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Bottom Bar - Transforms between search and chat input -->
    <div class="bottom-bar" :class="{ 'chat-active': globalChatActive }">
      <!-- Back button (when in chat) -->
      <Transition name="fade">
        <button v-if="globalChatActive" class="back-btn" @click="closeGlobalChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
      </Transition>

      <!-- Input area -->
      <div class="input-area">
        <input
          ref="globalInputRef"
          v-model="globalInput"
          type="text"
          :placeholder="globalChatActive ? 'Message SAM...' : 'Search or ask SAM...'"
          @focus="activateGlobalChat"
          @keydown.enter="sendGlobalMessage"
          @keydown.escape="closeGlobalChat"
        />
        <Transition name="fade">
          <button v-if="globalInput && globalInput.trim()" class="send-btn" @click="sendGlobalMessage">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
            </svg>
          </button>
        </Transition>
      </div>

      <!-- Right side controls (hide when typing) -->
      <Transition name="fade">
        <div v-if="!globalChatActive" class="bar-controls">
          <button class="nav-btn" @click="showDailyBrief" title="Daily Brief">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="4" width="18" height="18" rx="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span v-if="hasBriefUpdate" class="notify-dot"></span>
          </button>
          <button class="nav-btn" @click="showProgress" title="Progress">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span v-if="streakDays > 0" class="streak-pip">{{ streakDays }}</span>
          </button>
          <div class="bar-stats">
            <span v-if="totalPendingDecisions > 0" class="stat-pill urgent">{{ totalPendingDecisions }}</span>
            <span v-if="activeTaskCount > 0" class="stat-pill active">{{ activeTaskCount }}</span>
          </div>
          <button class="privacy-btn" :class="{ private: privateMode }" @click="togglePrivateMode">
            <svg v-if="!privateMode" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
              <path d="M1 1l22 22" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { useProjectStore, type Project } from '../stores/projectStore'

// === WINDOW CONTROLS (Tauri only) ===
const isTauri = ref(typeof window !== 'undefined' && '__TAURI__' in window)

async function closeWindow() {
  if (!isTauri.value) return
  const { appWindow } = await import('@tauri-apps/api/window')
  await appWindow.close()
}

async function minimizeWindow() {
  if (!isTauri.value) return
  const { appWindow } = await import('@tauri-apps/api/window')
  await appWindow.minimize()
}

async function toggleMaximize() {
  if (!isTauri.value) return
  const { appWindow } = await import('@tauri-apps/api/window')
  await appWindow.toggleMaximize()
}

const ProjectPanel = defineAsyncComponent(() => import('./ProjectPanel.vue'))
import AnimatedEmoji from './AnimatedEmoji.vue'

const props = defineProps<{
  searchQuery: string
  expandedProjectId: string | null
  viewMode?: 'projects' | 'chats'
}>()

const emit = defineEmits<{
  (e: 'expand-project', id: string): void
  (e: 'collapse-project'): void
  (e: 'approve-task', task: any): void
  (e: 'approve-all', id: string): void
  (e: 'open-chat', id: string, name: string): void
  (e: 'add-project'): void
  (e: 'delete-project', id: string): void
  (e: 'search', query: string): void
}>()

const projectStore = useProjectStore()

// === COLOR THEME ===
const hueShift = ref(parseInt(localStorage.getItem('sam_hue') || '200'))
// Save on change
function updateHue(e: Event) {
  const val = (e.target as HTMLInputElement).value
  hueShift.value = parseInt(val)
  localStorage.setItem('sam_hue', val)
}

// === ECO IMPACT SYSTEM ===
// Tracking water/carbon savings from local AI vs cloud
const ecoStats = reactive({
  localQueries: parseInt(localStorage.getItem('sam_local_queries') || '0'),
  cloudQueries: parseInt(localStorage.getItem('sam_cloud_queries') || '0'),
  waterSavedMl: parseInt(localStorage.getItem('sam_water_saved') || '0'), // ml water saved
  efficiencyGains: parseInt(localStorage.getItem('sam_efficiency_gains') || '0'), // cumulative % savings
})
const waterJustSaved = ref(false)

// Water consumption: Cloud ~0.5L per query (cooling data centers), Local ~0.02L per query (home power)
const WATER_SAVED_PER_LOCAL_QUERY = 480 // ml saved vs cloud (0.5L - 0.02L)

const localRatio = computed(() => {
  const total = ecoStats.localQueries + ecoStats.cloudQueries
  return total > 0 ? Math.round((ecoStats.localQueries / total) * 100) : 100
})

const waterSavedLiters = computed(() => (ecoStats.waterSavedMl / 1000).toFixed(1))

function trackLocalQuery(isLocal = true) {
  if (isLocal) {
    ecoStats.localQueries++
    ecoStats.waterSavedMl += WATER_SAVED_PER_LOCAL_QUERY
    localStorage.setItem('sam_local_queries', ecoStats.localQueries.toString())
    localStorage.setItem('sam_water_saved', ecoStats.waterSavedMl.toString())
    waterJustSaved.value = true
    setTimeout(() => waterJustSaved.value = false, 500)
  } else {
    ecoStats.cloudQueries++
    localStorage.setItem('sam_cloud_queries', ecoStats.cloudQueries.toString())
  }
}

function trackEfficiencyGain(percentSaved: number) {
  ecoStats.efficiencyGains += percentSaved
  localStorage.setItem('sam_efficiency_gains', ecoStats.efficiencyGains.toString())
}

// === ORIENTATION DETECTION ===
const isPortrait = ref(window.innerHeight > window.innerWidth)
const isMobile = ref(window.innerWidth < 500)
const isWallpaper = ref(window.innerWidth < 430 || (window.innerHeight / window.innerWidth > 1.8))
const orientationClass = computed(() => ({
  'portrait': isPortrait.value,
  'landscape': !isPortrait.value,
  'mobile': isMobile.value,
  'wallpaper': isWallpaper.value
}))

function updateOrientation() {
  isPortrait.value = window.innerHeight > window.innerWidth
  isMobile.value = window.innerWidth < 500
  // iPhone 16 Pro Max: 430x932 in portrait
  isWallpaper.value = window.innerWidth < 430 || (window.innerHeight / window.innerWidth > 1.8)
}

onMounted(() => window.addEventListener('resize', updateOrientation))
onUnmounted(() => window.removeEventListener('resize', updateOrientation))

// === VIEW DENSITY (Apple Photos-style) ===
type ViewDensity = 'compact' | 'regular' | 'focus'
const viewDensity = ref<ViewDensity>(
  (localStorage.getItem('sam_view_density') as ViewDensity) || 'regular'
)

// Persist view preference
function setViewDensity(density: ViewDensity) {
  viewDensity.value = density
  localStorage.setItem('sam_view_density', density)
}

// Auto-adjust density based on topic count (like smart folders)
const autoAdjustedDensity = computed(() => {
  const count = filteredProjects.value.length
  if (count > 12) return 'compact'
  if (count <= 3) return 'focus'
  return 'regular'
})

// === GLOBAL STATS (always visible context) ===
const totalPendingDecisions = computed(() => {
  return (filteredProjects.value || []).reduce((sum, p) => {
    return sum + (p.suggestedTasks?.filter(t => t.needsApproval)?.length || 0)
  }, 0)
})

const activeTaskCount = computed(() => {
  return (filteredProjects.value || []).reduce((sum, p) => {
    return sum + (p.runningTasks?.length || 0)
  }, 0)
})

const healthyCount = computed(() => {
  return (filteredProjects.value || []).filter(p => p.status === 'healthy' || !p.status).length
})

// === RECENT ACTIVITY FEED ===
interface Activity {
  id: string
  icon: string
  text: string
  time: string
  projectId: string
}

const recentActivity = computed<Activity[]>(() => {
  const activities: Activity[] = []

  for (const project of (filteredProjects.value || [])) {
    // Running tasks
    for (const task of (project.runningTasks || [])) {
      const taskName = task.description || task.name || 'Running'
      activities.push({
        id: `${project.id}-task-${task.id}`,
        icon: '⚡',
        text: `${project.name}: ${taskName}`,
        time: 'now',
        projectId: project.id
      })
    }

    // Pending decisions (most important)
    const pending = project.suggestedTasks?.filter(t => t.needsApproval) || []
    if (pending.length > 0) {
      activities.push({
        id: `${project.id}-decisions`,
        icon: '🔔',
        text: `${project.name}: ${pending.length} pending`,
        time: 'waiting',
        projectId: project.id
      })
    }

    // Recent messages
    const msgs = getMessagesForDisplay(project.id)
    if (msgs.length > 0) {
      const last = msgs[msgs.length - 1]
      activities.push({
        id: `${project.id}-msg-${msgs.length}`,
        icon: last.role === 'user' ? '💬' : '🤖',
        text: `${project.name}: ${last.content.slice(0, 30)}...`,
        time: 'recent',
        projectId: project.id
      })
    }
  }

  return activities.slice(0, 5) // Top 5 most relevant
})

// === CAROUSEL ROTATION ===
const carouselIndex = reactive<Record<string, number>>({})
onMounted(() => {
  // Update streak counter
  updateStreak()
})

onUnmounted(() => {
  // Cleanup if needed
})

// === CHAT MODE ===
const chatModeProjects = reactive<Record<string, boolean>>({})
const inputMap = reactive<Record<string, string>>({})
const thinkingMap = reactive<Record<string, boolean>>({})
const chatRefs = reactive<Record<string, HTMLElement | null>>({})

// Track which cards have expanded chat (focus-based)
const expandedChats = reactive<Record<string, boolean>>({})

// Check if chat is expanded (input focused or has messages being typed)
function isChatExpanded(id: string): boolean {
  return expandedChats[id] || props.viewMode === 'chats' || thinkingMap[id]
}

// Legacy function for compatibility
function isInChatMode(id: string): boolean {
  return isChatExpanded(id)
}

function toggleChatMode(id: string) {
  expandedChats[id] = !expandedChats[id]
}

// Expand chat when input is focused
function expandChat(id: string) {
  expandedChats[id] = true
}

function setChatRef(id: string, el: any) {
  if (el) chatRefs[id] = el
}

function getMessages(id: string) {
  return projectStore.getProjectChat(id)
}

// Local messages for private mode (not persisted)
const privateMessages = reactive<Record<string, Array<{ id: string; role: string; content: string }>>>({})

// Get messages - from store or private local state
function getMessagesForDisplay(id: string) {
  if (privateMode.value) {
    return privateMessages[id] || []
  }
  return projectStore.getProjectChat(id)
}

// Collapse chat when input loses focus (with delay to allow button clicks)
function maybeCollapseChat(id: string) {
  setTimeout(() => {
    // Don't collapse if there's text being typed or thinking
    if (inputMap[id]?.trim() || thinkingMap[id]) return
    // Don't collapse if there are messages (keep conversation visible)
    if (getMessagesForDisplay(id).length > 0) return
    expandedChats[id] = false
  }, 200)
}

// === CONTEXTUAL HELPERS ===

// Get last activity description
function getLastActivity(project: Project): string {
  if (project.runningTasks?.length) return `${project.runningTasks.length} running`
  const msgs = getMessagesForDisplay(project.id)
  if (msgs.length) {
    const last = msgs[msgs.length - 1]
    const preview = last.content.slice(0, 20)
    return preview + (last.content.length > 20 ? '...' : '')
  }
  return project.status || 'Ready'
}

// Get pending decisions count
function getPendingDecisions(project: Project): number {
  return project.suggestedTasks?.filter(t => t.needsApproval)?.length || 0
}

// Show decisions panel
function showDecisions(id: string) {
  // Emit to open project panel in decisions mode
  emit('expand-project', id)
}

// Get contextual placeholder for input
function getInputPlaceholder(project: Project): string {
  const decisions = getPendingDecisions(project)
  if (decisions > 0) return `${decisions} decision${decisions > 1 ? 's' : ''} waiting...`
  if (project.runningTasks?.length) return 'Check status...'
  return 'Ask anything...'
}

// Get quick action hint based on project state
function getQuickAction(project: Project): string | null {
  const decisions = getPendingDecisions(project)
  if (decisions > 0) return `⚡ ${decisions} to approve`
  if (project.runningTasks?.length) return `🔄 ${project.runningTasks.length} in progress`
  const incomplete = (project.goals?.length || 0) - getCompletedGoals(project)
  if (incomplete > 0) return `📋 ${incomplete} goals remaining`
  return null
}

// Get contextual prompt suggestion
function getQuickPrompt(project: Project): string {
  const prompts: Record<string, string> = {
    'stash': 'Try: "scan for new content"',
    'music': 'Try: "import new albums"',
    'sam': 'Try: "what can you do?"',
    'rvc': 'Try: "check training status"',
    'comfy': 'Try: "generate an image"',
    'ssot': 'Try: "sync all projects"',
    'cloudflare': 'Try: "check tunnel status"',
    'topaz': 'Try: "upscale a video"',
  }
  const key = Object.keys(prompts).find(k => project.id.toLowerCase().includes(k))
  return key ? prompts[key] : 'Ask me anything...'
}

interface QuickAction {
  label: string
  command: string
  icon?: string
}

interface OrchestratorResponse {
  type: 'instant' | 'search' | 'generated' | 'error'
  output?: string
  content?: string
  message?: string
  query?: string
  chunks?: Array<{ file_path: string; content: string; line_start: number }>
  tool_calls?: Array<{ tool: string; result: string; success: boolean }>
  model_used?: string
  latency_ms?: number
  task_type?: string
  path_attempted?: string
  actions?: QuickAction[]
}

// Track what SAM is thinking
const thinkingText = reactive<Record<string, string>>({})

// Thinking log - visible history of SAM's reasoning
const thinkingLog = reactive<Record<string, Array<{ time: string; thought: string }>>>({})

// Private mode - no logging
const privateMode = ref(localStorage.getItem('sam_private_mode') === 'true')

// === UI STATE ===
const streakDays = ref(parseInt(localStorage.getItem('sam_streak') || '0'))
const hasBriefUpdate = ref(true)
const lastActiveDate = ref(localStorage.getItem('sam_last_active') || '')

// === GLOBAL CHAT STATE ===
const globalChatActive = ref(false)
const globalInput = ref('')
const globalInputRef = ref<HTMLInputElement | null>(null)
const globalChatRef = ref<HTMLElement | null>(null)
const globalThinking = ref(false)
const globalMessages = ref<Array<{ id: string; role: 'user' | 'assistant'; content: string; actions?: QuickAction[] }>>([])

function activateGlobalChat() {
  globalChatActive.value = true
}

function closeGlobalChat() {
  globalChatActive.value = false
  globalInput.value = ''
}

async function executeAction(action: QuickAction) {
  // Show executing state
  globalThinking.value = true

  try {
    // Call the actual execute_action command
    const result = await invoke<any>('execute_action', { command: action.command })

    // Build response message
    let content = ''
    if (result.success) {
      content = `✅ **${result.task_type}** completed\n\n`
      if (result.output) {
        content += `\`\`\`\n${result.output}\n\`\`\`\n`
      }
      if (result.changes_made && result.changes_made.length > 0) {
        content += `\n**Changes:**\n${result.changes_made.map((c: string) => `- ${c}`).join('\n')}`
      }
    } else {
      content = `❌ **${result.task_type}** failed\n\n`
      if (result.error) {
        content += `Error: ${result.error}`
      }
    }

    // Add result to messages
    globalMessages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content,
      actions: []
    })
  } catch (e: any) {
    globalMessages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: `❌ Action failed: ${e}`,
      actions: []
    })
  } finally {
    globalThinking.value = false
  }
}

function setGlobalInput(text: string) {
  globalInput.value = text
  globalInputRef.value?.focus()
}

async function sendGlobalMessage() {
  const text = globalInput.value.trim()
  if (!text || globalThinking.value) return

  // Ensure chat is active
  globalChatActive.value = true

  // Add user message
  globalMessages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: text
  })

  globalInput.value = ''
  globalThinking.value = true

  // Scroll to bottom
  setTimeout(() => {
    if (globalChatRef.value) {
      const msgs = globalChatRef.value.querySelector('.chat-messages')
      if (msgs) msgs.scrollTop = msgs.scrollHeight
    }
  }, 50)

  try {
    const response = await invoke<any>('orchestrate_request', {
      input: text,
      workingDir: null,
      sessionId: 'global',
      privateMode: privateMode.value
    })

    // Debug: log the full response
    console.log('[SAM Debug] Response:', JSON.stringify(response, null, 2))

    let content = ''
    if (response.type === 'instant') {
      content = response.output || 'Done.'
    } else if (response.type === 'search') {
      content = response.chunks?.map((c: any) => `📄 ${c.file_path}\n${c.content.slice(0, 150)}...`).join('\n\n') || 'No results.'
    } else if (response.type === 'generated') {
      content = response.content || 'Done.'
    } else {
      content = response.message || 'Response received.'
    }

    globalMessages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content,
      actions: response.actions || []
    })

    trackLocalQuery(true)
  } catch (e: any) {
    globalMessages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: `Error: ${e}`
    })
  } finally {
    globalThinking.value = false
    // Scroll to bottom again
    setTimeout(() => {
      if (globalChatRef.value) {
        const msgs = globalChatRef.value.querySelector('.chat-messages')
        if (msgs) msgs.scrollTop = msgs.scrollHeight
      }
    }, 50)
  }
}

// Check/update streak on mount
function updateStreak() {
  const today = new Date().toDateString()
  const yesterday = new Date(Date.now() - 86400000).toDateString()

  if (lastActiveDate.value === yesterday) {
    streakDays.value++
  } else if (lastActiveDate.value !== today) {
    streakDays.value = 1
  }

  lastActiveDate.value = today
  localStorage.setItem('sam_streak', streakDays.value.toString())
  localStorage.setItem('sam_last_active', today)
}

// Brief and Progress buttons - activate chat with preset query
function showDailyBrief() {
  hasBriefUpdate.value = false
  globalChatActive.value = true
  globalInput.value = 'Give me my daily brief - what needs attention across all projects?'
  sendGlobalMessage()
}

function showProgress() {
  globalChatActive.value = true
  globalInput.value = 'Show my progress this week - what have I accomplished and what\'s pending?'
  sendGlobalMessage()
}

// Quick actions for watch-style cards
function quickApprove(project: Project) {
  // Approve all pending tasks for this project
  const pending = project.suggestedTasks?.filter(t => t.needsApproval) || []
  if (pending.length > 0) {
    emit('approve-all', project.id)
  }
}

function askAboutProject(project: Project) {
  globalChatActive.value = true
  globalInput.value = `What's the status of ${project.name}? What should I focus on next?`
  sendGlobalMessage()
}

function showProjectTasks(project: Project) {
  // Open project panel to tasks view
  emit('expand-project', project.id)
}

function getProjectAge(project: Project): string {
  // Get how old the project is based on creation or last activity
  const created = project.createdAt ? new Date(project.createdAt) : new Date()
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return '1d ago'
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
  return `${Math.floor(diffDays / 30)}mo ago`
}

function pinProject(project: Project) {
  // Toggle pinned state
  project.pinned = !project.pinned
  // Could emit event for persistence
}

function toggleFavorite(project: Project) {
  // Toggle favorite state
  project.favorite = !project.favorite
  // Could emit event for persistence
}

function showProjectSettings(project: Project) {
  // Open settings - for now just expand the project
  emit('expand-project', project.id)
}

// Local search - now handled by global chat
// Removed: localSearchQuery, handleBottomSearch

function togglePrivateMode() {
  privateMode.value = !privateMode.value
  localStorage.setItem('sam_private_mode', privateMode.value.toString())

  // When entering private mode, clear all logs
  if (privateMode.value) {
    Object.keys(thinkingLog).forEach(key => {
      thinkingLog[key] = []
    })
  }
}

function logThinking(projectId: string, thought: string) {
  // In private mode, don't log anything
  if (privateMode.value) return

  if (!thinkingLog[projectId]) thinkingLog[projectId] = []
  thinkingLog[projectId].push({
    time: new Date().toLocaleTimeString(),
    thought
  })
  // Keep last 20 thoughts
  if (thinkingLog[projectId].length > 20) {
    thinkingLog[projectId].shift()
  }
}

async function sendMessage(project: Project) {
  const text = inputMap[project.id]?.trim()
  if (!text || thinkingMap[project.id]) return

  const userMsg = { id: Date.now().toString(), role: 'user', content: text }

  // Add message to appropriate store
  if (privateMode.value) {
    if (!privateMessages[project.id]) privateMessages[project.id] = []
    privateMessages[project.id].push(userMsg)
  } else {
    projectStore.addChatMessage(project.id, { role: 'user', content: text })
  }

  inputMap[project.id] = ''
  thinkingMap[project.id] = true
  thinkingText[project.id] = 'Routing...'
  logThinking(project.id, `📥 Received: "${text.slice(0, 50)}..."`)

  try {
    // Use orchestrator for intelligent routing and tool execution
    const response = await invoke<OrchestratorResponse>('orchestrate_request', {
      input: text,
      workingDir: null,  // Uses current directory
      sessionId: project.id,
      privateMode: privateMode.value  // Don't log when in private mode
    })

    let assistantContent = ''
    let thinking = ''

    switch (response.type) {
      case 'instant':
        // Deterministic response (shell commands, file ops)
        thinking = `⚡ Instant: ${response.task_type || 'Direct'}`
        logThinking(project.id, thinking)
        assistantContent = response.output || 'Done.'
        break

      case 'search':
        // Semantic code search results
        thinking = `🔍 Search: ${response.chunks?.length || 0} results`
        logThinking(project.id, thinking)
        thinkingText[project.id] = thinking
        if (response.chunks && response.chunks.length > 0) {
          assistantContent = response.chunks
            .map(c => `📄 ${c.file_path}:${c.line_start}\n${c.content.slice(0, 200)}...`)
            .join('\n\n')
        } else {
          assistantContent = 'No results found.'
        }
        break

      case 'generated':
        // LLM generated response with potential tool calls
        thinking = `🧠 Model: ${response.model_used || 'LLM'}`
        logThinking(project.id, thinking)
        thinkingText[project.id] = thinking
        assistantContent = response.content || ''
        // Log and show tool calls if any
        if (response.tool_calls && response.tool_calls.length > 0) {
          response.tool_calls.forEach(t => {
            logThinking(project.id, `🔧 Tool: ${t.tool} → ${t.success ? '✅' : '❌'}`)
          })
          const toolSummary = response.tool_calls
            .map(t => `${t.success ? '✅' : '❌'} ${t.tool}: ${t.result.slice(0, 100)}...`)
            .join('\n')
          assistantContent = `${assistantContent}\n\n📋 Tool calls:\n${toolSummary}`
        }
        break

      case 'error':
        thinking = `❌ Error: ${response.path_attempted || 'unknown'}`
        logThinking(project.id, thinking)
        assistantContent = `${response.message || 'Unknown error'}`
        break

      default:
        assistantContent = 'Response received.'
    }

    // Log latency
    if (response.latency_ms) {
      logThinking(project.id, `⏱ ${response.latency_ms}ms`)
    }

    // Add assistant response to appropriate store
    const assistantMsg = { id: Date.now().toString(), role: 'assistant', content: assistantContent }
    if (privateMode.value) {
      if (!privateMessages[project.id]) privateMessages[project.id] = []
      privateMessages[project.id].push(assistantMsg)
    } else {
      projectStore.addChatMessage(project.id, { role: 'assistant', content: assistantContent })
    }
    trackLocalQuery(true) // Track as local query - water saved!

  } catch (e: any) {
    logThinking(project.id, `❌ Exception: ${e}`)
    const errorMsg = { id: Date.now().toString(), role: 'assistant', content: `Error: ${e}` }
    if (privateMode.value) {
      if (!privateMessages[project.id]) privateMessages[project.id] = []
      privateMessages[project.id].push(errorMsg)
    } else {
      projectStore.addChatMessage(project.id, { role: 'assistant', content: `Error: ${e}` })
    }
  } finally {
    thinkingMap[project.id] = false
    thinkingText[project.id] = ''
  }
}

// === CELEBRATIONS ===
const celebratingProjects = reactive<Record<string, boolean>>({})
const activityFlash = reactive<Record<string, boolean>>({})

function celebrate(id: string) {
  celebratingProjects[id] = true
  trackEfficiencyGain(5) // 5% efficiency improvement for completing all tasks
  setTimeout(() => celebratingProjects[id] = false, 3000) // Longer, gentler glow
}

// === COMPUTED ===
const filteredProjects = computed(() => {
  const projects = projectStore.projects.value || []
  if (!props.searchQuery) return projects
  const q = props.searchQuery.toLowerCase()
  return projects.filter(p =>
    p.name.toLowerCase().includes(q) ||
    p.description?.toLowerCase().includes(q) ||
    p.tags?.some(t => t.toLowerCase().includes(q))
  )
})

const expandedProject = computed(() => {
  if (!props.expandedProjectId) return null
  return (projectStore.projects.value || []).find(p => p.id === props.expandedProjectId)
})

// === HELPERS ===
function cardClasses(p: Project) {
  return {
    [`status-${p.status}`]: true,
    'chat-mode': isInChatMode(p.id),
    'has-running': p.runningTasks?.length > 0,
    'celebrating': celebratingProjects[p.id]
  }
}

// Simplified card helpers for Apple Watch style
function getCardClass(p: Project) {
  return {
    'has-decisions': getPendingDecisions(p) > 0,
    'has-running': (p.runningTasks?.length || 0) > 0,
    'healthy': p.status === 'healthy',
    'warning': p.status === 'warning',
    'error': p.status === 'error'
  }
}

// Get emoji animation state based on project status
function getEmojiState(p: Project): 'idle' | 'working' | 'excited' | 'error' | 'celebrating' {
  if (celebratingProjects[p.id]) return 'celebrating'
  if (p.status === 'error') return 'error'
  if (getPendingDecisions(p) > 0) return 'excited'
  if ((p.runningTasks?.length || 0) > 0) return 'working'
  return 'idle'
}

function getStatusText(p: Project): string {
  const decisions = getPendingDecisions(p)
  if (decisions > 0) return `${decisions} pending`
  if (p.runningTasks?.length) return `${p.runningTasks.length} active`
  const goals = p.goals?.length || 0
  const done = getCompletedGoals(p)
  if (goals > 0) return `${done}/${goals}`
  return p.status || 'Ready'
}

function getProgress(p: Project): number {
  if (!p.goals?.length) return 0
  const done = p.goals.filter(g => g.status === 'complete').length
  return Math.round((done / p.goals.length) * 100)
}

function getCompletedGoals(p: Project): number {
  return p.goals?.filter(g => g.status === 'complete').length || 0
}

function isNearComplete(p: Project): boolean {
  if (!p.goals?.length) return false
  const done = getCompletedGoals(p)
  return done > 0 && p.goals.length - done === 1
}

function handleCardClick(p: Project) {
  if (isInChatMode(p.id)) return
  emit('expand-project', p.id)
}

function handleApproveTask(task: any) {
  emit('approve-task', { ...task, projectId: props.expandedProjectId })
  trackEfficiencyGain(1) // Each task approved = 1% efficiency improvement
  activityFlash[props.expandedProjectId!] = true
  setTimeout(() => activityFlash[props.expandedProjectId!] = false, 1000)
}

function handleApproveAll() {
  if (props.expandedProjectId) {
    emit('approve-all', props.expandedProjectId)
    celebrate(props.expandedProjectId)
  }
}

function handleDeleteProject() {
  if (props.expandedProjectId) {
    emit('delete-project', props.expandedProjectId)
  }
}
</script>

<style scoped>
/* === BASE - Hermès Watch OS + Liquid Glass === */
.topic-grid {
  height: 100%;
  display: flex;
  flex-direction: column;
  /* Semi-transparent dark to ensure visibility on any wallpaper */
  background: rgba(30, 30, 30, 0.7);
  padding: 0 8px;

  /* === NATIVE macOS SEQUOIA COLORS === */
  /* System accent - user's chosen accent color */
  --accent: #0a84ff;
  --accent-hover: #409cff;

  /* System semantic colors */
  --system-red: #ff453a;
  --system-orange: #ff9f0a;
  --system-yellow: #ffd60a;
  --system-green: #30d158;
  --system-blue: #0a84ff;
  --system-purple: #bf5af2;

  /* Native text colors */
  --text-primary: rgba(255, 255, 255, 0.88);
  --text-secondary: rgba(255, 255, 255, 0.55);
  --text-tertiary: rgba(255, 255, 255, 0.35);

  /* Native surfaces - ultra subtle */
  --bg-hover: rgba(255, 255, 255, 0.06);
  --bg-active: rgba(255, 255, 255, 0.08);
  --bg-selected: rgba(10, 132, 255, 0.2);
  --separator: rgba(255, 255, 255, 0.08);

  /* Native typography */
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
  font-size: 13px;
  letter-spacing: -0.08px;
}

/* === macOS TRAFFIC LIGHTS - Hidden when using native decorations === */
.traffic-lights {
  display: none;
}

.traffic-light {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  -webkit-app-region: no-drag;
}

.traffic-light svg {
  width: 8px;
  height: 8px;
  opacity: 0;
  color: rgba(0, 0, 0, 0.5);
  transition: opacity 0.15s ease;
}

.traffic-lights:hover .traffic-light svg {
  opacity: 1;
}

.traffic-light.close {
  background: #ff5f57;
}

.traffic-light.close:hover {
  background: #ff3b30;
}

.traffic-light.minimize {
  background: #febc2e;
}

.traffic-light.minimize:hover {
  background: #ff9500;
}

.traffic-light.maximize {
  background: #28c840;
}

.traffic-light.maximize:hover {
  background: #34c759;
}

.traffic-light:active {
  transform: scale(0.9);
}

/* === GLOBAL CHAT AREA === */
.global-chat-area {
  position: absolute;
  top: 40px;  /* Below traffic lights */
  left: 0;
  right: 0;
  bottom: 70px;  /* Above bottom bar */
  display: flex;
  flex-direction: column;
  background: rgba(20, 20, 25, 0.98);
  z-index: 100;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-msg {
  max-width: 80%;
  animation: msg-in 0.2s ease;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(10px); }
}

.chat-msg.user {
  align-self: flex-end;
}

.chat-msg.assistant {
  align-self: flex-start;
}

.msg-content {
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.5;
}

.chat-msg.user .msg-content {
  background: linear-gradient(135deg, #0a84ff, #5ac8fa);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-msg.assistant .msg-content {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  border-bottom-left-radius: 4px;
}

.msg-content.thinking {
  display: flex;
  gap: 4px;
  padding: 16px 20px;
}

.msg-content.thinking .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  animation: thinking-bounce 1.2s infinite ease-in-out;
}

.msg-content.thinking .dot:nth-child(2) { animation-delay: 0.15s; }
.msg-content.thinking .dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes thinking-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-6px); opacity: 1; }
}

.msg-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-left: 4px;
}

.msg-actions .action-btn {
  padding: 8px 16px;
  border-radius: 20px;
  border: 1px solid rgba(10, 132, 255, 0.5);
  background: rgba(10, 132, 255, 0.15);
  color: #5ac8fa;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.msg-actions .action-btn:hover {
  background: rgba(10, 132, 255, 0.3);
  border-color: #0a84ff;
  transform: translateY(-1px);
}

.msg-actions .action-btn:active {
  transform: translateY(0);
}

.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.welcome-icon {
  font-size: 48px;
}

.welcome-text {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.6);
}

.welcome-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}

.welcome-hints button {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.welcome-hints button:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

/* Chat expand transition */
.chat-expand-enter-active,
.chat-expand-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-expand-enter-from,
.chat-expand-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* === BOTTOM BAR - Native Spotlight/Search Style === */
.bottom-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  margin: 8px 12px 12px;
  /* Native macOS: subtle gray, no border */
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  border: none;
  box-shadow: none;
  flex-shrink: 0;
  transition: background-color 0.15s ease;
  z-index: 200;
}

.bottom-bar:focus-within {
  background: rgba(255, 255, 255, 0.08);
}

.bottom-bar.chat-active {
  margin: 8px 12px 12px;
  background: rgba(255, 255, 255, 0.08);
}

.back-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.08);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  flex-shrink: 0;
}

.back-btn svg {
  width: 18px;
  height: 18px;
  color: rgba(255, 255, 255, 0.7);
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.input-area {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.input-area input {
  flex: 1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px 16px;
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

.input-area input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.input-area input:focus {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(10, 132, 255, 0.4);
}

.input-area .send-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0a84ff, #5ac8fa);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.input-area .send-btn svg {
  width: 16px;
  height: 16px;
  color: #fff;
}

.input-area .send-btn:hover {
  transform: scale(1.1);
}

.bar-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Nav buttons (Brief, Progress) */
.nav-btn {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-btn svg {
  width: 18px;
  height: 18px;
  color: rgba(255, 255, 255, 0.6);
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.12);
}

.nav-btn:hover svg {
  color: rgba(255, 255, 255, 0.9);
}

/* Notification dot */
.notify-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ff453a;
}

/* Streak pip */
.streak-pip {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, #ff9f0a, #ff6b35);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bar-stats {
  display: flex;
  gap: 6px;
}

.stat-pill {
  padding: 4px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.stat-pill.urgent {
  background: rgba(255, 69, 58, 0.2);
  color: #ff453a;
}

.stat-pill.active {
  background: rgba(48, 209, 88, 0.2);
  color: #30d158;
}

.privacy-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.privacy-btn svg {
  width: 18px;
  height: 18px;
  color: rgba(255, 255, 255, 0.6);
}

.privacy-btn:hover {
  background: rgba(255, 255, 255, 0.12);
}

.privacy-btn.private {
  background: rgba(99, 102, 241, 0.3);
}

.privacy-btn.private svg {
  color: rgba(165, 180, 252, 0.95);
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* View density controls (like Photos zoom) */
.view-controls {
  display: flex;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}

.density-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.density-btn svg {
  width: 14px;
  height: 14px;
}

.density-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.7);
}

.density-btn.active {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

/* Global stats chips (center) */
.global-stats {
  display: flex;
  gap: 8px;
  flex: 1;
  justify-content: center;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}

.stat-chip.healthy {
  color: var(--success);
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.chip-dot.urgent {
  background: #ff6b6b;
  animation: pulse-dot 1.5s infinite;
}

.chip-dot.active {
  background: var(--success);
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.8); }
}

/* Right side: eco + private */
.status-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Activity ticker (horizontal scroll of recent events) */
.activity-ticker {
  display: flex;
  gap: 16px;
  padding: 6px 16px;
  overflow-x: auto;
  background: rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.activity-ticker::-webkit-scrollbar {
  display: none;
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  font-size: 11px;
  white-space: nowrap;
  color: rgba(255, 255, 255, 0.6);
}

.ticker-icon {
  font-size: 12px;
}

.ticker-text {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ticker-time {
  color: rgba(255, 255, 255, 0.35);
  font-size: 10px;
}

.ticker-enter-active, .ticker-leave-active {
  transition: all 0.3s ease;
}
.ticker-enter-from { opacity: 0; transform: translateX(-10px); }
.ticker-leave-to { opacity: 0; transform: translateX(10px); }

/* === Privacy Eye Toggle === */
.privacy-eye {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 8px;
  border: none;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.12);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  overflow: visible;
}

.privacy-eye:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: scale(1.04);
}

.privacy-eye:active {
  transform: scale(0.97);
}

/* Private mode - calming indigo/purple */
.privacy-eye.private {
  background: rgba(99, 102, 241, 0.25);
  box-shadow:
    0 0 16px rgba(99, 102, 241, 0.3),
    inset 0 0 12px rgba(99, 102, 241, 0.1);
}

/* Ambient glow */
.eye-glow {
  position: absolute;
  inset: -4px;
  border-radius: 24px;
  background: radial-gradient(ellipse at center, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
  animation: eye-breathe 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes eye-breathe {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* Eye icon container */
.eye-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.eye-icon {
  width: 20px;
  height: 20px;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.eye-open {
  color: rgba(52, 199, 89, 0.9);
}

.eye-closed {
  color: rgba(129, 140, 248, 0.95);
  filter: drop-shadow(0 0 4px rgba(99, 102, 241, 0.5));
}

/* Label text */
.eye-label {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.3s ease;
  -webkit-font-smoothing: antialiased;
}

.privacy-eye.private .eye-label {
  color: rgba(165, 180, 252, 0.95);
}

.eco-stat {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  white-space: nowrap;
}

/* === GRID CONTAINER - Widget Dashboard === */
.grid-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  align-content: start;
}

/* Single column on narrow screens */
@media (max-width: 700px) {
  .grid-container {
    grid-template-columns: 1fr;
    padding: 16px;
    gap: 12px;
  }
}

/* Hide stats on narrow windows to prioritize project names */
@media (max-width: 900px) {
  .widget-stats .stat:nth-child(n+2) {
    display: none;
  }
}

@media (max-width: 750px) {
  .widget-stats {
    display: none;
  }
}

/* Density variants */
.grid-compact {
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
}

.grid-regular {
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
}

.grid-focus {
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px;
}

/* Compact mode card overrides */
.density-compact .project-card {
  padding: 10px 8px;
  min-height: 140px;
}

.density-compact .card-header {
  padding: 6px 8px;
}

.density-compact .card-icon {
  font-size: 24px;
}

.density-compact .card-title {
  font-size: 11px;
}

.density-compact .card-subtitle {
  display: none;
}

.density-compact .stats-preview {
  padding: 4px 0;
}

.density-compact .primary-stat {
  font-size: 18px;
}

.density-compact .secondary-stats,
.density-compact .quick-hint {
  display: none;
}

.density-compact .card-footer {
  padding: 6px 8px 10px 8px;
}

.density-compact .chat-input-field {
  font-size: 11px;
  padding: 6px 8px;
}

/* Focus mode card overrides */
.density-focus .project-card {
  max-width: 100%;
  min-height: 280px;
}

.density-focus .card-body {
  flex: 1;
}

.density-focus .chat-area {
  min-height: 120px;
}

/* === NATIVE macOS SEQUOIA STYLE === */
/* Designed to feel like a first-party Apple app */

.widget-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 12px 16px;
  gap: 14px;
  /* Native macOS: no border, no gradient, just subtle bg */
  background: transparent;
  border: none;
  border-radius: 10px;
  transition: background-color 0.15s ease;
  cursor: pointer;
  margin: 2px 0;
}

.widget-row:hover {
  /* Native hover: subtle gray overlay like Finder/Notes */
  background: rgba(255, 255, 255, 0.06);
}

.widget-row:active {
  background: rgba(255, 255, 255, 0.08);
}

/* Selected state - system accent color */
.widget-row.selected {
  background: rgba(10, 132, 255, 0.2);
}

.widget-row.selected:hover {
  background: rgba(10, 132, 255, 0.25);
}

/* Status indicators - subtle, native style */
.widget-row.has-decisions {
  /* Small dot indicator instead of border */
  position: relative;
}

.widget-row.has-decisions::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ff453a; /* System red */
}

.widget-row.has-running {
  position: relative;
}

.widget-row.has-running::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #0a84ff; /* System blue */
  animation: pulse-dot 2s ease-in-out infinite;
}

.widget-icon {
  font-size: 32px;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Native: no background on icon, let emoji stand alone */
  background: transparent;
  border-radius: 8px;
  /* Subtle alive animation */
  animation: emoji-breathe 4s ease-in-out infinite;
  transform-origin: center center;
}

/* === EXPRESSIVE EMOJI ANIMATIONS === */
/* Like Apple keynotes - personality-driven, not just effects */

/* ALIVE - Subtle breathing (idle state, shows presence) */
@keyframes emoji-breathe {
  0%, 100% { transform: scale(1) translateY(0); }
  50% { transform: scale(1.02) translateY(-1px); }
}

/* WORKING - Focused concentration (has running tasks) */
@keyframes emoji-working {
  0%, 100% { transform: scale(1) rotate(0deg); }
  25% { transform: scale(1.03) rotate(-2deg); }
  75% { transform: scale(0.98) rotate(2deg); }
}

/* EXCITED - Wants attention (has pending decisions) */
@keyframes emoji-excited {
  0%, 100% { transform: scale(1) translateY(0) rotate(0deg); }
  10% { transform: scale(1.15) translateY(-4px) rotate(-5deg); }
  20% { transform: scale(1.08) translateY(-2px) rotate(3deg); }
  30% { transform: scale(1.12) translateY(-3px) rotate(-3deg); }
  40% { transform: scale(1.05) translateY(-1px) rotate(2deg); }
  50% { transform: scale(1) translateY(0) rotate(0deg); }
}

/* HELLO - Recognition when noticed (hover state) */
@keyframes emoji-hello {
  0% { transform: scale(1) rotate(0deg); }
  15% { transform: scale(1.2) rotate(-12deg); }
  30% { transform: scale(1.15) rotate(10deg); }
  45% { transform: scale(1.18) rotate(-8deg); }
  60% { transform: scale(1.12) rotate(5deg); }
  75% { transform: scale(1.08) rotate(-2deg); }
  100% { transform: scale(1.1) rotate(0deg); }
}

/* WORRIED - Something's wrong (error state) */
@keyframes emoji-worried {
  0%, 100% { transform: translateX(0) scale(1); }
  10% { transform: translateX(-3px) scale(0.98); }
  20% { transform: translateX(3px) scale(1.02); }
  30% { transform: translateX(-2px) scale(0.99); }
  40% { transform: translateX(2px) scale(1.01); }
  50% { transform: translateX(0) scale(1); }
}

/* CELEBRATE - Joy! (task completed) */
@keyframes emoji-celebrate {
  0% { transform: scale(1) rotate(0deg) translateY(0); }
  10% { transform: scale(1.3) rotate(-15deg) translateY(-8px); }
  20% { transform: scale(1.2) rotate(12deg) translateY(-12px); }
  30% { transform: scale(1.25) rotate(-10deg) translateY(-10px); }
  40% { transform: scale(1.15) rotate(8deg) translateY(-6px); }
  50% { transform: scale(1.2) rotate(-5deg) translateY(-4px); }
  60% { transform: scale(1.1) rotate(3deg) translateY(-2px); }
  70% { transform: scale(1.05) rotate(-2deg) translateY(-1px); }
  80% { transform: scale(1.02) rotate(1deg) translateY(0); }
  100% { transform: scale(1) rotate(0deg) translateY(0); }
}

/* WARNING - Concerned/alert */
@keyframes emoji-alert {
  0%, 100% { transform: scale(1) translateY(0); }
  25% { transform: scale(1.05) translateY(-2px); }
  50% { transform: scale(0.97) translateY(1px); }
  75% { transform: scale(1.03) translateY(-1px); }
}

/* INVITING - Add new project (+) */
@keyframes emoji-inviting {
  0%, 100% { transform: scale(1) rotate(0deg); opacity: 0.5; }
  50% { transform: scale(1.1) rotate(90deg); opacity: 0.8; }
}

/* Apply animations based on project state */
.widget-row.has-running .widget-icon {
  animation: emoji-working 2s ease-in-out infinite;
}

.widget-row.has-decisions .widget-icon {
  animation: emoji-excited 3s ease-in-out infinite;
}

.widget-row.error .widget-icon {
  animation: emoji-worried 0.5s ease-in-out infinite;
}

.widget-row.warning .widget-icon {
  animation: emoji-alert 2s ease-in-out infinite;
}

.widget-row.celebrating .widget-icon {
  animation: emoji-celebrate 1s ease-out forwards;
}

/* Hover - emoji says hello! */
.widget-row:hover .widget-icon {
  animation: emoji-hello 0.6s ease-out forwards;
}

/* Add widget special animation */
.widget-row.add-widget .widget-icon {
  animation: emoji-inviting 3s ease-in-out infinite;
}

.widget-row.add-widget:hover .widget-icon {
  animation: emoji-hello 0.5s ease-out forwards;
  opacity: 1;
}

.widget-content {
  flex: 1;
  min-width: 140px; /* Guarantee space for project names */
}

.widget-title {
  /* Native macOS: SF Pro Text, regular weight, system primary */
  font-size: 13px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.88);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.08px;
  line-height: 1.3;
}

.widget-subtitle {
  /* Native: secondary label color */
  font-size: 11px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0;
}

/* Stats - minimal, right-aligned like Finder */
.widget-stats {
  display: flex;
  gap: 8px;
  flex-shrink: 1; /* Allow shrinking to give title priority */
  min-width: 0; /* Enable truncation */
  align-items: center;
  overflow: hidden;
}

.widget-stats .stat {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
}

.widget-stats .stat-num {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
  font-variant-numeric: tabular-nums;
}

.widget-stats .stat-num.active {
  color: #0a84ff;
}

.widget-stats .stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* === SUBTLE WORKFLOW ANIMATIONS === */
/* Fun but not overstimulating - helps focus */

/* Gentle pulse for active items */
.pulse-gentle {
  animation: pulse-soft 2s ease-in-out infinite;
}

@keyframes pulse-soft {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Progress ring - visual completion indicator */
.progress-stat {
  position: relative;
  width: 24px;
  height: 24px;
}

.progress-ring {
  width: 24px;
  height: 24px;
  transform: rotate(-90deg);
}

.progress-ring-bg {
  fill: none;
  stroke: rgba(255, 255, 255, 0.1);
  stroke-width: 2;
}

.progress-ring-fill {
  fill: none;
  stroke: var(--system-green);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-dasharray: 63;
  transition: stroke-dashoffset 0.6s ease-out;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 8px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
}

/* Count animation - numbers feel alive */
.count-up {
  transition: transform 0.2s ease-out;
}

.count-up:hover {
  transform: scale(1.1);
}

/* Completion checkmark animation */
@keyframes check-pop {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}

.check-complete {
  animation: check-pop 0.3s ease-out forwards;
  color: var(--system-green);
}

/* Loading shimmer for processing states */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.loading-shimmer {
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,0.1) 50%,
    rgba(255,255,255,0) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

/* Notification badge bounce */
@keyframes badge-bounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}

.badge-attention {
  animation: badge-bounce 0.6s ease-in-out;
}

.widget-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
}

/* Show actions on row hover */
.widget-row:hover .widget-actions {
  opacity: 1;
}

.widget-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.12s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.widget-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.widget-btn:active {
  background: var(--bg-active);
}

.widget-btn.approve {
  background: rgba(48, 209, 88, 0.15);
  color: var(--system-green);
}

.widget-btn.approve:hover {
  background: rgba(48, 209, 88, 0.25);
}

/* Add widget - Native macOS style */
.widget-row.add-widget {
  background: transparent;
  opacity: 0.5;
}

.widget-row.add-widget:hover {
  background: var(--bg-hover);
  opacity: 1;
}

.widget-row.add-widget .widget-icon {
  font-size: 20px;
  color: var(--text-tertiary);
  background: transparent;
}

.widget-row.add-widget:hover .widget-icon {
  color: var(--accent);
}

.add-title {
  color: var(--text-tertiary);
}

.widget-row.add-widget:hover .add-title {
  color: var(--text-primary);
}

/* Legacy watch-card (keep for backwards compat) */
.watch-card {
  display: none;
}

/* Header row */
.watch-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.watch-icon {
  font-size: 18px;
}

.watch-name {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.watch-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
}

.watch-dot.healthy { background: #30d158; }
.watch-dot.warning { background: #ff9f0a; }
.watch-dot.error { background: #ff453a; }
.watch-dot.idle { background: rgba(255, 255, 255, 0.3); }

/* Metrics row */
.watch-metrics {
  display: flex;
  gap: 8px;
  padding: 10px 0;
  flex: 1;
}

.metric {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 4px;
  border-radius: 8px;
  transition: background 0.15s;
}

.metric:hover {
  background: rgba(255, 255, 255, 0.08);
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.metric-label {
  font-size: 8px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.metric.running .metric-value {
  color: #0a84ff;
}

/* Progress bar section */
.watch-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
}

.progress-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #30d158, #5ac8fa);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
  min-width: 32px;
  text-align: right;
}

/* Activity section */
.watch-activity {
  padding: 8px 0;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.activity-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.activity-icon {
  font-size: 14px;
}

.activity-text {
  flex: 1;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Info chips row */
.watch-info {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 4px 0;
}

.info-chip {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
}

.info-chip.time {
  color: rgba(255, 255, 255, 0.4);
}

/* Action buttons row */
.watch-actions {
  display: flex;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.watch-actions.secondary {
  border-top: none;
  padding-top: 4px;
}

.action-btn {
  flex: 1;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.08);
  border: none;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.action-btn:active {
  transform: scale(0.95);
}

.action-btn.approve {
  background: rgba(52, 199, 89, 0.2);
  color: #30d158;
}

.action-btn.approve:hover {
  background: rgba(52, 199, 89, 0.3);
}

.action-btn.chat {
  font-size: 14px;
}

.action-btn.icon-only {
  flex: none;
  width: 32px;
  padding: 0;
  font-size: 13px;
}

.action-btn.icon-only.settings {
  opacity: 0.6;
}

.action-btn.icon-only:hover {
  background: rgba(255, 255, 255, 0.12);
}

/* Add card */
.watch-card.add-card {
  background: rgba(255, 255, 255, 0.03);
  border: 2px dashed rgba(255, 255, 255, 0.12);
  justify-content: center;
  align-items: center;
  cursor: pointer;
  min-height: 280px;
}

.watch-card.add-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(10, 132, 255, 0.5);
  transform: translateY(-4px);
}

.add-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.add-icon {
  font-size: 36px;
  color: rgba(255, 255, 255, 0.3);
  transition: all 0.2s ease;
}

.add-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
}

.add-hint {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.25);
  margin-top: 4px;
}

.watch-card.add-card:hover .add-icon {
  color: #0a84ff;
  transform: scale(1.2);
}

.watch-card.add-card:hover .add-label {
  color: rgba(255, 255, 255, 0.9);
}

.watch-card.add-card:hover .add-hint {
  color: rgba(255, 255, 255, 0.5);
}

/* === PROGRESS RING - Hidden in compact mode === */
.progress-ring {
  display: none;
}

.ring-bg {
  fill: none;
  stroke: rgba(255,255,255,0.1);
  stroke-width: 3;
}

.ring-fill {
  fill: none;
  stroke: var(--success);
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

/* === CARD CONTENT - Base styles === */
.card-icon {
  transition: transform 0.4s ease;
}

.project-card:hover .card-icon {
  transform: scale(1.08);
}

.card-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* === CAROUSEL - Visible in full-height mode === */
.detail-carousel {
  margin-top: auto;
  margin-bottom: 20px;
  height: 50px;
  overflow: hidden;
}

.carousel-track {
  position: relative;
  height: 100%;
}

.carousel-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.detail-stat {
  font-size: 20px;
  font-weight: 800;
  color: #fff;
}

.detail-label {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-pill {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 8px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-pill.healthy { background: rgba(52,199,89,0.2); color: var(--success); }
.status-pill.warning { background: rgba(255,149,0,0.2); color: var(--warning); }
.status-pill.error { background: rgba(255,59,48,0.2); color: var(--error); }
.status-pill.idle { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); }

/* Gentle fade carousel transitions - slow and calming */
.fade-gentle-enter-active, .fade-gentle-leave-active {
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-gentle-enter-from {
  opacity: 0;
}
.fade-gentle-leave-to {
  opacity: 0;
  position: absolute;
}

/* === RUNNING BADGE - Visible in full-height mode === */
.running-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--accent);
  padding: 4px 8px;
  background: hsla(var(--hue), 60%, 30%, 0.3);
  border-radius: 8px;
}

.pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: breathe 3s infinite ease-in-out;
}

@keyframes breathe {
  0%, 100% { opacity: 0.8; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.9); }
}

/* === QUICK ACTIONS - Bottom of card === */
.card-actions {
  position: absolute;
  bottom: 16px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.project-card:hover .card-actions {
  opacity: 1;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: rgba(255,255,255,0.15);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:hover {
  background: rgba(255,255,255,0.25);
  transform: scale(1.1);
}

.action-btn.chat { background: rgba(88,86,214,0.3); }

/* === CARD HEADER - Compresses when chat expands === */
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 14px 10px 14px;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1); /* Spring feel */
}

.card-header:hover {
  background: rgba(255,255,255,0.03);
}

.card-header .card-icon {
  font-size: 32px;
  line-height: 1;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,0.4));
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.card-header .header-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-header .card-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.95);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.2px;
}

.card-header .card-subtitle {
  font-size: 10px;
  color: rgba(255,255,255,0.45);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Decisions badge - pulsing attention */
.decisions-badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: badge-pulse 2s ease-in-out infinite;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.decisions-badge:hover {
  transform: scale(1.15);
}

@keyframes badge-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(255, 107, 107, 0); }
}

.card-header .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.card-header .status-dot.healthy {
  background: var(--success);
  box-shadow: 0 0 8px rgba(52, 199, 89, 0.5);
}
.card-header .status-dot.warning {
  background: var(--warning);
  box-shadow: 0 0 8px rgba(255, 149, 0, 0.5);
}
.card-header .status-dot.error {
  background: var(--error);
  box-shadow: 0 0 8px rgba(255, 59, 48, 0.5);
}

/* Compact header when chat is expanded */
.card-header.compact {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  background: rgba(0,0,0,0.1);
}

.card-header.compact .card-icon {
  font-size: 20px;
}

.card-header.compact .card-title {
  font-size: 12px;
}

.card-header.compact .card-subtitle {
  display: none;
}

/* === CARD BODY - Expands to show chat === */
.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-body.expanded {
  flex: 1;
}

/* Stats preview (when collapsed) */
.stats-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 0;
  flex: 1;
}

.primary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -1px;
  line-height: 1;
}

.stat-label {
  font-size: 9px;
  color: rgba(255,255,255,0.45);
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Secondary stats row */
.secondary-stats {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.mini-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.mini-value {
  font-weight: 600;
  color: rgba(255,255,255,0.7);
}

.mini-label {
  color: rgba(255,255,255,0.4);
}

.pulse-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--success);
  animation: pulse 2s infinite;
}

/* Quick action hint */
.quick-hint {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
  padding: 4px 10px;
  background: rgba(255,255,255,0.04);
  border-radius: 8px;
  margin-top: 6px;
}

/* Chat area (when expanded) */
.chat-area {
  flex: 1;
  width: 100%;
  background: transparent;
  border-radius: 10px;
  padding: 8px 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 60px;
}

.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.3);
  font-size: 12px;
  font-style: italic;
}

/* === CARD FOOTER - Always visible input === */
.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 14px 12px;
  margin-top: auto;
  transition: all 0.3s ease;
}

.card-footer.has-focus {
  background: rgba(0,0,0,0.15);
  border-top: 1px solid rgba(255,255,255,0.06);
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.chat-input-field {
  width: 100%;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  padding: 10px 16px;
  padding-right: 36px;
  color: #fff;
  font-size: 13px;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-input-field::placeholder {
  color: rgba(255,255,255,0.35);
}

.chat-input-field:focus {
  background: rgba(255,255,255,0.1);
  border-color: rgba(10, 132, 255, 0.4);
  box-shadow:
    0 0 0 3px rgba(10, 132, 255, 0.08),
    inset 0 1px 2px rgba(0,0,0,0.1);
}

/* Expand hint - subtle chevron that pulses */
.expand-hint {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255,255,255,0.2);
  font-size: 12px;
  animation: hint-float 2s ease-in-out infinite;
  pointer-events: none;
}

@keyframes hint-float {
  0%, 100% { transform: translateY(-50%); opacity: 0.2; }
  50% { transform: translateY(-60%); opacity: 0.4; }
}

/* Send button */
.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, var(--accent), #5ac8fa);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(10, 132, 255, 0.3);
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(10, 132, 255, 0.4);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-thinking {
  animation: thinking-pulse 1s ease-in-out infinite;
}

@keyframes thinking-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* Pop transition for send button */
.pop-enter-active {
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pop-leave-active {
  animation: pop-out 0.2s ease-out;
}

@keyframes pop-in {
  from { opacity: 0; transform: scale(0.5); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes pop-out {
  from { opacity: 1; transform: scale(1); }
  to { opacity: 0; transform: scale(0.5); }
}

/* === SLIDE UP TRANSITION === */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
  max-height: 0;
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
  max-height: 0;
}

.msg {
  max-width: 85%;
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.4;
  animation: msgIn 0.2s ease;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
}

.msg.user {
  align-self: flex-end;
  background: linear-gradient(135deg, var(--accent), #5ac8fa);
  color: #fff;
}

.msg.assistant {
  align-self: flex-start;
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.9);
}

/* Thinking indicator with label */
.thinking-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px !important;
  background: rgba(255,255,255,0.05) !important;
}

.thinking-label {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  white-space: nowrap;
}

.thinking-dots {
  display: flex;
  gap: 3px;
}

.thinking-dots span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255,255,255,0.4);
  animation: thinking-bounce 1s infinite ease-in-out;
}

.thinking-dots span:nth-child(2) { animation-delay: 0.15s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes thinking-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-3px); opacity: 1; }
}

/* Thinking log - shows recent thoughts */
.thinking-log {
  width: 100%;
  padding: 4px 8px;
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
  margin-bottom: 4px;
}

.thought {
  font-size: 9px;
  color: rgba(255,255,255,0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
}

.chat-input {
  display: flex;
  gap: 6px;
  margin-top: auto;
  width: 100%;
  padding-top: 8px;
}

.chat-input input {
  flex: 1;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 8px;
  padding: 8px 10px;
  color: #fff;
  font-size: 12px;
  outline: none;
}

.chat-input input:focus {
  border-color: var(--accent);
}

.chat-input button {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.chat-input button:disabled {
  opacity: 0.4;
}


/* === ADD CARD - Same size as project cards === */
.add-card {
  background: hsla(var(--hue), 30%, 15%, 0.3);
  border: 1px dashed hsla(var(--hue), 40%, 40%, 0.2);
}

.add-card:hover {
  border-color: var(--accent);
  background: hsla(var(--hue), 40%, 20%, 0.4);
}

.add-plus {
  font-size: 28px;
  color: hsla(var(--hue), 50%, 60%, 0.5);
}

.add-text {
  display: none;
}

.add-card:hover .add-plus {
  color: var(--accent);
}

/* === EMPTY STATE === */
.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(255,255,255,0.4);
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

/* === TRANSITIONS === */
.expand-enter-active, .expand-leave-active {
  transition: all 0.3s ease;
}
.expand-enter-from, .expand-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* Morph transition for project ↔ chat - slow, gentle */
.morph-enter-active, .morph-leave-active {
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.morph-enter-from {
  opacity: 0;
}
.morph-leave-to {
  opacity: 0;
}

/* ==========================================================================
   RESPONSIVE BREAKPOINTS - All Apple Devices
   ========================================================================== */

/* iPhone SE (375x667) and small phones */
@media (max-width: 390px) {
  .grid-container {
    padding: 12px;
    gap: 10px;
  }

  .widget-row {
    padding: 12px;
    gap: 12px;
    border-radius: 14px;
  }

  .widget-icon {
    font-size: 28px;
    width: 44px;
    height: 44px;
    border-radius: 12px;
  }

  .widget-title {
    font-size: 14px;
  }

  .widget-subtitle {
    font-size: 12px;
  }

  .widget-stats {
    display: none;
  }

  .bottom-bar {
    margin: 0 8px 8px;
    padding: 10px 12px;
    border-radius: 16px;
  }

  .input-area input {
    font-size: 16px; /* Prevent zoom on iOS */
    padding: 10px 12px;
  }

  .traffic-lights {
    top: 8px;
    left: 8px;
    padding: 3px 6px;
  }
}

/* iPhone 14/15/16 (393x852) */
@media (min-width: 391px) and (max-width: 430px) {
  .grid-container {
    padding: 16px;
    gap: 12px;
  }

  .widget-row {
    padding: 14px 16px;
  }

  .widget-stats .stat:nth-child(3) {
    display: none;
  }

  .bottom-bar {
    margin: 0 12px 12px;
  }
}

/* iPhone Pro Max (430x932) */
@media (min-width: 431px) and (max-width: 500px) {
  .grid-container {
    padding: 16px;
    gap: 14px;
  }
}

/* iPad Mini / Small Tablet (768px) */
@media (min-width: 501px) and (max-width: 834px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    padding: 20px;
    gap: 16px;
  }

  .widget-row {
    padding: 16px 20px;
  }

  .bottom-bar {
    max-width: 600px;
    margin: 0 auto 16px;
  }
}

/* iPad (834px) and iPad Air (820px) */
@media (min-width: 835px) and (max-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    padding: 24px;
    gap: 20px;
  }

  .bottom-bar {
    max-width: 700px;
    margin: 0 auto 20px;
  }
}

/* iPad Pro 11" (1024px) */
@media (min-width: 1025px) and (max-width: 1194px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    padding: 28px;
    gap: 20px;
  }

  .bottom-bar {
    max-width: 800px;
  }
}

/* iPad Pro 12.9" and MacBook (1366px+) */
@media (min-width: 1195px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    padding: 32px;
    gap: 24px;
  }

  .widget-row {
    padding: 18px 22px;
    gap: 18px;
  }

  .widget-icon {
    font-size: 40px;
    width: 56px;
    height: 56px;
  }

  .widget-title {
    font-size: 17px;
  }

  .bottom-bar {
    max-width: 900px;
    margin: 0 auto 24px;
    padding: 14px 20px;
  }
}

/* Large Desktop (1920px+) */
@media (min-width: 1920px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    padding: 40px;
    gap: 28px;
  }
}

/* Landscape mode on phones */
@media (max-height: 500px) and (orientation: landscape) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    padding: 12px;
    gap: 10px;
  }

  .widget-row {
    padding: 10px 14px;
  }

  .widget-icon {
    font-size: 24px;
    width: 40px;
    height: 40px;
  }

  .traffic-lights {
    top: 6px;
    left: 6px;
  }

  .bottom-bar {
    margin: 0 8px 8px;
    padding: 8px 12px;
    border-radius: 14px;
  }
}

/* Safe area insets for notched devices */
@supports (padding-top: env(safe-area-inset-top)) {
  .topic-grid {
    padding-top: env(safe-area-inset-top);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }

  .bottom-bar {
    padding-bottom: calc(12px + env(safe-area-inset-bottom));
    margin-bottom: env(safe-area-inset-bottom);
  }
}

/* Reduce motion for accessibility */
@media (prefers-reduced-motion: reduce) {
  .widget-row,
  .bottom-bar,
  .chat-msg,
  .traffic-light,
  * {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}

</style>
