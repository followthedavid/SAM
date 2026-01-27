/**
 * Dual Terminal System - Claude Code + SAM Bridge
 *
 * Manages two terminals side by side:
 * - Terminal 1: Claude Code CLI (handles complex tasks)
 * - Terminal 2: SAM Local (handles routine tasks, personality)
 *
 * The bridge enables:
 * - Context sharing between terminals
 * - Task routing (SAM can escalate to Claude)
 * - Learning capture (Claude responses logged for SAM training)
 */

import { ref, reactive, computed, watch } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

// Types
interface TerminalState {
  id: number | null
  type: 'claude' | 'sam'
  ready: boolean
  lastOutput: string
  currentTask: string | null
}

interface BridgeMessage {
  from: 'claude' | 'sam'
  to: 'claude' | 'sam'
  type: 'context' | 'escalate' | 'response' | 'learn' | 'delegate'
  content: string
  timestamp: number
}

interface SharedContext {
  currentFile: string | null
  currentDirectory: string
  recentCommands: string[]
  activeTask: string | null
  conversationHistory: Array<{ role: string; content: string }>
}

// Singleton state
const claudeTerminal = reactive<TerminalState>({
  id: null,
  type: 'claude',
  ready: false,
  lastOutput: '',
  currentTask: null
})

const samTerminal = reactive<TerminalState>({
  id: null,
  type: 'sam',
  ready: false,
  lastOutput: '',
  currentTask: null
})

const sharedContext = reactive<SharedContext>({
  currentFile: null,
  currentDirectory: process.cwd?.() || '~',
  recentCommands: [],
  activeTask: null,
  conversationHistory: []
})

const bridgeMessages = ref<BridgeMessage[]>([])
const bridgeEnabled = ref(true)

