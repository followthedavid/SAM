<template>
  <footer class="status-bar">
    <!-- Left: Git & CWD -->
    <div class="status-left">
      <!-- Git Branch -->
      <div v-if="gitBranch" class="status-item status-git">
        <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 3v12M18 9a3 3 0 100 6 3 3 0 000-6zM6 21a3 3 0 100-6 3 3 0 000 6zM18 12a9 9 0 01-9 9" stroke-linecap="round"/>
        </svg>
        <span class="git-branch">{{ gitBranch }}</span>
        <span v-if="gitDirty" class="git-dirty" title="Uncommitted changes">*</span>
      </div>

      <!-- Current Working Directory -->
      <div class="status-item status-cwd" :title="currentDirectory">
        <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>{{ displayPath }}</span>
      </div>
    </div>

    <!-- Center: Notifications -->
    <div class="status-center">
      <div v-if="activeNotification" class="status-notification" :class="activeNotification.type">
        {{ activeNotification.message }}
      </div>
    </div>

    <!-- Right: AI & Recording Status -->
    <div class="status-right">
      <!-- Character Library Button -->
      <div class="status-item status-characters" @click="toggleCharacterMenu">
        <span class="character-icon">🎭</span>
        <span>Characters</span>

        <!-- Character Dropdown Menu -->
        <div v-if="showCharacterMenu" class="character-menu" @click.stop>
          <div class="character-menu-header">
            <span class="menu-title">Roleplay Characters</span>
          </div>

          <button class="character-menu-btn" @click="openCharacterLibrary">
            <span>📚</span> Browse Library
            <span class="btn-hint">80+ archetypes</span>
          </button>

          <button class="character-menu-btn" @click="openCharacterCreator">
            <span>✨</span> Create New
            <span class="btn-hint">Custom character</span>
          </button>

          <div v-if="recentCharacters.length > 0" class="recent-characters">
            <div class="section-title">Recent</div>
            <button
              v-for="char in recentCharacters"
              :key="char.id"
              class="recent-character-btn"
              @click="selectCharacter(char)"
            >
              <span class="char-name">{{ char.name }}</span>
              <span class="char-archetype">{{ char.archetype || 'Custom' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Recording Indicator -->
      <div v-if="isRecording" class="status-item status-recording">
        <span class="recording-dot"></span>
        <span>{{ isPaused ? 'Paused' : 'Recording' }}</span>
      </div>

      <!-- AI Status -->
      <div class="status-item status-ai" :class="{ active: aiEnabled }">
        <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" stroke-linecap="round"/>
          <circle cx="9" cy="13" r="1"/>
          <circle cx="15" cy="13" r="1"/>
          <path d="M9 17h6"/>
        </svg>
        <span>{{ aiEnabled ? 'AI Active' : 'AI Off' }}</span>
      </div>

      <!-- Model Info -->
      <div v-if="aiEnabled && modelName" class="status-item status-model" :title="modelName">
        <span>{{ shortModelName }}</span>
      </div>

      <!-- MLX Connection (Clickable for controls) -->
      <div
        class="status-item status-connection"
        :class="{ connected: mlxConnected, loading: mlxLoading }"
        @click="toggleMLXMenu"
      >
        <span class="connection-dot" :class="{ spinning: mlxLoading }"></span>
        <span>{{ mlxLoading ? 'Loading...' : (mlxConnected ? 'MLX' : 'Offline') }}</span>

        <!-- MLX Dropdown Menu -->
        <div v-if="showMLXMenu" class="mlx-menu" @click.stop>
          <div class="mlx-menu-header">
            <span class="menu-title">MLX Controls</span>
            <span class="model-count">{{ availableModels.length }} models</span>
          </div>

          <!-- Status -->
          <div class="mlx-status-row">
            <span :class="mlxConnected ? 'status-ok' : 'status-error'">
              {{ mlxConnected ? '● Connected' : '○ Disconnected' }}
            </span>
          </div>

          <!-- Restart Button -->
          <button class="mlx-menu-btn" @click="restartMLX" :disabled="mlxLoading">
            <span>🔄</span> Restart MLX
          </button>

          <!-- Model Selection -->
          <div class="mlx-models" v-if="availableModels.length > 0">
            <div class="model-section-title">Models</div>
            <div
              v-for="model in availableModels"
              :key="model"
              class="model-item"
              :class="{ active: model === currentModel }"
            >
              <span class="model-name">{{ model }}</span>
              <div class="model-actions">
                <button
                  class="model-btn warm"
                  @click="warmModel(model)"
                  title="Pre-warm model"
                >
                  🔥
                </button>
                <button
                  class="model-btn unload"
                  @click="unloadModel(model)"
                  title="Unload from memory"
                >
                  💤
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

// Props
const props = defineProps<{
  currentDirectory?: string
  gitBranch?: string | null
  gitDirty?: boolean
  aiEnabled?: boolean
  modelName?: string
  isRecording?: boolean
  isPaused?: boolean
}>()

// MLX connection state (Ollama decommissioned 2026-01-18)
const mlxConnected = ref(false)
const mlxLoading = ref(false)
const showMLXMenu = ref(false)
const availableModels = ref<string[]>([])
const currentModel = ref<string | null>(null)

// Character menu state
const showCharacterMenu = ref(false)
const recentCharacters = ref<Array<{ id: string; name: string; archetype?: string }>>([])

// Emits for character actions
const emit = defineEmits<{
  openCharacterLibrary: []
  openCharacterCreator: []
  selectCharacter: [character: { id: string; name: string; archetype?: string }]
}>()

// Toggle character menu
function toggleCharacterMenu() {
  showCharacterMenu.value = !showCharacterMenu.value
  if (showCharacterMenu.value) {
    showMLXMenu.value = false
    loadRecentCharacters()
  }
}

// Load recent characters from backend
async function loadRecentCharacters() {
  try {
    const characters = await invoke<Array<{ id: string; name: string; archetype?: string; times_used: number }>>('cmd_list_saved_characters')
    // Sort by usage and take top 5
    recentCharacters.value = characters
      .sort((a, b) => b.times_used - a.times_used)
      .slice(0, 5)
  } catch (e) {
    console.error('Failed to load recent characters:', e)
  }
}

// Open character library
function openCharacterLibrary() {
  showCharacterMenu.value = false
  emit('openCharacterLibrary')
}

// Open character creator
function openCharacterCreator() {
  showCharacterMenu.value = false
  emit('openCharacterCreator')
}

// Select a recent character
function selectCharacter(character: { id: string; name: string; archetype?: string }) {
  showCharacterMenu.value = false
  emit('selectCharacter', character)
}

// Notification state
const activeNotification = ref<{ message: string; type: 'info' | 'success' | 'warning' | 'error' } | null>(null)

// Toggle MLX menu
function toggleMLXMenu() {
  showMLXMenu.value = !showMLXMenu.value
  if (showMLXMenu.value) {
    fetchMLXStatus()
  }
}

// Close menus when clicking outside
function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.status-connection')) {
    showMLXMenu.value = false
  }
  if (!target.closest('.status-characters')) {
    showCharacterMenu.value = false
  }
}

