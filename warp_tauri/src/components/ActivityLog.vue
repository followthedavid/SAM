<template>
  <div class="activity-log">
    <!-- Summary Bar -->
    <div class="summary-bar">
      <div class="summary-stat">
        <span class="stat-value">{{ summary?.totalTasks || 0 }}</span>
        <span class="stat-label">tasks</span>
      </div>
      <div class="summary-stat">
        <span class="stat-value">{{ (summary?.totalHours || 0).toFixed(1) }}h</span>
        <span class="stat-label">work</span>
      </div>
      <div class="summary-stat">
        <span class="stat-value">{{ Object.keys(summary?.byProject || {}).length }}</span>
        <span class="stat-label">projects</span>
      </div>
    </div>

    <!-- Timeline -->
    <div class="timeline">
      <div v-for="entry in recentEntries" :key="entry.id" class="timeline-entry">
        <span class="entry-time">{{ formatTime(entry.timestamp) }}</span>
        <span class="entry-status" :class="entry.status">
          {{ entry.status === 'success' ? '✓' : entry.status === 'failed' ? '✗' : '◐' }}
        </span>
        <span class="entry-project">{{ entry.project }}</span>
        <span class="entry-action">{{ entry.action }}</span>
      </div>

      <div v-if="entries.length === 0" class="empty-state">
        No activity in the last 24 hours
      </div>
    </div>

    <!-- Project Breakdown -->
    <div class="project-breakdown" v-if="summary?.byProject">
      <h4>By Project</h4>
      <div
        v-for="(stats, project) in summary.byProject"
        :key="project"
        class="project-row"
      >
        <span class="project-name">{{ project }}</span>
        <span class="project-tasks">{{ stats.tasks }} tasks</span>
        <div class="project-bar">
          <div
            class="project-fill"
            :style="{ width: `${(stats.hours / (summary.totalHours || 1)) * 100}%` }"
          ></div>
        </div>
        <span class="project-hours">{{ stats.hours.toFixed(1) }}h</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ActivityEntry, ActivitySummary } from '../composables/useActivityLog'

const props = defineProps<{
  entries: ActivityEntry[]
  summary: ActivitySummary | null
}>()

const recentEntries = computed(() => {
  return props.entries.slice(0, 15)
})

function formatTime(date: Date | string) {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.activity-log {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  gap: 24px;
}

.summary-stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

/* Timeline */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.timeline-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  font-size: 13px;
}

.entry-time {
  color: rgba(255, 255, 255, 0.4);
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  min-width: 50px;
}

.entry-status {
  width: 18px;
  text-align: center;
}

.entry-status.success {
  color: #34c759;
}

.entry-status.failed {
  color: #ff3b30;
}

.entry-status.partial {
  color: #ff9500;
}

.entry-project {
  font-weight: 600;
  color: #0a84ff;
  min-width: 80px;
}

.entry-action {
  flex: 1;
  color: rgba(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-state {
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  padding: 20px;
  font-size: 14px;
}

/* Project Breakdown */
.project-breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-breakdown h4 {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.project-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.project-name {
  min-width: 100px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
}

.project-tasks {
  min-width: 60px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
}

.project-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.project-fill {
  height: 100%;
  background: linear-gradient(90deg, #0a84ff, #5ac8fa);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.project-hours {
  min-width: 40px;
  text-align: right;
  color: rgba(255, 255, 255, 0.6);
  font-family: 'SF Mono', monospace;
  font-size: 11px;
}
</style>
