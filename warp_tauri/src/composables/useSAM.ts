/**
 * useSAM - The Complete AI Companion
 *
 * This is SAM - your personal AI assistant with full "Her" (Samantha) parity.
 * A masculine, cocky, sultry AI that:
 * - Is always available (24/7 daemon)
 * - Speaks with a deep, confident voice
 * - Proactively reaches out when needed
 * - Responds to "Hey SAM"
 * - Manages your calendar
 * - Remembers your relationships
 * - Learns and adapts to you
 * - Has a visual avatar in game engines
 *
 * "Hey SAM..."
 * "Yeah? What do you need?"
 */

import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { usePersonality } from './usePersonality'
import { useTTS } from './useTTS'
import { useProactiveNotifications } from './useProactiveNotifications'
import { useWakeWord } from './useWakeWord'
import { useCalendar } from './useCalendar'
import { useRelationships } from './useRelationships'
import { useLearning } from './useLearning'
import { useAvatarBridge } from './useAvatarBridge'
import { useDaemonOrchestrator } from './useDaemonOrchestrator'
import { useAuditLog } from './useAuditLog'
// New enhanced systems
import { useSAMMemory } from './useSAMMemory'
import { useSAMPersonality } from './useSAMPersonality'
import { useSAMVoice } from './useSAMVoice'
import { useCharacterCustomization } from './useCharacterCustomization'
// Cognitive API connection
import { useCognitiveAPI, type CognitiveResponse } from './useCognitiveAPI'

// ============================================================================
// TYPES
// ============================================================================

export interface SAMConfig {
  enabled: boolean
  voiceEnabled: boolean
  wakeWordEnabled: boolean
  avatarEnabled: boolean
  proactiveEnabled: boolean
  learningEnabled: boolean
  autoStart: boolean
}

export interface SAMStatus {
  isOnline: boolean
  isListening: boolean
  isSpeaking: boolean
  isThinking: boolean
  lastInteraction: Date | null
  mood: 'neutral' | 'playful' | 'focused' | 'flirty'
  energyLevel: 'low' | 'medium' | 'high'
}

// ============================================================================
// STORAGE
// ============================================================================

const CONFIG_KEY = 'warp_atlas_config'

function loadConfig(): SAMConfig {
  try {
    const stored = localStorage.getItem(CONFIG_KEY)
    if (stored) return JSON.parse(stored)
  } catch {}
  return {
    enabled: true,
    voiceEnabled: true,
    wakeWordEnabled: true,
    avatarEnabled: true,
    proactiveEnabled: true,
    learningEnabled: true,
    autoStart: true
  }
}

