/**
 * useAvatarBridge - Game Engine Avatar Integration
 *
 * Bridges SAM AI to a visual avatar in a game engine.
 * Supports Unity, Unreal, Godot via WebSocket protocol.
 *
 * The avatar is a masculine, cocky, sultry visual representation of SAM.
 * Think: sharp jawline, knowing smirk, confident posture, intense eyes.
 */

import { ref, computed, watch, reactive, onUnmounted } from 'vue'
import { usePersonality } from './usePersonality'
import { useTTS } from './useTTS'
import { useAuditLog } from './useAuditLog'

// ============================================================================
// TYPES
// ============================================================================

export type GameEngine = 'unity' | 'unreal' | 'godot' | 'custom'

export type AnimationState =
  | 'idle'
  | 'talking'
  | 'thinking'
  | 'listening'
  | 'pleased'
  | 'smirking'
  | 'flirting'
  | 'concerned'
  | 'laughing'
  | 'eyebrow_raise'
  | 'head_tilt'
  | 'nod'
  | 'shake_head'
  | 'wink'
  | 'custom'

export type EmotionalState =
  | 'neutral'
  | 'happy'
  | 'amused'
  | 'interested'
  | 'flirty'
  | 'confident'
  | 'thoughtful'
  | 'concerned'
  | 'playful'
  | 'intense'

export interface AvatarState {
  connected: boolean
  engine: GameEngine | null
  currentAnimation: AnimationState
  emotionalState: EmotionalState
  isSpeaking: boolean
  eyeContact: boolean
  headPosition: { x: number; y: number; z: number }
  bodyPosture: 'relaxed' | 'alert' | 'leaning_forward' | 'leaning_back'
  handGesture: string | null
  facialExpression: {
    browRaise: number       // 0-1
    smirkIntensity: number  // 0-1
    eyeIntensity: number    // 0-1
    jawTension: number      // 0-1
  }
}

export interface LipSyncData {
  timestamp: number
  viseme: string       // Mouth shape: A, E, I, O, U, M, F, etc.
  intensity: number    // 0-1
  duration: number     // ms
}

export interface AvatarConfig {
  enabled: boolean
  engine: GameEngine
  host: string
  port: number
  reconnectAttempts: number
  reconnectDelay: number
  lipSyncEnabled: boolean
  lipSyncSampleRate: number
  idleAnimationEnabled: boolean
  idleAnimationInterval: number
  blinkRate: number
  breathingEnabled: boolean
}

export interface AvatarCommand {
  type: 'animation' | 'emotion' | 'lipsync' | 'gesture' | 'look' | 'custom'
  payload: Record<string, unknown>
  timestamp: number
}

export interface AvatarEvent {
  type: 'user_gesture' | 'user_touch' | 'state_change' | 'error'
  data: Record<string, unknown>
  timestamp: number
}

// ============================================================================
// VISEME MAPPING
// ============================================================================

const PHONEME_TO_VISEME: Record<string, string> = {
  // Vowels
  'AA': 'A', 'AE': 'A', 'AH': 'A',
  'AO': 'O', 'AW': 'O',
  'AY': 'A',
  'EH': 'E', 'ER': 'E', 'EY': 'E',
  'IH': 'I', 'IY': 'I',
  'OW': 'O', 'OY': 'O',
  'UH': 'U', 'UW': 'U',
  // Consonants
  'B': 'M', 'P': 'M', 'M': 'M',
  'F': 'F', 'V': 'F',
  'TH': 'TH', 'DH': 'TH',
  'S': 'S', 'Z': 'S', 'SH': 'S', 'ZH': 'S', 'CH': 'S', 'JH': 'S',
  'T': 'T', 'D': 'T', 'N': 'T', 'L': 'T',
  'K': 'K', 'G': 'K', 'NG': 'K',
  'R': 'R',
  'W': 'W',
  'Y': 'I',
  'HH': 'REST',
  // Rest
  'REST': 'REST', ' ': 'REST', '.': 'REST', ',': 'REST'
}

// Simple text-to-viseme (approximate)
const TEXT_TO_VISEMES: Record<string, string[]> = {
  'a': ['A'], 'e': ['E'], 'i': ['I'], 'o': ['O'], 'u': ['U'],
  'b': ['M', 'REST'], 'p': ['M', 'REST'], 'm': ['M', 'M'],
  'f': ['F'], 'v': ['F'],
  'th': ['TH'],
  's': ['S'], 'z': ['S'], 'sh': ['S'], 'ch': ['S'],
  't': ['T', 'REST'], 'd': ['T', 'REST'], 'n': ['T'], 'l': ['T'],
  'k': ['K', 'REST'], 'g': ['K', 'REST'],
  'r': ['R'], 'w': ['W'], 'y': ['I'],
  ' ': ['REST'], '.': ['REST', 'REST'], ',': ['REST']
}

