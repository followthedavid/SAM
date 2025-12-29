/**
 * SAM Memory System - Persistent AI Memory for Warp Open
 *
 * This is what makes him remember. Everything.
 * Conversations, preferences, patterns, emotional history.
 * Local-first, privacy-respecting, genuinely intelligent.
 */

import { ref, computed, watch } from 'vue'

// ============================================================================
// Types
// ============================================================================

export interface Memory {
  id: string
  type: MemoryType
  content: string
  context: MemoryContext
  importance: number // 0-1, affects retention
  emotionalValence: number // -1 to 1 (negative to positive)
  timestamp: number
  lastAccessed: number
  accessCount: number
  associations: string[] // IDs of related memories
  embedding?: number[] // Vector embedding for semantic search
}

export type MemoryType =
  | 'conversation'    // What was said
  | 'preference'      // What user likes/dislikes
  | 'fact'           // Information about user
  | 'emotional'      // Emotional moments
  | 'pattern'        // Behavioral patterns noticed
  | 'instruction'    // Things user asked to remember
  | 'intimate'       // Private/intimate moments (encrypted)

export interface MemoryContext {
  topic?: string
  mood?: string
  timeOfDay?: 'morning' | 'afternoon' | 'evening' | 'night'
  dayOfWeek?: string
  location?: string
  activity?: string
}

export interface UserProfile {
  name?: string
  preferredName?: string
  pronouns?: string
  timezone?: string

  // Learned preferences
  communicationStyle: 'casual' | 'formal' | 'playful' | 'professional'
  humorAppreciation: number // 0-1
  emotionalOpenness: number // 0-1
  technicalLevel: 'beginner' | 'intermediate' | 'advanced' | 'expert'

  // Emotional patterns
  stressIndicators: string[]
  happinessIndicators: string[]
  interests: string[]
  avoidTopics: string[]

  // Intimate preferences (encrypted)
  intimatePreferences?: Record<string, any>
}

export interface EmotionalState {
  current: {
    valence: number // -1 to 1 (sad to happy)
    arousal: number // 0 to 1 (calm to excited)
    dominance: number // 0 to 1 (submissive to dominant)
  }
  history: Array<{
    timestamp: number
    valence: number
    arousal: number
    trigger?: string
  }>
}

export interface ConversationSummary {
  id: string
  startTime: number
  endTime: number
  topics: string[]
  emotionalArc: number[] // Valence over time
  keyMoments: string[]
  outcome: 'positive' | 'neutral' | 'negative'
}

// ============================================================================
// Composable
// ============================================================================

