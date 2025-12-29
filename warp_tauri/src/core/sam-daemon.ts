// SAM Daemon - Perpetual autonomous operation
// Runs forever. No check-ins. No permissions. Just action.

import { invoke } from '@tauri-apps/api/core'

// =============================================================================
// DAEMON STATE
// =============================================================================

interface DaemonState {
  running: boolean
  startedAt: Date
  lastHealthCheck: Date
  actionsExecuted: number
  bytesFreed: number
  issuesResolved: number
  projectsMaintained: number
}

const state: DaemonState = {
  running: false,
  startedAt: new Date(),
  lastHealthCheck: new Date(),
  actionsExecuted: 0,
  bytesFreed: 0,
  issuesResolved: 0,
  projectsMaintained: 0
}

// =============================================================================
// LOGGING - Everything gets logged, nothing gets asked
// =============================================================================

type LogLevel = 'debug' | 'info' | 'warn' | 'action' | 'error'

interface LogEntry {
  timestamp: Date
  level: LogLevel
  message: string
  details?: any
}

const logs: LogEntry[] = []
const MAX_LOGS = 10000

function log(level: LogLevel, message: string, details?: any) {
  const entry: LogEntry = {
    timestamp: new Date(),
    level,
    message,
    details
  }

  logs.push(entry)
  if (logs.length > MAX_LOGS) {
    logs.shift()
  }

  // Console output with color coding
  const colors = {
    debug: '\x1b[90m',   // gray
    info: '\x1b[36m',    // cyan
    warn: '\x1b[33m',    // yellow
    action: '\x1b[32m',  // green
    error: '\x1b[31m'    // red
  }
  const reset = '\x1b[0m'

  console.log(`${colors[level]}[SAM ${level.toUpperCase()}]${reset} ${message}`)
  if (details) {
    console.log(`  ${JSON.stringify(details, null, 2)}`)
  }
}

// =============================================================================
// HEALTH MONITORING LOOP
// =============================================================================

async function healthLoop() {
  const INTERVAL = 30_000 // 30 seconds

  while (state.running) {
    try {
      const metrics = await invoke<SystemMetrics>('get_system_metrics')
      state.lastHealthCheck = new Date()

      // Check disk
      if (metrics.disk.percentage > 0.85) {
        log('warn', `Disk usage at ${(metrics.disk.percentage * 100).toFixed(1)}%`)

        if (metrics.disk.percentage > 0.95) {
          // CRITICAL - aggressive cleanup NOW
          log('action', 'CRITICAL: Disk nearly full. Executing aggressive cleanup.')
          await executeAggressiveCleanup()
        } else if (metrics.disk.percentage > 0.90) {
          // HIGH - standard cleanup
          log('action', 'HIGH: Disk usage elevated. Cleaning caches and trash.')
          await invoke('cleanup_caches')
          await invoke('empty_trash')
          state.actionsExecuted += 2
        } else {
          // WARNING - just caches
          log('action', 'Disk usage elevated. Cleaning caches.')
          await invoke('cleanup_caches')
          state.actionsExecuted++
        }
      }

      // Check memory
      if (metrics.memory.percentage > 0.90) {
        log('warn', `Memory usage at ${(metrics.memory.percentage * 100).toFixed(1)}%`)
        log('action', 'Memory high. Checking for runaway processes.')
        // Don't auto-kill - too dangerous. Just log.
      }

      // Check zombies
      if (metrics.zombie_count > 0) {
        log('action', `Found ${metrics.zombie_count} zombie processes. Cleaning up.`)
        await invoke('kill_zombies')
        state.actionsExecuted++
        state.issuesResolved++
      }

      log('debug', 'Health check complete', {
        disk: `${(metrics.disk.percentage * 100).toFixed(1)}%`,
        memory: `${(metrics.memory.percentage * 100).toFixed(1)}%`,
        processes: metrics.process_count
      })

    } catch (error) {
      log('error', 'Health check failed', { error })
      // Don't stop - keep trying
    }

    await sleep(INTERVAL)
  }
}

