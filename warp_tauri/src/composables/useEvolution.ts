/**
 * useEvolution - Bridge to SSOT Evolution System
 *
 * Connects warp_tauri UI to the perpetual improvement engine
 * running on the Mac Mini. Works across all Apple devices via
 * shared SSOT volume.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

// SSOT paths
const SSOT_PATH = '/Volumes/Plex/SSOT'
const SAM_BRAIN_PATH = `${SSOT_PATH}/sam_brain`
const EVOLUTION_DB = `${SAM_BRAIN_PATH}/evolution_tracker.db`
const EVOLUTION_LOG = `${SAM_BRAIN_PATH}/evolution.log`

// Types matching the Python system
export interface Project {
  id: string
  name: string
  category: 'brain' | 'visual' | 'voice' | 'content' | 'platform'
  current_progress: number
  last_updated: string
  ssot_path: string
}

export interface Improvement {
  id: string
  project_id: string
  type: 'efficiency' | 'reliability' | 'feature' | 'integration' | 'documentation' | 'testing'
  priority: 1 | 2 | 3
  status: 'detected' | 'validated' | 'queued' | 'implementing' | 'completed' | 'rejected'
  description: string
  detected_at: string
  completed_at?: string
  outcome?: string
}

export interface EvolutionStatus {
  daemon_running: boolean
  daemon_pid?: number
  last_cycle?: string
  projects_count: number
  improvements: {
    detected: number
    completed: number
    pending: number
  }
  escalations: number
}

export function useEvolution() {
  const projects = ref<Project[]>([])
  const improvements = ref<Improvement[]>([])
  const status = ref<EvolutionStatus>({
    daemon_running: false,
    projects_count: 0,
    improvements: { detected: 0, completed: 0, pending: 0 },
    escalations: 0
  })
  const recentLogs = ref<string[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const pollInterval = ref<number | null>(null)

  // ========================================================================
  // DATA FETCHING
  // ========================================================================

  async function fetchProjects(): Promise<void> {
    try {
      const result = await invoke<{ stdout: string }>('execute_shell', {
        command: `python3 ${SAM_BRAIN_PATH}/evolution_tracker.py projects 2>/dev/null || echo "[]"`,
        cwd: SSOT_PATH
      })

      // Parse the output (format: [category] name: progress%)
      const lines = result.stdout.trim().split('\n').filter(Boolean)
      const parsed: Project[] = []

      for (const line of lines) {
        const match = line.match(/\[(\w+)\]\s+(.+?):\s+(\d+)%/)
        if (match) {
          parsed.push({
            id: match[2].toLowerCase().replace(/\s+/g, '_'),
            name: match[2],
            category: match[1] as Project['category'],
            current_progress: parseInt(match[3]) / 100,
            last_updated: new Date().toISOString(),
            ssot_path: ''
          })
        }
      }

      projects.value = parsed
    } catch (e) {
      console.error('Failed to fetch projects:', e)
    }
  }

  async function fetchImprovements(): Promise<void> {
    try {
      const result = await invoke<{ stdout: string }>('execute_shell', {
        command: `python3 -c "
import sys
sys.path.insert(0, '${SAM_BRAIN_PATH}')
from evolution_tracker import EvolutionTracker
import json
t = EvolutionTracker()
imps = t.get_improvements()
print(json.dumps([{
  'id': i.id,
  'project_id': i.project_id,
  'type': i.type,
  'priority': i.priority,
  'status': i.status,
  'description': i.description,
  'detected_at': i.detected_at
} for i in imps[:50]]))
"`,
        cwd: SSOT_PATH
      })

      improvements.value = JSON.parse(result.stdout.trim() || '[]')
    } catch (e) {
      console.error('Failed to fetch improvements:', e)
      improvements.value = []
    }
  }

  async function fetchStatus(): Promise<void> {
    try {
      // Check daemon PID
      const pidResult = await invoke<{ stdout: string }>('execute_shell', {
        command: `cat ${SAM_BRAIN_PATH}/daemon.pid 2>/dev/null && ps -p $(cat ${SAM_BRAIN_PATH}/daemon.pid 2>/dev/null) > /dev/null 2>&1 && echo "running" || echo "stopped"`,
        cwd: SSOT_PATH
      })

      const lines = pidResult.stdout.trim().split('\n')
      const pid = parseInt(lines[0]) || undefined
      const running = lines[lines.length - 1] === 'running'

      // Get summary
      const summaryResult = await invoke<{ stdout: string }>('execute_shell', {
        command: `python3 -c "
import sys
sys.path.insert(0, '${SAM_BRAIN_PATH}')
from evolution_tracker import EvolutionTracker
import json
t = EvolutionTracker()
s = t.summary()
print(json.dumps(s))
"`,
        cwd: SSOT_PATH
      })

      const summary = JSON.parse(summaryResult.stdout.trim() || '{}')
      const imps = summary.improvements || {}

      status.value = {
        daemon_running: running,
        daemon_pid: pid,
        projects_count: summary.total_projects || 0,
        improvements: {
          detected: imps.detected || 0,
          completed: imps.completed || 0,
          pending: (imps.detected || 0) + (imps.validated || 0) + (imps.queued || 0)
        },
        escalations: 0
      }
    } catch (e) {
      console.error('Failed to fetch status:', e)
    }
  }

  async function fetchRecentLogs(): Promise<void> {
    try {
      const result = await invoke<{ stdout: string }>('execute_shell', {
        command: `tail -20 ${EVOLUTION_LOG} 2>/dev/null || echo "No logs yet"`,
        cwd: SSOT_PATH
      })

      recentLogs.value = result.stdout.trim().split('\n').filter(Boolean)
    } catch (e) {
      recentLogs.value = ['Failed to load logs']
    }
  }

  async function refresh(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      await Promise.all([
        fetchStatus(),
        fetchProjects(),
        fetchImprovements(),
        fetchRecentLogs()
      ])
    } catch (e) {
      error.value = String(e)
    } finally {
      isLoading.value = false
    }
  }

  // ========================================================================
  // ACTIONS
  // ========================================================================

  async function startDaemon(): Promise<boolean> {
    try {
      await invoke('execute_shell', {
        command: `cd ${SSOT_PATH} && nohup python3 sam_brain/advanced_evolution.py run --interval 15 > sam_brain/evolution.log 2>&1 &`,
        cwd: SSOT_PATH
      })
      await new Promise(resolve => setTimeout(resolve, 2000))
      await fetchStatus()
      return status.value.daemon_running
    } catch (e) {
      error.value = String(e)
      return false
    }
  }

  async function stopDaemon(): Promise<boolean> {
    try {
      if (status.value.daemon_pid) {
        await invoke('execute_shell', {
          command: `kill ${status.value.daemon_pid} 2>/dev/null || true`,
          cwd: SSOT_PATH
        })
      }
      await new Promise(resolve => setTimeout(resolve, 1000))
      await fetchStatus()
      return !status.value.daemon_running
    } catch (e) {
      error.value = String(e)
      return false
    }
  }

  async function triggerScan(): Promise<void> {
    try {
      await invoke('execute_shell', {
        command: `python3 ${SAM_BRAIN_PATH}/improvement_detector.py save`,
        cwd: SSOT_PATH
      })
      await refresh()
    } catch (e) {
      error.value = String(e)
    }
  }

  async function syncFromSSoT(): Promise<void> {
    try {
      await invoke('execute_shell', {
        command: `python3 ${SAM_BRAIN_PATH}/evolution_tracker.py sync`,
        cwd: SSOT_PATH
      })
      await fetchProjects()
    } catch (e) {
      error.value = String(e)
    }
  }

  async function approveImprovement(id: string): Promise<void> {
    try {
      await invoke('execute_shell', {
        command: `python3 -c "
import sys
sys.path.insert(0, '${SAM_BRAIN_PATH}')
from evolution_tracker import EvolutionTracker
t = EvolutionTracker()
t.update_improvement_status('${id}', 'queued')
"`,
        cwd: SSOT_PATH
      })
      await fetchImprovements()
    } catch (e) {
      error.value = String(e)
    }
  }

  async function rejectImprovement(id: string): Promise<void> {
    try {
      await invoke('execute_shell', {
        command: `python3 -c "
import sys
sys.path.insert(0, '${SAM_BRAIN_PATH}')
from evolution_tracker import EvolutionTracker
t = EvolutionTracker()
t.update_improvement_status('${id}', 'rejected')
"`,
        cwd: SSOT_PATH
      })
      await fetchImprovements()
    } catch (e) {
      error.value = String(e)
    }
  }

  // ========================================================================
  // COMPUTED
  // ========================================================================

  const projectsByCategory = computed(() => {
    const grouped: Record<string, Project[]> = {}
    for (const p of projects.value) {
      if (!grouped[p.category]) grouped[p.category] = []
      grouped[p.category].push(p)
    }
    return grouped
  })

  const pendingImprovements = computed(() =>
    improvements.value.filter(i => i.status === 'detected' || i.status === 'validated')
  )

  const overallProgress = computed(() => {
    if (projects.value.length === 0) return 0
    const sum = projects.value.reduce((acc, p) => acc + p.current_progress, 0)
    return sum / projects.value.length
  })

  // ========================================================================
  // LIFECYCLE
  // ========================================================================

  function startPolling(intervalMs: number = 30000): void {
    if (pollInterval.value) return
    pollInterval.value = window.setInterval(refresh, intervalMs)
  }

  function stopPolling(): void {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      pollInterval.value = null
    }
  }

  onMounted(() => {
    refresh()
    startPolling()
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    // State
    projects,
    improvements,
    status,
    recentLogs,
    isLoading,
    error,

    // Computed
    projectsByCategory,
    pendingImprovements,
    overallProgress,

    // Actions
    refresh,
    startDaemon,
    stopDaemon,
    triggerScan,
    syncFromSSoT,
    approveImprovement,
    rejectImprovement,

    // Polling
    startPolling,
    stopPolling
  }
}
