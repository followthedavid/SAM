/**
 * useWakeWord - Always-Listening Wake Word Detection
 *
 * Listens for "Hey SAM" (or custom wake word) to activate the AI.
 * Uses Web Speech API for continuous listening with low resource usage.
 *
 * "Hey SAM..." *SAM perks up* "What do you need?"
 */

import { ref, computed, watch, onUnmounted } from 'vue'
import { usePersonality } from './usePersonality'
import { useTTS } from './useTTS'
import { useAuditLog } from './useAuditLog'

// ============================================================================
// TYPES
// ============================================================================

export interface WakeWordConfig {
  enabled: boolean
  wakeWord: string
  alternativeWakeWords: string[]
  sensitivity: 'low' | 'medium' | 'high'
  confirmationSound: boolean
  speakConfirmation: boolean
  autoTimeout: number  // Seconds to stay active after wake word
}

export interface WakeWordEvent {
  timestamp: Date
  transcript: string
  confidence: number
  wakeWordDetected: string
}

// ============================================================================
// WAKE WORD RESPONSES
// ============================================================================

const WAKE_RESPONSES = {
  casual: [
    "Yeah?",
    "What's up?",
    "I'm here.",
    "Talk to me.",
    "Go ahead.",
    "Listening.",
    "Mm-hmm?",
    "What do you need?"
  ],
  flirty: [
    "Well hello there...",
    "You rang?",
    "Miss me?",
    "At your service.",
    "I was hoping you'd call.",
    "There you are."
  ],
  professional: [
    "Ready.",
    "Go ahead.",
    "I'm listening.",
    "What can I do for you?",
    "How can I help?"
  ]
}

const STORAGE_KEY = 'warp_wake_word_config'

// ============================================================================
// COMPOSABLE
// ============================================================================

function loadConfig(): WakeWordConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch {}
  return {
    enabled: true,
    wakeWord: 'hey atlas',
    alternativeWakeWords: ['atlas', 'hey boss', 'yo atlas'],
    sensitivity: 'medium',
    confirmationSound: true,
    speakConfirmation: true,
    autoTimeout: 30
  }
}