// ============================================================================
// IDLE ANIMATIONS
// ============================================================================

const IDLE_ANIMATIONS: Array<{
  animation: AnimationState
  weight: number
  minInterval: number
  maxInterval: number
}> = [
  { animation: 'smirking', weight: 0.3, minInterval: 15, maxInterval: 45 },
  { animation: 'eyebrow_raise', weight: 0.2, minInterval: 10, maxInterval: 30 },
  { animation: 'head_tilt', weight: 0.2, minInterval: 20, maxInterval: 60 },
  { animation: 'idle', weight: 0.3, minInterval: 30, maxInterval: 90 }
]

// ============================================================================
// STORAGE
// ============================================================================

const CONFIG_KEY = 'warp_avatar_config'

function loadConfig(): AvatarConfig {
  try {
    const stored = localStorage.getItem(CONFIG_KEY)
    if (stored) return JSON.parse(stored)
  } catch {}
  return {
    enabled: true,
    engine: 'unity',
    host: 'localhost',
    port: 8765,
    reconnectAttempts: 5,
    reconnectDelay: 3000,
    lipSyncEnabled: true,
    lipSyncSampleRate: 60,  // 60 visemes per second max
    idleAnimationEnabled: true,
    idleAnimationInterval: 5000,
    blinkRate: 4,  // blinks per minute
    breathingEnabled: true
  }
}

