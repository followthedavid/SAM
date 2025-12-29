/**
 * useLearning - Continuous Learning & Preference Adaptation
 *
 * Learns from interactions to better understand and serve the user.
 * Tracks preferences, patterns, and adapts behavior over time.
 *
 * "I noticed you always work late on Thursdays. Want me to adjust reminders?"
 */

import { ref, computed, watch, reactive } from 'vue'
import { useAuditLog } from './useAuditLog'

// ============================================================================
// TYPES
// ============================================================================

export interface LearnedPreference {
  id: string
  category: PreferenceCategory
  key: string
  value: string | number | boolean
  confidence: number  // 0-1, increases with confirmation
  learnedAt: Date
  confirmedAt?: Date
  source: 'inferred' | 'explicit' | 'observed'
  examples: string[]  // Supporting evidence
}

export type PreferenceCategory =
  | 'communication'   // How they like to be communicated with
  | 'workflow'        // Work patterns
  | 'coding'          // Coding preferences
  | 'schedule'        // Time preferences
  | 'personality'     // How they want SAM to behave
  | 'topics'          // Topics they're interested in
  | 'avoidances'      // Things they don't like
  | 'tools'           // Tool/app preferences
  | 'other'

export interface BehaviorPattern {
  id: string
  type: PatternType
  description: string
  frequency: number      // Times observed
  lastObserved: Date
  timeOfDay?: string     // e.g., "morning", "afternoon"
  dayOfWeek?: number     // 0-6
  triggers?: string[]    // What triggers this behavior
  confidence: number
}

export type PatternType =
  | 'schedule'        // Regular time-based patterns
  | 'reaction'        // How they react to things
  | 'preference'      // Repeated choices
  | 'habit'           // Regular behaviors
  | 'mood'            // Emotional patterns

export interface FeedbackRecord {
  id: string
  timestamp: Date
  type: 'positive' | 'negative' | 'correction' | 'preference'
  context: string
  originalResponse?: string
  feedback: string
  applied: boolean
}

export interface LearningStats {
  totalPreferences: number
  highConfidencePreferences: number
  totalPatterns: number
  feedbackReceived: number
  adaptationsApplied: number
  lastLearningUpdate: Date
}

// ============================================================================
// STORAGE
// ============================================================================

const PREFERENCES_KEY = 'warp_learning_preferences'
const PATTERNS_KEY = 'warp_learning_patterns'
const FEEDBACK_KEY = 'warp_learning_feedback'

function loadPreferences(): LearnedPreference[] {
  try {
    const stored = localStorage.getItem(PREFERENCES_KEY)
    if (stored) {
      return JSON.parse(stored).map((p: any) => ({
        ...p,
        learnedAt: new Date(p.learnedAt),
        confirmedAt: p.confirmedAt ? new Date(p.confirmedAt) : undefined
      }))
    }
  } catch {}
  return []
}

function savePreferences(prefs: LearnedPreference[]): void {
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(prefs))
}

function loadPatterns(): BehaviorPattern[] {
  try {
    const stored = localStorage.getItem(PATTERNS_KEY)
    if (stored) {
      return JSON.parse(stored).map((p: any) => ({
        ...p,
        lastObserved: new Date(p.lastObserved)
      }))
    }
  } catch {}
  return []
}

function savePatterns(patterns: BehaviorPattern[]): void {
  localStorage.setItem(PATTERNS_KEY, JSON.stringify(patterns))
}

function loadFeedback(): FeedbackRecord[] {
  try {
    const stored = localStorage.getItem(FEEDBACK_KEY)
    if (stored) {
      return JSON.parse(stored).map((f: any) => ({
        ...f,
        timestamp: new Date(f.timestamp)
      }))
    }
  } catch {}
  return []
}

