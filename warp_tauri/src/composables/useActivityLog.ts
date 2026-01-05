// Activity Log - 24 hour progress tracking
import { ref, computed } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

export interface ActivityEntry {
  id: string
  timestamp: Date
  project: string
  action: string
  details?: string
  duration?: number // seconds
  status: 'success' | 'failed' | 'partial'
}

export interface ActivitySummary {
  totalTasks: number
  totalHours: number
  byProject: Record<string, { tasks: number; hours: number }>
}

const entries = ref<ActivityEntry[]>([])
const loading = ref(false)

// Load from backend/SSOT
async function loadEntries() {
  loading.value = true
  try {
    const data = await invoke<ActivityEntry[]>('get_activity_log', {
      hours: 24
    }).catch(() => [])

    entries.value = data.map(e => ({
      ...e,
      timestamp: new Date(e.timestamp)
    }))
  } catch (e) {
    console.error('[useActivityLog] Failed to load:', e)
  } finally {
    loading.value = false
  }
}

// Log a new activity
async function logActivity(entry: Omit<ActivityEntry, 'id' | 'timestamp'>) {
  const newEntry: ActivityEntry = {
    ...entry,
    id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date(),
  }

  // Add to local state
  entries.value.unshift(newEntry)

  // Persist to backend
  try {
    await invoke('log_activity', { entry: newEntry })
  } catch (e) {
    console.error('[useActivityLog] Failed to persist:', e)
  }
}

// Computed summary
const summary = computed<ActivitySummary>(() => {
  const byProject: Record<string, { tasks: number; hours: number }> = {}
  let totalTasks = 0
  let totalSeconds = 0

  for (const entry of entries.value) {
    const project = entry.project || 'Unknown'
    if (!byProject[project]) {
      byProject[project] = { tasks: 0, hours: 0 }
    }
    byProject[project].tasks++
    byProject[project].hours += (entry.duration || 0) / 3600
    totalTasks++
    totalSeconds += entry.duration || 0
  }

  return {
    totalTasks,
    totalHours: totalSeconds / 3600,
    byProject,
  }
})

// Group entries by time period
const groupedEntries = computed(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)

  const groups: { label: string; entries: ActivityEntry[] }[] = [
    { label: 'Today', entries: [] },
    { label: 'Yesterday', entries: [] },
    { label: 'Earlier', entries: [] },
  ]

  for (const entry of entries.value) {
    const entryDate = new Date(entry.timestamp)
    if (entryDate >= today) {
      groups[0].entries.push(entry)
    } else if (entryDate >= yesterday) {
      groups[1].entries.push(entry)
    } else {
      groups[2].entries.push(entry)
    }
  }

  return groups.filter(g => g.entries.length > 0)
})

export function useActivityLog() {
  // Load on first use
  if (entries.value.length === 0) {
    loadEntries()
  }

  return {
    entries,
    summary,
    groupedEntries,
    loading,
    logActivity,
    loadEntries,
  }
}
