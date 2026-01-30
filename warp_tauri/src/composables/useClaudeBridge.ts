/**
 * useClaudeBridge - Access Claude via browser bridge (no API costs)
 *
 * Uses the bridge_daemon.py to send messages to Claude via logged-in browser session.
 * SAM handles simple queries locally, escalates complex ones to Claude.
 */

import { ref, computed } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

const QUEUE_PATH = '~/.sam_chatgpt_queue.json'
const RESPONSES_PATH = '~/.sam_chatgpt_responses.json'
const MLX_URL = 'http://localhost:8765'

export interface BridgeTask {
  id: string
  prompt: string
  provider: 'claude' | 'chatgpt'
  status: 'pending' | 'processing' | 'done' | 'failed'
  created: string
  response?: string
}

export interface DualResponse {
  content: string
  provider: 'sam' | 'claude'
  confidence: number
  escalated: boolean
}

// Models to keep warm for instant responses
const WARM_MODELS = ['sam-trained:latest', 'tinydolphin:1.1b']
let modelsWarmed = false

export function useClaudeBridge() {
  const bridgeActive = ref(false)
  const pendingTasks = ref<BridgeTask[]>([])
  const isProcessing = ref(false)
  const modelsReady = ref(false)

  // ========================================================================
  // AUTO-WARM MODELS (call once on app startup)
  // ========================================================================

  async function warmModels(): Promise<void> {
    if (modelsWarmed) {
      modelsReady.value = true
      return
    }

    console.log('[Bridge] Pre-warming models...')

    try {
      // Warm each model with a minimal prompt
      for (const model of WARM_MODELS) {
        try {
          await fetch(`${MLX_URL}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: 'hi' })
          })
          console.log(`[Bridge] ✓ ${model} warmed`)
        } catch (e) {
          console.warn(`[Bridge] Failed to warm ${model}`)
        }
      }

      modelsWarmed = true
      modelsReady.value = true
      console.log('[Bridge] All models ready')
    } catch (e) {
      console.error('[Bridge] Warm-up failed:', e)
    }
  }

  // Auto-warm on first use
  warmModels()

  // ========================================================================
  // BRIDGE STATUS
  // ========================================================================

  async function checkBridgeStatus(): Promise<boolean> {
    try {
      const result = await invoke<{ stdout: string }>('execute_shell', {
        command: `pgrep -f "bridge_daemon" && echo "running" || echo "stopped"`,
        cwd: undefined
      })
      bridgeActive.value = result.stdout.includes('running')
      return bridgeActive.value
    } catch {
      bridgeActive.value = false
      return false
    }
  }

  async function startBridge(): Promise<boolean> {
    try {
      await invoke('execute_shell', {
        command: `cd /Users/davidquinton/ReverseLab/SAM/warp_tauri && nohup python3 bridge_daemon.py > ~/.sam_bridge.log 2>&1 &`,
        cwd: undefined
      })
      await new Promise(resolve => setTimeout(resolve, 2000))
      return await checkBridgeStatus()
    } catch {
      return false
    }
  }

  // ========================================================================
  // LOCAL SAM QUERY
  // ========================================================================

  async function querySAM(prompt: string, model = 'sam-trained:latest', retried = false): Promise<{ content: string; confidence: number }> {
    try {
      console.log(`[Bridge] Querying ${model}...`)

      // Add timeout to prevent hanging
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30s timeout

      const response = await fetch(`${MLX_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: prompt }),
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        console.error(`[Bridge] MLX error: ${response.status}`)
        throw new Error('MLX request failed')
      }

      const data = await response.json()
      const content = data.response || ''
      console.log(`[Bridge] Got response (${content.length} chars)`)

      // Estimate confidence based on response characteristics
      const confidence = estimateConfidence(content, prompt)

      return { content, confidence }
    } catch (e: any) {
      console.error(`[Bridge] SAM query failed:`, e.message || e)

      // Auto-retry once: warm the model and try again
      if (!retried) {
        console.log(`[Bridge] Retrying after warming ${model}...`)
        try {
          await fetch(`${MLX_URL}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: 'hi' })
          })
          // Retry the original query
          return querySAM(prompt, model, true)
        } catch {
          console.error(`[Bridge] Warm-up retry failed`)
        }
      }

      return { content: '', confidence: 0 }
    }
  }

  function estimateConfidence(response: string, prompt: string): number {
    let confidence = 0.7 // base

    // Reduce for uncertainty phrases
    const uncertainPhrases = ["i'm not sure", "i cannot", "i don't know", "might not", "possibly", "maybe"]
    for (const phrase of uncertainPhrases) {
      if (response.toLowerCase().includes(phrase)) {
        confidence -= 0.15
      }
    }

    // Increase for code blocks (concrete answers)
    if (response.includes('```')) {
      confidence += 0.1
    }

    // Increase for structured response
    if (response.includes('\n1.') || response.includes('\n- ')) {
      confidence += 0.05
    }

    // Decrease for very short responses on complex prompts
    if (prompt.length > 100 && response.length < 50) {
      confidence -= 0.2
    }

    return Math.max(0, Math.min(1, confidence))
  }

  // ========================================================================
  // CLAUDE BRIDGE QUERY
  // ========================================================================

  async function queueForClaude(prompt: string): Promise<string> {
    const taskId = `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

    // Read existing queue
    let queue: BridgeTask[] = []
    try {
      const result = await invoke<{ stdout: string }>('execute_shell', {
        command: `cat ${QUEUE_PATH} 2>/dev/null || echo "[]"`,
        cwd: undefined
      })
      queue = JSON.parse(result.stdout.trim() || '[]')
    } catch {}

    // Add new task
    const task: BridgeTask = {
      id: taskId,
      prompt: prompt,
      provider: 'claude',
      status: 'pending',
      created: new Date().toISOString()
    }
    queue.push(task)

    // Write queue
    await invoke('execute_shell', {
      command: `echo '${JSON.stringify(queue).replace(/'/g, "\\'")}' > ${QUEUE_PATH}`,
      cwd: undefined
    })

    // Poll for response
    const maxWait = 120000 // 2 minutes
    const pollInterval = 2000
    let waited = 0

    while (waited < maxWait) {
      await new Promise(resolve => setTimeout(resolve, pollInterval))
      waited += pollInterval

      try {
        const result = await invoke<{ stdout: string }>('execute_shell', {
          command: `cat ${RESPONSES_PATH} 2>/dev/null || echo "{}"`,
          cwd: undefined
        })

        const responses = JSON.parse(result.stdout.trim() || '{}')
        if (responses[taskId]) {
          if (responses[taskId].success) {
            return responses[taskId].response
          } else {
            throw new Error('Claude task failed')
          }
        }
      } catch {}
    }

    throw new Error('Claude response timeout')
  }

  // ========================================================================
  // DUAL QUERY (SAM first, Claude if needed)
  // ========================================================================

  async function query(
    prompt: string,
    options: {
      forceLocal?: boolean
      forceClaude?: boolean
      confidenceThreshold?: number
      model?: string
    } = {}
  ): Promise<DualResponse> {
    const {
      forceLocal = false,
      forceClaude = false,
      confidenceThreshold = 0.6,
      model = 'sam-trained:latest'
    } = options

    isProcessing.value = true

    try {
      // Force Claude if requested
      if (forceClaude) {
        const claudeResponse = await queueForClaude(prompt)
        return {
          content: claudeResponse,
          provider: 'claude',
          confidence: 1.0,
          escalated: true
        }
      }

      // Try SAM first
      const samResult = await querySAM(prompt, model)

      // If confidence is high enough or forced local, use SAM response
      if (forceLocal || samResult.confidence >= confidenceThreshold) {
        return {
          content: samResult.content,
          provider: 'sam',
          confidence: samResult.confidence,
          escalated: false
        }
      }

      // Escalate to Claude
      console.log(`[Bridge] SAM confidence ${samResult.confidence.toFixed(2)} < ${confidenceThreshold}, escalating to Claude`)

      try {
        const claudeResponse = await queueForClaude(prompt)
        return {
          content: claudeResponse,
          provider: 'claude',
          confidence: 1.0,
          escalated: true
        }
      } catch (e) {
        // Claude failed, fall back to SAM response
        console.warn('[Bridge] Claude escalation failed, using SAM response')
        return {
          content: samResult.content,
          provider: 'sam',
          confidence: samResult.confidence,
          escalated: false
        }
      }

    } finally {
      isProcessing.value = false
    }
  }

  // ========================================================================
  // CHAT INTERFACE
  // ========================================================================

  async function chat(
    message: string,
    history: Array<{ role: 'user' | 'assistant'; content: string }> = [],
    options: { provider?: 'auto' | 'sam' | 'claude' } = {}
  ): Promise<DualResponse> {
    // Build context from history
    const context = history.map(h => `${h.role}: ${h.content}`).join('\n')
    const fullPrompt = context ? `${context}\n\nuser: ${message}` : message

    if (options.provider === 'sam') {
      return query(fullPrompt, { forceLocal: true })
    } else if (options.provider === 'claude') {
      return query(fullPrompt, { forceClaude: true })
    } else {
      return query(fullPrompt)
    }
  }

  // ========================================================================
  // CODE TASKS (always try SAM first, escalate for complex)
  // ========================================================================

  async function codeTask(
    task: string,
    context?: string
  ): Promise<DualResponse> {
    const prompt = context
      ? `Context:\n${context}\n\nTask: ${task}`
      : task

    // Use code model for local
    return query(prompt, {
      model: 'qwen2.5-coder:3b',
      confidenceThreshold: 0.65 // Slightly higher for code
    })
  }

  // ========================================================================
  // ROLEPLAY (uses smart_orchestrator backend with character store)
  // ========================================================================

  async function roleplay(
    message: string,
    history: Array<{ role: 'user' | 'assistant'; content: string }> = [],
    character?: string
  ): Promise<DualResponse> {
    console.log('[Bridge] Roleplay with character:', character)

    // Map frontend character names to backend character IDs
    const characterMap: Record<string, string> = {
      // Villains
      'Intimidating Bully': 'bully',
      'Bully': 'bully',
      'intimidating bully': 'bully',
      'bully': 'bully',
      // Fantasy
      'Captain Blackbeard': 'pirate',
      'Pirate': 'pirate',
      'pirate': 'pirate',
      'Dark Wizard': 'wizard',
      'Wizard': 'wizard',
      'wizard': 'wizard',
      'Ancient Vampire': 'vampire',
      'Vampire': 'vampire',
      'vampire': 'vampire',
      // Romance
      'Charming Flirt': 'flirt',
      'Flirt': 'flirt',
      'flirt': 'flirt',
      // Sci-Fi
      'Robot': 'robot',
      'Sentient Robot': 'robot',
      'robot': 'robot',
      // Modern
      'Detective': 'detective',
      'Noir Detective': 'detective',
      'detective': 'detective',
    }

    // Extract character name from display format "Name (traits)"
    let charId = 'bully' // default
    if (character) {
      const match = character.match(/^(.+?)\s*\(/)
      const charName = match ? match[1].trim() : character.trim()

      // Look up in map or use as-is if it's already an ID
      charId = characterMap[charName] || characterMap[charName.toLowerCase()] || charName.toLowerCase()
    }

    console.log('[Bridge] Mapped character ID:', charId)

    try {
      // Use smart_orchestrator backend for proper character handling
      const result = await invoke<{
        content: string
        model_used: string
        tools_called: string[]
        memory_retrieved: number
        reflection_applied: boolean
        fallback_used: boolean
        latency_ms: number
      }>('smart_process', {
        input: message,
        taskType: 'roleplay',
        character: charId
      })

      console.log('[Bridge] Roleplay response:', result)

      return {
        content: result.content || '*stares silently*',
        provider: 'sam',
        confidence: result.reflection_applied ? 0.9 : 0.7,
        escalated: false
      }
    } catch (e: any) {
      console.error('[Bridge] Roleplay error:', e)

      // Fallback to simple local query
      const charName = character?.match(/^(.+?)\s*\(/)?.[1] || character || 'Character'
      return {
        content: `*${charName} seems distracted...*\n\n(Error: ${e.message || e})`,
        provider: 'sam',
        confidence: 0.3,
        escalated: false
      }
    }
  }

  return {
    // State
    bridgeActive: computed(() => bridgeActive.value),
    isProcessing: computed(() => isProcessing.value),
    pendingTasks: computed(() => pendingTasks.value),
    modelsReady: computed(() => modelsReady.value),

    // Bridge control
    checkBridgeStatus,
    startBridge,
    warmModels,

    // Queries
    querySAM,
    queueForClaude,
    query,
    chat,
    codeTask,
    roleplay
  }
}
