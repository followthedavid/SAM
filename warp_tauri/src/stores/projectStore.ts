// Project Store - Central state for all projects
import { reactive, computed } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

export interface ProjectGoal {
  id: string
  description: string
  status: 'pending' | 'in_progress' | 'complete'
  progress?: number
}

export interface TaskConfig {
  [key: string]: string | number | boolean
}

export interface ProjectTask {
  id: string
  description: string
  estimatedHours: number
  command: string
  approved?: boolean
  // Editable configuration options
  config?: TaskConfig
  configSchema?: {
    [key: string]: {
      type: 'string' | 'number' | 'boolean' | 'select'
      label: string
      default: string | number | boolean
      options?: string[] // For select type
      description?: string
    }
  }
}

export interface RunningTask {
  id: string
  description: string
  command?: string  // The command being executed
  progress: number
  eta?: string
  pid?: number
  startedAt: Date
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  // Context chunks - structured breakdown of what was discussed/changed
  contextChunks?: {
    type: 'code' | 'decision' | 'task' | 'insight'
    summary: string
    details?: string
    files?: string[]
  }[]
}

export interface ProjectChat {
  messages: ChatMessage[]
  lastActivity: Date | null
}

export interface Project {
  id: string
  name: string
  icon: string
  description?: string
  status: 'healthy' | 'warning' | 'error' | 'idle'

  // Metrics
  metrics: {
    linesOfCode: number
    filesModified: number
    lastActivity: Date | null
  }

  // Goals with progress
  goals: ProjectGoal[]

  // Suggested tasks (10+ hours worth)
  suggestedTasks: ProjectTask[]

  // Currently running tasks
  runningTasks: RunningTask[]

  // Issues requiring attention
  issues?: string[]

  // Project path (for code projects)
  path?: string

  // Tags for filtering
  tags?: string[]

  // Chat history for this project
  chat?: ProjectChat
}