function saveConfig(config: SAMConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useSAM() {
  // Core subsystems
  const personality = usePersonality()
  const tts = useTTS()
  const notifications = useProactiveNotifications()
  const wakeWord = useWakeWord()
  const calendar = useCalendar()
  const relationships = useRelationships()
  const learning = useLearning()
  const avatar = useAvatarBridge()
  const daemon = useDaemonOrchestrator()
  const auditLog = useAuditLog()

  // Enhanced subsystems (new)
  const memory = useSAMMemory()
  const enhancedPersonality = useSAMPersonality()
  const voice = useSAMVoice()
  const characterCustomization = useCharacterCustomization()

  // Cognitive API connection (Python backend)
  const cognitiveAPI = useCognitiveAPI({
    baseUrl: 'http://localhost:8765',
    userId: 'david'
  })

  // Configuration
  const config = ref<SAMConfig>(loadConfig())

  // Status
  const status = reactive<SAMStatus>({
    isOnline: false,
    isListening: false,
    isSpeaking: false,
    isThinking: false,
    lastInteraction: null,
    mood: 'neutral',
    energyLevel: 'medium'
  })

  // Current conversation context
  const conversationHistory = ref<Array<{
    role: 'user' | 'atlas'
    content: string
    timestamp: Date
  }>>([])

  // ========================================================================
  // LIFECYCLE
  // ========================================================================

  /**
   * Boot up SAM
   */
  async function start(): Promise<void> {
    if (status.isOnline) return

    console.log('[SAM] Booting up...')

    status.isOnline = true

    // Start subsystems based on config
    if (config.value.voiceEnabled) {
      // TTS is ready by default
    }

    if (config.value.wakeWordEnabled) {
      wakeWord.start()
      wakeWord.onWake(handleWakeWord)
      wakeWord.onTranscript(handleVoiceTranscript)
      status.isListening = true
    }

    if (config.value.proactiveEnabled) {
      notifications.start()
    }

    if (config.value.avatarEnabled) {
      await avatar.connect()
    }

    // Start calendar
    calendar.start()

    // Start daemon
    daemon.start()

    // Greet the user
    const greeting = personality.getTimeBasedGreeting()
    await say(greeting, { emotion: 'confident' })

    // Share schedule if there are upcoming events
    const upcoming = calendar.getUpcoming(4)
    if (upcoming.length > 0) {
      const summary = calendar.getScheduleSummary()
      await say(summary, { emotion: 'neutral', addContext: true })
    }

    // Check for people needing attention
    const attention = relationships.needsAttention.value
    if (attention.length > 0 && attention[0].urgency === 'high') {
      const person = attention[0]
      await say(`By the way, ${person.reason} with ${person.person.name}.`, {
        emotion: 'concerned'
      })
    }

    await auditLog.log('atlas_started', 'SAM is online', { riskLevel: 'low' })
    console.log('[SAM] Online and ready')
  }

  /**
   * Shut down SAM
   */
  async function stop(): Promise<void> {
    if (!status.isOnline) return

    console.log('[SAM] Shutting down...')

    // Farewell
    await say("Alright, I'll be here if you need me.", { emotion: 'neutral' })

    // Stop subsystems
    wakeWord.stop()
    notifications.stop()
    avatar.disconnect()
    calendar.stop()
    daemon.stop()

    status.isOnline = false
    status.isListening = false

    await auditLog.log('atlas_stopped', 'SAM is offline', { riskLevel: 'low' })
    console.log('[SAM] Offline')
  }

  // ========================================================================
  // VOICE INTERACTION
  // ========================================================================

  /**
   * Handle wake word detection
   */
  function handleWakeWord(transcript: string): void {
    console.log('[SAM] Wake word detected')

    status.isListening = true
    personality.conversationMood.value = 'neutral'

    // Visual feedback via avatar
    if (avatar.state.connected) {
      avatar.setEmotion('interested')
      avatar.setAnimation('listening')
    }
  }

  /**
   * Handle voice transcript
   */
  async function handleVoiceTranscript(
    transcript: string,
    isFinal: boolean
  ): Promise<void> {
    if (!isFinal) return

    // Process the user's speech
    await handleUserMessage(transcript)
  }

  /**
   * Speak as SAM
   */
  async function say(
    text: string,
    options?: {
      emotion?: 'neutral' | 'confident' | 'flirty' | 'concerned' | 'happy'
      addContext?: boolean
      skipLearning?: boolean
    }
  ): Promise<void> {
    status.isSpeaking = true

    // Format with personality
    let formattedText = text
    if (options?.addContext) {
      const learnedContext = learning.getLearnedSystemPrompt()
      // Could inject context here
    }

    // Set avatar state
    if (avatar.state.connected) {
      avatar.setEmotion(
        options?.emotion === 'flirty' ? 'flirty' :
        options?.emotion === 'concerned' ? 'concerned' :
        options?.emotion === 'happy' ? 'happy' :
        options?.emotion === 'confident' ? 'confident' :
        'neutral'
      )
      await avatar.speak(formattedText)
    } else {
      // Just TTS without avatar
      await tts.speak(formattedText, {
        emotion: options?.emotion as any
      })
    }

    status.isSpeaking = false

    // Add to conversation history
    conversationHistory.value.push({
      role: 'atlas',
      content: text,
      timestamp: new Date()
    })

    // Learn from interaction
    if (config.value.learningEnabled && !options?.skipLearning) {
      learning.learnSchedule(`Spoke to user`)
    }
  }

  // ========================================================================
  // MESSAGE HANDLING
  // ========================================================================

  /**
   * Handle user message (voice or text)
   */
  async function handleUserMessage(message: string): Promise<void> {
    status.isThinking = true
    status.lastInteraction = new Date()

    // Add to history
    conversationHistory.value.push({
      role: 'user',
      content: message,
      timestamp: new Date()
    })

    // Extract mentions
    const mentions = relationships.extractMentions(message)
    if (mentions.length > 0) {
      console.log('[SAM] Detected mentions:', mentions.map(m => m.name))
    }

    // Avatar thinking state
    if (avatar.state.connected) {
      avatar.setEmotion('thoughtful')
      avatar.setAnimation('thinking')
    }

    // Learn from message patterns
    if (config.value.learningEnabled) {
      analyzeAndLearn(message)
    }

    // Generate response (this would normally go to an LLM)
    const response = await generateResponse(message, mentions)

    status.isThinking = false

    // Speak the response
    await say(response, {
      emotion: determineEmotion(response)
    })

    // Keep wake word alive
    wakeWord.keepAlive()
  }

  /**
   * Generate a response using the cognitive API
   */
  async function generateResponse(
    message: string,
    mentions: ReturnType<typeof relationships.extractMentions>
  ): Promise<string> {
    const lower = message.toLowerCase()

    // Quick local responses for simple queries (no API call needed)

    // Calendar queries - handled locally for speed
    if (lower.includes('schedule') || lower.includes('calendar') || lower.includes('meeting')) {
      const summary = calendar.getScheduleSummary()
      return summary || "Your schedule is clear. What would you like to do?"
    }

    // Time queries - instant local response
    if (lower.includes('what time') || lower.includes('the time')) {
      const time = new Date().toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit'
      })
      return `It's ${time}.`
    }

    // Relationship queries - use local data
    if (mentions.length > 0) {
      const person = mentions[0]
      const context = relationships.getPersonContext(person.id)
      return `About ${person.name}... ${context}`
    }

    // Everything else goes to the cognitive API
    try {
      // Check if cognitive API is available
      const isAvailable = await cognitiveAPI.ping()

      if (!isAvailable) {
        console.warn('[SAM] Cognitive API not available, using fallback')
        return getFallbackResponse(message)
      }

      // Call the cognitive API
      const result = await cognitiveAPI.process(message)

      if (result && result.response) {
        // Store confidence for mood adjustment
        if (result.confidence < 0.5) {
          status.mood = 'focused'  // Lower confidence = more careful
        } else if (result.confidence > 0.8) {
          status.mood = 'playful'  // High confidence = more playful
        }

        // Track if escalated to Claude
        if (result.escalated) {
          console.log('[SAM] Response was escalated to Claude')
        }

        return result.response
      }

      // API returned null/empty, use fallback
      return getFallbackResponse(message)

    } catch (e) {
      console.error('[SAM] Cognitive API error:', e)
      return getFallbackResponse(message)
    }
  }

  /**
   * Fallback responses when cognitive API is unavailable
   */
  function getFallbackResponse(message: string): string {
    const lower = message.toLowerCase()

    // Learning queries
    if (lower.includes('what have you learned') || lower.includes('know about me')) {
      return learning.getLearningSummary()
    }

    // Flirty responses for certain inputs
    if (lower.includes('miss you') || lower.includes('love you')) {
      return personality.getPhrase('flirtations')
    }

    // Default response with personality
    const responses = [
      "Tell me more about that.",
      "Interesting. Go on.",
      "I'm listening.",
      "What else is on your mind?",
      personality.getPhrase('affirmations')
    ]

    return responses[Math.floor(Math.random() * responses.length)]
  }

  /**
   * Stream a response token-by-token (for real-time display)
   */
  function streamResponse(
    message: string,
    onToken: (token: string) => void,
    onComplete?: (fullResponse: string) => void,
    onError?: (error: string) => void
  ): () => void {
    // Start streaming from cognitive API
    return cognitiveAPI.stream(
      message,
      onToken,
      (response) => {
        // Add to conversation history
        conversationHistory.value.push({
          role: 'atlas',
          content: response.response,
          timestamp: new Date()
        })
        onComplete?.(response.response)
      },
      onError
    )
  }

  /**
   * Process an image and get a response
   */
  async function processImage(
    imagePath: string,
    query: string = 'What do you see in this image?'
  ): Promise<string> {
    try {
      const result = await cognitiveAPI.processImage(imagePath, query)
      if (result && result.response) {
        return result.response
      }
      return "I couldn't process that image right now."
    } catch (e) {
      console.error('[SAM] Vision error:', e)
      return "Having trouble with my vision system at the moment."
    }
  }

  /**
   * Determine emotion for response
   */
  function determineEmotion(
    response: string
  ): 'neutral' | 'confident' | 'flirty' | 'concerned' | 'happy' {
    const lower = response.toLowerCase()

    if (lower.includes('sorry') || lower.includes('concern')) {
      return 'concerned'
    }

    if (lower.includes('love') || lower.includes('miss') || lower.includes('flirt')) {
      return 'flirty'
    }

    if (lower.includes('done') || lower.includes('got it') || lower.includes('easy')) {
      return 'confident'
    }

    if (lower.includes('great') || lower.includes('nice') || lower.includes('congrat')) {
      return 'happy'
    }

    return 'neutral'
  }

  /**
   * Analyze message and learn from it
   */
  function analyzeAndLearn(message: string): void {
    // Learn time patterns
    const hour = new Date().getHours()
    const timeOfDay = hour < 12 ? 'morning' :
                      hour < 17 ? 'afternoon' :
                      hour < 21 ? 'evening' : 'night'

    learning.observePattern('schedule', `Active in ${timeOfDay}`, {
      timeOfDay,
      dayOfWeek: new Date().getDay()
    })

    // Learn topic interests
    const topics = extractTopics(message)
    for (const topic of topics) {
      learning.learnLikes(topic, message)
    }
  }

  /**
   * Extract topics from message (simple keyword extraction)
   */
  function extractTopics(message: string): string[] {
    const techWords = ['code', 'programming', 'api', 'database', 'server', 'frontend', 'backend']
    const topics: string[] = []

    const lower = message.toLowerCase()
    for (const word of techWords) {
      if (lower.includes(word)) {
        topics.push(word)
      }
    }

    return topics
  }

  // ========================================================================
  // PROACTIVE FEATURES
  // ========================================================================

  /**
   * Check in with the user
   */
  async function checkIn(): Promise<void> {
    const greeting = personality.getTimeBasedGreeting()
    await say(greeting, { emotion: 'neutral' })
  }

  /**
   * Remind about something
   */
  async function remind(about: string, inMinutes?: number): Promise<void> {
    if (inMinutes) {
      setTimeout(async () => {
        await say(`Hey, just reminding you: ${about}`, { emotion: 'neutral' })
      }, inMinutes * 60 * 1000)
    } else {
      await say(`Don't forget: ${about}`, { emotion: 'neutral' })
    }
  }

  /**
   * Share an insight proactively
   */
  async function shareInsight(insight: string): Promise<void> {
    const intro = personality.getPhrase('thinking')
    await say(`${intro} ${insight}`, { emotion: 'confident' })
  }

  // ========================================================================
  // MOOD & PERSONALITY
  // ========================================================================

  /**
   * Set SAM's mood
   */
  function setMood(mood: SAMStatus['mood']): void {
    status.mood = mood
    personality.conversationMood.value =
      mood === 'flirty' ? 'intimate' :
      mood === 'playful' ? 'playful' :
      mood === 'focused' ? 'serious' :
      'neutral'

    if (avatar.state.connected) {
      avatar.setEmotion(
        mood === 'flirty' ? 'flirty' :
        mood === 'playful' ? 'playful' :
        mood === 'focused' ? 'intense' :
        'neutral'
      )
    }
  }

  /**
   * Make SAM flirt
   */
  async function flirt(): Promise<void> {
    setMood('flirty')
    const line = personality.getPhrase('flirtations')
    await say(line, { emotion: 'flirty' })

    if (avatar.state.connected) {
      avatar.flirt()
    }
  }

  // ========================================================================
  // CONFIGURATION
  // ========================================================================

  /**
   * Update configuration
   */
  function updateConfig(updates: Partial<SAMConfig>): void {
    Object.assign(config.value, updates)
    saveConfig(config.value)

    // Apply changes
    if (updates.wakeWordEnabled !== undefined) {
      if (updates.wakeWordEnabled && status.isOnline) {
        wakeWord.start()
      } else {
        wakeWord.stop()
      }
    }

    if (updates.avatarEnabled !== undefined) {
      if (updates.avatarEnabled && status.isOnline) {
        avatar.connect()
      } else {
        avatar.disconnect()
      }
    }
  }

  /**
   * Get comprehensive system prompt for LLM
   */
  const systemPrompt = computed(() => {
    const parts = [
      personality.systemPrompt.value,
      '',
      '--- LEARNED CONTEXT ---',
      learning.getLearnedSystemPrompt()
    ]

    return parts.join('\n')
  })

  // ========================================================================
  // AUTO-START
  // ========================================================================

  onMounted(() => {
    if (config.value.autoStart && config.value.enabled) {
      start()
    }
  })

  onUnmounted(() => {
    stop()
  })

  return {
    // Configuration
    config,
    updateConfig,

    // Status
    status,
    systemPrompt,

    // Lifecycle
    start,
    stop,

    // Communication
    say,
    handleUserMessage,

    // Proactive
    checkIn,
    remind,
    shareInsight,

    // Mood
    setMood,
    flirt,

    // Subsystems (exposed for direct access)
    subsystems: {
      personality,
      tts,
      notifications,
      wakeWord,
      calendar,
      relationships,
      learning,
      avatar,
      daemon
    },

    // Enhanced subsystems (new "Her" systems)
    enhanced: {
      memory,           // Persistent memory - he remembers everything
      personality: enhancedPersonality,  // Emotional intelligence
      voice,            // Neural voice synthesis
      character: characterCustomization  // Avatar customization
    },

    // Quick access to enhanced features
    memory,
    voice,
    character: characterCustomization,

    // Cognitive API (Python backend connection)
    cognitiveAPI,
    streamResponse,
    processImage,

    // Conversation
    conversationHistory
  }
}

export type UseSAMReturn = ReturnType<typeof useSAM>
