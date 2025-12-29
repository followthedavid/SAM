/**
 * useTTS - Text-to-Speech System
 *
 * Provides masculine, sultry voice output for the AI persona.
 * Supports multiple backends:
 * - macOS `say` command (built-in, free)
 * - Web Speech API (browser-based)
 * - Eleven Labs (premium, most realistic)
 * - Local models (Piper, Coqui TTS)
 */

import { ref, computed, watch } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { usePersonality } from './usePersonality'

// ============================================================================
// TYPES
// ============================================================================

export type TTSBackend = 'macos' | 'webspeech' | 'elevenlabs' | 'piper' | 'coqui'

export interface TTSConfig {
  backend: TTSBackend
  enabled: boolean
  volume: number          // 0-1
  rate: number            // 0.5-2
  pitch: number           // 0.5-2
  voice: string           // Voice ID
  elevenLabsApiKey?: string
  elevenLabsVoiceId?: string
  piperModelPath?: string
}

export interface SpeechQueueItem {
  id: string
  text: string
  priority: 'low' | 'normal' | 'high' | 'interrupt'
  emotion?: 'neutral' | 'happy' | 'thoughtful' | 'flirty' | 'serious'
  onStart?: () => void
  onEnd?: () => void
}

// ============================================================================
// CONSTANTS
// ============================================================================

// macOS voices ranked by masculinity/depth
const MACOS_MALE_VOICES = [
  { id: 'Daniel', accent: 'British', depth: 'deep', quality: 'premium' },
  { id: 'Alex', accent: 'American', depth: 'medium', quality: 'premium' },
  { id: 'Tom', accent: 'American', depth: 'deep', quality: 'enhanced' },
  { id: 'Oliver', accent: 'British', depth: 'medium', quality: 'enhanced' },
  { id: 'Fred', accent: 'American', depth: 'deep', quality: 'standard' },
  { id: 'Ralph', accent: 'American', depth: 'very-deep', quality: 'standard' }
]

// Eleven Labs voice IDs for masculine voices
const ELEVEN_LABS_VOICES = {
  adam: 'pNInz6obpgDQGcFmaJgB',      // Deep, authoritative
  antoni: 'ErXwobaYiN019PkySvjV',    // Well-rounded
  arnold: '5Q0t7uMcjvnagumLfvZi',    // Crisp, professional
  josh: 'TxGEqnHWrfWFTfGW9XjX',      // Deep, narrative
  sam: 'yoZ06aMxZJJ28mfd3POQ'        // Raspy, masculine
}

const STORAGE_KEY = 'warp_tts_config'

// ============================================================================
// COMPOSABLE
// ============================================================================

function loadConfig(): TTSConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch {}
  return {
    backend: 'macos',
    enabled: true,
    volume: 0.8,
    rate: 0.95,
    pitch: 0.85,  // Slightly lower for masculine
    voice: 'Daniel'
  }
}

