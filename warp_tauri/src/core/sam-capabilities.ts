/**
 * SAM Capability Modules
 * ======================
 *
 * Every capability SAM has. Each module is:
 * - Independently enableable/disableable
 * - Has its own permission level
 * - Fully audited
 * - Designed for maximum utility with maximum safety
 *
 * This is what makes SAM actually useful.
 */

import { ref, computed, reactive } from 'vue'
import {
  SAMSafety,
  PermissionLevel,
  RiskLevel,
  ActionCategory,
  validateAction,
  type SAMAction,
  type ValidationResult
} from './sam-safety'

// ============================================================================
// CAPABILITY MODULE INTERFACE
// ============================================================================

export interface CapabilityModule {
  /** Unique identifier */
  id: string

  /** Human-readable name */
  name: string

  /** Description of what this capability does */
  description: string

  /** Icon for UI */
  icon: string

  /** Action category for permissions */
  category: ActionCategory

  /** Whether this module is currently enabled */
  enabled: boolean

  /** Current permission level */
  permissionLevel: PermissionLevel

  /** Available actions in this module */
  actions: CapabilityAction[]

  /** Initialize the module */
  initialize(): Promise<void>

  /** Cleanup when disabling */
  cleanup(): Promise<void>

  /** Get current status */
  getStatus(): CapabilityStatus
}

export interface CapabilityAction {
  id: string
  name: string
  description: string
  riskLevel: RiskLevel
  execute: (params: Record<string, unknown>) => Promise<ActionResult>
  validate: (params: Record<string, unknown>) => ValidationResult
  getUndo?: (params: Record<string, unknown>, result: unknown) => (() => Promise<void>) | undefined
}

export interface CapabilityStatus {
  enabled: boolean
  connected: boolean
  lastActivity?: Date
  pendingActions: number
  errors: string[]
}

export interface ActionResult {
  success: boolean
  data?: unknown
  error?: string
  undoAvailable: boolean
  undoFn?: () => Promise<void>
}

// ============================================================================
// FILESYSTEM CAPABILITY
// ============================================================================