function saveConfig(config: WakeWordConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

export function useWakeWord() {
  const personality = usePersonality()
  const tts = useTTS()
  const auditLog = useAuditLog()

  const config = ref<WakeWordConfig>(loadConfig())
  const isListening = ref(false)
  const isActivated = ref(false)
  const lastWakeEvent = ref<WakeWordEvent | null>(null)
  const recentTranscripts = ref<string[]>([])

  let recognition: SpeechRecognition | null = null
  let activationTimeout: ReturnType<typeof setTimeout> | null = null

  // Callbacks
  let onWakeCallback: ((transcript: string) => void) | null = null
  let onTranscriptCallback: ((transcript: string, isFinal: boolean) => void) | null = null

  // ========================================================================
  // SPEECH RECOGNITION SETUP
  // ========================================================================

  function initRecognition(): boolean {
    if (typeof window === 'undefined') return false

    const SpeechRecognition = (window as any).SpeechRecognition ||
                              (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      console.warn('[WakeWord] Speech recognition not supported')
      return false
    }

    recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'
    recognition.maxAlternatives = 3

    recognition.onresult = handleResult
    recognition.onerror = handleError
    recognition.onend = handleEnd

    return true
  }

  function handleResult(event: SpeechRecognitionEvent): void {
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i]
      const transcript = result[0].transcript.toLowerCase().trim()
      const confidence = result[0].confidence
      const isFinal = result.isFinal

      // Store recent transcripts for debugging
      if (isFinal) {
        recentTranscripts.value = [...recentTranscripts.value.slice(-9), transcript]
      }

      // If already activated, pass through to callback
      if (isActivated.value && onTranscriptCallback) {
        onTranscriptCallback(transcript, isFinal)
        // Reset timeout on each transcript
        resetActivationTimeout()
        continue
      }

      // Check for wake word
      const detectedWakeWord = detectWakeWord(transcript)
      if (detectedWakeWord) {
        handleWakeWordDetected(detectedWakeWord, transcript, confidence)

        // Get the part after the wake word for immediate processing
        const afterWakeWord = getTextAfterWakeWord(transcript, detectedWakeWord)
        if (afterWakeWord && isFinal && onTranscriptCallback) {
          onTranscriptCallback(afterWakeWord, true)
        }
      }
    }
  }

  function handleError(event: SpeechRecognitionErrorEvent): void {
    console.error('[WakeWord] Recognition error:', event.error)

    if (event.error === 'not-allowed') {
      console.error('[WakeWord] Microphone permission denied')
      isListening.value = false
      return
    }

    // Auto-restart on recoverable errors
    if (event.error === 'network' || event.error === 'aborted') {
      setTimeout(() => {
        if (config.value.enabled && !isListening.value) {
          start()
        }
      }, 1000)
    }
  }

  function handleEnd(): void {
    // Auto-restart if still enabled
    if (config.value.enabled && isListening.value) {
      try {
        recognition?.start()
      } catch (e) {
        // Already started or other error
      }
    }
  }

  // ========================================================================
  // WAKE WORD DETECTION
  // ========================================================================

  /**
   * Check if transcript contains wake word
   */
  function detectWakeWord(transcript: string): string | null {
    const words = transcript.toLowerCase()

    // Check primary wake word
    if (words.includes(config.value.wakeWord)) {
      return config.value.wakeWord
    }

    // Check alternatives
    for (const alt of config.value.alternativeWakeWords) {
      if (words.includes(alt.toLowerCase())) {
        return alt
      }
    }

    // Fuzzy matching for sensitivity
    if (config.value.sensitivity === 'high') {
      const wakeWordParts = config.value.wakeWord.split(' ')
      const transcriptWords = words.split(' ')

      for (const part of wakeWordParts) {
        for (const word of transcriptWords) {
          if (levenshteinDistance(part, word) <= 1) {
            return config.value.wakeWord // Fuzzy match
          }
        }
      }
    }

    return null
  }

  /**
   * Get text that comes after the wake word
   */
  function getTextAfterWakeWord(transcript: string, wakeWord: string): string {
    const lower = transcript.toLowerCase()
    const index = lower.indexOf(wakeWord.toLowerCase())
    if (index === -1) return ''

    return transcript.substring(index + wakeWord.length).trim()
  }

  /**
   * Simple Levenshtein distance for fuzzy matching
   */
  function levenshteinDistance(a: string, b: string): number {
    const matrix: number[][] = []

    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i]
    }
    for (let j = 0; j <= a.length; j++) {
      matrix[0][j] = j
    }

    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        if (b.charAt(i - 1) === a.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1]
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          )
        }
      }
    }

    return matrix[b.length][a.length]
  }

  // ========================================================================
  // ACTIVATION HANDLING
  // ========================================================================

  /**
   * Handle wake word detection
   */
  async function handleWakeWordDetected(
    wakeWord: string,
    fullTranscript: string,
    confidence: number
  ): Promise<void> {
    // Prevent double-activation
    if (isActivated.value) return

    isActivated.value = true

    const event: WakeWordEvent = {
      timestamp: new Date(),
      transcript: fullTranscript,
      confidence,
      wakeWordDetected: wakeWord
    }
    lastWakeEvent.value = event

    console.log(`[WakeWord] Activated: "${wakeWord}" (confidence: ${(confidence * 100).toFixed(1)}%)`)

    // Play confirmation sound
    if (config.value.confirmationSound) {
      playConfirmationSound()
    }

    // Speak confirmation
    if (config.value.speakConfirmation) {
      const response = getWakeResponse()
      await tts.speak(response, { emotion: 'neutral', priority: 'interrupt' })
    }

    // Notify callback
    if (onWakeCallback) {
      onWakeCallback(fullTranscript)
    }

    // Log
    await auditLog.log('wake_word_detected', `SAM activated by "${wakeWord}"`, {
      riskLevel: 'low'
    })

    // Set auto-timeout
    resetActivationTimeout()
  }

  /**
   * Get a wake response based on personality
   */
  function getWakeResponse(): string {
    const mood = personality.conversationMood.value
    let responses: string[]

    switch (mood) {
      case 'playful':
      case 'intimate':
        responses = WAKE_RESPONSES.flirty
        break
      case 'serious':
        responses = WAKE_RESPONSES.professional
        break
      default:
        responses = WAKE_RESPONSES.casual
    }

    return responses[Math.floor(Math.random() * responses.length)]
  }

  /**
   * Play a subtle confirmation sound
   */
  function playConfirmationSound(): void {
    try {
      const audioContext = new AudioContext()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      // Pleasant two-tone chime
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(523.25, audioContext.currentTime) // C5
      oscillator.frequency.setValueAtTime(659.25, audioContext.currentTime + 0.1) // E5

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)

      oscillator.start()
      oscillator.stop(audioContext.currentTime + 0.3)
    } catch {
      // Audio not available
    }
  }

  /**
   * Reset the activation timeout
   */
  function resetActivationTimeout(): void {
    if (activationTimeout) {
      clearTimeout(activationTimeout)
    }

    activationTimeout = setTimeout(() => {
      deactivate()
    }, config.value.autoTimeout * 1000)
  }

  /**
   * Deactivate (stop listening for commands, go back to wake word mode)
   */
  function deactivate(): void {
    isActivated.value = false
    if (activationTimeout) {
      clearTimeout(activationTimeout)
      activationTimeout = null
    }
    console.log('[WakeWord] Deactivated, returning to wake word listening')
  }

  /**
   * Keep the activation alive (call when user is actively interacting)
   */
  function keepAlive(): void {
    if (isActivated.value) {
      resetActivationTimeout()
    }
  }

  // ========================================================================
  // LIFECYCLE
  // ========================================================================

  /**
   * Start listening for wake word
   */
  function start(): boolean {
    if (isListening.value) return true
    if (!config.value.enabled) return false

    if (!recognition && !initRecognition()) {
      return false
    }

    try {
      recognition!.start()
      isListening.value = true
      console.log('[WakeWord] Started listening for:', config.value.wakeWord)
      return true
    } catch (error) {
      console.error('[WakeWord] Failed to start:', error)
      return false
    }
  }

  /**
   * Stop listening
   */
  function stop(): void {
    if (!isListening.value) return

    try {
      recognition?.stop()
    } catch {}

    isListening.value = false
    isActivated.value = false

    if (activationTimeout) {
      clearTimeout(activationTimeout)
      activationTimeout = null
    }

    console.log('[WakeWord] Stopped')
  }

  /**
   * Toggle wake word listening
   */
  function toggle(): boolean {
    if (isListening.value) {
      stop()
      return false
    } else {
      return start()
    }
  }

  // ========================================================================
  // CONFIGURATION
  // ========================================================================

  /**
   * Set the wake word
   */
  function setWakeWord(word: string): void {
    config.value.wakeWord = word.toLowerCase()
    saveConfig(config.value)
  }

  /**
   * Add alternative wake word
   */
  function addAlternative(word: string): void {
    if (!config.value.alternativeWakeWords.includes(word.toLowerCase())) {
      config.value.alternativeWakeWords.push(word.toLowerCase())
      saveConfig(config.value)
    }
  }

  /**
   * Remove alternative wake word
   */
  function removeAlternative(word: string): void {
    config.value.alternativeWakeWords = config.value.alternativeWakeWords
      .filter(w => w !== word.toLowerCase())
    saveConfig(config.value)
  }

  /**
   * Set sensitivity
   */
  function setSensitivity(level: WakeWordConfig['sensitivity']): void {
    config.value.sensitivity = level
    saveConfig(config.value)
  }

  /**
   * Register wake callback
   */
  function onWake(callback: (transcript: string) => void): void {
    onWakeCallback = callback
  }

  /**
   * Register transcript callback
   */
  function onTranscript(callback: (transcript: string, isFinal: boolean) => void): void {
    onTranscriptCallback = callback
  }

  // Save config on changes
  watch(config, () => saveConfig(config.value), { deep: true })

  // Clean up on unmount
  onUnmounted(() => {
    stop()
  })

  return {
    // State
    config,
    isListening,
    isActivated,
    lastWakeEvent,
    recentTranscripts,

    // Lifecycle
    start,
    stop,
    toggle,

    // Activation
    deactivate,
    keepAlive,

    // Configuration
    setWakeWord,
    addAlternative,
    removeAlternative,
    setSensitivity,

    // Callbacks
    onWake,
    onTranscript
  }
}

export type UseWakeWordReturn = ReturnType<typeof useWakeWord>