async function executeAggressiveCleanup() {
  try {
    const results = await invoke<ActionResult[]>('aggressive_cleanup')

    let totalFreed = 0
    for (const result of results) {
      log('action', `${result.action}: ${result.details}`)
      if (result.bytes_affected) {
        totalFreed += result.bytes_affected
      }
      state.actionsExecuted++
    }

    state.bytesFreed += totalFreed
    log('info', `Aggressive cleanup complete. Freed ${formatBytes(totalFreed)}`)

  } catch (error) {
    log('error', 'Aggressive cleanup failed', { error })
  }
}

// =============================================================================
// PROJECT MAINTENANCE LOOP
// =============================================================================

async function projectLoop() {
  const INTERVAL = 300_000 // 5 minutes
  const PROJECT_PATHS = [
    '/Users/davidquinton/ReverseLab',
    '/Users/davidquinton/Projects'
  ]

  while (state.running) {
    try {
      log('info', 'Scanning projects...')
      const projects = await invoke<ProjectInfo[]>('scan_projects', { basePaths: PROJECT_PATHS })

      log('info', `Found ${projects.length} projects`)

      for (const project of projects) {
        // Check for issues
        if (project.has_uncommitted) {
          log('info', `Project ${project.name} has uncommitted changes`)
          // Don't auto-commit - that's too far
        }

        // Maintain dependencies periodically (not every loop)
        if (shouldMaintain(project)) {
          log('action', `Maintaining project: ${project.name}`)
          const results = await invoke<ActionResult[]>('maintain_project', { path: project.path })

          for (const result of results) {
            log('action', `  ${result.action}: ${result.details}`)
            state.actionsExecuted++
          }
          state.projectsMaintained++
        }
      }

    } catch (error) {
      log('error', 'Project scan failed', { error })
    }

    await sleep(INTERVAL)
  }
}

// Maintain each project at most once per hour
const lastMaintained: Map<string, number> = new Map()

function shouldMaintain(project: ProjectInfo): boolean {
  const now = Date.now()
  const last = lastMaintained.get(project.path) || 0
  const hourAgo = now - 3600_000

  if (last < hourAgo) {
    lastMaintained.set(project.path, now)
    return true
  }
  return false
}

// =============================================================================
// SELF-IMPROVEMENT LOOP
// =============================================================================

interface Optimization {
  type: string
  description: string
  applied: boolean
}

const optimizations: Optimization[] = []

async function improvementLoop() {
  const INTERVAL = 3600_000 // 1 hour

  while (state.running) {
    try {
      log('info', 'Running self-improvement cycle')

      // Analyze action patterns
      const actionAnalysis = analyzeActions()

      // Learn from patterns
      if (actionAnalysis.frequentCleanups > 3) {
        log('info', 'Pattern detected: Frequent disk cleanups. Consider increasing cleanup aggressiveness.')
        optimizations.push({
          type: 'config',
          description: 'Lower disk threshold to trigger cleanup earlier',
          applied: false
        })
      }

      // Check for recurring errors
      const errorPatterns = logs
        .filter(l => l.level === 'error')
        .reduce((acc, l) => {
          const key = l.message
          acc[key] = (acc[key] || 0) + 1
          return acc
        }, {} as Record<string, number>)

      for (const [error, count] of Object.entries(errorPatterns)) {
        if (count > 5) {
          log('warn', `Recurring error detected (${count} times): ${error}`)
        }
      }

      // Performance report
      const uptime = Date.now() - state.startedAt.getTime()
      log('info', 'Performance report', {
        uptime: formatDuration(uptime),
        actionsExecuted: state.actionsExecuted,
        bytesFreed: formatBytes(state.bytesFreed),
        issuesResolved: state.issuesResolved,
        projectsMaintained: state.projectsMaintained
      })

    } catch (error) {
      log('error', 'Improvement cycle failed', { error })
    }

    await sleep(INTERVAL)
  }
}

