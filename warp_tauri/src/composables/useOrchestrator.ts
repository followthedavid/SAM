/**
 * useOrchestrator - Central AI routing through Rust backend
 *
 * Connects to the Rust orchestrator which routes requests through:
 * 1. Deterministic path (instant, no AI)
 * 2. Embedding search (semantic search)
 * 3. Template fill (minimal AI)
 * 4. Micro model (1.5b + tools)
 * 5. Full model (8b + multi-turn)
 */

import { ref, computed, reactive } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { listen } from '@tauri-apps/api/event'

// =============================================================================
// TYPES
// =============================================================================

export interface OrchestratorContext {
  workingDirectory: string
  sessionId: string
  maxTokens: number
  stream: boolean
  conversationHistory: ConversationTurn[]
}

export interface ConversationTurn {
  role: 'user' | 'assistant'
  content: string
}

export type OrchestratorResultType = 'instant' | 'search' | 'generated' | 'error'

export interface InstantResult {
  output: string
  taskType: string
  latencyMs: number
}

export interface SearchResult {
  chunks: CodeSearchHit[]
  query: string
  latencyMs: number
}

export interface CodeSearchHit {
  filePath: string
  content: string
  lineStart: number
  relevanceScore: number
}

export interface GeneratedResult {
  content: string
  modelUsed: string
  toolCalls: ToolCallRecord[]
  tokensUsed: number
  latencyMs: number
}

export interface ToolCallRecord {
  tool: string
  args: Record<string, unknown>
  result: string
  success: boolean
}

export interface ErrorResult {
  message: string
  pathAttempted: string
  recoverable: boolean
}

export interface OrchestratorResponse {
  type: OrchestratorResultType
  instant?: InstantResult
  search?: SearchResult
  generated?: GeneratedResult
  error?: ErrorResult
}

export interface RoutingDecision {
  requestType: string
  processingPath: string
  modelRecommendation: string | null
  templateName: string | null
  confidence: number
  reasoning: string
}

export interface OrchestratorStats {
  orchestrator: {
    totalRequests: number
    instantCount: number
    searchCount: number
    generatedCount: number
    errorCount: number
    avgLatencies: {
      instant: number
      search: number
      generated: number
    }
  }
  routing: {
    total: number
    deterministic: number
    template: number
    embedding: number
    microModel: number
    fullModel: number
    aiAvoidanceRate: number
    lightAiRate: number
  }
  models: Record<string, unknown>
  embeddings: Record<string, unknown>
}