function saveFeedback(feedback: FeedbackRecord[]): void {
  localStorage.setItem(FEEDBACK_KEY, JSON.stringify(feedback))
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useLearning() {
  const auditLog = useAuditLog()

  const preferences = ref<LearnedPreference[]>(loadPreferences())
  const patterns = ref<BehaviorPattern[]>(loadPatterns())
  const feedback = ref<FeedbackRecord[]>(loadFeedback())

  // ========================================================================
  // PREFERENCE LEARNING
  // ========================================================================

  /**
   * Learn a new preference
   */
  function learnPreference(
    category: PreferenceCategory,
    key: string,
    value: string | number | boolean,
    options?: {
      source?: LearnedPreference['source']
      example?: string
      confidence?: number
    }
  ): LearnedPreference {
    // Check if preference already exists
    const existing = preferences.value.find(
      p => p.category === category && p.key === key
    )

    if (existing) {
      // Update existing preference
      existing.value = value
      existing.confidence = Math.min(1, existing.confidence + 0.1)

      if (options?.example && !existing.examples.includes(options.example)) {
        existing.examples.push(options.example)
        if (existing.examples.length > 10) {
          existing.examples = existing.examples.slice(-10)
        }
      }

      savePreferences(preferences.value)
      return existing
    }

    // Create new preference
    const pref: LearnedPreference = {
      id: `pref_${Date.now()}`,
      category,
      key,
      value,
      confidence: options?.confidence || 0.5,
      learnedAt: new Date(),
      source: options?.source || 'inferred',
      examples: options?.example ? [options.example] : []
    }

    preferences.value.push(pref)
    savePreferences(preferences.value)

    auditLog.log('preference_learned', `Learned: ${key} = ${value}`, {
      riskLevel: 'low'
    })

    return pref
  }

  /**
   * Get preference value
   */
  function getPreference<T>(category: PreferenceCategory, key: string): T | undefined {
    const pref = preferences.value.find(
      p => p.category === category && p.key === key
    )
    return pref?.value as T | undefined
  }

  /**
   * Get all preferences in a category
   */
  function getCategoryPreferences(category: PreferenceCategory): LearnedPreference[] {
    return preferences.value.filter(p => p.category === category)
  }

  /**
   * Confirm a learned preference (increases confidence)
   */
  function confirmPreference(prefId: string): void {
    const pref = preferences.value.find(p => p.id === prefId)
    if (pref) {
      pref.confidence = Math.min(1, pref.confidence + 0.2)
      pref.confirmedAt = new Date()
      pref.source = 'explicit'
      savePreferences(preferences.value)
    }
  }

  /**
   * Reject a learned preference
   */
  function rejectPreference(prefId: string): void {
    const pref = preferences.value.find(p => p.id === prefId)
    if (pref) {
      pref.confidence = Math.max(0, pref.confidence - 0.3)
      if (pref.confidence <= 0.2) {
        // Remove low-confidence preferences
        preferences.value = preferences.value.filter(p => p.id !== prefId)
      }
      savePreferences(preferences.value)
    }
  }

  /**
   * High confidence preferences
   */
  const confirmedPreferences = computed(() =>
    preferences.value.filter(p => p.confidence >= 0.7)
  )

  // ========================================================================
  // PATTERN RECOGNITION
  // ========================================================================

  /**
   * Record a pattern observation
   */
  function observePattern(
    type: PatternType,
    description: string,
    options?: {
      timeOfDay?: string
      dayOfWeek?: number
      triggers?: string[]
    }
  ): BehaviorPattern {
    // Check if pattern exists
    const existing = patterns.value.find(
      p => p.type === type && p.description === description
    )

    if (existing) {
      existing.frequency++
      existing.lastObserved = new Date()
      existing.confidence = Math.min(1, existing.confidence + 0.05)

      if (options?.timeOfDay && !existing.timeOfDay) {
        existing.timeOfDay = options.timeOfDay
      }
      if (options?.dayOfWeek !== undefined && existing.dayOfWeek === undefined) {
        existing.dayOfWeek = options.dayOfWeek
      }
      if (options?.triggers) {
        existing.triggers = [...new Set([...(existing.triggers || []), ...options.triggers])]
      }

      savePatterns(patterns.value)
      return existing
    }

    // Create new pattern
    const pattern: BehaviorPattern = {
      id: `pattern_${Date.now()}`,
      type,
      description,
      frequency: 1,
      lastObserved: new Date(),
      timeOfDay: options?.timeOfDay,
      dayOfWeek: options?.dayOfWeek,
      triggers: options?.triggers,
      confidence: 0.3
    }

    patterns.value.push(pattern)
    savePatterns(patterns.value)

    return pattern
  }

  /**
   * Get patterns by type
   */
  function getPatternsByType(type: PatternType): BehaviorPattern[] {
    return patterns.value.filter(p => p.type === type)
  }

  /**
   * Get current relevant patterns (based on time)
   */
  const currentPatterns = computed(() => {
    const now = new Date()
    const hour = now.getHours()
    const dayOfWeek = now.getDay()

    const timeOfDay = hour < 12 ? 'morning' :
                      hour < 17 ? 'afternoon' :
                      hour < 21 ? 'evening' : 'night'

    return patterns.value.filter(p =>
      p.confidence >= 0.5 &&
      (!p.timeOfDay || p.timeOfDay === timeOfDay) &&
      (p.dayOfWeek === undefined || p.dayOfWeek === dayOfWeek)
    )
  })

  /**
   * Significant patterns (frequently observed)
   */
  const significantPatterns = computed(() =>
    patterns.value.filter(p => p.frequency >= 5 && p.confidence >= 0.6)
  )

  // ========================================================================
  // FEEDBACK SYSTEM
  // ========================================================================

  /**
   * Record feedback
   */
  function recordFeedback(
    type: FeedbackRecord['type'],
    context: string,
    feedbackContent: string,
    originalResponse?: string
  ): FeedbackRecord {
    const record: FeedbackRecord = {
      id: `feedback_${Date.now()}`,
      timestamp: new Date(),
      type,
      context,
      feedback: feedbackContent,
      originalResponse,
      applied: false
    }

    feedback.value.push(record)

    // Keep feedback manageable
    if (feedback.value.length > 200) {
      feedback.value = feedback.value.slice(-200)
    }

    saveFeedback(feedback.value)

    // Learn from feedback
    applyFeedback(record)

    return record
  }

  /**
   * Apply learnings from feedback
   */
  function applyFeedback(record: FeedbackRecord): void {
    switch (record.type) {
      case 'positive':
        // Reinforce current behavior
        break

      case 'negative':
        // Learn to avoid similar responses
        learnPreference('avoidances', record.context, record.feedback, {
          source: 'explicit',
          example: record.originalResponse
        })
        break

      case 'correction':
        // Learn the correct approach
        learnPreference('communication', record.context, record.feedback, {
          source: 'explicit'
        })
        break

      case 'preference':
        // Explicit preference
        learnPreference('personality', record.context, record.feedback, {
          source: 'explicit',
          confidence: 0.9
        })
        break
    }

    record.applied = true
    saveFeedback(feedback.value)
  }

  /**
   * Get feedback summary
   */
  const feedbackSummary = computed(() => {
    const total = feedback.value.length
    const positive = feedback.value.filter(f => f.type === 'positive').length
    const negative = feedback.value.filter(f => f.type === 'negative').length
    const corrections = feedback.value.filter(f => f.type === 'correction').length

    return {
      total,
      positive,
      negative,
      corrections,
      positiveRatio: total > 0 ? positive / total : 0
    }
  })

  // ========================================================================
  // LEARNING INSIGHTS
  // ========================================================================

  /**
   * Get a summary of what SAM has learned
   */
  function getLearningSummary(): string {
    const parts: string[] = []

    // Communication style
    const commPrefs = getCategoryPreferences('communication')
    if (commPrefs.length > 0) {
      parts.push(`I've learned about your communication preferences: ${
        commPrefs.map(p => p.key).join(', ')
      }.`)
    }

    // Work patterns
    const schedulePatterns = getPatternsByType('schedule').filter(p => p.confidence >= 0.6)
    if (schedulePatterns.length > 0) {
      parts.push(`I've noticed these work patterns: ${
        schedulePatterns.map(p => p.description).join('; ')
      }.`)
    }

    // Coding preferences
    const codePrefs = getCategoryPreferences('coding')
    if (codePrefs.length > 0) {
      parts.push(`Your coding preferences: ${
        codePrefs.map(p => `${p.key}: ${p.value}`).join(', ')
      }.`)
    }

    // Things to avoid
    const avoidances = getCategoryPreferences('avoidances')
    if (avoidances.length > 0) {
      parts.push(`Things to avoid: ${avoidances.map(p => p.key).join(', ')}.`)
    }

    if (parts.length === 0) {
      return "I'm still learning about you. The more we interact, the better I'll understand your preferences."
    }

    return parts.join(' ')
  }

  /**
   * Generate system prompt additions based on learnings
   */
  function getLearnedSystemPrompt(): string {
    const parts: string[] = []

    // High-confidence preferences
    const highConf = confirmedPreferences.value
    if (highConf.length > 0) {
      parts.push('USER PREFERENCES (learned from interactions):')
      for (const pref of highConf) {
        parts.push(`- ${pref.key}: ${pref.value}`)
      }
    }

    // Avoidances
    const avoidances = getCategoryPreferences('avoidances')
    if (avoidances.length > 0) {
      parts.push('\nTHINGS TO AVOID:')
      for (const avoid of avoidances) {
        parts.push(`- ${avoid.key}: ${avoid.value}`)
      }
    }

    // Current patterns
    const current = currentPatterns.value
    if (current.length > 0) {
      parts.push('\nCURRENT CONTEXT (based on patterns):')
      for (const pattern of current) {
        parts.push(`- ${pattern.description}`)
      }
    }

    return parts.join('\n')
  }

  /**
   * Learning stats
   */
  const stats = computed((): LearningStats => {
    const recentFeedback = feedback.value.filter(f =>
      f.timestamp > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    )

    return {
      totalPreferences: preferences.value.length,
      highConfidencePreferences: confirmedPreferences.value.length,
      totalPatterns: patterns.value.length,
      feedbackReceived: feedback.value.length,
      adaptationsApplied: feedback.value.filter(f => f.applied).length,
      lastLearningUpdate: new Date(
        Math.max(
          ...preferences.value.map(p => p.learnedAt.getTime()),
          ...patterns.value.map(p => p.lastObserved.getTime()),
          0
        )
      )
    }
  })

  // ========================================================================
  // QUICK LEARNING HELPERS
  // ========================================================================

  /**
   * Learn that user likes something
   */
  function learnLikes(thing: string, example?: string): void {
    learnPreference('topics', thing, true, { source: 'observed', example })
  }

  /**
   * Learn that user dislikes something
   */
  function learnDislikes(thing: string, example?: string): void {
    learnPreference('avoidances', thing, true, { source: 'observed', example })
  }

  /**
   * Learn a coding preference
   */
  function learnCodingPref(key: string, value: string): void {
    learnPreference('coding', key, value, { source: 'observed' })
  }

  /**
   * Learn a schedule pattern
   */
  function learnSchedule(description: string): void {
    const now = new Date()
    const hour = now.getHours()
    const timeOfDay = hour < 12 ? 'morning' :
                      hour < 17 ? 'afternoon' :
                      hour < 21 ? 'evening' : 'night'

    observePattern('schedule', description, {
      timeOfDay,
      dayOfWeek: now.getDay()
    })
  }

  // Save on changes
  watch(preferences, () => savePreferences(preferences.value), { deep: true })
  watch(patterns, () => savePatterns(patterns.value), { deep: true })
  watch(feedback, () => saveFeedback(feedback.value), { deep: true })

  return {
    // State
    preferences,
    patterns,
    feedback,
    confirmedPreferences,
    currentPatterns,
    significantPatterns,
    feedbackSummary,
    stats,

    // Preferences
    learnPreference,
    getPreference,
    getCategoryPreferences,
    confirmPreference,
    rejectPreference,

    // Patterns
    observePattern,
    getPatternsByType,

    // Feedback
    recordFeedback,

    // Insights
    getLearningSummary,
    getLearnedSystemPrompt,

    // Quick helpers
    learnLikes,
    learnDislikes,
    learnCodingPref,
    learnSchedule
  }
}

export type UseLearningReturn = ReturnType<typeof useLearning>