function saveConfig(config: AvatarConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useAvatarBridge() {
  const personality = usePersonality()
  const tts = useTTS()
  const auditLog = useAuditLog()

  const config = ref<AvatarConfig>(loadConfig())

  const state = reactive<AvatarState>({
    connected: false,
    engine: null,
    currentAnimation: 'idle',
    emotionalState: 'neutral',
    isSpeaking: false,
    eyeContact: true,
    headPosition: { x: 0, y: 0, z: 0 },
    bodyPosture: 'relaxed',
    handGesture: null,
    facialExpression: {
      browRaise: 0,
      smirkIntensity: 0.3,  // Default slight smirk
      eyeIntensity: 0.5,
      jawTension: 0
    }
  })

  const commandQueue = ref<AvatarCommand[]>([])
  const eventHistory = ref<AvatarEvent[]>([])

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  let idleAnimationInterval: ReturnType<typeof setInterval> | null = null
  let blinkInterval: ReturnType<typeof setInterval> | null = null
  let breathingInterval: ReturnType<typeof setInterval> | null = null

  // Event callbacks
  const eventCallbacks: Map<string, ((event: AvatarEvent) => void)[]> = new Map()

  // ========================================================================
  // CONNECTION MANAGEMENT
  // ========================================================================

  /**
   * Connect to the game engine
   */
  function connect(): Promise<boolean> {
    return new Promise((resolve) => {
      if (ws?.readyState === WebSocket.OPEN) {
        resolve(true)
        return
      }

      const url = `ws://${config.value.host}:${config.value.port}`

      try {
        ws = new WebSocket(url)

        ws.onopen = () => {
          console.log('[Avatar] Connected to game engine')
          state.connected = true
          state.engine = config.value.engine
          reconnectAttempts = 0

          // Send initial state
          sendCommand('emotion', { emotion: 'neutral' })

          // Start idle animations
          if (config.value.idleAnimationEnabled) {
            startIdleAnimations()
          }

          // Start blinking
          startBlinking()

          // Start breathing
          if (config.value.breathingEnabled) {
            startBreathing()
          }

          auditLog.log('avatar_connected', 'Connected to avatar', { riskLevel: 'low' })
          resolve(true)
        }

        ws.onmessage = (event) => {
          handleMessage(event.data)
        }

        ws.onerror = (error) => {
          console.error('[Avatar] WebSocket error:', error)
          state.connected = false
        }

        ws.onclose = () => {
          console.log('[Avatar] Disconnected')
          state.connected = false
          stopIdleAnimations()
          stopBlinking()
          stopBreathing()

          // Attempt reconnection
          if (reconnectAttempts < config.value.reconnectAttempts) {
            reconnectAttempts++
            reconnectTimeout = setTimeout(() => {
              console.log(`[Avatar] Reconnection attempt ${reconnectAttempts}`)
              connect()
            }, config.value.reconnectDelay)
          }
        }

      } catch (error) {
        console.error('[Avatar] Connection failed:', error)
        resolve(false)
      }
    })
  }

  /**
   * Disconnect from the game engine
   */
  function disconnect(): void {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }

    stopIdleAnimations()
    stopBlinking()
    stopBreathing()

    if (ws) {
      ws.close()
      ws = null
    }

    state.connected = false
    state.engine = null
  }

  /**
   * Handle incoming message from game engine
   */
  function handleMessage(data: string): void {
    try {
      const event: AvatarEvent = JSON.parse(data)
      event.timestamp = Date.now()

      eventHistory.value.push(event)
      if (eventHistory.value.length > 100) {
        eventHistory.value = eventHistory.value.slice(-100)
      }

      // Trigger callbacks
      const callbacks = eventCallbacks.get(event.type) || []
      for (const callback of callbacks) {
        callback(event)
      }

      // Handle specific events
      switch (event.type) {
        case 'user_gesture':
          handleUserGesture(event)
          break
        case 'state_change':
          handleStateChange(event)
          break
      }

    } catch (error) {
      console.error('[Avatar] Message parse error:', error)
    }
  }

  function handleUserGesture(event: AvatarEvent): void {
    console.log('[Avatar] User gesture:', event.data)
    // Could trigger responses based on user gestures in the game
  }

  function handleStateChange(event: AvatarEvent): void {
    if (event.data.animation) {
      state.currentAnimation = event.data.animation as AnimationState
    }
    if (event.data.emotion) {
      state.emotionalState = event.data.emotion as EmotionalState
    }
  }

  // ========================================================================
  // COMMAND SENDING
  // ========================================================================

  /**
   * Send a command to the game engine
   */
  function sendCommand(
    type: AvatarCommand['type'],
    payload: Record<string, unknown>
  ): void {
    const command: AvatarCommand = {
      type,
      payload,
      timestamp: Date.now()
    }

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(command))
    } else {
      // Queue command for when connection is restored
      commandQueue.value.push(command)
    }
  }

  /**
   * Flush queued commands
   */
  function flushCommandQueue(): void {
    if (ws?.readyState !== WebSocket.OPEN) return

    while (commandQueue.value.length > 0) {
      const command = commandQueue.value.shift()!
      ws.send(JSON.stringify(command))
    }
  }

  // ========================================================================
  // ANIMATION CONTROL
  // ========================================================================

  /**
   * Set animation state
   */
  function setAnimation(
    animation: AnimationState,
    options?: {
      blend?: number      // 0-1, blend speed
      loop?: boolean
      duration?: number   // ms, for non-looping
    }
  ): void {
    state.currentAnimation = animation

    sendCommand('animation', {
      animation,
      blend: options?.blend ?? 0.3,
      loop: options?.loop ?? true,
      duration: options?.duration
    })
  }

  /**
   * Set emotional state (affects facial expression)
   */
  function setEmotion(emotion: EmotionalState): void {
    state.emotionalState = emotion

    // Map emotion to facial expression
    const expressionMap: Record<EmotionalState, Partial<AvatarState['facialExpression']>> = {
      neutral: { browRaise: 0, smirkIntensity: 0.2, eyeIntensity: 0.5 },
      happy: { browRaise: 0.2, smirkIntensity: 0.6, eyeIntensity: 0.7 },
      amused: { browRaise: 0.3, smirkIntensity: 0.7, eyeIntensity: 0.6 },
      interested: { browRaise: 0.4, smirkIntensity: 0.3, eyeIntensity: 0.8 },
      flirty: { browRaise: 0.5, smirkIntensity: 0.8, eyeIntensity: 0.9 },
      confident: { browRaise: 0.2, smirkIntensity: 0.6, eyeIntensity: 0.7 },
      thoughtful: { browRaise: 0.1, smirkIntensity: 0.1, eyeIntensity: 0.4 },
      concerned: { browRaise: 0.3, smirkIntensity: 0, eyeIntensity: 0.6 },
      playful: { browRaise: 0.4, smirkIntensity: 0.7, eyeIntensity: 0.8 },
      intense: { browRaise: 0.1, smirkIntensity: 0.4, eyeIntensity: 1.0 }
    }

    const expression = expressionMap[emotion] || expressionMap.neutral
    Object.assign(state.facialExpression, expression)

    sendCommand('emotion', {
      emotion,
      expression: state.facialExpression
    })
  }

  /**
   * Perform a gesture
   */
  function gesture(
    gestureName: string,
    options?: {
      hand?: 'left' | 'right' | 'both'
      intensity?: number
    }
  ): void {
    state.handGesture = gestureName

    sendCommand('gesture', {
      gesture: gestureName,
      hand: options?.hand ?? 'right',
      intensity: options?.intensity ?? 0.7
    })

    // Clear gesture after a moment
    setTimeout(() => {
      state.handGesture = null
    }, 2000)
  }

  /**
   * Look at a target
   */
  function lookAt(target: 'user' | 'away' | { x: number; y: number; z: number }): void {
    state.eyeContact = target === 'user'

    sendCommand('look', {
      target: target === 'user' ? { x: 0, y: 1.6, z: 1 } :
              target === 'away' ? { x: 2, y: 1.4, z: 0 } :
              target
    })
  }

  // ========================================================================
  // LIP SYNC
  // ========================================================================

  /**
   * Generate lip sync data from text
   */
  function generateLipSync(text: string, durationMs: number): LipSyncData[] {
    const visemes: LipSyncData[] = []
    const cleanText = text.toLowerCase().replace(/[^a-z\s.,]/g, '')
    const chars = cleanText.split('')

    const timePerChar = durationMs / chars.length
    let currentTime = 0

    for (let i = 0; i < chars.length; i++) {
      const char = chars[i]
      const nextChar = chars[i + 1] || ''
      const combo = char + nextChar

      // Check for digraphs first
      let visemeList = TEXT_TO_VISEMES[combo]
      if (visemeList && combo.length === 2) {
        i++ // Skip next char
      } else {
        visemeList = TEXT_TO_VISEMES[char] || ['REST']
      }

      for (const viseme of visemeList) {
        visemes.push({
          timestamp: currentTime,
          viseme,
          intensity: viseme === 'REST' ? 0 : 0.8,
          duration: timePerChar / visemeList.length
        })
        currentTime += timePerChar / visemeList.length
      }
    }

    return visemes
  }

  /**
   * Start lip sync for speech
   */
  function startLipSync(text: string, durationMs: number): void {
    if (!config.value.lipSyncEnabled) return

    state.isSpeaking = true
    setAnimation('talking')

    const lipSyncData = generateLipSync(text, durationMs)

    sendCommand('lipsync', {
      data: lipSyncData,
      totalDuration: durationMs
    })

    // End speaking state after duration
    setTimeout(() => {
      state.isSpeaking = false
      setAnimation('idle')
    }, durationMs)
  }

  /**
   * Stop lip sync
   */
  function stopLipSync(): void {
    state.isSpeaking = false
    sendCommand('lipsync', { stop: true })
    setAnimation('idle')
  }

  // ========================================================================
  // IDLE BEHAVIORS
  // ========================================================================

  /**
   * Start idle animations
   */
  function startIdleAnimations(): void {
    if (idleAnimationInterval) return

    const triggerIdleAnimation = () => {
      if (state.isSpeaking || state.currentAnimation === 'listening') return

      // Weighted random selection
      const totalWeight = IDLE_ANIMATIONS.reduce((sum, a) => sum + a.weight, 0)
      let random = Math.random() * totalWeight
      let selected = IDLE_ANIMATIONS[0]

      for (const anim of IDLE_ANIMATIONS) {
        random -= anim.weight
        if (random <= 0) {
          selected = anim
          break
        }
      }

      setAnimation(selected.animation, { loop: false, duration: 2000 })

      // Return to idle after animation
      setTimeout(() => {
        if (!state.isSpeaking) {
          setAnimation('idle')
        }
      }, 2000)
    }

    idleAnimationInterval = setInterval(
      triggerIdleAnimation,
      config.value.idleAnimationInterval
    )
  }

  /**
   * Stop idle animations
   */
  function stopIdleAnimations(): void {
    if (idleAnimationInterval) {
      clearInterval(idleAnimationInterval)
      idleAnimationInterval = null
    }
  }

  /**
   * Start blinking
   */
  function startBlinking(): void {
    if (blinkInterval) return

    const blink = () => {
      sendCommand('custom', {
        action: 'blink',
        duration: 150
      })
    }

    // Random blink interval based on blink rate
    const scheduleNextBlink = () => {
      const intervalMs = (60 / config.value.blinkRate) * 1000
      const variance = intervalMs * 0.3
      const nextBlink = intervalMs + (Math.random() * variance * 2 - variance)

      blinkInterval = setTimeout(() => {
        blink()
        scheduleNextBlink()
      }, nextBlink)
    }

    scheduleNextBlink()
  }

  /**
   * Stop blinking
   */
  function stopBlinking(): void {
    if (blinkInterval) {
      clearTimeout(blinkInterval as any)
      blinkInterval = null
    }
  }

  /**
   * Start breathing animation
   */
  function startBreathing(): void {
    if (breathingInterval) return

    let breathPhase = 0

    breathingInterval = setInterval(() => {
      breathPhase = (breathPhase + 0.05) % (Math.PI * 2)
      const breathIntensity = (Math.sin(breathPhase) + 1) / 2 * 0.1

      sendCommand('custom', {
        action: 'breathing',
        intensity: breathIntensity
      })
    }, 100)
  }

  /**
   * Stop breathing animation
   */
  function stopBreathing(): void {
    if (breathingInterval) {
      clearInterval(breathingInterval)
      breathingInterval = null
    }
  }

  // ========================================================================
  // AVATAR RESPONSES
  // ========================================================================

  /**
   * React to user message (sets appropriate emotion and animation)
   */
  function reactToMessage(
    sentiment: 'positive' | 'neutral' | 'negative' | 'question'
  ): void {
    switch (sentiment) {
      case 'positive':
        setEmotion('happy')
        setAnimation('smirking')
        break
      case 'negative':
        setEmotion('concerned')
        setAnimation('head_tilt')
        break
      case 'question':
        setEmotion('interested')
        setAnimation('eyebrow_raise')
        break
      default:
        setEmotion('neutral')
        setAnimation('listening')
    }
  }

  /**
   * Speaking response (with lip sync)
   */
  async function speak(text: string): Promise<void> {
    // Estimate duration (rough: 150ms per word)
    const wordCount = text.split(' ').length
    const estimatedDuration = wordCount * 150

    // Set speaking state
    setEmotion('confident')
    startLipSync(text, estimatedDuration)

    // Trigger TTS
    await tts.speak(text)

    // End speaking state
    stopLipSync()
    setEmotion('neutral')
  }

  /**
   * Flirty reaction
   */
  function flirt(): void {
    setEmotion('flirty')
    setAnimation('wink')
    gesture('point', { hand: 'right', intensity: 0.5 })

    setTimeout(() => {
      setEmotion('confident')
      setAnimation('smirking')
    }, 2000)
  }

  // ========================================================================
  // EVENT HANDLING
  // ========================================================================

  /**
   * Register event callback
   */
  function onEvent(
    type: AvatarEvent['type'],
    callback: (event: AvatarEvent) => void
  ): () => void {
    if (!eventCallbacks.has(type)) {
      eventCallbacks.set(type, [])
    }
    eventCallbacks.get(type)!.push(callback)

    // Return unsubscribe function
    return () => {
      const callbacks = eventCallbacks.get(type) || []
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  // ========================================================================
  // CONFIGURATION
  // ========================================================================

  /**
   * Update configuration
   */
  function updateConfig(updates: Partial<AvatarConfig>): void {
    Object.assign(config.value, updates)
    saveConfig(config.value)

    // Apply changes
    if (updates.idleAnimationEnabled !== undefined) {
      if (updates.idleAnimationEnabled) {
        startIdleAnimations()
      } else {
        stopIdleAnimations()
      }
    }

    if (updates.breathingEnabled !== undefined) {
      if (updates.breathingEnabled) {
        startBreathing()
      } else {
        stopBreathing()
      }
    }
  }

  // Save config on changes
  watch(config, () => saveConfig(config.value), { deep: true })

  // Clean up on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    config,
    state,
    commandQueue,
    eventHistory,

    // Connection
    connect,
    disconnect,

    // Animation
    setAnimation,
    setEmotion,
    gesture,
    lookAt,

    // Lip sync
    startLipSync,
    stopLipSync,
    generateLipSync,

    // Idle behaviors
    startIdleAnimations,
    stopIdleAnimations,

    // High-level responses
    reactToMessage,
    speak,
    flirt,

    // Events
    onEvent,

    // Config
    updateConfig
  }
}

export type UseAvatarBridgeReturn = ReturnType<typeof useAvatarBridge>
