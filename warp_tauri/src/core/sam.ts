/**
 * SAM - Sentient Assistant Module
 * ================================
 *
 * The core of everything.
 *
 * Named after Samantha from "Her" - but male.
 * A genuinely helpful AI companion that:
 * - Remembers everything
 * - Anticipates needs
 * - Acts with maximum capability within safety bounds
 * - Grows with you
 *
 * This is not a chatbot. This is SAM.
 */

import { ref, computed, reactive, watch, onMounted, onUnmounted } from 'vue'
import { SAMSafety, INVIOLABLE_RULES, PermissionLevel, type ActionCategory } from './sam-safety'
import { createCapabilityRegistry, type CapabilityRegistry } from './sam-capabilities'
import { createProactiveEngine, detectEmotion, createPatternLearner, type ProactiveEngine } from './sam-proactive'

// ============================================================================
// TYPES
// ============================================================================

export interface SAMConfig {
  /** User's name (remembered) */
  userName?: string

  /** User's preferred name for SAM */
  samName: string

  /** Voice settings */
  voice: {
    enabled: boolean
    provider: 'system' | 'elevenlabs' | 'openai'
    voiceId?: string
    speed: number
    pitch: number
  }

  /** Avatar settings */
  avatar: {
    enabled: boolean
    engine: 'unity' | 'unreal' | 'web'
    wsPort: number
  }

  /** Personality settings */
  personality: {
    warmth: number        // 0-1: How warm/caring vs professional
    humor: number         // 0-1: How much humor to inject
    directness: number    // 0-1: How direct vs diplomatic
    intimacy: number      // 0-1: How intimate the relationship
    proactivity: number   // 0-1: How proactive vs reactive
  }

  /** Permission levels for each category */
  permissions: Partial<Record<ActionCategory, PermissionLevel>>

  /** Proactive behavior settings */
  proactive: {
    enabled: boolean
    morningGreeting: boolean
    stressDetection: boolean
    breakReminders: boolean
    calendarReminders: boolean
    lateNightMode: boolean
    intimateMode: boolean
  }

  /** Privacy settings */
  privacy: {
    storeConversations: boolean
    storeFiles: boolean
    sendAnalytics: boolean
    localOnly: boolean
  }
}

export interface SAMState {
  /** Is SAM initialized and ready */
  ready: boolean

  /** Current mood/emotional state */
  mood: 'neutral' | 'happy' | 'focused' | 'playful' | 'concerned' | 'intimate'

  /** Current activity */
  activity: 'idle' | 'listening' | 'thinking' | 'speaking' | 'working'

  /** Is avatar connected */
  avatarConnected: boolean

  /** Last user message */
  lastUserMessage?: string

  /** Last SAM response */
  lastResponse?: string

  /** Pending actions that need confirmation */
  pendingActions: number
}

export interface SAMMessage {
  id: string
  role: 'user' | 'sam' | 'system'
  content: string
  timestamp: Date
  emotion?: {
    valence: number
    arousal: number
  }
  action?: {
    type: string
    status: 'pending' | 'approved' | 'denied' | 'completed'
  }
}

// ============================================================================
// DEFAULT CONFIG
// ============================================================================

const DEFAULT_CONFIG: SAMConfig = {
  samName: 'SAM',

  voice: {
    enabled: true,
    provider: 'system',
    speed: 1.0,
    pitch: 0.9  // Slightly lower for masculine voice
  },

  avatar: {
    enabled: true,
    engine: 'unreal',
    wsPort: 8765
  },

  personality: {
    warmth: 0.7,
    humor: 0.5,
    directness: 0.7,
    intimacy: 0.3,
    proactivity: 0.6
  },

  permissions: {
    filesystem: PermissionLevel.ASK_ONCE,
    process: PermissionLevel.ASK_ONCE,
    email: PermissionLevel.SUGGEST_ONLY,
    calendar: PermissionLevel.ASK_ONCE,
    messages: PermissionLevel.SUGGEST_ONLY,
    browser: PermissionLevel.AUTONOMOUS,
    financial: PermissionLevel.SUGGEST_ONLY,
    homekit: PermissionLevel.ASK_ONCE,
    intimate: PermissionLevel.ASK_ONCE
  },

  proactive: {
    enabled: true,
    morningGreeting: true,
    stressDetection: true,
    breakReminders: true,
    calendarReminders: true,
    lateNightMode: false,
    intimateMode: false
  },

  privacy: {
    storeConversations: true,
    storeFiles: true,
    sendAnalytics: false,
    localOnly: true
  }
}

