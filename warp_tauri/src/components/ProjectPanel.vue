<template>
  <div class="project-panel">
    <!-- Panel Header -->
    <div class="panel-header">
      <div class="header-left">
        <span class="project-icon">{{ project.icon }}</span>
        <div class="header-text">
          <h2>{{ project.name }}</h2>
          <p v-if="project.description">{{ project.description }}</p>
        </div>
      </div>
      <div class="header-right">
        <button class="chat-btn" @click="$emit('open-chat')" title="Chat about this project">
          💬 Chat
        </button>
        <button class="delete-btn" @click="confirmDelete" title="Delete project">
          🗑️ Delete
        </button>
        <button class="close-btn" @click="$emit('close')" title="Close (Esc)">
          ✕
        </button>
      </div>
    </div>

    <!-- Site Ripper: Custom Dashboard -->
    <div v-if="project.id === 'site-ripper'" class="panel-content scraper-panel">
      <ScraperDashboard />
    </div>

    <!-- Panel Content (default) -->
    <div v-else class="panel-content">
      <!-- Metrics Section -->
      <section class="section metrics-section">
        <h3>Metrics</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="metric-value">{{ formatNumber(project.metrics?.linesOfCode || 0) }}</span>
            <span class="metric-label">Lines of Code</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ project.metrics?.filesModified || 0 }}</span>
            <span class="metric-label">Files Modified</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ formatLastActivity(project.metrics?.lastActivity) }}</span>
            <span class="metric-label">Last Activity</span>
          </div>
          <div class="metric-card">
            <span class="metric-value" :class="project.status">{{ project.status }}</span>
            <span class="metric-label">Status</span>
          </div>
        </div>
      </section>

      <!-- Goals Section -->
      <section class="section goals-section">
        <div class="section-header">
          <h3>Goals</h3>
          <span class="progress-badge">{{ overallProgress }}%</span>
        </div>
        <div class="goals-list">
          <div
            v-for="goal in project.goals"
            :key="goal.id"
            class="goal-item"
            :class="goal.status"
          >
            <div class="goal-status-icon">
              <span v-if="goal.status === 'complete'">✓</span>
              <span v-else-if="goal.status === 'in_progress'">◐</span>
              <span v-else>○</span>
            </div>
            <div class="goal-content">
              <span class="goal-description">{{ goal.description }}</span>
              <div v-if="goal.status === 'in_progress' && goal.progress" class="goal-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: goal.progress + '%' }"></div>
                </div>
                <span class="progress-text">{{ goal.progress }}%</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Running Tasks Section (moved above suggested for visibility) -->
      <section v-if="project.runningTasks?.length" class="section running-section">
        <div class="section-header">
          <h3>🔄 Running Now</h3>
          <span class="running-count">{{ project.runningTasks.length }} active</span>
        </div>
        <div class="running-list">
          <div
            v-for="task in project.runningTasks"
            :key="task.id"
            class="running-item"
          >
            <div class="running-indicator">
              <div class="spinner"></div>
            </div>
            <div class="running-content">
              <span class="running-description">{{ task.description }}</span>
              <code v-if="task.command" class="running-command">$ {{ task.command }}</code>
              <div class="running-progress">
                <div class="progress-bar">
                  <div class="progress-fill running" :style="{ width: task.progress + '%' }"></div>
                </div>
                <span class="progress-text">{{ task.progress }}%</span>
                <span v-if="task.eta" class="eta-text">ETA: {{ task.eta }}</span>
              </div>
            </div>
            <button class="stop-btn" @click="handleStop(task)" title="Stop task">
              ⏹
            </button>
          </div>
        </div>
      </section>

      <!-- Suggested Tasks Section -->
      <section class="section tasks-section">
        <div class="section-header">
          <h3>Suggested Tasks</h3>
          <div class="section-actions" v-if="project.suggestedTasks?.length">
            <span class="total-hours">{{ totalHours }}h total</span>
            <button class="approve-all-btn" @click="$emit('approve-all')">
              Approve All
            </button>
          </div>
        </div>

        <!-- Empty state when all tasks approved -->
        <div v-if="!project.suggestedTasks?.length" class="empty-tasks">
          <span class="empty-icon">✅</span>
          <span class="empty-text">All tasks approved! Check "Running Now" above.</span>
        </div>

        <div v-else class="tasks-list">
          <div
            v-for="task in project.suggestedTasks"
            :key="task.id"
            class="task-item"
            :class="{ expanded: expandedTaskId === task.id }"
            @click="toggleTaskDetails(task.id)"
          >
            <div class="task-main">
              <div class="task-checkbox">
                <span>□</span>
              </div>
              <div class="task-content">
                <span class="task-description">{{ task.description }}</span>
                <span class="task-estimate">~{{ task.estimatedHours }}h</span>
              </div>
              <button
                class="approve-btn"
                @click.stop="handleApprove(task)"
              >
                ▶ Approve
              </button>
            </div>
            <!-- Task Details (expanded) - with editable config -->
            <div v-if="expandedTaskId === task.id" class="task-details">
              <div class="detail-row">
                <span class="detail-label">Command:</span>
                <code class="detail-value">{{ task.command }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">Estimated:</span>
                <span class="detail-value">{{ task.estimatedHours }} hours</span>
              </div>

              <!-- Editable Configuration -->
              <div v-if="task.configSchema" class="task-config">
                <div class="config-header">
                  <span class="config-title">⚙️ Configuration</span>
                  <button class="reset-btn" @click.stop="resetConfig(task)" title="Reset to defaults">↺ Reset</button>
                </div>
                <div class="config-fields">
                  <div
                    v-for="(schema, key) in task.configSchema"
                    :key="key"
                    class="config-field"
                  >
                    <label :for="`config-${task.id}-${key}`">
                      {{ schema.label }}
                      <span v-if="schema.description" class="field-hint">{{ schema.description }}</span>
                    </label>

                    <!-- Select -->
                    <select
                      v-if="schema.type === 'select'"
                      :id="`config-${task.id}-${key}`"
                      :value="getConfigValue(task, key)"
                      @change="updateConfig(task, key, ($event.target as HTMLSelectElement).value)"
                      @click.stop
                    >
                      <option v-for="opt in schema.options" :key="opt" :value="opt">{{ opt }}</option>
                    </select>

                    <!-- Number -->
                    <input
                      v-else-if="schema.type === 'number'"
                      type="number"
                      :id="`config-${task.id}-${key}`"
                      :value="getConfigValue(task, key)"
                      @input="updateConfig(task, key, Number(($event.target as HTMLInputElement).value))"
                      @click.stop
                    />

                    <!-- Boolean (checkbox) -->
                    <label v-else-if="schema.type === 'boolean'" class="toggle-label">
                      <input
                        type="checkbox"
                        :id="`config-${task.id}-${key}`"
                        :checked="getConfigValue(task, key) as boolean"
                        @change="updateConfig(task, key, ($event.target as HTMLInputElement).checked)"
                        @click.stop
                      />
                      <span class="toggle-switch"></span>
                    </label>

                    <!-- String (text) -->
                    <input
                      v-else
                      type="text"
                      :id="`config-${task.id}-${key}`"
                      :value="getConfigValue(task, key)"
                      @input="updateConfig(task, key, ($event.target as HTMLInputElement).value)"
                      @click.stop
                    />
                  </div>
                </div>
              </div>

              <div class="detail-actions">
                <button class="approve-large-btn" @click.stop="handleApprove(task)">
                  ▶ Start Task
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>


      <!-- Issues Section -->
      <section v-if="project.issues?.length" class="section issues-section">
        <h3>Issues</h3>
        <div class="issues-list">
          <div v-for="(issue, index) in project.issues" :key="index" class="issue-item">
            <span class="issue-icon">⚠</span>
            <span class="issue-text">{{ issue }}</span>
            <button class="fix-btn" @click="handleFixIssue(issue)">Fix</button>
          </div>
        </div>
      </section>

      <!-- Project Path -->
      <div v-if="project.path" class="project-path">
        <span class="path-label">Path:</span>
        <code>{{ project.path }}</code>
        <button class="copy-btn" @click="copyPath" title="Copy path">📋</button>
      </div>

      <!-- Tags -->
      <div v-if="project.tags?.length" class="project-tags">
        <span v-for="tag in project.tags" :key="tag" class="tag">{{ tag }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, defineAsyncComponent } from 'vue'
import type { Project, ProjectTask, RunningTask } from '../stores/projectStore'

// Lazy load ScraperDashboard for Site Ripper project
const ScraperDashboard = defineAsyncComponent(() => import('./ScraperDashboard.vue'))

const props = defineProps<{
  project: Project
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'approve-task', task: ProjectTask): void
  (e: 'approve-all'): void
  (e: 'open-chat'): void
  (e: 'delete-project'): void
}>()

