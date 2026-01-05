<template>
  <div id="app" class="app-shell">
    <!-- Minimal drag region for window controls -->
    <header class="topbar minimal" data-tauri-drag-region>
      <div class="traffic-light-spacer"></div>
    </header>

    <!-- 24h Progress Panel (collapsible) -->
    <Transition name="slide">
      <div v-if="showProgress" class="progress-panel">
        <ActivityLog :entries="activityEntries" :summary="activitySummary" />
      </div>
    </Transition>

    <!-- Main Content: Full-Screen Gallery with unified Project/Chat modes -->
    <main class="gallery-container">
      <TopicGrid
        :searchQuery="searchQuery"
        :expandedProjectId="expandedProjectId"
        :viewMode="viewMode"
        @expand-project="handleExpandProject"
        @collapse-project="expandedProjectId = null"
        @approve-task="handleApproveTask"
        @approve-all="handleApproveAllTasks"
        @open-chat="handleOpenProjectChat"
        @search="handleSearchFromGrid"
        @add-project="handleAddProject"
        @delete-project="handleDeleteProject"
      />
    </main>

    <!-- Morning Brief Modal -->
    <Teleport to="body">
      <div v-if="showMorningBrief" class="modal-overlay" @click.self="showMorningBrief = false">
        <div class="morning-brief-modal">
          <div class="modal-header">
            <h2>☀️ Good {{ timeOfDay }}, David</h2>
            <button @click="showMorningBrief = false">×</button>
          </div>
          <div class="modal-body">
            <div class="brief-section">
              <h3>Overnight Summary</h3>
              <p>{{ overnightSummary }}</p>
            </div>
            <div class="brief-section">
              <h3>Today's Suggestions</h3>
              <ul class="suggestions-list">
                <li v-for="suggestion in todaySuggestions" :key="suggestion.id">
                  <span class="suggestion-project">{{ suggestion.project }}</span>
                  <span class="suggestion-task">{{ suggestion.description }}</span>
                  <button class="approve-btn" @click="handleApproveTask(suggestion)">Approve</button>
                </li>
              </ul>
            </div>
            <button class="approve-all-btn" @click="handleApproveAllSuggestions">
              Approve All Suggestions ({{ todaySuggestions.length }})
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Command Palette (⌘K) -->
    <CommandPalette
      :isVisible="showCommandPalette"
      @close="showCommandPalette = false"
      @command="handleCommand"
    />

    <!-- Toast Notifications -->
    <ToastContainer />

    <!-- Add Project Modal -->
    <Teleport to="body">
      <div v-if="showAddProject" class="modal-overlay" @click.self="showAddProject = false">
        <div class="add-project-modal">
          <div class="modal-header">
            <h2>Add New Project</h2>
            <button @click="showAddProject = false">×</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Project Name</label>
              <input
                v-model="newProjectName"
                type="text"
                class="form-input"
                placeholder="My Project"
                @keydown.enter="confirmAddProject"
                autofocus
              />
            </div>
            <div class="form-group">
              <label>Icon (emoji) - click to select or type your own</label>
              <div class="icon-picker">
                <input
                  v-model="newProjectIcon"
                  type="text"
                  class="form-input icon-input"
                  placeholder="📁"
                />
                <div class="emoji-categories">
                  <button
                    v-for="cat in emojiCategories"
                    :key="cat.name"
                    class="category-btn"
                    :class="{ active: selectedEmojiCategory === cat.name }"
                    @click="selectedEmojiCategory = cat.name"
                  >
                    {{ cat.icon }}
                  </button>
                </div>
                <div class="emoji-grid">
                  <button
                    v-for="emoji in currentCategoryEmojis"
                    :key="emoji"
                    @click="newProjectIcon = emoji"
                    class="emoji-btn"
                    :class="{ selected: newProjectIcon === emoji }"
                  >
                    {{ emoji }}
                  </button>
                </div>
              </div>
            </div>
            <button class="create-btn" @click="confirmAddProject">
              Create Project
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Global Chat Panel -->
    <ChatPanel
      v-if="showChat"
      :projectId="chatProjectId"
      :projectName="chatProjectName"
      @close="showChat = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

// Core components
import ToastContainer from './components/ToastContainer.vue'