// Initial projects - will be enhanced by SSOT
const defaultProjects: Project[] = [
  {
    id: 'stash',
    name: 'Stash',
    icon: '🎬',
    description: 'Media organization and metadata management',
    status: 'healthy',
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Organize 5000 scenes with metadata', status: 'complete' },
      { id: 'g2', description: 'Auto-tag performers via StashDB', status: 'in_progress', progress: 73 },
      { id: 'g3', description: 'Generate preview thumbnails', status: 'in_progress', progress: 45 },
      { id: 'g4', description: 'Set up Cloudflare caching', status: 'pending' },
    ],
    suggestedTasks: [
      {
        id: 't1',
        description: 'Regenerate all scene previews',
        estimatedHours: 4,
        command: 'stash:generate-previews',
        config: { previewType: 'video', duration: 60, segments: 30, excludeEnd: 5 },
        configSchema: {
          previewType: { type: 'select', label: 'Preview Type', default: 'video', options: ['video', 'sprite', 'both'], description: 'Video previews or sprite sheets' },
          duration: { type: 'number', label: 'Duration (seconds)', default: 60, description: 'Total preview length' },
          segments: { type: 'number', label: 'Segments', default: 30, description: 'Number of clips to include' },
          excludeEnd: { type: 'number', label: 'Exclude End (seconds)', default: 5, description: 'Skip last N seconds (avoid credits)' },
        }
      },
      {
        id: 't2',
        description: 'Run StashDB identify on unmatched',
        estimatedHours: 2,
        command: 'stash:identify',
        config: { source: 'stashdb', autoTag: true, matchThreshold: 80 },
        configSchema: {
          source: { type: 'select', label: 'Source', default: 'stashdb', options: ['stashdb', 'tpdb', 'all'], description: 'Which database to query' },
          autoTag: { type: 'boolean', label: 'Auto-tag performers', default: true, description: 'Automatically apply performer tags' },
          matchThreshold: { type: 'number', label: 'Match Threshold (%)', default: 80, description: 'Minimum confidence for auto-match' },
        }
      },
      {
        id: 't3',
        description: 'Warm Cloudflare cache for thumbnails',
        estimatedHours: 1,
        command: 'stash:warm-cache',
        config: { concurrent: 10, includeScreenshots: true, includePreviews: false },
        configSchema: {
          concurrent: { type: 'number', label: 'Concurrent Requests', default: 10, description: 'Parallel cache warming requests' },
          includeScreenshots: { type: 'boolean', label: 'Include Screenshots', default: true },
          includePreviews: { type: 'boolean', label: 'Include Previews', default: false, description: 'Also cache video previews (larger)' },
        }
      },
      { id: 't4', description: 'Clean duplicate performers', estimatedHours: 0.5, command: 'stash:clean-dupes' },
      { id: 't5', description: 'Export metadata backup', estimatedHours: 0.25, command: 'stash:backup' },
    ],
    runningTasks: [],
    tags: ['media', 'docker'],
  },
  {
    id: 'music',
    name: 'Music Library',
    icon: '🎵',
    description: 'Lossless music organization with beets',
    status: 'healthy',
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Import all FLAC files', status: 'complete' },
      { id: 'g2', description: 'Fix featured artists metadata', status: 'complete' },
      { id: 'g3', description: 'Fetch album artwork', status: 'in_progress', progress: 88 },
      { id: 'g4', description: 'Generate animated covers', status: 'pending' },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Scan for new music files', estimatedHours: 1, command: 'beets:import' },
      { id: 't2', description: 'Fetch missing lyrics', estimatedHours: 2, command: 'beets:lyrics' },
      { id: 't3', description: 'Update Navidrome library', estimatedHours: 0.5, command: 'navidrome:scan' },
    ],
    runningTasks: [],
    tags: ['media', 'beets'],
  },
  {
    id: 'sam',
    name: 'SAM Terminal',
    icon: '🤖',
    description: 'This application - Tauri + Vue + Rust',
    status: 'healthy',
    metrics: { linesOfCode: 15000, filesModified: 47, lastActivity: new Date() },
    goals: [
      { id: 'g1', description: 'Full-screen gallery layout', status: 'in_progress', progress: 60 },
      { id: 'g2', description: 'Project expansion panel', status: 'pending' },
      { id: 'g3', description: '24-hour activity log', status: 'pending' },
      { id: 'g4', description: 'Background task execution', status: 'pending' },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Build and deploy to /Applications', estimatedHours: 0.2, command: 'sam:build' },
      { id: 't2', description: 'Run test suite', estimatedHours: 0.1, command: 'sam:test' },
      { id: 't3', description: 'Generate TypeScript types', estimatedHours: 0.1, command: 'sam:types' },
    ],
    runningTasks: [],
    path: '/Users/davidquinton/ReverseLab/SAM/warp_tauri',
    tags: ['code', 'rust', 'vue'],
  },
  {
    id: 'rvc',
    name: 'RVC Voice Training',
    icon: '🎤',
    description: 'Voice cloning model training',
    status: 'idle',
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Collect training samples', status: 'complete' },
      { id: 'g2', description: 'Train voice model', status: 'in_progress', progress: 30 },
      { id: 'g3', description: 'Fine-tune for quality', status: 'pending' },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Continue training (50 epochs)', estimatedHours: 8, command: 'rvc:train' },
      { id: 't2', description: 'Test voice conversion', estimatedHours: 0.5, command: 'rvc:test' },
    ],
    runningTasks: [],
    tags: ['ai', 'training'],
  },
  {
    id: 'comfyui',
    name: 'ComfyUI',
    icon: '🎨',
    description: 'Image generation with Stable Diffusion',
    status: 'idle',
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Install and configure', status: 'complete' },
      { id: 'g2', description: 'Train LoRA on style', status: 'pending' },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Download latest checkpoints', estimatedHours: 1, command: 'comfyui:download-models' },
      { id: 't2', description: 'Start ComfyUI server', estimatedHours: 0.1, command: 'comfyui:start' },
    ],
    runningTasks: [],
    tags: ['ai', 'images'],
  },
  {
    id: 'ssot',
    name: 'SSOT System',
    icon: '🧠',
    description: 'Single Source of Truth - persistent memory',
    status: 'healthy',
    metrics: { linesOfCode: 500, filesModified: 12, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Code indexing complete', status: 'complete' },
      { id: 'g2', description: 'Context per project', status: 'in_progress', progress: 80 },
      { id: 'g3', description: 'Activity log integration', status: 'pending' },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Reindex all code', estimatedHours: 2, command: 'ssot:reindex' },
      { id: 't2', description: 'Sync with SAM state', estimatedHours: 0.5, command: 'ssot:sync' },
    ],
    runningTasks: [],
    path: '/Volumes/Plex/SSOT',
    tags: ['system', 'data'],
  },
  {
    id: 'cloudflare',
    name: 'Cloudflare Tunnel',
    icon: '☁️',
    description: 'Secure tunnels for services',
    status: 'healthy',
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Tunnel running stable', status: 'complete' },
      { id: 'g2', description: 'Cache rules configured', status: 'complete' },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Check tunnel health', estimatedHours: 0.1, command: 'cloudflared:status' },
      { id: 't2', description: 'Purge cache', estimatedHours: 0.1, command: 'cloudflare:purge' },
    ],
    runningTasks: [],
    tags: ['infrastructure'],
  },
  {
    id: 'topaz',
    name: 'Topaz Parity',
    icon: '💎',
    description: 'Video upscaling pipeline',
    status: 'idle',
    metrics: { linesOfCode: 0, filesModified: 0, lastActivity: null },
    goals: [
      { id: 'g1', description: 'Open source alternative research', status: 'in_progress', progress: 40 },
    ],
    suggestedTasks: [
      { id: 't1', description: 'Test Real-ESRGAN on samples', estimatedHours: 2, command: 'topaz:test-esrgan' },
    ],
    runningTasks: [],
    tags: ['video', 'ai'],
  },
]

