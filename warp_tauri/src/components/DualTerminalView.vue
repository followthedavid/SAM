<template>
  <div class="dual-terminal-container">
    <!-- Header with status -->
    <div class="dual-header">
      <div class="header-left">
        <span class="logo">SAM</span>
        <span class="subtitle">Dual Terminal System</span>
      </div>
      <div class="header-center">
        <div class="bridge-status" :class="{ active: bridgeEnabled }">
          <span class="bridge-icon">⚡</span>
          <span>Bridge {{ bridgeEnabled ? 'Active' : 'Inactive' }}</span>
          <button @click="bridgeEnabled = !bridgeEnabled" class="toggle-btn">
            {{ bridgeEnabled ? 'Disable' : 'Enable' }}
          </button>
        </div>
        <button @click="manualEscalate" class="escalate-btn" title="Send SAM's context to Claude">
          🚀 Escalate to Claude
        </button>
        <button @click="delegateToSam" class="delegate-btn" title="Send Claude's task to SAM">
          📤 Delegate to SAM
        </button>
      </div>
      <div class="header-right">
        <span v-if="isReady" class="status ready">● Ready</span>
        <span v-else class="status loading">◌ Loading...</span>
      </div>
    </div>

    <!-- Dual terminal panes -->
    <div class="terminals-wrapper">
      <!-- Claude Code Terminal -->
      <div class="terminal-pane claude-pane">
        <div class="pane-header">
          <span class="pane-icon">🤖</span>
          <span class="pane-title">Claude Code</span>
          <span class="pane-status" :class="{ ready: claudeReady }">
            {{ claudeReady ? '● Connected' : '○ Connecting...' }}
          </span>
        </div>
        <div class="pane-content" ref="claudePaneRef">
          <TerminalPane
            v-if="claudeTerminalId"
            :ptyId="claudeTerminalId"
            :paneId="'claude-' + claudeTerminalId"
            @output-change="handleClaudeOutput"
          />
          <div v-else class="loading-placeholder">
            <span>Starting Claude Code...</span>
          </div>
        </div>
      </div>

      <!-- Resize Handle -->
      <div
        class="resize-handle"
        @mousedown="startResize"
        @touchstart="startResize"
      >
        <div class="handle-grip"></div>
      </div>

      <!-- SAM Local Terminal -->
      <div class="terminal-pane sam-pane" :style="{ width: samPaneWidth }">
        <div class="pane-header">
          <span class="pane-icon">🧠</span>
          <span class="pane-title">SAM Local</span>
          <span class="pane-status" :class="{ ready: samReady }">
            {{ samReady ? '● Connected' : '○ Connecting...' }}
          </span>
        </div>
        <div class="pane-content" ref="samPaneRef">
          <TerminalPane
            v-if="samTerminalId"
            :ptyId="samTerminalId"
            :paneId="'sam-' + samTerminalId"
            @output-change="handleSamOutput"
          />
          <div v-else class="loading-placeholder">
            <span>Starting SAM...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bridge Activity Log (collapsible) -->
    <div class="bridge-log" :class="{ expanded: showBridgeLog }">
      <div class="log-header" @click="showBridgeLog = !showBridgeLog">
        <span>Bridge Activity</span>
        <span class="log-count">({{ bridgeMessages.length }})</span>
        <span class="expand-icon">{{ showBridgeLog ? '▼' : '▶' }}</span>
      </div>
      <div v-if="showBridgeLog" class="log-content">
        <div
          v-for="(msg, i) in bridgeMessages.slice(-10).reverse()"
          :key="i"
          class="log-entry"
          :class="msg.type"
        >
          <span class="log-direction">{{ msg.from }} → {{ msg.to }}</span>
          <span class="log-type">{{ msg.type }}</span>
          <span class="log-preview">{{ msg.content.substring(0, 50) }}...</span>
        </div>
        <div v-if="bridgeMessages.length === 0" class="log-empty">
          No bridge activity yet
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import TerminalPane from './TerminalPane.vue'
import { useDualTerminal } from '../composables/useDualTerminal'