// Escalation patterns - when SAM should ask Claude for help
const ESCALATION_PATTERNS = [
  /i('m| am) not sure/i,
  /i don('t|'t) know/i,
  /beyond my (capabilities|knowledge)/i,
  /complex|complicated|difficult/i,
  /need more context/i,
  /error|failed|exception/i,
]

// Delegation patterns - when Claude could let SAM handle it
const DELEGATION_PATTERNS = [
  /simple (question|task|request)/i,
  /basic (question|task|request)/i,
  /sam (can|could|should) handle/i,
  /this is (easy|straightforward|routine)/i,
  /let me (pass|send|delegate) this to sam/i,
  /sam('s| is) got this/i,
]

/**
 * Spawn the Claude Code terminal
 */
async function spawnClaudeTerminal(): Promise<number> {
  try {
    // Spawn PTY with 'claude' as the shell command
    const result = await invoke<{ id: number }>('spawn_pty', {
      shell: 'claude'
    })

    claudeTerminal.id = result.id
    claudeTerminal.ready = true

    console.log('[DualTerminal] Claude Code terminal spawned:', result.id)
    return result.id
  } catch (error) {
    console.error('[DualTerminal] Failed to spawn Claude terminal:', error)
    throw error
  }
}

/**
 * Spawn the SAM local terminal (REPL mode)
 */
async function spawnSamTerminal(): Promise<number> {
  try {
    // Spawn PTY with SAM REPL
    const samBrainPath = '/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain'
    const result = await invoke<{ id: number }>('spawn_pty', {
      shell: `/bin/zsh -c "cd ${samBrainPath} && source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null; python sam_repl.py"`
    })

    samTerminal.id = result.id
    samTerminal.ready = true

    console.log('[DualTerminal] SAM REPL spawned:', result.id)
    return result.id
  } catch (error) {
    console.error('[DualTerminal] Failed to spawn SAM terminal:', error)
    throw error
  }
}

/**
 * Send input to a specific terminal
 */
async function sendToTerminal(
  terminal: 'claude' | 'sam',
  input: string
): Promise<void> {
  const terminalState = terminal === 'claude' ? claudeTerminal : samTerminal

  if (!terminalState.id || !terminalState.ready) {
    throw new Error(`${terminal} terminal not ready`)
  }

  await invoke('send_input', {
    id: terminalState.id,
    input: input + '\n'
  })

  // Track command
  sharedContext.recentCommands.push(input)
  if (sharedContext.recentCommands.length > 50) {
    sharedContext.recentCommands.shift()
  }
}

/**
 * Read output from a terminal
 */
async function readFromTerminal(terminal: 'claude' | 'sam'): Promise<string> {
  const terminalState = terminal === 'claude' ? claudeTerminal : samTerminal

  if (!terminalState.id) {
    return ''
  }

  const output = await invoke<string>('read_pty', {
    id: terminalState.id
  })

  terminalState.lastOutput = output
  return output
}

/**
 * Check if SAM's response should be escalated to Claude
 */
function shouldEscalate(samResponse: string): boolean {
  if (!bridgeEnabled.value) return false

  for (const pattern of ESCALATION_PATTERNS) {
    if (pattern.test(samResponse)) {
      return true
    }
  }

  // Check response length (very short = uncertain)
  if (samResponse.trim().length < 20) {
    return true
  }

  return false
}

/**
 * Check if Claude's response suggests delegation to SAM
 */
function shouldDelegate(claudeResponse: string): boolean {
  if (!bridgeEnabled.value) return false

  for (const pattern of DELEGATION_PATTERNS) {
    if (pattern.test(claudeResponse)) {
      return true
    }
  }

  return false
}

/**
 * Escalate a task from SAM to Claude
 */
async function escalateToClaudeCode(
  task: string,
  context?: string
): Promise<void> {
  if (!claudeTerminal.ready) {
    console.warn('[DualTerminal] Cannot escalate - Claude terminal not ready')
    return
  }

  // Build the prompt with context
  let prompt = task
  if (context) {
    prompt = `Context: ${context}\n\nTask: ${task}`
  }

  // Add shared context
  if (sharedContext.currentFile) {
    prompt = `Working on file: ${sharedContext.currentFile}\n${prompt}`
  }

  // Log the escalation
  bridgeMessages.value.push({
    from: 'sam',
    to: 'claude',
    type: 'escalate',
    content: task,
    timestamp: Date.now()
  })

  // Send to Claude
  await sendToTerminal('claude', prompt)

  console.log('[DualTerminal] Escalated to Claude:', task.substring(0, 50))
}

/**
 * Share context between terminals
 */
function shareContext(context: Partial<SharedContext>): void {
  Object.assign(sharedContext, context)

  bridgeMessages.value.push({
    from: 'sam',
    to: 'claude',
    type: 'context',
    content: JSON.stringify(context),
    timestamp: Date.now()
  })
}

/**
 * Log Claude's response for SAM training
 */
function logForTraining(prompt: string, response: string): void {
  bridgeMessages.value.push({
    from: 'claude',
    to: 'sam',
    type: 'learn',
    content: JSON.stringify({ prompt, response }),
    timestamp: Date.now()
  })

  // Also save to file for training pipeline
  invoke('write_file', {
    path: `${process.env.HOME}/.sam/escalation_training.jsonl`,
    content: JSON.stringify({
      prompt,
      response,
      timestamp: Date.now()
    }) + '\n',
    append: true
  }).catch(console.error)
}

/**
 * Initialize the dual terminal system
 */
async function initDualTerminal(): Promise<{
  claudeId: number
  samId: number
}> {
  console.log('[DualTerminal] Initializing dual terminal system...')

  const [claudeId, samId] = await Promise.all([
    spawnClaudeTerminal(),
    spawnSamTerminal()
  ])

  console.log('[DualTerminal] Both terminals ready:', { claudeId, samId })

  return { claudeId, samId }
}

/**
 * Close both terminals
 */
async function closeDualTerminal(): Promise<void> {
  const promises = []

  if (claudeTerminal.id) {
    promises.push(invoke('close_pty', { id: claudeTerminal.id }))
    claudeTerminal.id = null
    claudeTerminal.ready = false
  }

  if (samTerminal.id) {
    promises.push(invoke('close_pty', { id: samTerminal.id }))
    samTerminal.id = null
    samTerminal.ready = false
  }

  await Promise.all(promises)
  console.log('[DualTerminal] Both terminals closed')
}

// Computed properties
const isReady = computed(() => claudeTerminal.ready && samTerminal.ready)
const claudeReady = computed(() => claudeTerminal.ready)
const samReady = computed(() => samTerminal.ready)

/**
 * Main composable export
 */
export function useDualTerminal() {
  return {
    // State
    claudeTerminal,
    samTerminal,
    sharedContext,
    bridgeMessages,
    bridgeEnabled,

    // Computed
    isReady,
    claudeReady,
    samReady,

    // Actions
    initDualTerminal,
    closeDualTerminal,
    spawnClaudeTerminal,
    spawnSamTerminal,
    sendToTerminal,
    readFromTerminal,
    escalateToClaudeCode,
    shareContext,
    logForTraining,
    shouldEscalate,
    shouldDelegate,
  }
}

export type { TerminalState, BridgeMessage, SharedContext }