// Reactive state
const state = reactive({
  projects: defaultProjects as Project[],
  loading: false,
  lastSync: null as Date | null,
})

// Computed
const projects = computed(() => state.projects)
const loading = computed(() => state.loading)

// Actions
async function loadProjects() {
  state.loading = true
  try {
    // Try to load from SSOT
    const ssotProjects = await invoke<Project[]>('load_projects_from_ssot').catch(() => null)
    if (ssotProjects && ssotProjects.length > 0) {
      state.projects = ssotProjects
    }
    state.lastSync = new Date()
  } catch (e) {
    console.error('[projectStore] Failed to load projects:', e)
  } finally {
    state.loading = false
  }
}

function updateProject(projectId: string, updates: Partial<Project>) {
  const index = state.projects.findIndex(p => p.id === projectId)
  if (index !== -1) {
    state.projects[index] = { ...state.projects[index], ...updates }
  }
}

function addRunningTask(projectId: string, task: RunningTask) {
  const project = state.projects.find(p => p.id === projectId)
  if (project) {
    project.runningTasks.push(task)
  }
}

// Approve a suggested task - moves it from suggestions to running
function approveTask(projectId: string, taskId: string): ProjectTask | null {
  const project = state.projects.find(p => p.id === projectId)
  if (!project) return null

  // Find and remove from suggestedTasks
  const taskIndex = project.suggestedTasks.findIndex(t => t.id === taskId)
  if (taskIndex === -1) return null

  const [task] = project.suggestedTasks.splice(taskIndex, 1)
  task.approved = true

  return task
}

function updateTaskProgress(projectId: string, taskId: string, progress: number, eta?: string) {
  const project = state.projects.find(p => p.id === projectId)
  if (project) {
    const task = project.runningTasks.find(t => t.id === taskId)
    if (task) {
      task.progress = progress
      if (eta) task.eta = eta
    }
  }
}