function saveConfig(config: TTSConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

export function useTTS() {
  const config = ref<TTSConfig>(loadConfig())
  const personality = usePersonality()

  const isSpeaking = ref(false)
  const isPaused = ref(false)
  const currentUtterance = ref<string | null>(null)
  const speechQueue = ref<SpeechQueueItem[]>([])

  // WebSpeech synthesis reference
  let synthesis: SpeechSynthesis | null = null
  let currentSpeechUtterance: SpeechSynthesisUtterance | null = null

  // Audio element for Eleven Labs
  let audioElement: HTMLAudioElement | null = null

  // Initialize WebSpeech if available
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    synthesis = window.speechSynthesis
  }

  // ========================================================================
  // MACOS BACKEND
  // ========================================================================

  async function speakMacOS(text: string, emotion?: string): Promise<void> {
    const voice = config.value.voice || 'Daniel'
    const rate = Math.round(config.value.rate * 175) // macOS rate is words per minute

    // Apply emotion modifiers
    let modifiedRate = rate
    let modifiedText = text

    switch (emotion) {
      case 'thoughtful':
        modifiedRate = rate * 0.9
        modifiedText = text.replace(/\.\.\./g, '... ... ')
        break
      case 'flirty':
        modifiedRate = rate * 0.85
        break
      case 'happy':
        modifiedRate = rate * 1.05
        break
      case 'serious':
        modifiedRate = rate * 0.95
        break
    }

    // Escape text for shell
    const escapedText = modifiedText.replace(/"/g, '\\"').replace(/`/g, '\\`')

    try {
      await invoke('execute_shell', {
        command: `say -v "${voice}" -r ${modifiedRate} "${escapedText}"`,
        cwd: undefined
      })
    } catch (error) {
      console.error('[TTS] macOS speak failed:', error)
    }
  }

  // ========================================================================
  // WEB SPEECH BACKEND
  // ========================================================================

  async function speakWebSpeech(text: string, emotion?: string): Promise<void> {
    if (!synthesis) {
      console.warn('[TTS] Web Speech API not available')
      return
    }

    return new Promise((resolve, reject) => {
      const utterance = new SpeechSynthesisUtterance(text)

      // Find a deep male voice
      const voices = synthesis!.getVoices()
      const maleVoice = voices.find(v =>
        v.name.toLowerCase().includes('daniel') ||
        v.name.toLowerCase().includes('alex') ||
        v.name.toLowerCase().includes('male')
      ) || voices.find(v => v.lang.startsWith('en'))

      if (maleVoice) {
        utterance.voice = maleVoice
      }

      utterance.volume = config.value.volume
      utterance.rate = config.value.rate
      utterance.pitch = config.value.pitch

      // Emotion adjustments
      switch (emotion) {
        case 'thoughtful':
          utterance.rate *= 0.9
          break
        case 'flirty':
          utterance.rate *= 0.85
          utterance.pitch *= 0.95
          break
      }

      currentSpeechUtterance = utterance

      utterance.onend = () => {
        currentSpeechUtterance = null
        resolve()
      }

      utterance.onerror = (event) => {
        currentSpeechUtterance = null
        reject(event)
      }

      synthesis!.speak(utterance)
    })
  }

  // ========================================================================
  // ELEVEN LABS BACKEND
  // ========================================================================

  async function speakElevenLabs(text: string, emotion?: string): Promise<void> {
    const apiKey = config.value.elevenLabsApiKey
    const voiceId = config.value.elevenLabsVoiceId || ELEVEN_LABS_VOICES.adam

    if (!apiKey) {
      console.warn('[TTS] Eleven Labs API key not configured')
      return speakMacOS(text, emotion) // Fallback
    }

    try {
      const response = await fetch(
        `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
        {
          method: 'POST',
          headers: {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': apiKey
          },
          body: JSON.stringify({
            text,
            model_id: 'eleven_monolingual_v1',
            voice_settings: {
              stability: 0.75,
              similarity_boost: 0.85,
              style: emotion === 'flirty' ? 0.75 : 0.5,
              use_speaker_boost: true
            }
          })
        }
      )

      if (!response.ok) {
        throw new Error(`Eleven Labs API error: ${response.status}`)
      }

      const audioBlob = await response.blob()
      const audioUrl = URL.createObjectURL(audioBlob)

      return new Promise((resolve, reject) => {
        if (!audioElement) {
          audioElement = new Audio()
        }

        audioElement.src = audioUrl
        audioElement.volume = config.value.volume

        audioElement.onended = () => {
          URL.revokeObjectURL(audioUrl)
          resolve()
        }

        audioElement.onerror = (error) => {
          URL.revokeObjectURL(audioUrl)
          reject(error)
        }

        audioElement.play()
      })
    } catch (error) {
      console.error('[TTS] Eleven Labs failed:', error)
      return speakMacOS(text, emotion) // Fallback
    }
  }

  // ========================================================================
  // MAIN SPEAK FUNCTION
  // ========================================================================

  /**
   * Speak text using configured backend
   */
  async function speak(
    text: string,
    options?: {
      emotion?: SpeechQueueItem['emotion']
      priority?: SpeechQueueItem['priority']
      skipQueue?: boolean
    }
  ): Promise<void> {
    if (!config.value.enabled) return

    const priority = options?.priority || 'normal'
    const emotion = options?.emotion || 'neutral'

    // Handle interrupt priority
    if (priority === 'interrupt') {
      stop()
    }

    // Add to queue or speak directly
    if (!options?.skipQueue && isSpeaking.value && priority !== 'interrupt') {
      speechQueue.value.push({
        id: Date.now().toString(),
        text,
        priority,
        emotion
      })

      // Sort queue by priority
      speechQueue.value.sort((a, b) => {
        const priorityOrder = { high: 0, normal: 1, low: 2, interrupt: -1 }
        return priorityOrder[a.priority] - priorityOrder[b.priority]
      })

      return
    }

    isSpeaking.value = true
    currentUtterance.value = text

    try {
      // Clean text for speech
      const cleanedText = cleanTextForSpeech(text)

      switch (config.value.backend) {
        case 'macos':
          await speakMacOS(cleanedText, emotion)
          break
        case 'webspeech':
          await speakWebSpeech(cleanedText, emotion)
          break
        case 'elevenlabs':
          await speakElevenLabs(cleanedText, emotion)
          break
        default:
          await speakMacOS(cleanedText, emotion)
      }
    } catch (error) {
      console.error('[TTS] Speak failed:', error)
    } finally {
      isSpeaking.value = false
      currentUtterance.value = null

      // Process queue
      if (speechQueue.value.length > 0) {
        const next = speechQueue.value.shift()!
        speak(next.text, { emotion: next.emotion, skipQueue: true })
      }
    }
  }

  /**
   * Clean text for better speech output
   */
  function cleanTextForSpeech(text: string): string {
    return text
      // Remove markdown
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/`/g, '')
      .replace(/#{1,6}\s/g, '')
      // Convert code blocks to spoken description
      .replace(/```[\s\S]*?```/g, '(code block)')
      // Handle ellipsis for dramatic pause
      .replace(/\.\.\./g, '... ')
      // Remove URLs
      .replace(/https?:\/\/[^\s]+/g, 'link')
      // Handle emojis - convert common ones to words
      .replace(/😊/g, '')
      .replace(/👍/g, 'thumbs up')
      .replace(/🤖/g, '')
      // Clean up extra whitespace
      .replace(/\s+/g, ' ')
      .trim()
  }

  /**
   * Stop speaking
   */
  function stop(): void {
    if (config.value.backend === 'webspeech' && synthesis) {
      synthesis.cancel()
    }

    if (audioElement) {
      audioElement.pause()
      audioElement.currentTime = 0
    }

    // For macOS, we can't easily stop mid-speech, but we can kill the process
    invoke('execute_shell', {
      command: 'pkill -f "say -v"',
      cwd: undefined
    }).catch(() => {})

    isSpeaking.value = false
    currentUtterance.value = null
    speechQueue.value = []
  }

  /**
   * Pause speaking (WebSpeech only)
   */
  function pause(): void {
    if (config.value.backend === 'webspeech' && synthesis) {
      synthesis.pause()
      isPaused.value = true
    }

    if (audioElement) {
      audioElement.pause()
      isPaused.value = true
    }
  }

  /**
   * Resume speaking
   */
  function resume(): void {
    if (config.value.backend === 'webspeech' && synthesis) {
      synthesis.resume()
      isPaused.value = false
    }

    if (audioElement) {
      audioElement.play()
      isPaused.value = false
    }
  }

  /**
   * Set backend
   */
  function setBackend(backend: TTSBackend): void {
    config.value.backend = backend
    saveConfig(config.value)
  }

  /**
   * Set voice
   */
  function setVoice(voiceId: string): void {
    config.value.voice = voiceId
    saveConfig(config.value)
  }

  /**
   * Set Eleven Labs credentials
   */
  function setElevenLabs(apiKey: string, voiceId?: string): void {
    config.value.elevenLabsApiKey = apiKey
    config.value.elevenLabsVoiceId = voiceId || ELEVEN_LABS_VOICES.adam
    saveConfig(config.value)
  }

  /**
   * Toggle TTS on/off
   */
  function toggle(): void {
    config.value.enabled = !config.value.enabled
    if (!config.value.enabled) {
      stop()
    }
    saveConfig(config.value)
  }

  /**
   * Get available voices for current backend
   */
  const availableVoices = computed(() => {
    switch (config.value.backend) {
      case 'macos':
        return MACOS_MALE_VOICES
      case 'elevenlabs':
        return Object.entries(ELEVEN_LABS_VOICES).map(([name, id]) => ({
          id,
          name,
          accent: 'American',
          depth: 'deep',
          quality: 'premium'
        }))
      case 'webspeech':
        if (synthesis) {
          return synthesis.getVoices()
            .filter(v => v.lang.startsWith('en'))
            .map(v => ({
              id: v.name,
              name: v.name,
              accent: v.lang,
              depth: 'unknown',
              quality: 'standard'
            }))
        }
        return []
      default:
        return MACOS_MALE_VOICES
    }
  })

  /**
   * Speak with personality context
   */
  async function speakWithPersonality(
    text: string,
    context?: {
      isGreeting?: boolean
      isCompletion?: boolean
      isFlirty?: boolean
    }
  ): Promise<void> {
    let emotion: SpeechQueueItem['emotion'] = 'neutral'

    if (context?.isFlirty) {
      emotion = 'flirty'
    } else if (context?.isGreeting) {
      emotion = 'happy'
    } else if (context?.isCompletion) {
      emotion = 'neutral'
    }

    await speak(text, { emotion })
  }

  // Save config when it changes
  watch(config, () => saveConfig(config.value), { deep: true })

  return {
    // State
    config,
    isSpeaking,
    isPaused,
    currentUtterance,
    speechQueue,
    availableVoices,

    // Methods
    speak,
    speakWithPersonality,
    stop,
    pause,
    resume,
    toggle,
    setBackend,
    setVoice,
    setElevenLabs,
    cleanTextForSpeech,

    // Constants
    MACOS_MALE_VOICES,
    ELEVEN_LABS_VOICES
  }
}

export type UseTTSReturn = ReturnType<typeof useTTS>