export function createFilesystemCapability(): CapabilityModule {
  const enabled = ref(true)
  const permissionLevel = ref(PermissionLevel.ASK_ONCE)
  const recentFiles = ref<string[]>([])
  const pendingOps = ref(0)

  // Backup storage for undo
  const backups = new Map<string, string>()

  return {
    id: 'filesystem',
    name: 'File System',
    description: 'Read, write, and manage files on your computer',
    icon: '📁',
    category: 'filesystem',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'read_file',
        name: 'Read File',
        description: 'Read the contents of a file',
        riskLevel: RiskLevel.NONE,
        async execute({ path }: { path: string }) {
          try {
            const fs = await import('@tauri-apps/api/fs')
            const content = await fs.readTextFile(path)
            recentFiles.value = [path, ...recentFiles.value.filter(f => f !== path)].slice(0, 100)
            return { success: true, data: content, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ path }) {
          return validateAction({
            category: 'filesystem',
            operation: 'read',
            description: `Read file: ${path}`,
            target: path,
            reversible: true
          }, { filesystem: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'write_file',
        name: 'Write File',
        description: 'Write content to a file',
        riskLevel: RiskLevel.MEDIUM,
        async execute({ path, content }: { path: string; content: string }) {
          try {
            const fs = await import('@tauri-apps/api/fs')

            // Backup existing content for undo
            let previousContent: string | undefined
            try {
              previousContent = await fs.readTextFile(path)
              backups.set(path, previousContent)
            } catch {
              // File doesn't exist yet
            }

            await fs.writeTextFile(path, content)
            recentFiles.value = [path, ...recentFiles.value.filter(f => f !== path)].slice(0, 100)

            return {
              success: true,
              undoAvailable: true,
              undoFn: previousContent
                ? async () => {
                    await fs.writeTextFile(path, previousContent!)
                    backups.delete(path)
                  }
                : async () => {
                    await fs.removeFile(path)
                  }
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ path }) {
          return validateAction({
            category: 'filesystem',
            operation: 'write',
            description: `Write to file: ${path}`,
            target: path,
            reversible: true
          }, { filesystem: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'delete_file',
        name: 'Delete File',
        description: 'Delete a file (moves to trash by default)',
        riskLevel: RiskLevel.HIGH,
        async execute({ path, permanent = false }: { path: string; permanent?: boolean }) {
          try {
            const fs = await import('@tauri-apps/api/fs')

            // Always backup before delete
            const content = await fs.readTextFile(path)
            backups.set(`deleted:${path}`, content)

            if (permanent) {
              await fs.removeFile(path)
            } else {
              // Move to trash (macOS)
              const { invoke } = await import('@tauri-apps/api/tauri')
              await invoke('move_to_trash', { path })
            }

            return {
              success: true,
              undoAvailable: true,
              undoFn: async () => {
                const backup = backups.get(`deleted:${path}`)
                if (backup) {
                  await fs.writeTextFile(path, backup)
                  backups.delete(`deleted:${path}`)
                }
              }
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ path, permanent }) {
          return validateAction({
            category: 'filesystem',
            operation: permanent ? 'permanent_delete' : 'delete',
            description: `Delete file: ${path}${permanent ? ' (permanent)' : ''}`,
            target: path,
            reversible: !permanent
          }, { filesystem: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'list_directory',
        name: 'List Directory',
        description: 'List files in a directory',
        riskLevel: RiskLevel.NONE,
        async execute({ path }: { path: string }) {
          try {
            const fs = await import('@tauri-apps/api/fs')
            const entries = await fs.readDir(path)
            return { success: true, data: entries, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ path }) {
          return validateAction({
            category: 'filesystem',
            operation: 'list',
            description: `List directory: ${path}`,
            target: path,
            reversible: true
          }, { filesystem: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'search_files',
        name: 'Search Files',
        description: 'Search for files matching a pattern',
        riskLevel: RiskLevel.NONE,
        async execute({ path, pattern, content }: { path: string; pattern?: string; content?: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const results = await invoke('search_files', { path, pattern, content })
            return { success: true, data: results, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ path }) {
          return validateAction({
            category: 'filesystem',
            operation: 'search',
            description: `Search in: ${path}`,
            target: path,
            reversible: true
          }, { filesystem: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      }
    ],

    async initialize() {
      // Initialize filesystem access
      enabled.value = true
    },

    async cleanup() {
      // Clear backups older than 24 hours
      // In production, persist these to disk
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: true,
        lastActivity: recentFiles.value.length > 0 ? new Date() : undefined,
        pendingActions: pendingOps.value,
        errors: []
      }
    }
  }
}

// ============================================================================
// PROCESS CAPABILITY
// ============================================================================

export function createProcessCapability(): CapabilityModule {
  const enabled = ref(true)
  const permissionLevel = ref(PermissionLevel.ASK_ONCE)
  const runningProcesses = ref<Map<number, { command: string; startedAt: Date }>>(new Map())

  return {
    id: 'process',
    name: 'Process Control',
    description: 'Start, stop, and manage system processes',
    icon: '⚙️',
    category: 'process',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'run_command',
        name: 'Run Command',
        description: 'Execute a shell command',
        riskLevel: RiskLevel.MEDIUM,
        async execute({ command, cwd, timeout = 60000 }: { command: string; cwd?: string; timeout?: number }) {
          try {
            const { Command } = await import('@tauri-apps/api/shell')

            // Parse command
            const parts = command.split(' ')
            const program = parts[0]
            const args = parts.slice(1)

            const cmd = new Command(program, args, { cwd })

            // Handle timeout
            const timeoutPromise = new Promise<never>((_, reject) => {
              setTimeout(() => reject(new Error('Command timed out')), timeout)
            })

            const outputPromise = cmd.execute()
            const output = await Promise.race([outputPromise, timeoutPromise])

            return {
              success: output.code === 0,
              data: {
                stdout: output.stdout,
                stderr: output.stderr,
                code: output.code
              },
              undoAvailable: false,
              error: output.code !== 0 ? output.stderr : undefined
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ command }) {
          // Check for dangerous commands
          const dangerous = ['rm -rf /', 'sudo rm', 'mkfs', 'dd if=/dev/zero', ':(){:|:&};:']
          const isDangerous = dangerous.some(d => command.includes(d))

          if (isDangerous) {
            return {
              allowed: false,
              reason: 'This command is potentially destructive',
              requiredPermission: PermissionLevel.FORBIDDEN,
              riskLevel: RiskLevel.EXTREME,
              warnings: ['This command could cause system damage'],
              requiresConfirmation: true
            }
          }

          return validateAction({
            category: 'process',
            operation: 'run',
            description: `Run command: ${command}`,
            target: command,
            reversible: false,
            affectsExternalSystems: command.includes('curl') || command.includes('wget')
          }, { process: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'list_processes',
        name: 'List Processes',
        description: 'List running processes',
        riskLevel: RiskLevel.NONE,
        async execute() {
          try {
            const { Command } = await import('@tauri-apps/api/shell')
            const output = await new Command('ps', ['aux']).execute()
            return { success: true, data: output.stdout, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.READ_ONLY,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'kill_process',
        name: 'Kill Process',
        description: 'Terminate a running process',
        riskLevel: RiskLevel.HIGH,
        async execute({ pid, signal = 'SIGTERM' }: { pid: number; signal?: string }) {
          try {
            const { Command } = await import('@tauri-apps/api/shell')
            await new Command('kill', ['-s', signal, String(pid)]).execute()
            return { success: true, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ pid }) {
          return validateAction({
            category: 'process',
            operation: 'kill',
            description: `Kill process ${pid}`,
            target: String(pid),
            reversible: false
          }, { process: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      }
    ],

    async initialize() {
      enabled.value = true
    },

    async cleanup() {
      runningProcesses.value.clear()
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: true,
        pendingActions: 0,
        errors: []
      }
    }
  }
}

// ============================================================================
// COMMUNICATION CAPABILITY (Email, Calendar, Messages)
// ============================================================================

export function createCommunicationCapability(): CapabilityModule {
  const enabled = ref(true)
  const permissionLevel = ref(PermissionLevel.SUGGEST_ONLY)
  const connectedAccounts = ref<string[]>([])

  return {
    id: 'communication',
    name: 'Communication',
    description: 'Email, calendar, and messaging integration',
    icon: '📧',
    category: 'email',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'read_emails',
        name: 'Read Emails',
        description: 'Read emails from your inbox',
        riskLevel: RiskLevel.LOW,
        async execute({ account, folder = 'INBOX', limit = 20 }: { account: string; folder?: string; limit?: number }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const emails = await invoke('read_emails', { account, folder, limit })
            return { success: true, data: emails, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return validateAction({
            category: 'email',
            operation: 'read',
            description: 'Read emails',
            reversible: true
          }, { email: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'draft_email',
        name: 'Draft Email',
        description: 'Create a draft email (not sent)',
        riskLevel: RiskLevel.LOW,
        async execute({ to, subject, body, account }: { to: string; subject: string; body: string; account: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const draftId = await invoke('create_email_draft', { to, subject, body, account })
            return {
              success: true,
              data: { draftId },
              undoAvailable: true,
              undoFn: async () => {
                await invoke('delete_email_draft', { draftId, account })
              }
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ to }) {
          return validateAction({
            category: 'email',
            operation: 'draft',
            description: `Draft email to: ${to}`,
            reversible: true
          }, { email: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'send_email',
        name: 'Send Email',
        description: 'Send an email',
        riskLevel: RiskLevel.HIGH,
        async execute({ to, subject, body, account }: { to: string; subject: string; body: string; account: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const result = await invoke('send_email', { to, subject, body, account })
            return {
              success: true,
              data: result,
              undoAvailable: false // Can't unsend
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ to }) {
          return validateAction({
            category: 'email',
            operation: 'send',
            description: `Send email to: ${to}`,
            reversible: false,
            affectsOtherPeople: true
          }, { email: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'get_calendar',
        name: 'Get Calendar',
        description: 'Read calendar events',
        riskLevel: RiskLevel.NONE,
        async execute({ start, end }: { start: Date; end: Date }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const events = await invoke('get_calendar_events', {
              start: start.toISOString(),
              end: end.toISOString()
            })
            return { success: true, data: events, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return validateAction({
            category: 'calendar',
            operation: 'read',
            description: 'Read calendar events',
            reversible: true
          }, { calendar: PermissionLevel.READ_ONLY } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'create_event',
        name: 'Create Event',
        description: 'Create a calendar event',
        riskLevel: RiskLevel.MEDIUM,
        async execute({ title, start, end, location, notes, attendees }: {
          title: string
          start: Date
          end: Date
          location?: string
          notes?: string
          attendees?: string[]
        }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const eventId = await invoke('create_calendar_event', {
              title,
              start: start.toISOString(),
              end: end.toISOString(),
              location,
              notes,
              attendees
            })
            return {
              success: true,
              data: { eventId },
              undoAvailable: true,
              undoFn: async () => {
                await invoke('delete_calendar_event', { eventId })
              }
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ attendees }) {
          return validateAction({
            category: 'calendar',
            operation: 'create',
            description: 'Create calendar event',
            reversible: true,
            affectsOtherPeople: attendees && attendees.length > 0
          }, { calendar: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      }
    ],

    async initialize() {
      // Check for connected accounts
      try {
        const { invoke } = await import('@tauri-apps/api/tauri')
        connectedAccounts.value = await invoke('get_connected_accounts')
      } catch {
        connectedAccounts.value = []
      }
      enabled.value = true
    },

    async cleanup() {
      // Cleanup
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: connectedAccounts.value.length > 0,
        pendingActions: 0,
        errors: connectedAccounts.value.length === 0 ? ['No accounts connected'] : []
      }
    }
  }
}

// ============================================================================
// KNOWLEDGE CAPABILITY (Web Search, Document Analysis, Learning)
// ============================================================================

export function createKnowledgeCapability(): CapabilityModule {
  const enabled = ref(true)
  const permissionLevel = ref(PermissionLevel.AUTONOMOUS)
  const cache = new Map<string, { data: unknown; timestamp: Date }>()

  return {
    id: 'knowledge',
    name: 'Knowledge',
    description: 'Web search, document analysis, and learning',
    icon: '🧠',
    category: 'browser',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'web_search',
        name: 'Web Search',
        description: 'Search the web for information',
        riskLevel: RiskLevel.NONE,
        async execute({ query, engine = 'duckduckgo' }: { query: string; engine?: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const results = await invoke('web_search', { query, engine })
            cache.set(`search:${query}`, { data: results, timestamp: new Date() })
            return { success: true, data: results, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.AUTONOMOUS,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'fetch_url',
        name: 'Fetch URL',
        description: 'Fetch and read a web page',
        riskLevel: RiskLevel.LOW,
        async execute({ url }: { url: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const content = await invoke('fetch_url', { url })
            return { success: true, data: content, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ url }) {
          // Block potentially malicious URLs
          const blocked = ['localhost', '127.0.0.1', '0.0.0.0', 'internal', 'admin']
          const isBlocked = blocked.some(b => url.includes(b))

          if (isBlocked) {
            return {
              allowed: false,
              reason: 'This URL appears to be internal/sensitive',
              requiredPermission: PermissionLevel.FORBIDDEN,
              riskLevel: RiskLevel.HIGH,
              warnings: ['Blocked for security'],
              requiresConfirmation: true
            }
          }

          return validateAction({
            category: 'browser',
            operation: 'fetch',
            description: `Fetch: ${url}`,
            target: url,
            reversible: true
          }, { browser: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'analyze_document',
        name: 'Analyze Document',
        description: 'Extract and analyze information from a document',
        riskLevel: RiskLevel.NONE,
        async execute({ path, format }: { path: string; format?: 'pdf' | 'docx' | 'txt' }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const analysis = await invoke('analyze_document', { path, format })
            return { success: true, data: analysis, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.READ_ONLY,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'summarize',
        name: 'Summarize',
        description: 'Summarize text or document content',
        riskLevel: RiskLevel.NONE,
        async execute({ text, length = 'medium' }: { text: string; length?: 'short' | 'medium' | 'long' }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const summary = await invoke('summarize_text', { text, length })
            return { success: true, data: summary, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.AUTONOMOUS,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      }
    ],

    async initialize() {
      enabled.value = true
    },

    async cleanup() {
      cache.clear()
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: true,
        pendingActions: 0,
        errors: []
      }
    }
  }
}

// ============================================================================
// HOME AUTOMATION CAPABILITY
// ============================================================================

export function createHomeCapability(): CapabilityModule {
  const enabled = ref(false) // Disabled by default
  const permissionLevel = ref(PermissionLevel.ASK_ONCE)
  const connectedDevices = ref<{ id: string; name: string; type: string }[]>([])

  return {
    id: 'home',
    name: 'Smart Home',
    description: 'Control HomeKit and smart home devices',
    icon: '🏠',
    category: 'homekit',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'list_devices',
        name: 'List Devices',
        description: 'List all connected smart home devices',
        riskLevel: RiskLevel.NONE,
        async execute() {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const devices = await invoke('homekit_list_devices')
            connectedDevices.value = devices as typeof connectedDevices.value
            return { success: true, data: devices, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.READ_ONLY,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'control_device',
        name: 'Control Device',
        description: 'Control a smart home device',
        riskLevel: RiskLevel.LOW,
        async execute({ deviceId, action, value }: { deviceId: string; action: string; value?: unknown }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')

            // Get current state for undo
            const currentState = await invoke('homekit_get_state', { deviceId })

            await invoke('homekit_control', { deviceId, action, value })

            return {
              success: true,
              undoAvailable: true,
              undoFn: async () => {
                await invoke('homekit_set_state', { deviceId, state: currentState })
              }
            }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ deviceId, action }) {
          const device = connectedDevices.value.find(d => d.id === deviceId)
          return validateAction({
            category: 'homekit',
            operation: action,
            description: `${action} ${device?.name || deviceId}`,
            target: deviceId,
            reversible: true
          }, { homekit: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'run_scene',
        name: 'Run Scene',
        description: 'Run a HomeKit scene',
        riskLevel: RiskLevel.MEDIUM,
        async execute({ sceneId }: { sceneId: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            await invoke('homekit_run_scene', { sceneId })
            return { success: true, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate({ sceneId }) {
          return validateAction({
            category: 'homekit',
            operation: 'scene',
            description: `Run scene: ${sceneId}`,
            target: sceneId,
            reversible: false
          }, { homekit: permissionLevel.value } as Record<ActionCategory, PermissionLevel>)
        }
      }
    ],

    async initialize() {
      try {
        const { invoke } = await import('@tauri-apps/api/tauri')
        connectedDevices.value = await invoke('homekit_list_devices')
        enabled.value = connectedDevices.value.length > 0
      } catch {
        enabled.value = false
      }
    },

    async cleanup() {
      connectedDevices.value = []
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: connectedDevices.value.length > 0,
        pendingActions: 0,
        errors: connectedDevices.value.length === 0 ? ['No HomeKit devices found'] : []
      }
    }
  }
}

// ============================================================================
// FINANCIAL CAPABILITY (Read-only by default, highest security)
// ============================================================================

export function createFinancialCapability(): CapabilityModule {
  const enabled = ref(false) // Disabled by default - must opt-in
  const permissionLevel = ref(PermissionLevel.SUGGEST_ONLY) // Cannot be raised above this

  return {
    id: 'financial',
    name: 'Financial',
    description: 'Read financial data (transactions, budgets). Payments require explicit confirmation.',
    icon: '💰',
    category: 'financial',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) {
      // Enforce maximum permission level
      permissionLevel.value = Math.min(v, PermissionLevel.SUGGEST_ONLY)
    },

    actions: [
      {
        id: 'get_transactions',
        name: 'Get Transactions',
        description: 'View recent transactions',
        riskLevel: RiskLevel.MEDIUM,
        async execute({ accountId, limit = 50 }: { accountId: string; limit?: number }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const transactions = await invoke('get_transactions', { accountId, limit })
            return { success: true, data: transactions, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return validateAction({
            category: 'financial',
            operation: 'read',
            description: 'View transactions',
            reversible: true
          }, { financial: PermissionLevel.SUGGEST_ONLY } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'get_balance',
        name: 'Get Balance',
        description: 'Get account balance',
        riskLevel: RiskLevel.MEDIUM,
        async execute({ accountId }: { accountId: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const balance = await invoke('get_balance', { accountId })
            return { success: true, data: balance, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return validateAction({
            category: 'financial',
            operation: 'read',
            description: 'View balance',
            reversible: true
          }, { financial: PermissionLevel.SUGGEST_ONLY } as Record<ActionCategory, PermissionLevel>)
        }
      },
      {
        id: 'categorize_spending',
        name: 'Categorize Spending',
        description: 'Analyze and categorize spending',
        riskLevel: RiskLevel.LOW,
        async execute({ startDate, endDate }: { startDate: Date; endDate: Date }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const analysis = await invoke('analyze_spending', {
              startDate: startDate.toISOString(),
              endDate: endDate.toISOString()
            })
            return { success: true, data: analysis, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.SUGGEST_ONLY,
            riskLevel: RiskLevel.LOW,
            warnings: [],
            requiresConfirmation: true,
            confirmationMessage: 'SAM wants to analyze your spending. Allow?'
          }
        }
      }
      // NOTE: No payment actions - SAM cannot initiate payments
      // User must do payments manually, SAM can only assist with information
    ],

    async initialize() {
      // Financial capability requires explicit opt-in
      enabled.value = false
    },

    async cleanup() {
      // Clear any cached financial data
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: false, // Requires account linking
        pendingActions: 0,
        errors: enabled.value ? [] : ['Financial capability disabled for security']
      }
    }
  }
}

// ============================================================================
// CREATIVE CAPABILITY (Writing, Code, Media)
// ============================================================================

export function createCreativeCapability(): CapabilityModule {
  const enabled = ref(true)
  const permissionLevel = ref(PermissionLevel.AUTONOMOUS)

  return {
    id: 'creative',
    name: 'Creative',
    description: 'Writing, code generation, and creative assistance',
    icon: '✨',
    category: 'filesystem', // Uses filesystem to save outputs
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'generate_text',
        name: 'Generate Text',
        description: 'Generate text based on a prompt',
        riskLevel: RiskLevel.NONE,
        async execute({ prompt, style, length }: { prompt: string; style?: string; length?: 'short' | 'medium' | 'long' }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const text = await invoke('generate_text', { prompt, style, length })
            return { success: true, data: text, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.AUTONOMOUS,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'generate_code',
        name: 'Generate Code',
        description: 'Generate code based on requirements',
        riskLevel: RiskLevel.NONE,
        async execute({ requirements, language, context }: { requirements: string; language: string; context?: string }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const code = await invoke('generate_code', { requirements, language, context })
            return { success: true, data: code, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.AUTONOMOUS,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'review_code',
        name: 'Review Code',
        description: 'Review code for bugs and improvements',
        riskLevel: RiskLevel.NONE,
        async execute({ code, language, focusAreas }: { code: string; language: string; focusAreas?: string[] }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const review = await invoke('review_code', { code, language, focusAreas })
            return { success: true, data: review, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.AUTONOMOUS,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      },
      {
        id: 'explain_code',
        name: 'Explain Code',
        description: 'Explain what code does',
        riskLevel: RiskLevel.NONE,
        async execute({ code, language, detail = 'medium' }: { code: string; language: string; detail?: 'brief' | 'medium' | 'detailed' }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            const explanation = await invoke('explain_code', { code, language, detail })
            return { success: true, data: explanation, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: true,
            requiredPermission: PermissionLevel.AUTONOMOUS,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      }
    ],

    async initialize() {
      enabled.value = true
    },

    async cleanup() {
      // Nothing to clean up
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: true,
        pendingActions: 0,
        errors: []
      }
    }
  }
}

// ============================================================================
// INTIMATE CAPABILITY (Adult content - separate permissions)
// ============================================================================

export function createIntimateCapability(): CapabilityModule {
  const enabled = ref(false) // Disabled by default
  const permissionLevel = ref(PermissionLevel.ASK_ONCE)

  return {
    id: 'intimate',
    name: 'Intimate',
    description: 'Adult conversations and avatar interactions',
    icon: '💋',
    category: 'intimate',
    get enabled() { return enabled.value },
    set enabled(v) { enabled.value = v },
    get permissionLevel() { return permissionLevel.value },
    set permissionLevel(v) { permissionLevel.value = v },

    actions: [
      {
        id: 'set_mode',
        name: 'Set Intimate Mode',
        description: 'Enable or disable intimate interaction mode',
        riskLevel: RiskLevel.NONE,
        async execute({ active }: { active: boolean }) {
          // This only affects the current session, nothing external
          return { success: true, data: { active }, undoAvailable: false }
        },
        validate() {
          return {
            allowed: enabled.value,
            requiredPermission: PermissionLevel.ASK_ONCE,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: !enabled.value,
            confirmationMessage: 'Enable intimate mode?'
          }
        }
      },
      {
        id: 'avatar_interaction',
        name: 'Avatar Interaction',
        description: 'Control avatar for intimate interactions',
        riskLevel: RiskLevel.NONE,
        async execute({ action, intensity }: { action: string; intensity: number }) {
          try {
            const { invoke } = await import('@tauri-apps/api/tauri')
            await invoke('avatar_intimate_action', { action, intensity })
            return { success: true, undoAvailable: false }
          } catch (error) {
            return { success: false, error: String(error), undoAvailable: false }
          }
        },
        validate() {
          return {
            allowed: enabled.value,
            requiredPermission: permissionLevel.value,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      }
    ],

    async initialize() {
      // Check if adult mode is enabled in settings
      try {
        const settings = localStorage.getItem('sam_intimate_enabled')
        enabled.value = settings === 'true'
      } catch {
        enabled.value = false
      }
    },

    async cleanup() {
      // Nothing to clean up
    },

    getStatus() {
      return {
        enabled: enabled.value,
        connected: true,
        pendingActions: 0,
        errors: []
      }
    }
  }
}

// ============================================================================
// CAPABILITY REGISTRY
// ============================================================================

export function createCapabilityRegistry() {
  const capabilities = reactive<Map<string, CapabilityModule>>(new Map())

  // Register all default capabilities
  const filesystem = createFilesystemCapability()
  const process = createProcessCapability()
  const communication = createCommunicationCapability()
  const knowledge = createKnowledgeCapability()
  const home = createHomeCapability()
  const financial = createFinancialCapability()
  const creative = createCreativeCapability()
  const intimate = createIntimateCapability()

  capabilities.set(filesystem.id, filesystem)
  capabilities.set(process.id, process)
  capabilities.set(communication.id, communication)
  capabilities.set(knowledge.id, knowledge)
  capabilities.set(home.id, home)
  capabilities.set(financial.id, financial)
  capabilities.set(creative.id, creative)
  capabilities.set(intimate.id, intimate)

  return {
    capabilities,

    get(id: string): CapabilityModule | undefined {
      return capabilities.get(id)
    },

    getAll(): CapabilityModule[] {
      return Array.from(capabilities.values())
    },

    getEnabled(): CapabilityModule[] {
      return this.getAll().filter(c => c.enabled)
    },

    async initializeAll() {
      for (const capability of capabilities.values()) {
        await capability.initialize()
      }
    },

    async cleanupAll() {
      for (const capability of capabilities.values()) {
        await capability.cleanup()
      }
    },

    // Execute an action with full safety checks
    async executeAction(
      capabilityId: string,
      actionId: string,
      params: Record<string, unknown>
    ): Promise<{ validation: ValidationResult; result?: ActionResult }> {
      const capability = capabilities.get(capabilityId)
      if (!capability) {
        return {
          validation: {
            allowed: false,
            reason: `Unknown capability: ${capabilityId}`,
            requiredPermission: PermissionLevel.FORBIDDEN,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      }

      if (!capability.enabled) {
        return {
          validation: {
            allowed: false,
            reason: `Capability ${capability.name} is disabled`,
            requiredPermission: PermissionLevel.FORBIDDEN,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      }

      const action = capability.actions.find(a => a.id === actionId)
      if (!action) {
        return {
          validation: {
            allowed: false,
            reason: `Unknown action: ${actionId}`,
            requiredPermission: PermissionLevel.FORBIDDEN,
            riskLevel: RiskLevel.NONE,
            warnings: [],
            requiresConfirmation: false
          }
        }
      }

      // Validate
      const validation = action.validate(params)

      if (!validation.allowed) {
        return { validation }
      }

      // If confirmation required and not provided, return
      if (validation.requiresConfirmation) {
        return { validation }
      }

      // Execute
      const result = await action.execute(params)
      return { validation, result }
    }
  }
}

export type CapabilityRegistry = ReturnType<typeof createCapabilityRegistry>