// Fetch MLX status via sam_api (Ollama decommissioned 2026-01-18)
async function fetchMLXStatus() {
  try {
    const response = await fetch('http://localhost:8765/api/status')
    if (response.ok) {
      const status = await response.json()
      mlxConnected.value = true
      availableModels.value = status.models || []
      currentModel.value = status.current_model || null
    } else {
      mlxConnected.value = false
    }
  } catch (e) {
    console.error('Failed to get MLX status:', e)
    mlxConnected.value = false
  }
}

// Restart MLX sam_api
async function restartMLX() {
  mlxLoading.value = true
  showNotification('Restarting MLX sam_api...', 'info')
  try {
    const result = await invoke<string>('execute_shell', { command: 'launchctl kickstart -k gui/$(id -u)/com.sam.api' })
    showNotification(result || 'MLX restarted', 'success')
    await fetchMLXStatus()
  } catch (e) {
    showNotification(`Failed to restart: ${e}`, 'error')
  } finally {
    mlxLoading.value = false
  }
}

// Warm a model
async function warmModel(model: string) {
  mlxLoading.value = true
  showNotification(`Warming ${model}...`, 'info')
  try {
    const result = await invoke<string>('cmd_warm_model', { model })
    showNotification(result, 'success')
    currentModel.value = model
  } catch (e) {
    showNotification(`Failed to warm: ${e}`, 'error')
  } finally {
    mlxLoading.value = false
  }
}

// Unload a model
async function unloadModel(model: string) {
  try {
    const result = await invoke<string>('cmd_unload_model', { model })
    showNotification(result, 'success')
    if (currentModel.value === model) {
      currentModel.value = null
    }
  } catch (e) {
    showNotification(`Failed to unload: ${e}`, 'error')
  }
}