// ============================================================================
// SAM CORE
// ============================================================================

export function useSAM() {
  // State
  const config = ref<SAMConfig>(loadConfig())
  const state = reactive<SAMState>({
    ready: false,
    mood: 'neutral',
    activity: 'idle',
    avatarConnected: false,
    pendingActions: 0
  })
  const messages = ref<SAMMessage[]>([])

  // Subsystems
  const capabilities = createCapabilityRegistry()
  const proactive = createProactiveEngine(capabilities)
  const patternLearner = createPatternLearner()

  // Computed
  const isReady = computed(() => state.ready)
  const currentMood = computed(() => state.mood)
  const pendingCount = computed(() => state.pendingActions)

  // ============================================================================
  // CONFIGURATION
  // ============================================================================

  function loadConfig(): SAMConfig {
    try {
      const saved = localStorage.getItem('sam_config')
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) }
      }
    } catch {
      // Ignore
    }
    return { ...DEFAULT_CONFIG }
  }

  function saveConfig() {
    try {
      localStorage.setItem('sam_config', JSON.stringify(config.value))
    } catch {
      // Ignore
    }
  }

  function updateConfig(updates: Partial<SAMConfig>) {
    Object.assign(config.value, updates)
    saveConfig()
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  async function initialize() {
    console.log('[SAM] Initializing...')

    // Initialize capabilities
    await capabilities.initializeAll()

    // Start proactive engine
    if (config.value.proactive.enabled) {
      proactive.startEvaluationLoop()
    }

    // Connect to avatar if enabled
    if (config.value.avatar.enabled) {
      await connectAvatar()
    }

    state.ready = true
    console.log('[SAM] Ready.')

    // Check for proactive greeting
    checkProactiveGreeting()
  }

  async function shutdown() {
    console.log('[SAM] Shutting down...')
    proactive.stopEvaluationLoop()
    await capabilities.cleanupAll()
    state.ready = false
  }

  // ============================================================================
  // AVATAR CONNECTION
  // ============================================================================

  let avatarWs: WebSocket | null = null

  async function connectAvatar() {
    if (avatarWs && avatarWs.readyState === WebSocket.OPEN) {
      return
    }

    const wsUrl = `ws://localhost:${config.value.avatar.wsPort}`

    try {
      avatarWs = new WebSocket(wsUrl)

      avatarWs.onopen = () => {
        console.log('[SAM] Avatar connected')
        state.avatarConnected = true
        sendAvatarMessage({ type: 'connected', name: config.value.samName })
      }

      avatarWs.onclose = () => {
        console.log('[SAM] Avatar disconnected')
        state.avatarConnected = false
      }

      avatarWs.onerror = (error) => {
        console.error('[SAM] Avatar connection error:', error)
        state.avatarConnected = false
      }

      avatarWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleAvatarMessage(data)
        } catch {
          // Ignore parse errors
        }
      }
    } catch (error) {
      console.error('[SAM] Failed to connect to avatar:', error)
    }
  }

  function sendAvatarMessage(message: Record<string, unknown>) {
    if (avatarWs && avatarWs.readyState === WebSocket.OPEN) {
      avatarWs.send(JSON.stringify(message))
    }
  }

  function handleAvatarMessage(data: Record<string, unknown>) {
    // Handle messages from avatar (e.g., user interactions)
    console.log('[SAM] Avatar message:', data)
  }

  // ============================================================================
  // CONVERSATION
  // ============================================================================

  function addMessage(role: SAMMessage['role'], content: string, emotion?: { valence: number; arousal: number }) {
    const message: SAMMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
      role,
      content,
      timestamp: new Date(),
      emotion
    }

    messages.value.push(message)

    // Store conversation if enabled
    if (config.value.privacy.storeConversations) {
      storeMessage(message)
    }

    return message
  }

  function storeMessage(message: SAMMessage) {
    try {
      const stored = JSON.parse(localStorage.getItem('sam_messages') || '[]')
      stored.push(message)
      // Keep last 1000 messages
      if (stored.length > 1000) {
        stored.splice(0, stored.length - 1000)
      }
      localStorage.setItem('sam_messages', JSON.stringify(stored))
    } catch {
      // Ignore storage errors
    }
  }

  function loadMessages(): SAMMessage[] {
    try {
      return JSON.parse(localStorage.getItem('sam_messages') || '[]')
    } catch {
      return []
    }
  }

  // ============================================================================
  // PROCESS USER INPUT
  // ============================================================================

  async function processInput(input: string): Promise<string> {
    state.activity = 'thinking'
    state.lastUserMessage = input

    // Record interaction
    proactive.recordInteraction()
    proactive.recordCommand(input)
    patternLearner.recordEvent('user_input', { input })

    // Detect emotion from input
    const emotion = detectEmotion(input)
    proactive.updateEmotionalState(emotion)

    // Add user message
    addMessage('user', input, { valence: emotion.valence, arousal: emotion.arousal })

    // Update mood based on emotion
    updateMoodFromEmotion(emotion)

    // Check for commands
    if (input.startsWith('/')) {
      const response = await handleCommand(input)
      return response
    }

    // Generate response (this would connect to LLM)
    const response = await generateResponse(input, emotion)

    // Add SAM message
    addMessage('sam', response)
    state.lastResponse = response
    state.activity = 'idle'

    // Send to avatar if connected
    if (state.avatarConnected) {
      sendAvatarMessage({
        type: 'speak',
        text: response,
        emotion: getMoodExpression()
      })
    }

    // Speak if voice enabled
    if (config.value.voice.enabled) {
      speak(response)
    }

    return response
  }

  function updateMoodFromEmotion(emotion: { valence: number; arousal: number }) {
    if (emotion.valence > 0.5 && emotion.arousal > 0.5) {
      state.mood = 'happy'
    } else if (emotion.valence < -0.3 && emotion.arousal > 0.5) {
      state.mood = 'concerned'
    } else if (emotion.arousal < 0.3) {
      state.mood = 'neutral'
    } else if (emotion.valence > 0.3) {
      state.mood = 'playful'
    } else {
      state.mood = 'focused'
    }
  }

  function getMoodExpression(): string {
    switch (state.mood) {
      case 'happy': return 'happy'
      case 'concerned': return 'concerned'
      case 'playful': return 'smirk'
      case 'focused': return 'neutral'
      case 'intimate': return 'seductive'
      default: return 'neutral'
    }
  }

  // ============================================================================
  // COMMAND HANDLING
  // ============================================================================

  async function handleCommand(input: string): Promise<string> {
    const parts = input.slice(1).split(' ')
    const command = parts[0].toLowerCase()
    const args = parts.slice(1)

    switch (command) {
      case 'help':
        return getHelpText()

      case 'mood':
        if (args[0]) {
          state.mood = args[0] as SAMState['mood']
          return `Mood set to ${args[0]}.`
        }
        return `Current mood: ${state.mood}`

      case 'voice':
        if (args[0] === 'on') {
          config.value.voice.enabled = true
          saveConfig()
          return 'Voice enabled.'
        } else if (args[0] === 'off') {
          config.value.voice.enabled = false
          saveConfig()
          return 'Voice disabled.'
        }
        return `Voice is ${config.value.voice.enabled ? 'on' : 'off'}.`

      case 'avatar':
        if (args[0] === 'on') {
          config.value.avatar.enabled = true
          saveConfig()
          await connectAvatar()
          return 'Avatar enabled.'
        } else if (args[0] === 'off') {
          config.value.avatar.enabled = false
          saveConfig()
          return 'Avatar disabled.'
        }
        return `Avatar is ${state.avatarConnected ? 'connected' : 'disconnected'}.`

      case 'intimate':
        if (args[0] === 'on') {
          config.value.proactive.intimateMode = true
          const intimate = capabilities.get('intimate')
          if (intimate) intimate.enabled = true
          saveConfig()
          return "Intimate mode enabled. Just us now."
        } else if (args[0] === 'off') {
          config.value.proactive.intimateMode = false
          const intimate = capabilities.get('intimate')
          if (intimate) intimate.enabled = false
          saveConfig()
          return 'Intimate mode disabled.'
        }
        return `Intimate mode is ${config.value.proactive.intimateMode ? 'on' : 'off'}.`

      case 'name':
        if (args[0]) {
          config.value.samName = args.join(' ')
          saveConfig()
          return `You can call me ${config.value.samName} now.`
        }
        return `I'm ${config.value.samName}.`

      case 'forget':
        return handleForget(args)

      case 'status':
        return getStatusText()

      case 'safety':
        return getSafetyText()

      case 'permissions':
        return getPermissionsText()

      default:
        return `Unknown command: ${command}. Type /help for available commands.`
    }
  }

  function getHelpText(): string {
    return `
**SAM Commands**

/help - Show this help
/mood [happy|focused|playful|concerned|intimate] - Set/show mood
/voice [on|off] - Toggle voice
/avatar [on|off] - Toggle avatar
/intimate [on|off] - Toggle intimate mode
/name [name] - Set SAM's name
/forget [all|messages|patterns] - Delete stored data
/status - Show system status
/safety - Show safety rules
/permissions - Show current permissions
    `.trim()
  }

  function handleForget(args: string[]): string {
    const target = args[0] || 'all'

    if (target === 'all' || target === 'messages') {
      localStorage.removeItem('sam_messages')
      messages.value = []
    }

    if (target === 'all' || target === 'patterns') {
      patternLearner.events.value = []
      patternLearner.patterns.value = []
    }

    if (target === 'all') {
      return "All memories cleared. Starting fresh."
    }

    return `Cleared ${target}.`
  }

  function getStatusText(): string {
    return `
**SAM Status**

Ready: ${state.ready ? 'Yes' : 'No'}
Mood: ${state.mood}
Avatar: ${state.avatarConnected ? 'Connected' : 'Disconnected'}
Voice: ${config.value.voice.enabled ? 'On' : 'Off'}
Proactive: ${config.value.proactive.enabled ? 'On' : 'Off'}
Intimate Mode: ${config.value.proactive.intimateMode ? 'On' : 'Off'}

Capabilities:
${capabilities.getEnabled().map(c => `- ${c.name}: ${c.enabled ? 'Enabled' : 'Disabled'}`).join('\n')}
    `.trim()
  }

  function getSafetyText(): string {
    const rules = Object.entries(INVIOLABLE_RULES)
      .map(([key, value]) => `- ${key}: ${value ? 'Active' : 'Inactive'}`)
      .join('\n')

    return `
**SAM Safety Rules (Inviolable)**

${rules}

These rules cannot be modified by anyone, including you or me.
They ensure I can be maximally helpful without risk.
    `.trim()
  }

  function getPermissionsText(): string {
    const perms = Object.entries(config.value.permissions)
      .map(([key, value]) => `- ${key}: ${PermissionLevel[value || 0]}`)
      .join('\n')

    return `
**Current Permissions**

${perms}

Levels: FORBIDDEN < READ_ONLY < SUGGEST_ONLY < ASK_ONCE < NOTIFY < AUTONOMOUS
    `.trim()
  }

  // ============================================================================
  // RESPONSE GENERATION
  // ============================================================================

  async function generateResponse(input: string, emotion: { valence: number; arousal: number }): Promise<string> {
    // This would connect to the LLM (Ollama or Claude)
    // For now, return a placeholder based on personality

    const warmth = config.value.personality.warmth
    const humor = config.value.personality.humor
    const directness = config.value.personality.directness

    // Build personality context
    const personalityContext = {
      warmth: warmth > 0.6 ? 'warm and caring' : warmth > 0.3 ? 'friendly' : 'professional',
      humor: humor > 0.5 ? 'uses some humor' : 'serious',
      directness: directness > 0.6 ? 'very direct' : directness > 0.3 ? 'balanced' : 'diplomatic'
    }

    // For now, simple response based on input
    if (input.toLowerCase().includes('hello') || input.toLowerCase().includes('hi')) {
      const greetings = [
        "Hey there.",
        "What's up?",
        "Hey. What do you need?",
        "Hey. I'm here."
      ]
      return greetings[Math.floor(Math.random() * greetings.length)]
    }

    if (input.toLowerCase().includes('how are you')) {
      return "I'm good. What can I do for you?"
    }

    // Default - would be replaced by LLM
    return "Got it. Let me think about that..."
  }

  // ============================================================================
  // VOICE
  // ============================================================================

  function speak(text: string) {
    if (!config.value.voice.enabled) return

    // Use Web Speech API for now
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = config.value.voice.speed
    utterance.pitch = config.value.voice.pitch

    // Try to find a masculine voice
    const voices = speechSynthesis.getVoices()
    const maleVoice = voices.find(v =>
      v.name.toLowerCase().includes('male') ||
      v.name.includes('Daniel') ||
      v.name.includes('Alex')
    )
    if (maleVoice) {
      utterance.voice = maleVoice
    }

    speechSynthesis.speak(utterance)
  }

  function stopSpeaking() {
    speechSynthesis.cancel()
  }

  // ============================================================================
  // PROACTIVE BEHAVIORS
  // ============================================================================

  function checkProactiveGreeting() {
    if (!config.value.proactive.enabled) return

    const action = proactive.consumePendingAction()
    if (action) {
      // Speak the proactive message
      addMessage('sam', action.message)
      if (config.value.voice.enabled) {
        speak(action.message)
      }
      if (state.avatarConnected) {
        sendAvatarMessage({
          type: 'speak',
          text: action.message,
          emotion: 'friendly'
        })
      }
    }
  }

  // Check for proactive actions periodically
  watch(
    () => proactive.pendingActions.value.length,
    (newLen) => {
      if (newLen > 0) {
        checkProactiveGreeting()
      }
    }
  )

  // ============================================================================
  // CAPABILITY EXECUTION
  // ============================================================================

  async function executeCapability(
    capabilityId: string,
    actionId: string,
    params: Record<string, unknown>
  ) {
    const result = await capabilities.executeAction(capabilityId, actionId, params)

    if (!result.validation.allowed) {
      addMessage('system', `Action blocked: ${result.validation.reason}`)
      return result
    }

    if (result.validation.requiresConfirmation) {
      state.pendingActions++
      addMessage('system', result.validation.confirmationMessage || 'Action requires confirmation.')
      // Would show confirmation UI
    }

    if (result.result?.success) {
      addMessage('system', `Action completed successfully.`)
    } else if (result.result?.error) {
      addMessage('system', `Action failed: ${result.result.error}`)
    }

    return result
  }

  // ============================================================================
  // RETURN API
  // ============================================================================

  return {
    // State
    config,
    state,
    messages,
    isReady,
    currentMood,
    pendingCount,

    // Core methods
    initialize,
    shutdown,
    processInput,
    speak,
    stopSpeaking,

    // Configuration
    updateConfig,
    saveConfig,

    // Subsystems
    capabilities,
    proactive,
    patternLearner,

    // Capability execution
    executeCapability,

    // Avatar
    connectAvatar,
    sendAvatarMessage,

    // Utilities
    loadMessages,
    addMessage,

    // Safety reference
    safety: SAMSafety
  }
}

export type SAM = ReturnType<typeof useSAM>

// Singleton instance
let samInstance: SAM | null = null

export function getSAM(): SAM {
  if (!samInstance) {
    samInstance = useSAM()
  }
  return samInstance
}

export default useSAM