const {
  claudeTerminal,
  samTerminal,
  bridgeMessages,
  bridgeEnabled,
  isReady,
  claudeReady,
  samReady,
  initDualTerminal,
  closeDualTerminal,
  shouldEscalate,
  shouldDelegate,
  escalateToClaudeCode,
  sendToTerminal,
  logForTraining,
} = useDualTerminal()

// Local state
const claudeTerminalId = ref<number | null>(null)
const samTerminalId = ref<number | null>(null)
const showBridgeLog = ref(false)
const samPaneWidth = ref('50%')
const isResizing = ref(false)

// Refs for panes
const claudePaneRef = ref<HTMLElement | null>(null)
const samPaneRef = ref<HTMLElement | null>(null)

// Initialize on mount
onMounted(async () => {
  try {
    const { claudeId, samId } = await initDualTerminal()
    claudeTerminalId.value = claudeId
    samTerminalId.value = samId
  } catch (error) {
    console.error('[DualTerminalView] Failed to initialize:', error)
  }
})

// Cleanup on unmount
onUnmounted(() => {
  closeDualTerminal()
})

// Handle Claude output (for learning capture and auto-delegation)
function handleClaudeOutput(output: string) {
  // If we recently escalated, capture the response for training
  const recentEscalation = bridgeMessages.value
    .filter(m => m.type === 'escalate')
    .slice(-1)[0]

  if (recentEscalation && Date.now() - recentEscalation.timestamp < 60000) {
    // Within 1 minute of escalation - likely the response
    logForTraining(recentEscalation.content, output)
  }

  // Check if Claude suggests delegating to SAM
  if (bridgeEnabled.value && shouldDelegate(output)) {
    console.log('[DualTerminalView] Claude suggests delegation to SAM:', output.substring(0, 100))
    // Auto-delegate could be triggered here, but for now just log it
    // The user can click the "Delegate to SAM" button
  }
}

// Handle SAM output (for escalation detection)
function handleSamOutput(output: string) {
  if (bridgeEnabled.value && shouldEscalate(output)) {
    // SAM seems uncertain - could trigger escalation
    // For now, just log it - user can manually escalate
    console.log('[DualTerminalView] SAM response may need escalation:', output.substring(0, 100))
  }
}

// Manual escalation - send last SAM context to Claude
async function manualEscalate() {
  if (!samTerminal.lastOutput) {
    console.log('[DualTerminalView] No SAM output to escalate')
    return
  }

  // Get the last meaningful output from SAM
  const context = samTerminal.lastOutput.substring(0, 2000)

  // Build escalation prompt
  const prompt = `SAM (local AI) was asked something and provided this response:\n\n${context}\n\nPlease help clarify or provide a better answer.`

  // Log the escalation
  bridgeMessages.value.push({
    from: 'sam',
    to: 'claude',
    type: 'escalate',
    content: prompt,
    timestamp: Date.now()
  })

  // Send to Claude terminal
  await escalateToClaudeCode(prompt)
  console.log('[DualTerminalView] Manually escalated to Claude')
}

// Delegate from Claude to SAM - send Claude's context to SAM for handling
async function delegateToSam() {
  if (!claudeTerminal.lastOutput) {
    console.log('[DualTerminalView] No Claude output to delegate')
    return
  }

  // Get the last meaningful output from Claude
  const context = claudeTerminal.lastOutput.substring(0, 2000)

  // Build delegation prompt for SAM
  const prompt = `Claude suggested you handle this:\n${context}`

  // Log the delegation
  bridgeMessages.value.push({
    from: 'claude',
    to: 'sam',
    type: 'delegate',
    content: prompt,
    timestamp: Date.now()
  })

  // Send to SAM terminal
  await sendToTerminal('sam', prompt)
  console.log('[DualTerminalView] Delegated to SAM')

  // Log for training (SAM learning what Claude considers simple)
  logForTraining(`[DELEGATION] ${context}`, 'SAM should handle this type of task')
}