// Lazy-loaded components
const TopicGrid = defineAsyncComponent(() => import('./components/TopicGrid.vue'))
const CommandPalette = defineAsyncComponent(() => import('./components/CommandPalette.vue'))
const ActivityLog = defineAsyncComponent(() => import('./components/ActivityLog.vue'))
const ChatPanel = defineAsyncComponent(() => import('./components/ChatPanel.vue'))

// Composables
import { useToast } from './composables/useToast'
import { useActivityLog } from './composables/useActivityLog'
import { useProjectStore } from './stores/projectStore'

const toast = useToast()
const { entries: activityEntries, summary: activitySummary, logActivity } = useActivityLog()
const projectStore = useProjectStore()

// UI State
const searchQuery = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
const showProgress = ref(false)
const showMorningBrief = ref(false)
const showCommandPalette = ref(false)
const expandedProjectId = ref<string | null>(null)
const showChat = ref(false)
const chatProjectId = ref<string | null>(null)
const chatProjectName = ref<string | null>(null)
const showAddProject = ref(false)
const viewMode = ref<'projects' | 'chats'>('projects')
const newProjectName = ref('')
const newProjectIcon = ref('📁')
const selectedEmojiCategory = ref('objects')

// Full emoji set organized by category
const emojiCategories = [
  { name: 'objects', icon: '📁', emojis: ['📁', '📂', '📄', '📋', '📌', '📎', '🔗', '📦', '📫', '📬', '📭', '📮', '📯', '📰', '📱', '📲', '💻', '🖥️', '🖨️', '⌨️', '🖱️', '💾', '💿', '📀', '🎥', '📹', '📷', '📸', '🔍', '🔎', '🔬', '🔭', '📡', '💡', '🔦', '🏮', '📔', '📕', '📖', '📗', '📘', '📙', '📚', '📓', '📒', '📃', '📜', '📄', '📰', '🗞️', '📑', '🔖', '🏷️', '💰', '💴', '💵', '💶', '💷', '💸', '💳', '🧾', '💹'] },
  { name: 'tech', icon: '🤖', emojis: ['🤖', '👾', '🎮', '🕹️', '🎰', '🔌', '🔋', '💻', '🖥️', '⌨️', '🖱️', '🖲️', '💾', '💿', '📀', '📱', '📟', '📠', '🔧', '🔩', '⚙️', '🛠️', '⛏️', '🔨', '⚒️', '🛡️', '🗡️', '⚔️', '🔫', '🏹', '🛸', '🚀', '✈️', '🛩️', '🛰️', '📡', '🧲', '🔬', '🔭', '💉', '🩺', '🩹', '🧬', '🦠', '🧪', '🧫', '🧯', '🔥', '💧', '🌊'] },
  { name: 'media', icon: '🎵', emojis: ['🎵', '🎶', '🎼', '🎹', '🥁', '🎷', '🎺', '🎸', '🪕', '🎻', '🎤', '🎧', '📻', '🎬', '🎥', '📹', '📺', '📷', '📸', '🖼️', '🎨', '🖌️', '🖍️', '✏️', '✒️', '🖊️', '🖋️', '📝', '🎭', '🎪', '🎟️', '🎫', '🎗️', '🏅', '🥇', '🥈', '🥉', '🏆', '⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🎱', '🏓', '🏸', '🥊'] },
  { name: 'nature', icon: '🌿', emojis: ['🌿', '🍀', '🌱', '🌲', '🌳', '🌴', '🌵', '🌾', '🌷', '🌸', '🌹', '🌺', '🌻', '🌼', '🪻', '🪷', '💐', '🍁', '🍂', '🍃', '🪹', '🪺', '🐚', '🌍', '🌎', '🌏', '🌐', '🗺️', '🧭', '🏔️', '⛰️', '🌋', '🗻', '🏕️', '🏖️', '🏜️', '🏝️', '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌦️', '🌧️', '⛈️', '🌩️', '🌨️', '❄️', '☃️', '⛄', '🌬️'] },
  { name: 'animals', icon: '🐱', emojis: ['🐱', '🐶', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🦆', '🦅', '🦉', '🦇', '🐺', '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🐞', '🐜', '🦟', '🦗', '🕷️', '🦂', '🐢', '🐍', '🦎', '🦖', '🦕', '🐙', '🦑', '🦐', '🦞', '🦀'] },
  { name: 'food', icon: '🍕', emojis: ['🍕', '🍔', '🍟', '🌭', '🥪', '🌮', '🌯', '🫔', '🥙', '🧆', '🥚', '🍳', '🥘', '🍲', '🫕', '🥣', '🥗', '🍿', '🧈', '🧂', '🥫', '🍝', '🍜', '🍛', '🍣', '🍱', '🥟', '🦪', '🍤', '🍙', '🍚', '🍘', '🍥', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧', '🧁', '🍰', '🎂', '🍮', '🍭', '🍬', '🍫', '🍩', '🍪', '☕'] },
  { name: 'travel', icon: '✈️', emojis: ['✈️', '🛫', '🛬', '🛩️', '💺', '🚀', '🛸', '🚁', '🛶', '⛵', '🚤', '🛥️', '🛳️', '⛴️', '🚢', '🚂', '🚃', '🚄', '🚅', '🚆', '🚇', '🚈', '🚉', '🚊', '🚝', '🚞', '🚋', '🚌', '🚍', '🚎', '🚐', '🚑', '🚒', '🚓', '🚔', '🚕', '🚖', '🚗', '🚘', '🚙', '🛻', '🚚', '🚛', '🚜', '🏎️', '🏍️', '🛵', '🦽', '🦼', '🛺', '🚲'] },
  { name: 'symbols', icon: '💎', emojis: ['💎', '💍', '👑', '💫', '✨', '⭐', '🌟', '💥', '💢', '💦', '💨', '🕳️', '💣', '💬', '👁️‍🗨️', '🗨️', '🗯️', '💭', '💤', '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❤️‍🔥', '❤️‍🩹', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️', '✝️', '☪️', '🕉️', '☸️', '✡️', '🔯', '🕎', '☯️', '☦️', '🛐', '⛎'] },
  { name: 'flags', icon: '🏳️', emojis: ['🏳️', '🏴', '🏁', '🚩', '🎌', '🏴‍☠️', '🇺🇸', '🇬🇧', '🇨🇦', '🇦🇺', '🇯🇵', '🇰🇷', '🇨🇳', '🇮🇳', '🇧🇷', '🇲🇽', '🇫🇷', '🇩🇪', '🇮🇹', '🇪🇸', '🇷🇺', '🇳🇱', '🇧🇪', '🇨🇭', '🇦🇹', '🇵🇱', '🇸🇪', '🇳🇴', '🇩🇰', '🇫🇮', '🇮🇪', '🇵🇹', '🇬🇷', '🇹🇷', '🇮🇱', '🇸🇦', '🇦🇪', '🇿🇦', '🇪🇬', '🇳🇬', '🇰🇪', '🇹🇭', '🇻🇳', '🇮🇩', '🇵🇭', '🇲🇾', '🇸🇬', '🇳🇿', '🇦🇷', '🇨🇴'] },
  { name: 'smileys', icon: '😀', emojis: ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '☺️', '😚', '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕'] },
]

const currentCategoryEmojis = computed(() => {
  const cat = emojiCategories.find(c => c.name === selectedEmojiCategory.value)
  return cat?.emojis || []
})

// Computed - note: projectStore.projects is a ComputedRef, need .value
const totalIssues = computed(() => {
  const projects = projectStore.projects.value || []
  return projects.reduce((sum, p) => sum + (p.issues?.length || 0), 0)
})

const overallHealth = computed(() => {
  const projects = projectStore.projects.value || []
  if (projects.some(p => p.status === 'error')) return 'error'
  if (projects.some(p => p.status === 'warning')) return 'warning'
  return 'healthy'
})

const healthSummary = computed(() => {
  const projects = projectStore.projects.value || []
  const healthy = projects.filter(p => p.status === 'healthy').length
  const total = projects.length
  if (totalIssues.value > 0) {
    return `${totalIssues.value} issues`
  }
  return `${healthy}/${total} healthy`
})

const timeOfDay = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'morning'
  if (hour < 17) return 'afternoon'
  return 'evening'
})

const overnightSummary = computed(() => {
  const completed = activitySummary.value?.totalTasks || 0
  const hours = activitySummary.value?.totalHours || 0
  return `${completed} tasks completed (${hours.toFixed(1)}h of work)`
})

const todaySuggestions = computed(() => {
  // Aggregate suggestions from all projects
  const projects = projectStore.projects.value || []
  return projects.flatMap(p =>
    (p.suggestedTasks || []).slice(0, 2).map(t => ({
      ...t,
      project: p.name,
      projectId: p.id
    }))
  ).slice(0, 10)
})

// Handlers
function handleSearchSubmit() {
  if (!searchQuery.value.trim()) return

  // Check if it's a command
  if (searchQuery.value.startsWith('/')) {
    handleCommand(searchQuery.value.slice(1))
  } else {
    // Natural language - send to AI router
    handleNaturalLanguage(searchQuery.value)
  }
  searchQuery.value = ''
}

function handleSearchFromGrid(query: string) {
  searchQuery.value = query
  handleSearchSubmit()
}

async function handleNaturalLanguage(query: string) {
  // Open chat panel and let ChatPanel handle the message
  showChat.value = true
  chatProjectId.value = expandedProjectId.value

  // Find project name if we have an expanded project
  if (expandedProjectId.value) {
    const projects = projectStore.projects.value || []
    const project = projects.find(p => p.id === expandedProjectId.value)
    chatProjectName.value = project?.name || null
  } else {
    chatProjectName.value = null
  }

  // The ChatPanel will handle the actual message sending
  // We just need to pass the initial query - but ChatPanel needs to receive it
  // For now, just open the chat - user can re-type or we enhance later
  toast.info('Opening chat - type your message there')
}

function handleCommand(command: string) {
  console.log('[App] Command:', command)

  switch (command.toLowerCase()) {
    case 'fix all':
      handleFixAll()
      break
    case 'morning brief':
    case 'brief':
      showMorningBrief.value = true
      break
    case 'progress':
    case '24h':
      showProgress.value = !showProgress.value
      break
    default:
      handleNaturalLanguage(command)
  }
}

function handleExpandProject(projectId: string) {
  expandedProjectId.value = projectId
}

function handleOpenProjectChat(projectId: string, projectName: string) {
  chatProjectId.value = projectId
  chatProjectName.value = projectName
  showChat.value = true
}

function handleDeleteProject(projectId: string) {
  const success = projectStore.deleteProject(projectId)
  if (success) {
    expandedProjectId.value = null
    toast.success('Project deleted')
    logActivity({
      project: projectId,
      action: 'Project deleted',
      status: 'success'
    })
  } else {
    toast.error('Failed to delete project')
  }
}

function handleAddProject() {
  // Open the add project modal
  newProjectName.value = ''
  newProjectIcon.value = '📁'
  showAddProject.value = true
}

function confirmAddProject() {
  if (!newProjectName.value.trim()) {
    toast.error('Project name is required')
    return
  }

  // Create a new project
  const newProject = {
    id: `project-${Date.now()}`,
    name: newProjectName.value.trim(),
    icon: newProjectIcon.value || '📁',
    description: '',
    status: 'idle' as const,
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [],
    suggestedTasks: [],
    runningTasks: [],
    tags: []
  }

  // Add to store (directly mutating the reactive array)
  const projects = projectStore.projects.value || []
  projects.push(newProject)

  toast.success(`Created project: ${newProject.name}`)
  logActivity({
    project: newProject.name,
    action: 'Project created',
    status: 'success'
  })

  showAddProject.value = false
}

async function handleApproveTask(task: any) {
  const projectId = task.projectId
  const taskId = task.id

  // Remove from suggestions and get task details
  const approvedTask = projectStore.approveTask(projectId, taskId)

  if (!approvedTask) {
    // Task might already be approved or not exist
    console.warn('[App] Task not found in suggestions:', taskId)
  }

  // Add to running tasks immediately for visual feedback
  const runningTask = {
    id: `running-${Date.now()}`,
    description: task.description,
    command: task.command,
    progress: 0,
    eta: `~${task.estimatedHours || 1}h`,
    startedAt: new Date()
  }
  projectStore.addRunningTask(projectId, runningTask)

  toast.success(`▶ Started: ${task.description}`)

  // Log the activity
  logActivity({
    project: task.project || projectId,
    action: `Started task: ${task.description}`,
    status: 'success'
  })

  // Simulate task progress (in reality, backend would send updates)
  simulateTaskProgress(projectId, runningTask.id, task.estimatedHours || 1)

  // Try to queue in backend (may not exist yet)
  try {
    await invoke('queue_background_task', {
      projectId: projectId,
      taskId: taskId,
      command: task.command
    })
  } catch (e) {
    console.log('[App] Backend task queue not available, simulating locally')
  }
}

// Simulate task progress for visual feedback
function simulateTaskProgress(projectId: string, taskId: string, hours: number) {
  const totalMs = Math.min(hours * 60000, 300000) // Cap at 5 mins for demo
  const startTime = Date.now()

  const interval = setInterval(() => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(Math.round((elapsed / totalMs) * 100), 100)
    const remainingMs = totalMs - elapsed
    const eta = remainingMs > 0 ? `${Math.ceil(remainingMs / 1000)}s` : 'Done'

    projectStore.updateTaskProgress(projectId, taskId, progress, eta)

    if (progress >= 100) {
      clearInterval(interval)
      setTimeout(() => {
        projectStore.completeTask(projectId, taskId)
        toast.success(`Task completed!`)
        logActivity({
          project: projectId,
          action: `Completed task`,
          status: 'success',
          duration: Math.round(totalMs / 1000)
        })
      }, 1000)
    }
  }, 1000)
}

function handleApproveAllTasks(projectId: string) {
  const projects = projectStore.projects.value || []
  const project = projects.find(p => p.id === projectId)
  if (!project) return

  project.suggestedTasks?.forEach(task => {
    handleApproveTask({ ...task, projectId })
  })

  toast.success(`Approved all tasks for ${project.name}`)
}

function handleApproveAllSuggestions() {
  todaySuggestions.value.forEach(handleApproveTask)
  showMorningBrief.value = false
  toast.success(`Approved ${todaySuggestions.value.length} tasks`)
}

async function handleFixAll() {
  toast.info('Auto-fixing all issues...')

  try {
    await invoke('auto_fix_all_issues')
    toast.success('All issues fixed!')
    logActivity({
      project: 'System',
      action: `Auto-fixed ${totalIssues.value} issues`,
      status: 'success'
    })
  } catch (e) {
    console.error('[App] Fix all failed:', e)
    toast.error('Some issues could not be auto-fixed')
  }
}

// Keyboard shortcuts
function handleKeyDown(event: KeyboardEvent) {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const cmdOrCtrl = isMac ? event.metaKey : event.ctrlKey

  // ⌘K: Focus search / Command palette
  if (cmdOrCtrl && event.key === 'k') {
    event.preventDefault()
    if (document.activeElement === searchInput.value) {
      showCommandPalette.value = true
    } else {
      searchInput.value?.focus()
    }
    return
  }

  // ⌘1-9: Jump to project by index
  if (cmdOrCtrl && event.key >= '1' && event.key <= '9') {
    event.preventDefault()
    const index = parseInt(event.key, 10) - 1
    const projects = projectStore.projects.value || []
    if (index < projects.length) {
      expandedProjectId.value = projects[index].id
    }
    return
  }

  // Space: Expand/collapse selected project (when not in input or textarea)
  if (event.key === ' ' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
    event.preventDefault()
    if (expandedProjectId.value) {
      expandedProjectId.value = null
    }
    return
  }

  // A: Approve all (when project expanded)
  if (event.key === 'a' && !event.metaKey && !event.ctrlKey && expandedProjectId.value) {
    if (document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
      event.preventDefault()
      handleApproveAllTasks(expandedProjectId.value)
    }
    return
  }

  // Escape: Close expanded project or modals, or return to projects view
  if (event.key === 'Escape') {
    if (showCommandPalette.value) {
      showCommandPalette.value = false
    } else if (showMorningBrief.value) {
      showMorningBrief.value = false
    } else if (showChat.value) {
      showChat.value = false
    } else if (showProgress.value) {
      showProgress.value = false
    } else if (viewMode.value === 'chats') {
      viewMode.value = 'projects'
    } else if (expandedProjectId.value) {
      expandedProjectId.value = null
    }
    return
  }

  // ⌘G: Toggle chat grid view
  if (cmdOrCtrl && event.key === 'g') {
    event.preventDefault()
    viewMode.value = viewMode.value === 'projects' ? 'chats' : 'projects'
    return
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)

  // Load projects from SSOT
  await projectStore.loadProjects()

  // Check for morning brief (first open of the day)
  const lastBrief = localStorage.getItem('sam_last_brief')
  const today = new Date().toDateString()
  if (lastBrief !== today) {
    showMorningBrief.value = true
    localStorage.setItem('sam_last_brief', today)
  }

  // Start activity log sync
  // activityLog.startSync()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<!-- Global styles - transparent window -->
<style>
html, body, #app {
  background: transparent !important;
  margin: 0;
  padding: 0;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>

<style scoped>
/* ==========================================================================
   SAM DASHBOARD - Apple Design System
   Clean, opaque design that works on all Apple devices
   ========================================================================== */

.app-shell {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  /* Native macOS: let vibrancy show through, no colored tint */
  background: transparent;
  /* System primary text color */
  color: rgba(255, 255, 255, 0.88);
  /* Native SF Pro font stack */
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', system-ui, sans-serif;
  font-size: 13px;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: -0.08px;
}

/* ==========================================================================
   TOP BAR - Search & Actions
   ========================================================================== */

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  padding-top: 8px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  gap: 16px;
  -webkit-app-region: drag;
}

/* Minimal topbar - just drag region for window controls */
.topbar.minimal {
  padding: 6px 16px;
  background: transparent;
  border-bottom: none;
  justify-content: flex-start;
}

/* Space for macOS traffic light buttons */
.traffic-light-spacer {
  width: 70px;
  height: 20px;
  flex-shrink: 0;
  -webkit-app-region: no-drag;
}

/* Search/Chat Bar */
/* === SEARCH BAR - Clean Apple Style === */
.search-chat-bar {
  flex: 1;
  max-width: 800px;
  display: flex;
  align-items: center;
  background: #2c2c2e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 0 16px;
  height: 44px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: all 0.2s ease;
  -webkit-app-region: no-drag;
}

.search-chat-bar:focus-within {
  background: #3a3a3c;
  border-color: #E35205;
  box-shadow: 0 0 0 3px rgba(227, 82, 5, 0.2);
}

.search-icon {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.4);
  margin-right: 12px;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #ffffff;
  font-size: 16px;
  font-weight: 400;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.search-hints {
  display: flex;
  gap: 8px;
}

.hint {
  font-size: 11px;
  font-family: 'SF Mono', monospace;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 8px;
  border-radius: 6px;
}

/* Top Bar Actions */
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  -webkit-app-region: no-drag;
}

/* === SEGMENTED CONTROL (Apple-style) === */
.segmented-control {
  display: flex;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 3px;
  gap: 2px;
}

.segment {
  width: 36px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.segment svg {
  width: 16px;
  height: 16px;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.segment:hover {
  color: rgba(255, 255, 255, 0.8);
}

.segment:hover svg {
  transform: scale(1.1);
}

.segment.active {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.segment.active svg {
  transform: scale(1.05);
}

/* === ICON BUTTON GROUP === */
.icon-btn-group {
  display: flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 4px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.icon-btn svg {
  width: 18px;
  height: 18px;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.icon-btn:hover svg {
  transform: scale(1.15);
}

.icon-btn:active svg {
  transform: scale(0.9);
}

.icon-btn.active {
  background: rgba(227, 82, 5, 0.2);
  color: #E35205;
}

.icon-btn.attention {
  color: #ff9500;
  animation: attention-pulse 2s ease-in-out infinite;
}

@keyframes attention-pulse {
  0%, 100% { background: transparent; }
  50% { background: rgba(255, 149, 0, 0.15); }
}

.icon-btn .badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: #ff3b30;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* === STATUS PILL (Header) === */
.status-pill-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  position: relative;
  overflow: hidden;
}

.status-pill-header .pulse-ring {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #34c759;
  position: relative;
}

.status-pill-header .pulse-ring::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid #34c759;
  animation: ring-pulse 2s ease-out infinite;
}

@keyframes ring-pulse {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.8); opacity: 0; }
}

.status-pill-header.warning .pulse-ring,
.status-pill-header.warning .pulse-ring::before {
  background: #ff9500;
  border-color: #ff9500;
}

.status-pill-header.error .pulse-ring,
.status-pill-header.error .pulse-ring::before {
  background: #ff3b30;
  border-color: #ff3b30;
}

.status-pill-header .status-label {
  white-space: nowrap;
}

/* ==========================================================================
   PROGRESS PANEL (24h)
   ========================================================================== */

.progress-panel {
  background: rgba(0, 0, 0, 0.4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding: 20px 24px;
  max-height: 300px;
  overflow-y: auto;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  padding: 0 24px;
  opacity: 0;
}

/* ==========================================================================
   GALLERY CONTAINER
   ========================================================================== */

.gallery-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* ==========================================================================
   MORNING BRIEF MODAL
   ========================================================================== */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.morning-brief-modal {
  background: linear-gradient(180deg, #1c1c24 0%, #16161e 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-header h2 {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.modal-header button {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
}

.modal-header button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  max-height: calc(80vh - 80px);
}

.brief-section {
  margin-bottom: 24px;
}

.brief-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 12px 0;
}

.brief-section p {
  font-size: 18px;
  color: #ffffff;
  margin: 0;
}

.suggestions-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.suggestions-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  margin-bottom: 8px;
}

.suggestion-project {
  font-size: 12px;
  font-weight: 600;
  color: #E35205;
  background: rgba(227, 82, 5, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
}

.suggestion-task {
  flex: 1;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

.approve-btn {
  padding: 6px 14px;
  background: rgba(52, 199, 89, 0.15);
  border: 1px solid rgba(52, 199, 89, 0.3);
  border-radius: 8px;
  color: #34c759;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.approve-btn:hover {
  background: rgba(52, 199, 89, 0.25);
}

.approve-all-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #E35205 0%, #C9A962 100%);
  border: none;
  border-radius: 12px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 16px;
}

.approve-all-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(227, 82, 5, 0.4);
}

/* Floating Chat Button */
/* === FLOATING CHAT BUTTON - Clean Apple Style === */
.chat-fab {
  position: fixed;
  bottom: 100px;
  right: 28px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #E35205 0%, #C9A962 100%);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(227, 82, 5, 0.4);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.chat-fab .fab-icon {
  width: 28px;
  height: 28px;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  z-index: 2;
}

.chat-fab .fab-dot {
  opacity: 0.7;
  animation: fab-dot-pulse 1.5s ease-in-out infinite;
}

.chat-fab .fab-dot:nth-child(2) { animation-delay: 0.15s; }
.chat-fab .fab-dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes fab-dot-pulse {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.chat-fab .fab-ripple {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle at center, rgba(255,255,255,0.3) 0%, transparent 70%);
  transform: scale(0);
  transition: transform 0.5s ease;
}

.chat-fab:hover {
  transform: scale(1.12) translateY(-6px);
  box-shadow:
    0 16px 48px rgba(227, 82, 5, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.15) inset,
    0 1px 0 rgba(255, 255, 255, 0.3) inset;
}

.chat-fab:hover .fab-icon {
  transform: scale(1.1);
}

.chat-fab:hover .fab-ripple {
  transform: scale(1.5);
}

.chat-fab:active {
  transform: scale(0.92);
  transition-duration: 0.1s;
}

/* FAB morph animation */
.fab-morph-enter-active {
  animation: fab-enter 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.fab-morph-leave-active {
  animation: fab-leave 0.3s ease-out;
}

@keyframes fab-enter {
  0% { opacity: 0; transform: scale(0) rotate(-180deg); }
  100% { opacity: 1; transform: scale(1) rotate(0deg); }
}

@keyframes fab-leave {
  0% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(0) rotate(90deg); }
}

/* Add Project Modal */
.add-project-modal {
  background: linear-gradient(180deg, #1c1c24 0%, #16161e 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  width: 90%;
  max-width: 400px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #ffffff;
  font-size: 16px;
  outline: none;
  transition: all 0.2s ease;
}

.form-input:focus {
  border-color: rgba(227, 82, 5, 0.5);
  background: rgba(255, 255, 255, 0.08);
}

.icon-picker {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.icon-input {
  width: 80px;
  text-align: center;
  font-size: 32px;
  padding: 16px;
}

.emoji-categories {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.category-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.category-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.category-btn.active {
  background: rgba(227, 82, 5, 0.2);
  box-shadow: 0 0 0 2px rgba(227, 82, 5, 0.4);
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
  padding: 4px;
}

.emoji-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.emoji-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: scale(1.15);
}

.emoji-btn.selected {
  background: rgba(227, 82, 5, 0.3);
  box-shadow: 0 0 0 2px #E35205;
}

.create-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #E35205 0%, #C9A962 100%);
  border: none;
  border-radius: 12px;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(227, 82, 5, 0.4);
}
</style>