// Display path (shortened for UI)
const displayPath = computed(() => {
  const path = props.currentDirectory || '~'
  const homePrefix = '/Users/'

  if (path.startsWith(homePrefix)) {
    const afterHome = path.substring(homePrefix.length)
    const parts = afterHome.split('/')
    if (parts.length > 1) {
      return '~/' + parts.slice(1).join('/')
    }
    return '~'
  }

  return path
})

// Short model name
const shortModelName = computed(() => {
  const name = props.modelName || ''
  // Extract just the model name without version/size
  const parts = name.split(':')
  return parts[0] || name
})

// Check MLX sam_api connection (Ollama decommissioned 2026-01-18)
async function checkMLXConnection() {
  try {
    const response = await fetch('http://localhost:8765/api/status')
    mlxConnected.value = response.ok
  } catch {
    mlxConnected.value = false
  }
}

// Polling interval
let connectionCheckInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  checkMLXConnection()
  connectionCheckInterval = setInterval(checkMLXConnection, 10000) // Check every 10s
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (connectionCheckInterval) {
    clearInterval(connectionCheckInterval)
  }
  document.removeEventListener('click', handleClickOutside)
})

// Expose method to show notifications
function showNotification(message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info', duration = 3000) {
  activeNotification.value = { message, type }
  setTimeout(() => {
    activeNotification.value = null
  }, duration)
}

defineExpose({ showNotification })
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 24px;
  padding: 0 var(--warp-space-3);
  background: var(--warp-bg-surface);
  border-top: 1px solid var(--warp-border-subtle);
  font-size: var(--warp-text-xs);
  color: var(--warp-text-tertiary);
  user-select: none;
}

.status-left,
.status-center,
.status-right {
  display: flex;
  align-items: center;
  gap: var(--warp-space-4);
}

.status-center {
  flex: 1;
  justify-content: center;
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--warp-space-1);
}

.status-icon {
  width: 12px;
  height: 12px;
  opacity: 0.7;
}

/* Git Status */
.status-git {
  color: var(--warp-accent-secondary);
}

.git-branch {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.git-dirty {
  color: var(--warp-warning);
  font-weight: var(--warp-weight-bold);
}

/* CWD */
.status-cwd {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Notification */
.status-notification {
  padding: 2px var(--warp-space-2);
  border-radius: var(--warp-radius-sm);
  animation: warp-fade-in 0.2s ease;
}

.status-notification.info {
  background: var(--warp-info-bg);
  color: var(--warp-info);
}

.status-notification.success {
  background: var(--warp-success-bg);
  color: var(--warp-success);
}

.status-notification.warning {
  background: var(--warp-warning-bg);
  color: var(--warp-warning);
}

.status-notification.error {
  background: var(--warp-error-bg);
  color: var(--warp-error);
}

/* Recording Indicator */
.status-recording {
  color: var(--warp-error);
}

.recording-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--warp-radius-full);
  background: var(--warp-error);
  animation: warp-pulse 1s ease-in-out infinite;
}

/* AI Status */
.status-ai {
  color: var(--warp-text-tertiary);
}

.status-ai.active {
  color: var(--warp-success);
}

.status-ai.active .status-icon {
  opacity: 1;
}

/* Model */
.status-model {
  color: var(--warp-accent-primary);
  font-family: var(--warp-font-mono);
}

/* Connection Status */
.status-connection {
  color: var(--warp-text-disabled);
}

.status-connection.connected {
  color: var(--warp-text-tertiary);
}

.connection-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--warp-radius-full);
  background: var(--warp-text-disabled);
}

.status-connection.connected .connection-dot {
  background: var(--warp-success);
}

/* Hover effects */
.status-item {
  cursor: default;
  padding: 2px var(--warp-space-1);
  border-radius: var(--warp-radius-sm);
  transition: background var(--warp-transition-fast);
}

.status-item:hover {
  background: var(--warp-bg-hover);
}

/* MLX Menu */
.status-connection {
  position: relative;
  cursor: pointer;
}

.status-connection.loading .connection-dot {
  background: var(--warp-warning);
}

.connection-dot.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.mlx-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 8px;
  min-width: 220px;
  background: var(--warp-bg-elevated);
  border: 1px solid var(--warp-border-subtle);
  border-radius: var(--warp-radius-md);
  box-shadow: var(--warp-shadow-lg);
  z-index: 1000;
  overflow: hidden;
}