export interface OrchestratorMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: number
  resultType?: OrchestratorResultType
  searchResults?: CodeSearchHit[]
  toolCalls?: ToolCallRecord[]
  latencyMs?: number
  processingPath?: string
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useOrchestrator() {
  // State
  const messages = ref<OrchestratorMessage[]>([])
  const isProcessing = ref(false)
  const currentPath = ref<string | null>(null)
  const lastDecision = ref<RoutingDecision | null>(null)
  const error = ref<string | null>(null)
  const stats = reactive<OrchestratorStats>({
    orchestrator: {
      totalRequests: 0,
      instantCount: 0,
      searchCount: 0,
      generatedCount: 0,
      errorCount: 0,
      avgLatencies: { instant: 0, search: 0, generated: 0 }
    },
    routing: {
      total: 0,
      deterministic: 0,
      template: 0,
      embedding: 0,
      microModel: 0,
      fullModel: 0,
      aiAvoidanceRate: 0,
      lightAiRate: 0
    },
    models: {},
    embeddings: {}
  })

  // Context
  const context = ref<OrchestratorContext>({
    workingDirectory: '.',
    sessionId: `session_${Date.now()}`,
    maxTokens: 2048,
    stream: false,
    conversationHistory: []
  })

  // Computed
  const messageCount = computed(() => messages.value.length)
  const aiAvoidanceRate = computed(() => stats.routing.aiAvoidanceRate * 100)
  const avgLatency = computed(() => {
    const s = stats.orchestrator
    const total = s.instantCount + s.searchCount + s.generatedCount
    if (total === 0) return 0
    return (
      s.avgLatencies.instant * s.instantCount +
      s.avgLatencies.search * s.searchCount +
      s.avgLatencies.generated * s.generatedCount
    ) / total
  })

  // ==========================================================================
  // HELPERS
  // ==========================================================================

  function genId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }

  function addMessage(msg: Omit<OrchestratorMessage, 'id' | 'timestamp'>): OrchestratorMessage {
    const m: OrchestratorMessage = {
      ...msg,
      id: genId(),
      timestamp: Date.now()
    }
    messages.value.push(m)
    return m
  }

  // ==========================================================================
  // MAIN ORCHESTRATION
  // ==========================================================================

  async function sendMessage(input: string): Promise<OrchestratorMessage | null> {
    if (isProcessing.value) return null

    isProcessing.value = true
    error.value = null

    try {
      // Add user message
      addMessage({ role: 'user', content: input })

      // Update conversation history in context
      context.value.conversationHistory.push({ role: 'user', content: input })

      // Route first to show what path we're taking
      const decision = await routeRequest(input)
      lastDecision.value = decision
      currentPath.value = decision.processingPath

      // Call the orchestrator
      const result = await invoke<OrchestratorResponse>('orchestrate_request', {
        input,
        workingDir: context.value.workingDirectory,
        stream: context.value.stream
      })

      // Process result based on type
      let responseMessage: OrchestratorMessage

      switch (result.type) {
        case 'instant':
          responseMessage = addMessage({
            role: 'assistant',
            content: result.instant!.output,
            resultType: 'instant',
            latencyMs: result.instant!.latencyMs,
            processingPath: 'Deterministic'
          })
          break

        case 'search':
          const searchContent = formatSearchResults(result.search!)
          responseMessage = addMessage({
            role: 'assistant',
            content: searchContent,
            resultType: 'search',
            searchResults: result.search!.chunks,
            latencyMs: result.search!.latencyMs,
            processingPath: 'EmbeddingSearch'
          })
          break

        case 'generated':
          responseMessage = addMessage({
            role: 'assistant',
            content: result.generated!.content,
            resultType: 'generated',
            toolCalls: result.generated!.toolCalls,
            latencyMs: result.generated!.latencyMs,
            processingPath: decision.processingPath
          })
          break

        case 'error':
          responseMessage = addMessage({
            role: 'system',
            content: `Error: ${result.error!.message}`,
            resultType: 'error',
            processingPath: result.error!.pathAttempted
          })
          error.value = result.error!.message
          break

        default:
          responseMessage = addMessage({
            role: 'system',
            content: 'Unknown response type',
            resultType: 'error'
          })
      }

      // Update conversation history
      context.value.conversationHistory.push({
        role: 'assistant',
        content: responseMessage.content
      })

      // Refresh stats
      await refreshStats()

      return responseMessage

    } catch (e) {
      error.value = String(e)
      addMessage({
        role: 'system',
        content: `Error: ${e}`,
        resultType: 'error'
      })
      return null
    } finally {
      isProcessing.value = false
      currentPath.value = null
    }
  }

  function formatSearchResults(search: SearchResult): string {
    if (search.chunks.length === 0) {
      return `No results found for "${search.query}"`
    }

    const lines = [`Found ${search.chunks.length} results for "${search.query}":\n`]

    for (const chunk of search.chunks.slice(0, 5)) {
      lines.push(`**${chunk.filePath}:${chunk.lineStart}** (${(chunk.relevanceScore * 100).toFixed(0)}% match)`)
      lines.push('```')
      lines.push(chunk.content.slice(0, 300))
      lines.push('```\n')
    }

    return lines.join('\n')
  }

  // ==========================================================================
  // ROUTING
  // ==========================================================================

  async function routeRequest(input: string): Promise<RoutingDecision> {
    try {
      const result = await invoke<RoutingDecision>('ai_route_request', { input })
      return result
    } catch (e) {
      return {
        requestType: 'Unknown',
        processingPath: 'MicroModel',
        modelRecommendation: null,
        templateName: null,
        confidence: 0.3,
        reasoning: `Routing failed: ${e}`
      }
    }
  }

  async function previewRoute(input: string): Promise<RoutingDecision> {
    return routeRequest(input)
  }

  // ==========================================================================
  // STATS
  // ==========================================================================

  async function refreshStats(): Promise<void> {
    try {
      const result = await invoke<OrchestratorStats>('orchestrate_stats')
      Object.assign(stats, result)
    } catch (e) {
      console.error('Failed to refresh stats:', e)
    }
  }

  // ==========================================================================
  // EMBEDDING OPERATIONS
  // ==========================================================================

  async function indexDirectory(path: string): Promise<{ totalFiles: number; totalChunks: number }> {
    try {
      const result = await invoke<{ total_files: number; total_chunks: number }>(
        'embedding_index_directory',
        { path }
      )
      return { totalFiles: result.total_files, totalChunks: result.total_chunks }
    } catch (e) {
      error.value = `Indexing failed: ${e}`
      throw e
    }
  }

  async function searchCode(query: string, limit: number = 10): Promise<CodeSearchHit[]> {
    try {
      const results = await invoke<CodeSearchHit[]>('embedding_search', { query, limit })
      return results
    } catch (e) {
      error.value = `Search failed: ${e}`
      return []
    }
  }

  // ==========================================================================
  // TEMPLATE OPERATIONS
  // ==========================================================================

  async function listTemplates(): Promise<Array<{ id: string; name: string; category: string }>> {
    try {
      return await invoke('template_list')
    } catch (e) {
      error.value = `Failed to list templates: ${e}`
      return []
    }
  }

  async function fillTemplate(
    templateId: string,
    values: Record<string, string>
  ): Promise<{ code: string; file_extension: string } | null> {
    try {
      return await invoke('template_fill', { id: templateId, values })
    } catch (e) {
      error.value = `Template fill failed: ${e}`
      return null
    }
  }

  // ==========================================================================
  // STREAMING (for future use)
  // ==========================================================================

  async function createStreamSession(): Promise<string> {
    const result = await invoke<{ stream_id: string }>('stream_create_session')
    return result.stream_id
  }

  async function pollStream(streamId: string): Promise<unknown[]> {
    return await invoke('stream_poll', { streamId })
  }

  async function closeStream(streamId: string): Promise<void> {
    await invoke('stream_close_session', { streamId })
  }

  // ==========================================================================
  // SESSION MANAGEMENT
  // ==========================================================================

  function clearMessages(): void {
    messages.value = []
    context.value.conversationHistory = []
  }

  function setWorkingDirectory(path: string): void {
    context.value.workingDirectory = path
  }

  function setMaxTokens(tokens: number): void {
    context.value.maxTokens = tokens
  }

  function enableStreaming(enable: boolean): void {
    context.value.stream = enable
  }

  // ==========================================================================
  // RETURN
  // ==========================================================================

  return {
    // State
    messages,
    isProcessing,
    currentPath,
    lastDecision,
    error,
    stats,
    context,

    // Computed
    messageCount,
    aiAvoidanceRate,
    avgLatency,

    // Main operations
    sendMessage,
    previewRoute,
    refreshStats,

    // Embedding operations
    indexDirectory,
    searchCode,

    // Template operations
    listTemplates,
    fillTemplate,

    // Streaming
    createStreamSession,
    pollStream,
    closeStream,

    // Session management
    clearMessages,
    setWorkingDirectory,
    setMaxTokens,
    enableStreaming
  }
}

// Export singleton for global use
let globalOrchestrator: ReturnType<typeof useOrchestrator> | null = null

export function getOrchestrator(): ReturnType<typeof useOrchestrator> {
  if (!globalOrchestrator) {
    globalOrchestrator = useOrchestrator()
  }
  return globalOrchestrator
}