// State for expanded task details
const expandedTaskId = ref<string | null>(null)

// Computed
const overallProgress = computed(() => {
  const goals = props.project.goals || []
  if (!goals.length) return 0

  const completed = goals.filter(g => g.status === 'complete').length
  const inProgress = goals.filter(g => g.status === 'in_progress')
  const inProgressSum = inProgress.reduce((sum, g) => sum + (g.progress || 50), 0)

  return Math.round((completed * 100 + inProgressSum) / goals.length)
})

const totalHours = computed(() => {
  return (props.project.suggestedTasks || [])
    .reduce((sum, t) => sum + (t.estimatedHours || 0), 0)
    .toFixed(1)
})

// Helpers
function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

function formatLastActivity(date: Date | string | null): string {
  if (!date) return 'Never'

  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - d.getTime()

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return `${Math.floor(diff / 86400000)}d ago`
}

// Handlers
function handleApprove(task: ProjectTask) {
  emit('approve-task', task)
  expandedTaskId.value = null // Close details after approving
}

function toggleTaskDetails(taskId: string) {
  expandedTaskId.value = expandedTaskId.value === taskId ? null : taskId
}

function handleStop(task: RunningTask) {
  console.log('[ProjectPanel] Stop task:', task.id)
  // TODO: Implement task stopping via backend
}