.mlx-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--warp-space-2) var(--warp-space-3);
  background: var(--warp-bg-surface);
  border-bottom: 1px solid var(--warp-border-subtle);
}

.menu-title {
  font-weight: var(--warp-weight-medium);
  color: var(--warp-text-primary);
}

.model-count {
  font-size: var(--warp-text-xs);
  color: var(--warp-text-tertiary);
}

.mlx-status-row {
  padding: var(--warp-space-2) var(--warp-space-3);
  font-size: var(--warp-text-sm);
}

.status-ok {
  color: var(--warp-success);
}

.status-error {
  color: var(--warp-error);
}

.mlx-menu-btn {
  display: flex;
  align-items: center;
  gap: var(--warp-space-2);
  width: 100%;
  padding: var(--warp-space-2) var(--warp-space-3);
  background: none;
  border: none;
  color: var(--warp-text-primary);
  font-size: var(--warp-text-sm);
  cursor: pointer;
  transition: background var(--warp-transition-fast);
}

.mlx-menu-btn:hover:not(:disabled) {
  background: var(--warp-bg-hover);
}

.mlx-menu-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mlx-models {
  border-top: 1px solid var(--warp-border-subtle);
  max-height: 200px;
  overflow-y: auto;
}

.model-section-title {
  padding: var(--warp-space-2) var(--warp-space-3);
  font-size: var(--warp-text-xs);
  color: var(--warp-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--warp-space-1) var(--warp-space-3);
  transition: background var(--warp-transition-fast);
}

.model-item:hover {
  background: var(--warp-bg-hover);
}

.model-item.active {
  background: var(--warp-accent-primary-subtle);
}

.model-name {
  font-family: var(--warp-font-mono);
  font-size: var(--warp-text-xs);
  color: var(--warp-text-secondary);
}

.model-item.active .model-name {
  color: var(--warp-accent-primary);
  font-weight: var(--warp-weight-medium);
}

.model-actions {
  display: flex;
  gap: var(--warp-space-1);
}

.model-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: none;
  border: none;
  border-radius: var(--warp-radius-sm);
  cursor: pointer;
  font-size: 12px;
  transition: background var(--warp-transition-fast);
}

.model-btn:hover {
  background: var(--warp-bg-surface);
}

.model-btn.warm:hover {
  background: rgba(255, 165, 0, 0.2);
}

.model-btn.unload:hover {
  background: rgba(100, 100, 255, 0.2);
}

/* Character Menu */
.status-characters {
  position: relative;
  cursor: pointer;
  color: var(--warp-accent-secondary);
}

.status-characters:hover {
  color: var(--warp-accent-primary);
}

.character-icon {
  font-size: 14px;
}

.character-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 8px;
  min-width: 240px;
  background: var(--warp-bg-elevated);
  border: 1px solid var(--warp-border-subtle);
  border-radius: var(--warp-radius-md);
  box-shadow: var(--warp-shadow-lg);
  z-index: 1000;
  overflow: hidden;
}

.character-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--warp-space-2) var(--warp-space-3);
  background: var(--warp-bg-surface);
  border-bottom: 1px solid var(--warp-border-subtle);
}

.character-menu-btn {
  display: flex;
  align-items: center;
  gap: var(--warp-space-2);
  width: 100%;
  padding: var(--warp-space-2) var(--warp-space-3);
  background: none;
  border: none;
  color: var(--warp-text-primary);
  font-size: var(--warp-text-sm);
  cursor: pointer;
  transition: background var(--warp-transition-fast);
  text-align: left;
}

.character-menu-btn:hover {
  background: var(--warp-bg-hover);
}

.btn-hint {
  margin-left: auto;
  font-size: var(--warp-text-xs);
  color: var(--warp-text-tertiary);
}

.recent-characters {
  border-top: 1px solid var(--warp-border-subtle);
  padding: var(--warp-space-1) 0;
}

.section-title {
  padding: var(--warp-space-1) var(--warp-space-3);
  font-size: var(--warp-text-xs);
  color: var(--warp-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.recent-character-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  padding: var(--warp-space-2) var(--warp-space-3);
  background: none;
  border: none;
  cursor: pointer;
  transition: background var(--warp-transition-fast);
}

.recent-character-btn:hover {
  background: var(--warp-bg-hover);
}

.char-name {
  color: var(--warp-text-primary);
  font-size: var(--warp-text-sm);
  font-weight: var(--warp-weight-medium);
}

.char-archetype {
  color: var(--warp-text-tertiary);
  font-size: var(--warp-text-xs);
}
</style>