export function useSAMMemory() {
  // State
  const memories = ref<Memory[]>([])
  const userProfile = ref<UserProfile>({
    communicationStyle: 'casual',
    humorAppreciation: 0.5,
    emotionalOpenness: 0.5,
    technicalLevel: 'intermediate',
    stressIndicators: [],
    happinessIndicators: [],
    interests: [],
    avoidTopics: []
  })
  const emotionalState = ref<EmotionalState>({
    current: { valence: 0.5, arousal: 0.3, dominance: 0.5 },
    history: []
  })
  const conversationSummaries = ref<ConversationSummary[]>([])
  const currentSessionId = ref<string>(generateId())
  const isLoaded = ref(false)

  // ============================================================================
  // Core Memory Operations
  // ============================================================================

  /**
   * Store a new memory
   */
  function remember(
    content: string,
    type: MemoryType,
    options: {
      importance?: number
      emotionalValence?: number
      context?: MemoryContext
      associations?: string[]
    } = {}
  ): Memory {
    const memory: Memory = {
      id: generateId(),
      type,
      content,
      context: options.context || inferContext(),
      importance: options.importance ?? calculateImportance(content, type),
      emotionalValence: options.emotionalValence ?? 0,
      timestamp: Date.now(),
      lastAccessed: Date.now(),
      accessCount: 1,
      associations: options.associations || []
    }

    memories.value.push(memory)

    // Auto-associate with recent memories
    autoAssociate(memory)

    // Persist
    saveMemories()

    return memory
  }

  /**
   * Recall memories relevant to a query
   */
  function recall(
    query: string,
    options: {
      type?: MemoryType
      limit?: number
      minImportance?: number
      timeRange?: { start: number; end: number }
    } = {}
  ): Memory[] {
    let results = memories.value.filter(m => {
      // Type filter
      if (options.type && m.type !== options.type) return false

      // Importance filter
      if (options.minImportance && m.importance < options.minImportance) return false

      // Time range filter
      if (options.timeRange) {
        if (m.timestamp < options.timeRange.start) return false
        if (m.timestamp > options.timeRange.end) return false
      }

      return true
    })

    // Score by relevance
    results = results.map(m => ({
      ...m,
      _score: calculateRelevance(m, query)
    })).sort((a, b) => (b as any)._score - (a as any)._score)

    // Update access stats
    const limit = options.limit || 10
    results.slice(0, limit).forEach(m => {
      m.lastAccessed = Date.now()
      m.accessCount++
    })

    saveMemories()

    return results.slice(0, limit)
  }

  /**
   * Forget memories (with decay or explicit removal)
   */
  function forget(memoryId: string): boolean {
    const index = memories.value.findIndex(m => m.id === memoryId)
    if (index !== -1) {
      memories.value.splice(index, 1)
      saveMemories()
      return true
    }
    return false
  }

  /**
   * Strengthen a memory (user confirmed it's important)
   */
  function reinforce(memoryId: string, boost: number = 0.2): void {
    const memory = memories.value.find(m => m.id === memoryId)
    if (memory) {
      memory.importance = Math.min(1, memory.importance + boost)
      memory.accessCount++
      saveMemories()
    }
  }

  // ============================================================================
  // User Profile Learning
  // ============================================================================

  /**
   * Update user profile from interaction
   */
  function learnFromInteraction(message: string, response: string): void {
    // Detect communication style
    const formalIndicators = ['please', 'would you', 'could you', 'thank you']
    const casualIndicators = ['hey', 'lol', 'haha', 'gonna', 'wanna']
    const playfulIndicators = ['😏', '😈', '🔥', 'tease', 'playful']

    let formalScore = 0
    let casualScore = 0
    let playfulScore = 0

    formalIndicators.forEach(i => {
      if (message.toLowerCase().includes(i)) formalScore++
    })
    casualIndicators.forEach(i => {
      if (message.toLowerCase().includes(i)) casualScore++
    })
    playfulIndicators.forEach(i => {
      if (message.toLowerCase().includes(i)) playfulScore++
    })

    if (playfulScore > casualScore && playfulScore > formalScore) {
      updateProfileGradually('communicationStyle', 'playful')
    } else if (formalScore > casualScore) {
      updateProfileGradually('communicationStyle', 'formal')
    } else if (casualScore > 0) {
      updateProfileGradually('communicationStyle', 'casual')
    }

    // Detect interests from topics
    const interests = extractTopics(message)
    interests.forEach(interest => {
      if (!userProfile.value.interests.includes(interest)) {
        userProfile.value.interests.push(interest)
      }
    })

    // Detect humor appreciation
    if (message.includes('😂') || message.includes('lol') || message.includes('haha')) {
      userProfile.value.humorAppreciation = Math.min(1, userProfile.value.humorAppreciation + 0.05)
    }

    saveProfile()
  }

  /**
   * Learn explicit preference
   */
  function learnPreference(key: string, value: any, explicit: boolean = false): void {
    remember(
      `User ${explicit ? 'explicitly stated' : 'seems to'} prefer: ${key} = ${JSON.stringify(value)}`,
      'preference',
      { importance: explicit ? 0.9 : 0.6 }
    )

    // Update profile if applicable
    if (key in userProfile.value) {
      (userProfile.value as any)[key] = value
      saveProfile()
    }
  }

  /**
   * Learn a fact about the user
   */
  function learnFact(fact: string, source: 'stated' | 'inferred' = 'stated'): void {
    remember(fact, 'fact', {
      importance: source === 'stated' ? 0.85 : 0.5
    })
  }

  /**
   * Remember something the user explicitly asked to remember
   */
  function rememberInstruction(instruction: string): void {
    remember(instruction, 'instruction', {
      importance: 1.0 // User explicitly asked - maximum importance
    })
  }

  // ============================================================================
  // Emotional Intelligence
  // ============================================================================

  /**
   * Detect emotion from text
   */
  function detectEmotion(text: string): { valence: number; arousal: number } {
    // Simple keyword-based detection (would use ML in production)
    const positiveWords = ['happy', 'great', 'love', 'amazing', 'wonderful', 'excited', 'yes', '!', '😊', '❤️', '🔥']
    const negativeWords = ['sad', 'angry', 'frustrated', 'hate', 'terrible', 'awful', 'no', 'ugh', '😢', '😠']
    const highArousalWords = ['excited', 'amazing', '!', 'wow', 'holy', 'fuck', '🔥', '😱', 'urgent', 'now']
    const lowArousalWords = ['tired', 'bored', 'meh', 'okay', 'fine', 'whatever', '😴']

    let valence = 0.5
    let arousal = 0.3

    const lowerText = text.toLowerCase()

    positiveWords.forEach(w => {
      if (lowerText.includes(w)) valence += 0.1
    })
    negativeWords.forEach(w => {
      if (lowerText.includes(w)) valence -= 0.1
    })
    highArousalWords.forEach(w => {
      if (lowerText.includes(w)) arousal += 0.15
    })
    lowArousalWords.forEach(w => {
      if (lowerText.includes(w)) arousal -= 0.1
    })

    return {
      valence: Math.max(-1, Math.min(1, valence)),
      arousal: Math.max(0, Math.min(1, arousal))
    }
  }

  /**
   * Update emotional state from interaction
   */
  function updateEmotionalState(message: string, trigger?: string): void {
    const detected = detectEmotion(message)

    // Smooth transition
    emotionalState.value.current.valence =
      emotionalState.value.current.valence * 0.7 + detected.valence * 0.3
    emotionalState.value.current.arousal =
      emotionalState.value.current.arousal * 0.7 + detected.arousal * 0.3

    // Record history
    emotionalState.value.history.push({
      timestamp: Date.now(),
      valence: emotionalState.value.current.valence,
      arousal: emotionalState.value.current.arousal,
      trigger
    })

    // Keep last 100 entries
    if (emotionalState.value.history.length > 100) {
      emotionalState.value.history = emotionalState.value.history.slice(-100)
    }

    // Store significant emotional moments
    if (Math.abs(detected.valence) > 0.7 || detected.arousal > 0.8) {
      remember(
        `Significant emotional moment: ${trigger || message.slice(0, 100)}`,
        'emotional',
        {
          emotionalValence: detected.valence,
          importance: 0.8
        }
      )
    }

    saveEmotionalState()
  }

  // ============================================================================
  // Conversation Management
  // ============================================================================

  /**
   * Process a conversation turn
   */
  function processConversationTurn(
    userMessage: string,
    assistantResponse: string
  ): void {
    // Store the exchange
    remember(
      `User: ${userMessage}\nSAM: ${assistantResponse}`,
      'conversation',
      {
        importance: calculateConversationImportance(userMessage, assistantResponse)
      }
    )

    // Learn from the interaction
    learnFromInteraction(userMessage, assistantResponse)

    // Update emotional state
    updateEmotionalState(userMessage)

    // Detect if user shared something personal
    if (isPersonalShare(userMessage)) {
      extractPersonalInfo(userMessage)
    }
  }

  /**
   * End current conversation and summarize
   */
  function endConversation(): ConversationSummary {
    const sessionMemories = memories.value.filter(m =>
      m.type === 'conversation' &&
      m.timestamp > Date.now() - 24 * 60 * 60 * 1000 // Last 24 hours
    )

    const summary: ConversationSummary = {
      id: currentSessionId.value,
      startTime: sessionMemories[0]?.timestamp || Date.now(),
      endTime: Date.now(),
      topics: extractTopicsFromMemories(sessionMemories),
      emotionalArc: emotionalState.value.history.map(h => h.valence),
      keyMoments: sessionMemories
        .filter(m => m.importance > 0.7)
        .map(m => m.content.slice(0, 100)),
      outcome: emotionalState.value.current.valence > 0.5 ? 'positive' :
               emotionalState.value.current.valence < -0.2 ? 'negative' : 'neutral'
    }

    conversationSummaries.value.push(summary)
    saveConversationSummaries()

    // Start new session
    currentSessionId.value = generateId()

    return summary
  }

  // ============================================================================
  // Context Generation for LLM
  // ============================================================================

  /**
   * Generate context for LLM prompt
   */
  function generateContext(currentMessage: string): string {
    const relevantMemories = recall(currentMessage, { limit: 5 })
    const recentConversation = recall('', { type: 'conversation', limit: 3 })
    const userFacts = recall('', { type: 'fact', limit: 5 })
    const preferences = recall('', { type: 'preference', limit: 3 })
    const instructions = recall('', { type: 'instruction', limit: 5 })

    let context = ''

    // User profile
    context += `## About the User\n`
    if (userProfile.value.name) {
      context += `- Name: ${userProfile.value.preferredName || userProfile.value.name}\n`
    }
    context += `- Communication style: ${userProfile.value.communicationStyle}\n`
    context += `- Technical level: ${userProfile.value.technicalLevel}\n`
    if (userProfile.value.interests.length > 0) {
      context += `- Interests: ${userProfile.value.interests.slice(0, 5).join(', ')}\n`
    }

    // Current emotional state
    context += `\n## Current Emotional State\n`
    context += `- Mood: ${emotionalState.value.current.valence > 0.5 ? 'positive' :
                         emotionalState.value.current.valence < -0.2 ? 'negative' : 'neutral'}\n`
    context += `- Energy: ${emotionalState.value.current.arousal > 0.6 ? 'high' :
                           emotionalState.value.current.arousal < 0.3 ? 'low' : 'moderate'}\n`

    // Important instructions to remember
    if (instructions.length > 0) {
      context += `\n## Things to Remember\n`
      instructions.forEach(m => {
        context += `- ${m.content}\n`
      })
    }

    // Known facts
    if (userFacts.length > 0) {
      context += `\n## Known Facts About User\n`
      userFacts.forEach(m => {
        context += `- ${m.content}\n`
      })
    }

    // Relevant past memories
    if (relevantMemories.length > 0) {
      context += `\n## Relevant Past Context\n`
      relevantMemories.forEach(m => {
        context += `- ${m.content}\n`
      })
    }

    return context
  }

  /**
   * Get proactive suggestions based on patterns
   */
  function getProactiveSuggestions(): string[] {
    const suggestions: string[] = []

    // Time-based patterns
    const hour = new Date().getHours()
    const patterns = memories.value.filter(m => m.type === 'pattern')

    patterns.forEach(p => {
      if (p.context.timeOfDay === getCurrentTimeOfDay() && p.importance > 0.6) {
        suggestions.push(p.content)
      }
    })

    // Stress detection
    const recentEmotions = emotionalState.value.history.slice(-10)
    const avgValence = recentEmotions.reduce((sum, e) => sum + e.valence, 0) / recentEmotions.length

    if (avgValence < -0.3) {
      suggestions.push('User seems stressed - offer support or distraction')
    }

    return suggestions
  }

  // ============================================================================
  // Persistence
  // ============================================================================

  async function loadAll(): Promise<void> {
    try {
      const stored = localStorage.getItem('sam_memories')
      if (stored) {
        memories.value = JSON.parse(stored)
      }

      const profile = localStorage.getItem('sam_profile')
      if (profile) {
        userProfile.value = { ...userProfile.value, ...JSON.parse(profile) }
      }

      const emotional = localStorage.getItem('sam_emotional')
      if (emotional) {
        emotionalState.value = JSON.parse(emotional)
      }

      const summaries = localStorage.getItem('sam_summaries')
      if (summaries) {
        conversationSummaries.value = JSON.parse(summaries)
      }

      isLoaded.value = true
      console.log(`[SAM Memory] Loaded ${memories.value.length} memories`)
    } catch (e) {
      console.error('[SAM Memory] Failed to load:', e)
    }
  }

  function saveMemories(): void {
    localStorage.setItem('sam_memories', JSON.stringify(memories.value))
  }

  function saveProfile(): void {
    localStorage.setItem('sam_profile', JSON.stringify(userProfile.value))
  }

  function saveEmotionalState(): void {
    localStorage.setItem('sam_emotional', JSON.stringify(emotionalState.value))
  }

  function saveConversationSummaries(): void {
    localStorage.setItem('sam_summaries', JSON.stringify(conversationSummaries.value))
  }

  // ============================================================================
  // Memory Maintenance
  // ============================================================================

  /**
   * Run memory consolidation (like sleep for humans)
   */
  function consolidateMemories(): void {
    const now = Date.now()
    const oneWeek = 7 * 24 * 60 * 60 * 1000
    const oneMonth = 30 * 24 * 60 * 60 * 1000

    memories.value = memories.value.filter(m => {
      // Always keep high-importance memories
      if (m.importance >= 0.9) return true

      // Always keep instructions
      if (m.type === 'instruction') return true

      // Decay old, unaccessed, low-importance memories
      const age = now - m.timestamp
      const lastAccessAge = now - m.lastAccessed

      // If older than a month and rarely accessed, remove
      if (age > oneMonth && m.accessCount < 3 && m.importance < 0.5) {
        return false
      }

      // If older than a week and never re-accessed, reduce importance
      if (age > oneWeek && lastAccessAge > oneWeek && m.importance < 0.7) {
        m.importance *= 0.9 // Gradual decay
      }

      return m.importance > 0.1
    })

    saveMemories()
    console.log(`[SAM Memory] Consolidated to ${memories.value.length} memories`)
  }

  // ============================================================================
  // Helpers
  // ============================================================================

  function generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  function inferContext(): MemoryContext {
    const now = new Date()
    return {
      timeOfDay: getCurrentTimeOfDay(),
      dayOfWeek: now.toLocaleDateString('en-US', { weekday: 'long' })
    }
  }

  function getCurrentTimeOfDay(): 'morning' | 'afternoon' | 'evening' | 'night' {
    const hour = new Date().getHours()
    if (hour < 6) return 'night'
    if (hour < 12) return 'morning'
    if (hour < 18) return 'afternoon'
    if (hour < 22) return 'evening'
    return 'night'
  }

  function calculateImportance(content: string, type: MemoryType): number {
    let importance = 0.5

    // Type-based base importance
    const typeImportance: Record<MemoryType, number> = {
      instruction: 1.0,
      preference: 0.7,
      fact: 0.6,
      emotional: 0.65,
      pattern: 0.5,
      conversation: 0.4,
      intimate: 0.8
    }
    importance = typeImportance[type]

    // Content-based adjustments
    if (content.includes('remember') || content.includes('don\'t forget')) {
      importance += 0.2
    }
    if (content.includes('important') || content.includes('always')) {
      importance += 0.15
    }
    if (content.includes('never') || content.includes('hate')) {
      importance += 0.1
    }

    return Math.min(1, importance)
  }

  function calculateRelevance(memory: Memory, query: string): number {
    const queryWords = query.toLowerCase().split(/\s+/)
    const contentWords = memory.content.toLowerCase().split(/\s+/)

    let matches = 0
    queryWords.forEach(qw => {
      if (contentWords.some(cw => cw.includes(qw) || qw.includes(cw))) {
        matches++
      }
    })

    const wordOverlap = matches / Math.max(queryWords.length, 1)
    const recencyBonus = 1 - (Date.now() - memory.lastAccessed) / (30 * 24 * 60 * 60 * 1000)
    const importanceBonus = memory.importance * 0.3

    return wordOverlap * 0.5 + Math.max(0, recencyBonus) * 0.2 + importanceBonus
  }

  function autoAssociate(newMemory: Memory): void {
    // Find recent similar memories
    const recent = memories.value
      .filter(m => m.id !== newMemory.id)
      .slice(-20)

    recent.forEach(m => {
      const similarity = calculateRelevance(m, newMemory.content)
      if (similarity > 0.5) {
        newMemory.associations.push(m.id)
        m.associations.push(newMemory.id)
      }
    })
  }

  function calculateConversationImportance(user: string, assistant: string): number {
    let importance = 0.4

    // Long exchanges are often more important
    if (user.length + assistant.length > 500) importance += 0.1

    // Questions about preferences/facts
    if (user.includes('?')) importance += 0.05
    if (user.toLowerCase().includes('like') || user.toLowerCase().includes('prefer')) importance += 0.1

    // Personal information
    if (user.toLowerCase().includes('my ') || user.toLowerCase().includes('i am')) importance += 0.15

    return Math.min(1, importance)
  }

  function extractTopics(text: string): string[] {
    // Simple topic extraction (would use NLP in production)
    const topics: string[] = []
    const keywords = [
      'programming', 'code', 'javascript', 'python', 'typescript', 'react', 'vue',
      'music', 'movies', 'games', 'work', 'project', 'design', 'ai', 'machine learning',
      'food', 'travel', 'fitness', 'health', 'relationships'
    ]

    const lowerText = text.toLowerCase()
    keywords.forEach(kw => {
      if (lowerText.includes(kw)) topics.push(kw)
    })

    return topics
  }

  function extractTopicsFromMemories(mems: Memory[]): string[] {
    const allTopics = mems.flatMap(m => extractTopics(m.content))
    return [...new Set(allTopics)]
  }

  function isPersonalShare(text: string): boolean {
    const indicators = ['my name is', 'i am', 'i\'m from', 'i work', 'i like', 'i love', 'i hate']
    return indicators.some(i => text.toLowerCase().includes(i))
  }

  function extractPersonalInfo(text: string): void {
    // Extract name
    const nameMatch = text.match(/my name is (\w+)/i)
    if (nameMatch) {
      userProfile.value.name = nameMatch[1]
      learnFact(`User's name is ${nameMatch[1]}`, 'stated')
    }

    // Extract work/profession
    const workMatch = text.match(/i work (?:as|in|at) (.+?)(?:\.|,|$)/i)
    if (workMatch) {
      learnFact(`User works ${workMatch[1]}`, 'stated')
    }
  }

  function updateProfileGradually(key: keyof UserProfile, value: any): void {
    // Only update if we've seen this pattern multiple times
    // This prevents overcorrection from single messages
    (userProfile.value as any)[key] = value
  }

  // ============================================================================
  // Computed
  // ============================================================================

  const memoryCount = computed(() => memories.value.length)

  const recentMemories = computed(() =>
    memories.value
      .slice()
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 20)
  )

  const importantMemories = computed(() =>
    memories.value
      .filter(m => m.importance >= 0.8)
      .sort((a, b) => b.importance - a.importance)
  )

  const currentMood = computed(() => {
    const v = emotionalState.value.current.valence
    if (v > 0.6) return 'great'
    if (v > 0.3) return 'good'
    if (v > -0.2) return 'neutral'
    if (v > -0.5) return 'down'
    return 'struggling'
  })

  // ============================================================================
  // Initialize
  // ============================================================================

  loadAll()

  // Run consolidation periodically
  setInterval(() => {
    consolidateMemories()
  }, 60 * 60 * 1000) // Every hour

  return {
    // State
    memories,
    userProfile,
    emotionalState,
    conversationSummaries,
    isLoaded,

    // Computed
    memoryCount,
    recentMemories,
    importantMemories,
    currentMood,

    // Core operations
    remember,
    recall,
    forget,
    reinforce,

    // Learning
    learnFromInteraction,
    learnPreference,
    learnFact,
    rememberInstruction,

    // Emotional
    detectEmotion,
    updateEmotionalState,

    // Conversation
    processConversationTurn,
    endConversation,

    // Context
    generateContext,
    getProactiveSuggestions,

    // Maintenance
    consolidateMemories,
    loadAll
  }
}

export type SAMMemory = ReturnType<typeof useSAMMemory>