// Resize handling
function startResize(event: MouseEvent | TouchEvent) {
  isResizing.value = true
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  document.addEventListener('touchmove', handleResize)
  document.addEventListener('touchend', stopResize)
}

function handleResize(event: MouseEvent | TouchEvent) {
  if (!isResizing.value) return

  const container = document.querySelector('.terminals-wrapper')
  if (!container) return

  const rect = container.getBoundingClientRect()
  const clientX = 'touches' in event ? event.touches[0].clientX : event.clientX
  const percentage = ((clientX - rect.left) / rect.width) * 100

  // Clamp between 20% and 80%
  samPaneWidth.value = `${Math.min(80, Math.max(20, 100 - percentage))}%`
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.removeEventListener('touchmove', handleResize)
  document.removeEventListener('touchend', stopResize)
}
</script>

<style scoped>
.dual-terminal-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0d1117;
  color: #c9d1d9;
}

.dual-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-weight: bold;
  font-size: 18px;
  color: #58a6ff;
}

.subtitle {
  font-size: 12px;
  color: #8b949e;
}

.bridge-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: #21262d;
  border-radius: 6px;
  font-size: 12px;
}

.bridge-status.active {
  background: #238636;
}

.bridge-icon {
  font-size: 14px;
}

.toggle-btn {
  padding: 2px 8px;
  font-size: 10px;
  background: #30363d;
  border: none;
  border-radius: 4px;
  color: #c9d1d9;
  cursor: pointer;
}

.toggle-btn:hover {
  background: #484f58;
}

.escalate-btn {
  padding: 4px 12px;
  font-size: 12px;
  background: linear-gradient(135deg, #f0883e 0%, #db6d28 100%);
  border: none;
  border-radius: 6px;
  color: #ffffff;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.escalate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(240, 136, 62, 0.4);
}

.delegate-btn {
  padding: 4px 12px;
  font-size: 12px;
  background: linear-gradient(135deg, #58a6ff 0%, #388bfd 100%);
  border: none;
  border-radius: 6px;
  color: #ffffff;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.delegate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(88, 166, 255, 0.4);
}

.status {
  font-size: 12px;
}

.status.ready {
  color: #3fb950;
}

.status.loading {
  color: #f0883e;
}

.terminals-wrapper {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.terminal-pane {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 200px;
}

.claude-pane {
  border-right: 1px solid #30363d;
}

.pane-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  font-size: 12px;
}

.pane-icon {
  font-size: 14px;
}

.pane-title {
  font-weight: 500;
}

.pane-status {
  margin-left: auto;
  font-size: 10px;
  color: #8b949e;
}

.pane-status.ready {
  color: #3fb950;
}

.pane-content {
  flex: 1;
  overflow: hidden;
}

.loading-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #8b949e;
}

.resize-handle {
  width: 6px;
  background: #30363d;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle:hover {
  background: #484f58;
}

.handle-grip {
  width: 2px;
  height: 30px;
  background: #8b949e;
  border-radius: 1px;
}

.bridge-log {
  background: #161b22;
  border-top: 1px solid #30363d;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 12px;
}

.log-header:hover {
  background: #21262d;
}

.log-count {
  color: #8b949e;
}

.expand-icon {
  margin-left: auto;
  font-size: 10px;
}

.log-content {
  max-height: 150px;
  overflow-y: auto;
  padding: 8px 16px;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  font-size: 11px;
  border-bottom: 1px solid #21262d;
}

.log-direction {
  color: #58a6ff;
  min-width: 100px;
}

.log-type {
  color: #8b949e;
  min-width: 60px;
}

.log-type.escalate {
  color: #f0883e;
}

.log-type.learn {
  color: #3fb950;
}

.log-type.delegate {
  color: #58a6ff;
}

.log-preview {
  color: #c9d1d9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-empty {
  color: #8b949e;
  font-style: italic;
}
</style>