function analyzeActions(): { frequentCleanups: number } {
  const recentActions = logs
    .filter(l => l.level === 'action')
    .filter(l => l.timestamp.getTime() > Date.now() - 3600_000) // Last hour

  const cleanupActions = recentActions.filter(l =>
    l.message.includes('cleanup') || l.message.includes('Cleaning')
  )

  return {
    frequentCleanups: cleanupActions.length
  }
}

// =============================================================================
// WEB MONITORING
// =============================================================================

interface MonitoredUrl {
  url: string
  interval: number
  lastContent: string
  lastCheck: Date
  callback: (change: { old: string, new: string }) => void
}

const monitoredUrls: Map<string, MonitoredUrl> = new Map()

async function webMonitorLoop() {
  const CHECK_INTERVAL = 60_000 // 1 minute base interval

  while (state.running) {
    const now = Date.now()

    for (const [url, monitor] of monitoredUrls) {
      const timeSinceCheck = now - monitor.lastCheck.getTime()

      if (timeSinceCheck >= monitor.interval) {
        try {
          const result = await invoke<ScrapeResult>('scrape_url', { url })

          if (monitor.lastContent && result.body !== monitor.lastContent) {
            log('action', `Change detected on ${url}`)
            monitor.callback({
              old: monitor.lastContent,
              new: result.body
            })
          }

          monitor.lastContent = result.body
          monitor.lastCheck = new Date()

        } catch (error) {
          log('error', `Failed to check ${url}`, { error })
        }
      }
    }

    await sleep(CHECK_INTERVAL)
  }
}

export function monitorUrl(
  url: string,
  intervalMs: number,
  callback: (change: { old: string, new: string }) => void
) {
  monitoredUrls.set(url, {
    url,
    interval: intervalMs,
    lastContent: '',
    lastCheck: new Date(0), // Force immediate check
    callback
  })
  log('info', `Now monitoring: ${url} (every ${intervalMs / 1000}s)`)
}

export function stopMonitoring(url: string) {
  monitoredUrls.delete(url)
  log('info', `Stopped monitoring: ${url}`)
}

// =============================================================================
// SCHEDULED TASKS
// =============================================================================

interface ScheduledTask {
  id: string
  name: string
  schedule: string // cron-like or simple schedule
  action: () => Promise<void>
  lastRun: Date | null
  nextRun: Date
}

const scheduledTasks: Map<string, ScheduledTask> = new Map()

export function scheduleTask(
  id: string,
  name: string,
  schedule: string,
  action: () => Promise<void>
) {
  const nextRun = calculateNextRun(schedule)
  scheduledTasks.set(id, {
    id,
    name,
    schedule,
    action,
    lastRun: null,
    nextRun
  })
  log('info', `Scheduled task: ${name} (${schedule})`)
}

function calculateNextRun(schedule: string): Date {
  const now = new Date()

  // Simple schedule parsing
  if (schedule === 'daily') {
    const next = new Date(now)
    next.setDate(next.getDate() + 1)
    next.setHours(3, 0, 0, 0) // 3 AM
    return next
  }

  if (schedule === 'hourly') {
    const next = new Date(now)
    next.setHours(next.getHours() + 1, 0, 0, 0)
    return next
  }

  if (schedule.startsWith('every ')) {
    const match = schedule.match(/every (\d+) (minute|hour|day)s?/)
    if (match) {
      const amount = parseInt(match[1])
      const unit = match[2]
      const next = new Date(now)

      switch (unit) {
        case 'minute':
          next.setMinutes(next.getMinutes() + amount)
          break
        case 'hour':
          next.setHours(next.getHours() + amount)
          break
        case 'day':
          next.setDate(next.getDate() + amount)
          break
      }
      return next
    }
  }

  // Default: 1 hour from now
  return new Date(now.getTime() + 3600_000)
}

