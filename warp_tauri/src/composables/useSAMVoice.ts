/**
 * SAM Voice Synthesis System
 *
 * Gives SAM a voice. Multiple options:
 * 1. System TTS (free, works offline)
 * 2. ElevenLabs (neural, paid)
 * 3. OpenAI TTS (neural, paid)
 * 4. Local neural TTS (Coqui, Piper)
 */

import { ref, computed, watch } from 'vue'

// ============================================================================
// Types
// ============================================================================

export type VoiceProvider = 'system' | 'elevenlabs' | 'openai' | 'coqui' | 'piper'

export interface VoiceSettings {
  provider: VoiceProvider
  enabled: boolean
  volume: number // 0-1
  rate: number // 0.5-2
  pitch: number // 0.5-2

  // Provider-specific
  systemVoice?: string // System TTS voice name
  elevenLabsVoiceId?: string
  elevenLabsApiKey?: string
  openaiVoice?: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer'
  openaiApiKey?: string

  // Local neural
  coquiModel?: string
  piperModel?: string
}

export interface VoiceState {
  isSpeaking: boolean
  isPaused: boolean
  currentText: string
  queue: string[]
}

// ============================================================================
// Composable
// ============================================================================

export function useSAMVoice() {
  // Settings
  const settings = ref<VoiceSettings>({
    provider: 'system',
    enabled: true,
    volume: 0.8,
    rate: 1.0,
    pitch: 1.0,
    systemVoice: undefined, // Will auto-select
    openaiVoice: 'onyx' // Deep male voice
  })

  // State
  const state = ref<VoiceState>({
    isSpeaking: false,
    isPaused: false,
    currentText: '',
    queue: []
  })

  // Available voices
  const availableVoices = ref<SpeechSynthesisVoice[]>([])

  // System TTS
  let synth: SpeechSynthesis | null = null
  let currentUtterance: SpeechSynthesisUtterance | null = null

  // Audio element for neural TTS
  let audioElement: HTMLAudioElement | null = null

  // ============================================================================
  // Initialization
  // ============================================================================

  function initialize(): void {
    // Check for Web Speech API
    if ('speechSynthesis' in window) {
      synth = window.speechSynthesis

      // Load voices
      const loadVoices = () => {
        availableVoices.value = synth!.getVoices()

        // Auto-select a good male voice for macOS
        if (!settings.value.systemVoice) {
          const preferredVoices = [
            'Daniel', // British male
            'Alex',   // American male
            'Tom',    // American male
            'Aaron',  // American male (neural)
          ]

          for (const preferred of preferredVoices) {
            const voice = availableVoices.value.find(v =>
              v.name.includes(preferred)
            )
            if (voice) {
              settings.value.systemVoice = voice.name
              break
            }
          }
        }

        console.log(`[SAM Voice] Loaded ${availableVoices.value.length} voices`)
      }

      // Voices may load asynchronously
      if (synth.getVoices().length > 0) {
        loadVoices()
      } else {
        synth.addEventListener('voiceschanged', loadVoices)
      }
    }

    // Create audio element for neural TTS
    audioElement = new Audio()
    audioElement.addEventListener('ended', () => {
      state.value.isSpeaking = false
      processQueue()
    })
    audioElement.addEventListener('error', (e) => {
      console.error('[SAM Voice] Audio error:', e)
      state.value.isSpeaking = false
      processQueue()
    })

    // Load saved settings
    loadSettings()
  }

  // ============================================================================
  // Core Speech Functions
  // ============================================================================

  /**
   * Speak text using configured provider
   */
  async function speak(text: string, immediate: boolean = false): Promise<void> {
    if (!settings.value.enabled) return

    // Clean up text for speech
    const cleanText = cleanForSpeech(text)
    if (!cleanText) return

    if (immediate) {
      // Stop current speech and speak immediately
      stop()
      state.value.queue = []
    }

    if (state.value.isSpeaking && !immediate) {
      // Queue the text
      state.value.queue.push(cleanText)
      return
    }

    state.value.isSpeaking = true
    state.value.currentText = cleanText

    try {
      switch (settings.value.provider) {
        case 'system':
          await speakWithSystem(cleanText)
          break
        case 'elevenlabs':
          await speakWithElevenLabs(cleanText)
          break
        case 'openai':
          await speakWithOpenAI(cleanText)
          break
        case 'coqui':
        case 'piper':
          await speakWithLocal(cleanText)
          break
        default:
          await speakWithSystem(cleanText)
      }
    } catch (error) {
      console.error('[SAM Voice] Speech error:', error)
      state.value.isSpeaking = false
      // Fall back to system TTS on error
      if (settings.value.provider !== 'system') {
        await speakWithSystem(cleanText)
      }
    }
  }

  /**
   * System TTS (Web Speech API)
   */
  function speakWithSystem(text: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!synth) {
        reject(new Error('Speech synthesis not available'))
        return
      }

      const utterance = new SpeechSynthesisUtterance(text)

      // Find voice
      if (settings.value.systemVoice) {
        const voice = availableVoices.value.find(v =>
          v.name === settings.value.systemVoice
        )
        if (voice) utterance.voice = voice
      }

      utterance.volume = settings.value.volume
      utterance.rate = settings.value.rate
      utterance.pitch = settings.value.pitch

      utterance.onend = () => {
        state.value.isSpeaking = false
        currentUtterance = null
        processQueue()
        resolve()
      }

      utterance.onerror = (e) => {
        state.value.isSpeaking = false
        currentUtterance = null
        reject(e)
      }

      currentUtterance = utterance
      synth.speak(utterance)
    })
  }

  /**
   * ElevenLabs TTS
   */
  async function speakWithElevenLabs(text: string): Promise<void> {
    const apiKey = settings.value.elevenLabsApiKey
    const voiceId = settings.value.elevenLabsVoiceId || 'pNInz6obpgDQGcFmaJgB' // Default: Adam

    if (!apiKey) {
      console.warn('[SAM Voice] ElevenLabs API key not set, falling back to system')
      return speakWithSystem(text)
    }

    const response = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'xi-api-key': apiKey
        },
        body: JSON.stringify({
          text,
          model_id: 'eleven_monolingual_v1',
          voice_settings: {
            stability: 0.5,
            similarity_boost: 0.75
          }
        })
      }
    )

    if (!response.ok) {
      throw new Error(`ElevenLabs error: ${response.status}`)
    }

    const audioBlob = await response.blob()
    const audioUrl = URL.createObjectURL(audioBlob)

    return playAudio(audioUrl)
  }

  /**
   * OpenAI TTS
   */
  async function speakWithOpenAI(text: string): Promise<void> {
    const apiKey = settings.value.openaiApiKey

    if (!apiKey) {
      console.warn('[SAM Voice] OpenAI API key not set, falling back to system')
      return speakWithSystem(text)
    }

    const response = await fetch('https://api.openai.com/v1/audio/speech', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'tts-1-hd',
        voice: settings.value.openaiVoice || 'onyx',
        input: text,
        speed: settings.value.rate
      })
    })

    if (!response.ok) {
      throw new Error(`OpenAI error: ${response.status}`)
    }

    const audioBlob = await response.blob()
    const audioUrl = URL.createObjectURL(audioBlob)

    return playAudio(audioUrl)
  }

  /**
   * Local neural TTS (Coqui/Piper via local server)
   */
  async function speakWithLocal(text: string): Promise<void> {
    // Assumes a local TTS server running on port 5002
    const endpoint = settings.value.provider === 'coqui'
      ? 'http://localhost:5002/api/tts'
      : 'http://localhost:5003/api/tts'

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          speaker_id: 'male_1',
          language_id: 'en'
        })
      })

      if (!response.ok) throw new Error('Local TTS error')

      const audioBlob = await response.blob()
      const audioUrl = URL.createObjectURL(audioBlob)
      return playAudio(audioUrl)
    } catch {
      console.warn('[SAM Voice] Local TTS not available, falling back to system')
      return speakWithSystem(text)
    }
  }

  /**
   * Play audio from URL
   */
  function playAudio(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!audioElement) {
        reject(new Error('Audio element not initialized'))
        return
      }

      audioElement.src = url
      audioElement.volume = settings.value.volume

      audioElement.onended = () => {
        URL.revokeObjectURL(url)
        state.value.isSpeaking = false
        processQueue()
        resolve()
      }

      audioElement.onerror = (e) => {
        URL.revokeObjectURL(url)
        state.value.isSpeaking = false
        reject(e)
      }

      audioElement.play()
    })
  }

  // ============================================================================
  // Control Functions
  // ============================================================================

  /**
   * Stop speaking
   */
  function stop(): void {
    if (synth && currentUtterance) {
      synth.cancel()
    }
    if (audioElement) {
      audioElement.pause()
      audioElement.currentTime = 0
    }
    state.value.isSpeaking = false
    state.value.isPaused = false
    currentUtterance = null
  }

  /**
   * Pause speaking
   */
  function pause(): void {
    if (synth && state.value.isSpeaking) {
      synth.pause()
      state.value.isPaused = true
    }
    if (audioElement && state.value.isSpeaking) {
      audioElement.pause()
      state.value.isPaused = true
    }
  }

  /**
   * Resume speaking
   */
  function resume(): void {
    if (synth && state.value.isPaused) {
      synth.resume()
      state.value.isPaused = false
    }
    if (audioElement && state.value.isPaused) {
      audioElement.play()
      state.value.isPaused = false
    }
  }

  /**
   * Toggle mute
   */
  function toggleMute(): void {
    settings.value.enabled = !settings.value.enabled
    if (!settings.value.enabled) {
      stop()
    }
    saveSettings()
  }

  /**
   * Process speech queue
   */
  function processQueue(): void {
    if (state.value.queue.length > 0 && !state.value.isSpeaking) {
      const next = state.value.queue.shift()!
      speak(next)
    }
  }

  /**
   * Clear queue
   */
  function clearQueue(): void {
    state.value.queue = []
  }

  // ============================================================================
  // Text Processing
  // ============================================================================

  /**
   * Clean text for speech
   */
  function cleanForSpeech(text: string): string {
    return text
      // Remove markdown
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/_(.+?)_/g, '$1')
      .replace(/`(.+?)`/g, '$1')
      .replace(/```[\s\S]*?```/g, '')
      // Remove code blocks entirely (don't read code)
      .replace(/```[\s\S]*?```/g, 'code block')
      // Remove URLs
      .replace(/https?:\/\/\S+/g, 'link')
      // Remove emojis for cleaner speech (optional)
      // .replace(/[\u{1F600}-\u{1F6FF}]/gu, '')
      // Clean up whitespace
      .replace(/\s+/g, ' ')
      .trim()
  }

  /**
   * Split long text into chunks for better speech
   */
  function splitForSpeech(text: string, maxLength: number = 200): string[] {
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text]
    const chunks: string[] = []
    let current = ''

    for (const sentence of sentences) {
      if ((current + sentence).length > maxLength) {
        if (current) chunks.push(current.trim())
        current = sentence
      } else {
        current += sentence
      }
    }

    if (current) chunks.push(current.trim())

    return chunks
  }

  // ============================================================================
  // Settings
  // ============================================================================

  function saveSettings(): void {
    // Don't save API keys to localStorage in production!
    const toSave = { ...settings.value }
    delete toSave.elevenLabsApiKey
    delete toSave.openaiApiKey

    localStorage.setItem('sam_voice_settings', JSON.stringify(toSave))
  }

  function loadSettings(): void {
    const saved = localStorage.getItem('sam_voice_settings')
    if (saved) {
      settings.value = { ...settings.value, ...JSON.parse(saved) }
    }
  }

  function setProvider(provider: VoiceProvider): void {
    settings.value.provider = provider
    saveSettings()
  }

  function setVoice(voiceName: string): void {
    settings.value.systemVoice = voiceName
    saveSettings()
  }

  function setVolume(volume: number): void {
    settings.value.volume = Math.max(0, Math.min(1, volume))
    saveSettings()
  }

  function setRate(rate: number): void {
    settings.value.rate = Math.max(0.5, Math.min(2, rate))
    saveSettings()
  }

  // ============================================================================
  // Computed
  // ============================================================================

  const isEnabled = computed(() => settings.value.enabled)
  const isSpeaking = computed(() => state.value.isSpeaking)
  const currentProvider = computed(() => settings.value.provider)

  const maleVoices = computed(() =>
    availableVoices.value.filter(v =>
      v.name.includes('Male') ||
      ['Daniel', 'Alex', 'Tom', 'Aaron', 'Gordon', 'Fred'].some(n => v.name.includes(n))
    )
  )

  // ============================================================================
  // Initialize
  // ============================================================================

  initialize()

  return {
    // Settings
    settings,
    availableVoices,

    // State
    state,
    isEnabled,
    isSpeaking,
    currentProvider,
    maleVoices,

    // Core
    speak,
    stop,
    pause,
    resume,
    toggleMute,
    clearQueue,

    // Settings
    setProvider,
    setVoice,
    setVolume,
    setRate,
    saveSettings,

    // Utilities
    cleanForSpeech,
    splitForSpeech
  }
}

export type SAMVoice = ReturnType<typeof useSAMVoice>