function completeTask(projectId: string, taskId: string) {
  const project = state.projects.find(p => p.id === projectId)
  if (project) {
    project.runningTasks = project.runningTasks.filter(t => t.id !== taskId)
  }
}

function getProjectById(id: string) {
  return state.projects.find(p => p.id === id)
}

function deleteProject(projectId: string) {
  const index = state.projects.findIndex(p => p.id === projectId)
  if (index !== -1) {
    state.projects.splice(index, 1)
    return true
  }
  return false
}

// Chat management
function addChatMessage(projectId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) {
  const project = state.projects.find(p => p.id === projectId)
  if (!project) return null

  if (!project.chat) {
    project.chat = { messages: [], lastActivity: null }
  }

  const newMessage: ChatMessage = {
    ...message,
    id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date()
  }

  project.chat.messages.push(newMessage)
  project.chat.lastActivity = new Date()

  // Persist to SSOT asynchronously
  persistChatToSSOT(projectId, project.chat).catch(console.error)

  return newMessage
}

function getProjectChat(projectId: string): ChatMessage[] {
  const project = state.projects.find(p => p.id === projectId)
  return project?.chat?.messages || []
}

function clearProjectChat(projectId: string) {
  const project = state.projects.find(p => p.id === projectId)
  if (project && project.chat) {
    project.chat.messages = []
    project.chat.lastActivity = null
  }
}

// Context detection - find which project a message relates to
function detectProjectContext(message: string): string | null {
  const lowerMessage = message.toLowerCase()

  // Build keyword map from projects
  for (const project of state.projects) {
    const keywords = [
      project.name.toLowerCase(),
      project.id.toLowerCase(),
      ...(project.tags || []).map(t => t.toLowerCase()),
      // Add project-specific terms
      ...(project.description?.toLowerCase().split(/\s+/) || []).filter(w => w.length > 4)
    ]

    // Check if message mentions any keywords
    for (const keyword of keywords) {
      if (keyword.length > 2 && lowerMessage.includes(keyword)) {
        return project.id
      }
    }
  }

  return null
}

// Route a message to the appropriate project based on content
function routeMessageToProject(message: string, defaultProjectId?: string): string {
  const detected = detectProjectContext(message)
  return detected || defaultProjectId || 'general'
}

// Persist chat to SSOT
async function persistChatToSSOT(projectId: string, chat: ProjectChat) {
  try {
    await invoke('save_project_chat', {
      projectId,
      messages: chat.messages.map(m => ({
        ...m,
        timestamp: m.timestamp.toISOString()
      }))
    })
  } catch (e) {
    // SSOT backend might not be implemented yet
    console.log('[projectStore] Chat persistence not available:', e)
  }
}

// Load chat history from SSOT
async function loadProjectChats() {
  try {
    const chats = await invoke<Record<string, any[]>>('load_project_chats')
    if (chats) {
      for (const [projectId, messages] of Object.entries(chats)) {
        const project = state.projects.find(p => p.id === projectId)
        if (project) {
          project.chat = {
            messages: messages.map(m => ({
              ...m,
              timestamp: new Date(m.timestamp)
            })),
            lastActivity: messages.length > 0 ? new Date(messages[messages.length - 1].timestamp) : null
          }
        }
      }
    }
  } catch (e) {
    console.log('[projectStore] Chat loading not available:', e)
  }
}

export function useProjectStore() {
  return {
    projects,
    loading,
    loadProjects,
    updateProject,
    addRunningTask,
    approveTask,
    updateTaskProgress,
    completeTask,
    getProjectById,
    deleteProject,
    // Chat functions
    addChatMessage,
    getProjectChat,
    clearProjectChat,
    detectProjectContext,
    routeMessageToProject,
    loadProjectChats,
  }
}