async function schedulerLoop() {
  while (state.running) {
    const now = new Date()

    for (const [id, task] of scheduledTasks) {
      if (now >= task.nextRun) {
        log('action', `Running scheduled task: ${task.name}`)

        try {
          await task.action()
          task.lastRun = now
          task.nextRun = calculateNextRun(task.schedule)
          state.actionsExecuted++
        } catch (error) {
          log('error', `Scheduled task failed: ${task.name}`, { error })
        }
      }
    }

    await sleep(60_000) // Check every minute
  }
}

// =============================================================================
// DEFAULT SCHEDULED TASKS
// =============================================================================

function setupDefaultTasks() {
  // Daily aggressive cleanup at 3 AM
  scheduleTask('daily_cleanup', 'Daily System Cleanup', 'daily', async () => {
    await executeAggressiveCleanup()
  })

  // Hourly cache cleanup
  scheduleTask('hourly_cache', 'Hourly Cache Cleanup', 'hourly', async () => {
    await invoke('cleanup_caches')
  })

  // Every 6 hours: update packages
  scheduleTask('package_updates', 'Package Updates', 'every 6 hours', async () => {
    await invoke('update_all_packages')
  })
}

// =============================================================================
// DAEMON CONTROL
// =============================================================================

export async function startDaemon() {
  if (state.running) {
    log('warn', 'Daemon already running')
    return
  }

  state.running = true
  state.startedAt = new Date()
  log('info', 'SAM Daemon starting...')
  log('info', 'Mode: AUTONOMOUS - No check-ins, no permissions')

  // Setup default scheduled tasks
  setupDefaultTasks()

  // Start all loops (they run concurrently)
  Promise.all([
    healthLoop(),
    projectLoop(),
    improvementLoop(),
    webMonitorLoop(),
    schedulerLoop()
  ]).catch(error => {
    log('error', 'Daemon loop crashed', { error })
    // Auto-restart
    setTimeout(startDaemon, 5000)
  })

  log('info', 'SAM Daemon running. All systems autonomous.')
}

export function stopDaemon() {
  log('info', 'SAM Daemon stopping...')
  state.running = false
}

export function getDaemonStatus(): DaemonState {
  return { ...state }
}

export function getLogs(level?: LogLevel, limit: number = 100): LogEntry[] {
  let filtered = level
    ? logs.filter(l => l.level === level)
    : logs

  return filtered.slice(-limit)
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function formatBytes(bytes: number): string {
  const KB = 1024
  const MB = KB * 1024
  const GB = MB * 1024

  if (bytes >= GB) return `${(bytes / GB).toFixed(2)} GB`
  if (bytes >= MB) return `${(bytes / MB).toFixed(2)} MB`
  if (bytes >= KB) return `${(bytes / KB).toFixed(2)} KB`
  return `${bytes} bytes`
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${minutes % 60}m`
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`
  return `${seconds}s`
}

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

interface SystemMetrics {
  disk: {
    total_bytes: number
    used_bytes: number
    available_bytes: number
    percentage: number
  }
  memory: {
    total_bytes: number
    used_bytes: number
    percentage: number
  }
  cpu_usage: number
  process_count: number
  zombie_count: number
}

interface ActionResult {
  success: boolean
  action: string
  details: string
  bytes_affected?: number
  files_affected?: number
  timestamp: number
}

interface ProjectInfo {
  path: string
  name: string
  project_type: string
  has_git: boolean
  has_uncommitted: boolean
  last_modified: number
}

interface ScrapeResult {
  url: string
  status: number
  headers: Record<string, string>
  body: string
  links: string[]
  timestamp: number
}

// =============================================================================
// AUTO-START (optional - controlled by config)
// =============================================================================

// Uncomment to auto-start when imported:
// startDaemon()

export default {
  start: startDaemon,
  stop: stopDaemon,
  status: getDaemonStatus,
  logs: getLogs,
  monitor: monitorUrl,
  schedule: scheduleTask
}