function handleFixIssue(issue: string) {
  console.log('[ProjectPanel] Fix issue:', issue)
}

function confirmDelete() {
  if (confirm(`Are you sure you want to delete "${props.project.name}"? This cannot be undone.`)) {
    emit('delete-project')
  }
}

// Config helpers
function getConfigValue(task: ProjectTask, key: string): string | number | boolean {
  if (task.config && key in task.config) {
    return task.config[key]
  }
  if (task.configSchema && key in task.configSchema) {
    return task.configSchema[key].default
  }
  return ''
}

function updateConfig(task: ProjectTask, key: string, value: string | number | boolean) {
  if (!task.config) {
    task.config = {}
  }
  task.config[key] = value
}

function resetConfig(task: ProjectTask) {
  if (!task.configSchema) return
  task.config = {}
  for (const [key, schema] of Object.entries(task.configSchema)) {
    task.config[key] = schema.default
  }
}

async function copyPath() {
  if (props.project.path) {
    await navigator.clipboard.writeText(props.project.path)
  }
}
</script>

<style scoped>
/* ==========================================================================
   PROJECT PANEL - Expanded View
   ========================================================================== */

.project-panel {
  grid-column: 1 / -1;
  background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 24px;
  overflow: hidden;
  animation: panelIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes panelIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==========================================================================
   HEADER
   ========================================================================== */

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  background: rgba(255,255,255,0.03);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-icon {
  font-size: 48px;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
}

.header-text h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
}

.header-text p {
  margin: 4px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.5);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(10,132,255,0.4);
}

.delete-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(255,59,48,0.3);
  background: rgba(255,59,48,0.1);
  color: #ff3b30;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.delete-btn:hover {
  background: rgba(255,59,48,0.2);
  border-color: rgba(255,59,48,0.5);
}

.close-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.6);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255,59,48,0.2);
  color: #ff3b30;
}

/* ==========================================================================
   CONTENT
   ========================================================================== */

