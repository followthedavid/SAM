/**
 * useCognitiveAPI - Connect to SAM's Cognitive Python Backend
 *
 * Connects to the cognitive orchestrator running at sam_api.py via HTTP.
 * Provides:
 * - Text processing with confidence scores
 * - Streaming responses via Server-Sent Events
 * - Vision/image understanding
 * - Mood and emotional state
 * - Learning and feedback
 */

import { ref, computed, reactive } from 'vue'

// =============================================================================
// TYPES
// =============================================================================

export interface CognitiveConfig {
  baseUrl: string
  userId: string
  timeout: number
}

export interface CognitiveResponse {
  response: string
  confidence: number
  mood: string
  model_used: string | null
  escalated: boolean
  processing_time_ms?: number
}

export interface CognitiveState {
  cognitive: {
    current_state: string
    confidence: number
    goals: string[]
    memory_pressure: number
  }
  emotional: {
    mood: string
    valence: number
    arousal: number
    energy: number
  }
  learning: {
    recent_topics: string[]
    adaptation_score: number
  }
}

export interface CognitiveMood {
  mood: string
  valence: number
  arousal: number
  energy: number
  influences: string[]
}

export interface VisionResponse {
  response: string
  confidence: number
  model_used: string
  objects_detected?: string[]
  escalated: boolean
}