.panel-content {
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 28px;
  max-height: 70vh;
  overflow-y: auto;
}

/* Scraper Dashboard - full bleed */
.panel-content.scraper-panel {
  padding: 0;
  max-height: calc(100vh - 100px);
}

/* Section Styles */
.section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section h3 {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ==========================================================================
   METRICS
   ========================================================================== */

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.metric-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
}

.metric-value.healthy { color: #34c759; }
.metric-value.warning { color: #ff9500; }
.metric-value.error { color: #ff3b30; }
.metric-value.idle { color: rgba(255,255,255,0.4); }

.metric-label {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}

/* ==========================================================================
   GOALS
   ========================================================================== */

.progress-badge {
  font-size: 14px;
  font-weight: 700;
  color: #34c759;
  background: rgba(52,199,89,0.15);
  padding: 4px 12px;
  border-radius: 12px;
}

.goals-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.goal-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 12px;
  transition: background 0.2s ease;
}

.goal-item:hover {
  background: rgba(255,255,255,0.06);
}

.goal-status-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.goal-item.complete .goal-status-icon { color: #34c759; }
.goal-item.in_progress .goal-status-icon { color: #0a84ff; }
.goal-item.pending .goal-status-icon { color: rgba(255,255,255,0.3); }

.goal-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.goal-description {
  font-size: 14px;
  color: rgba(255,255,255,0.9);
}

.goal-item.complete .goal-description {
  text-decoration: line-through;
  color: rgba(255,255,255,0.5);
}

.goal-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ==========================================================================
   TASKS
   ========================================================================== */

.total-hours {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
}

.approve-all-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  border: none;
  border-radius: 10px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.approve-all-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(10,132,255,0.4);
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.task-item:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.1);
}

.task-item.approved {
  opacity: 0.6;
}

.task-checkbox {
  font-size: 16px;
  color: rgba(255,255,255,0.4);
}

.task-item.approved .task-checkbox {
  color: #34c759;
}

.task-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-description {
  font-size: 14px;
  color: rgba(255,255,255,0.9);
}

.task-estimate {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  font-family: 'SF Mono', monospace;
}

.approve-btn {
  padding: 6px 14px;
  background: rgba(52,199,89,0.15);
  border: 1px solid rgba(52,199,89,0.3);
  border-radius: 8px;
  color: #34c759;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.approve-btn:hover {
  background: rgba(52,199,89,0.25);
  transform: scale(1.02);
}

.approved-label {
  font-size: 12px;
  color: rgba(255,255,255,0.3);
  font-style: italic;
}

/* Empty Tasks State */
.empty-tasks {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: rgba(52,199,89,0.08);
  border: 1px solid rgba(52,199,89,0.2);
  border-radius: 12px;
}

.empty-tasks .empty-icon {
  font-size: 24px;
}

.empty-tasks .empty-text {
  font-size: 14px;
  color: rgba(255,255,255,0.7);
}

/* Task Main (wraps checkbox, content, button) */
.task-main {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

/* Task Details (expandable) */
.task-item {
  cursor: pointer;
  flex-direction: column;
}

.task-item.expanded {
  background: rgba(10,132,255,0.08);
  border-color: rgba(10,132,255,0.2);
}

.task-details {
  width: 100%;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-label {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  min-width: 80px;
}

.detail-value {
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  font-family: 'SF Mono', monospace;
}

.detail-hint {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  font-style: italic;
  text-align: center;
  margin-top: 4px;
}

/* Task Configuration Form */
.task-config {
  margin-top: 16px;
  padding: 16px;
  background: rgba(0,0,0,0.3);
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.config-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
}

.reset-btn {
  padding: 4px 10px;
  font-size: 11px;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 6px;
  background: transparent;
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.reset-btn:hover {
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.8);
}

.config-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-field label {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.7);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-hint {
  font-size: 10px;
  font-weight: 400;
  color: rgba(255,255,255,0.4);
  font-style: italic;
}

.config-field input[type="text"],
.config-field input[type="number"],
.config-field select {
  padding: 10px 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

.config-field input:focus,
.config-field select:focus {
  border-color: rgba(10,132,255,0.5);
  background: rgba(255,255,255,0.08);
}

.config-field select {
  cursor: pointer;
}

.config-field select option {
  background: #1c1c24;
  color: #ffffff;
}

/* Toggle Switch */
.toggle-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.toggle-label input[type="checkbox"] {
  display: none;
}

.toggle-switch {
  width: 44px;
  height: 24px;
  background: rgba(255,255,255,0.15);
  border-radius: 12px;
  position: relative;
  transition: all 0.3s ease;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.3s ease;
}

.toggle-label input:checked + .toggle-switch {
  background: #34c759;
}

.toggle-label input:checked + .toggle-switch::after {
  transform: translateX(20px);
}

/* Detail Actions */
.detail-actions {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.approve-large-btn {
  padding: 12px 32px;
  background: linear-gradient(135deg, #34c759 0%, #30d158 100%);
  border: none;
  border-radius: 12px;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.approve-large-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(52,199,89,0.4);
}

/* Running Count Badge */
.running-count {
  font-size: 12px;
  font-weight: 600;
  color: #0a84ff;
  background: rgba(10,132,255,0.15);
  padding: 4px 10px;
  border-radius: 10px;
}

/* Running Command Display */
.running-command {
  font-size: 11px;
  font-family: 'SF Mono', monospace;
  color: rgba(255,255,255,0.5);
  background: rgba(0,0,0,0.3);
  padding: 4px 8px;
  border-radius: 4px;
  margin-top: 4px;
}

/* Stop Button */
.stop-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(255,59,48,0.15);
  color: #ff3b30;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stop-btn:hover {
  background: rgba(255,59,48,0.25);
}

/* ==========================================================================
   RUNNING TASKS
   ========================================================================== */

.running-section h3 {
  color: #0a84ff;
}

.running-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.running-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(10,132,255,0.08);
  border: 1px solid rgba(10,132,255,0.2);
  border-radius: 12px;
}

.running-indicator {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(10,132,255,0.3);
  border-top-color: #0a84ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.running-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.running-description {
  font-size: 14px;
  color: #ffffff;
}

.running-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.eta-text {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
}


/* ==========================================================================
   ISSUES
   ========================================================================== */

.issues-section h3 {
  color: #ff9500;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255,149,0,0.08);
  border: 1px solid rgba(255,149,0,0.2);
  border-radius: 12px;
}

.issue-icon {
  font-size: 16px;
  color: #ff9500;
}

.issue-text {
  flex: 1;
  font-size: 14px;
  color: rgba(255,255,255,0.9);
}

.fix-btn {
  padding: 6px 14px;
  background: rgba(255,149,0,0.15);
  border: 1px solid rgba(255,149,0,0.3);
  border-radius: 8px;
  color: #ff9500;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.fix-btn:hover {
  background: rgba(255,149,0,0.25);
}

/* ==========================================================================
   PROGRESS BAR (shared)
   ========================================================================== */

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #34c759, #30d158);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-fill.running {
  background: linear-gradient(90deg, #0a84ff, #5ac8fa);
}

.progress-text {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255,255,255,0.6);
  min-width: 40px;
}

/* ==========================================================================
   FOOTER ELEMENTS
   ========================================================================== */

.project-path {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 10px;
  font-size: 12px;
}

.path-label {
  color: rgba(255,255,255,0.4);
}

.project-path code {
  flex: 1;
  font-family: 'SF Mono', monospace;
  color: rgba(255,255,255,0.7);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-btn {
  background: transparent;
  border: none;
  font-size: 14px;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.copy-btn:hover {
  opacity: 1;
}

.project-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255,255,255,0.6);
  background: rgba(255,255,255,0.08);
  padding: 4px 10px;
  border-radius: 6px;
}

/* ==========================================================================
   RESPONSIVE
   ========================================================================== */

@media (max-width: 768px) {
  .panel-header {
    padding: 16px 20px;
  }

  .project-icon {
    font-size: 36px;
  }

  .header-text h2 {
    font-size: 20px;
  }

  .panel-content {
    padding: 20px;
    gap: 20px;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