export interface StreamToken {
  token?: string
  done?: boolean
  response?: string
  confidence?: number
  error?: string
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useCognitiveAPI(config?: Partial<CognitiveConfig>) {
  // Default configuration
  const settings = reactive<CognitiveConfig>({
    baseUrl: config?.baseUrl || 'http://localhost:8765',
    userId: config?.userId || 'default',
    timeout: config?.timeout || 120000  // 2 minutes for cold starts
  })

  // State
  const isProcessing = ref(false)
  const isStreaming = ref(false)
  const lastResponse = ref<CognitiveResponse | null>(null)
  const currentMood = ref<CognitiveMood | null>(null)
  const systemState = ref<CognitiveState | null>(null)
  const error = ref<string | null>(null)
  const streamBuffer = ref<string>('')

  // Connection state
  const isConnected = ref(false)
  const lastPingMs = ref<number | null>(null)

  // ==========================================================================
  // HELPERS
  // ==========================================================================

  async function fetchWithTimeout<T>(
    url: string,
    options: RequestInit = {},
    timeout = settings.timeout
  ): Promise<T> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    } finally {
      clearTimeout(timeoutId)
    }
  }

  // ==========================================================================
  // CONNECTION
  // ==========================================================================

  async function ping(): Promise<boolean> {
    const start = Date.now()
    try {
      await fetchWithTimeout<{ status: string }>(
        `${settings.baseUrl}/api/health`,
        {},
        5000
      )
      lastPingMs.value = Date.now() - start
      isConnected.value = true
      return true
    } catch (e) {
      isConnected.value = false
      lastPingMs.value = null
      return false
    }
  }

  // ==========================================================================
  // TEXT PROCESSING
  // ==========================================================================

  /**
   * Process a text query through the cognitive system
   */
  async function process(query: string): Promise<CognitiveResponse | null> {
    if (isProcessing.value) {
      error.value = 'Already processing a request'
      return null
    }

    isProcessing.value = true
    error.value = null

    try {
      const result = await fetchWithTimeout<CognitiveResponse>(
        `${settings.baseUrl}/api/cognitive/process`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            user_id: settings.userId
          })
        }
      )

      lastResponse.value = result
      return result

    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * Stream a response token-by-token via SSE
   */
  function stream(
    query: string,
    onToken: (token: string) => void,
    onComplete?: (response: CognitiveResponse) => void,
    onError?: (error: string) => void
  ): () => void {
    if (isStreaming.value) {
      onError?.('Already streaming')
      return () => {}
    }

    isStreaming.value = true
    streamBuffer.value = ''
    error.value = null

    // Build SSE URL with query params
    const url = new URL(`${settings.baseUrl}/api/cognitive/stream`)
    url.searchParams.set('query', query)
    url.searchParams.set('user_id', settings.userId)

    const eventSource = new EventSource(url.toString())

    eventSource.onmessage = (event) => {
      try {
        const data: StreamToken = JSON.parse(event.data)

        if (data.error) {
          error.value = data.error
          onError?.(data.error)
          eventSource.close()
          isStreaming.value = false
          return
        }

        if (data.token) {
          streamBuffer.value += data.token
          onToken(data.token)
        }

        if (data.done) {
          const finalResponse: CognitiveResponse = {
            response: data.response || streamBuffer.value,
            confidence: data.confidence || 0.75,
            mood: currentMood.value?.mood || 'neutral',
            model_used: null,
            escalated: false
          }
          lastResponse.value = finalResponse
          onComplete?.(finalResponse)
          eventSource.close()
          isStreaming.value = false
        }
      } catch (e) {
        console.error('[CognitiveAPI] Parse error:', e)
      }
    }

    eventSource.onerror = (e) => {
      const errMsg = 'Stream connection error'
      error.value = errMsg
      onError?.(errMsg)
      eventSource.close()
      isStreaming.value = false
    }

    // Return cleanup function
    return () => {
      eventSource.close()
      isStreaming.value = false
    }
  }

  // ==========================================================================
  // VISION
  // ==========================================================================

  /**
   * Process an image with a query
   */
  async function processImage(
    imagePath: string,
    query: string = 'Describe this image'
  ): Promise<VisionResponse | null> {
    isProcessing.value = true
    error.value = null

    try {
      const result = await fetchWithTimeout<VisionResponse>(
        `${settings.baseUrl}/api/vision/process`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_path: imagePath,
            query,
            user_id: settings.userId
          })
        }
      )
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * Get a description of an image
   */
  async function describeImage(imagePath: string): Promise<string | null> {
    isProcessing.value = true
    error.value = null

    try {
      const result = await fetchWithTimeout<{ description: string; confidence: number }>(
        `${settings.baseUrl}/api/vision/describe`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_path: imagePath,
            user_id: settings.userId
          })
        }
      )
      return result.description
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * Detect objects in an image
   */
  async function detectObjects(imagePath: string): Promise<string[] | null> {
    isProcessing.value = true
    error.value = null

    try {
      const result = await fetchWithTimeout<{ objects: string[]; confidence: number }>(
        `${settings.baseUrl}/api/vision/detect`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_path: imagePath,
            user_id: settings.userId
          })
        }
      )
      return result.objects
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    } finally {
      isProcessing.value = false
    }
  }

  // ==========================================================================
  // STATE & MOOD
  // ==========================================================================

  /**
   * Get the current cognitive system state
   */
  async function getState(): Promise<CognitiveState | null> {
    try {
      const result = await fetchWithTimeout<CognitiveState>(
        `${settings.baseUrl}/api/cognitive/state`,
        {},
        10000
      )
      systemState.value = result
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    }
  }

  /**
   * Get the current emotional/mood state
   */
  async function getMood(): Promise<CognitiveMood | null> {
    try {
      const result = await fetchWithTimeout<CognitiveMood>(
        `${settings.baseUrl}/api/cognitive/mood`,
        {},
        10000
      )
      currentMood.value = result
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    }
  }

  // ==========================================================================
  // LEARNING & FEEDBACK
  // ==========================================================================

  /**
   * Submit feedback on a response
   */
  async function submitFeedback(
    responseId: string,
    helpful: boolean,
    comment?: string
  ): Promise<boolean> {
    try {
      await fetchWithTimeout<{ success: boolean }>(
        `${settings.baseUrl}/api/cognitive/feedback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: responseId,
            helpful,
            comment,
            user_id: settings.userId
          })
        }
      )
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    }
  }

  // ==========================================================================
  // VOICE (if voice bridge is available)
  // ==========================================================================

  /**
   * Generate a voice response (text + audio)
   */
  async function speak(query: string): Promise<{ text: string; audioUrl: string } | null> {
    isProcessing.value = true
    error.value = null

    try {
      const result = await fetchWithTimeout<{ text: string; audio_url: string }>(
        `${settings.baseUrl}/api/cognitive/speak`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            user_id: settings.userId
          })
        }
      )
      return { text: result.text, audioUrl: result.audio_url }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    } finally {
      isProcessing.value = false
    }
  }

  // ==========================================================================
  // COMPUTED
  // ==========================================================================

  const isReady = computed(() => isConnected.value && !isProcessing.value && !isStreaming.value)
  const confidenceLevel = computed(() => {
    const conf = lastResponse.value?.confidence || 0
    if (conf >= 0.8) return 'high'
    if (conf >= 0.5) return 'medium'
    return 'low'
  })

  // ==========================================================================
  // RETURN
  // ==========================================================================

  return {
    // Configuration
    settings,

    // State
    isProcessing,
    isStreaming,
    isConnected,
    isReady,
    lastResponse,
    currentMood,
    systemState,
    error,
    streamBuffer,
    lastPingMs,

    // Computed
    confidenceLevel,

    // Connection
    ping,

    // Text processing
    process,
    stream,

    // Vision
    processImage,
    describeImage,
    detectObjects,

    // State & Mood
    getState,
    getMood,

    // Learning
    submitFeedback,

    // Voice
    speak
  }
}

// =============================================================================
// SINGLETON
// =============================================================================

let globalCognitiveAPI: ReturnType<typeof useCognitiveAPI> | null = null

export function getCognitiveAPI(config?: Partial<CognitiveConfig>): ReturnType<typeof useCognitiveAPI> {
  if (!globalCognitiveAPI) {
    globalCognitiveAPI = useCognitiveAPI(config)
  }
  return globalCognitiveAPI
}
