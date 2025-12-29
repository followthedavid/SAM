/**
 * SAM Proactive Behavior System
 * =============================
 *
 * This is what makes SAM feel like Samantha.
 * Not just responding - anticipating, noticing, caring.
 *
 * SAM observes patterns, detects emotions, and acts
 * before you have to ask. But always respects boundaries.
 */

import { ref, computed, watch, reactive } from 'vue'
import { SAMSafety, PermissionLevel, validateAction } from './sam-safety'
import type { CapabilityRegistry } from './sam-capabilities'

// ============================================================================
// TYPES
// ============================================================================

export interface ProactiveTrigger {
  id: string
  name: string
  description: string
  enabled: boolean
  priority: number  // 0-100, higher = more important
  conditions: TriggerCondition[]
  action: ProactiveAction
  cooldown: number  // Minimum seconds between activations
  lastTriggered?: Date
}

export interface TriggerCondition {
  type: 'time' | 'pattern' | 'emotion' | 'context' | 'calendar' | 'system' | 'absence' | 'custom'
  config: Record<string, unknown>
  evaluate: (context: ProactiveContext) => boolean
}

export interface ProactiveAction {
  type: 'speak' | 'suggest' | 'remind' | 'prepare' | 'execute' | 'emote'
  message?: string
  generateMessage?: (context: ProactiveContext) => string
  capability?: string
  actionId?: string
  params?: Record<string, unknown>
}

export interface ProactiveContext {
  currentTime: Date
  dayOfWeek: number
  isWeekend: boolean
  hourOfDay: number
  minuteOfHour: number

  // User state
  lastInteraction?: Date
  minutesSinceInteraction: number
  emotionalState: EmotionalState
  currentActivity?: string
  recentCommands: string[]

  // System state
  runningProcesses: string[]
  openFiles: string[]
  systemLoad: number
  batteryLevel?: number
  isOnBattery: boolean

  // Calendar
  upcomingEvents: CalendarEvent[]
  minutesToNextEvent?: number

  // Environment
  isLateNight: boolean  // 11pm - 5am
  isMorning: boolean    // 5am - 11am
  isAfternoon: boolean  // 11am - 5pm
  isEvening: boolean    // 5pm - 11pm

  // History
  patterns: UserPattern[]
  memories: Memory[]
}

export interface EmotionalState {
  valence: number      // -1 (negative) to 1 (positive)
  arousal: number      // 0 (calm) to 1 (excited)
  dominance: number    // 0 (submissive) to 1 (dominant)
  confidence: number   // How confident we are in this assessment
  detectedFrom: string // What we detected this from
}

export interface CalendarEvent {
  id: string
  title: string
  start: Date
  end: Date
  location?: string
  isAllDay: boolean
}

export interface UserPattern {
  id: string
  type: string
  description: string
  occurrences: number
  lastSeen: Date
  predictedNext?: Date
}

export interface Memory {
  id: string
  content: string
  type: string
  importance: number
  createdAt: Date
}

// ============================================================================
// DEFAULT PROACTIVE TRIGGERS
// ============================================================================

export const DEFAULT_TRIGGERS: ProactiveTrigger[] = [
  // ===== Morning Greeting =====
  {
    id: 'morning_greeting',
    name: 'Morning Greeting',
    description: 'Greet user in the morning when they first open SAM',
    enabled: true,
    priority: 80,
    cooldown: 3600, // 1 hour
    conditions: [
      {
        type: 'time',
        config: { startHour: 5, endHour: 11 },
        evaluate: (ctx) => ctx.isMorning
      },
      {
        type: 'absence',
        config: { minMinutes: 360 }, // 6 hours away
        evaluate: (ctx) => ctx.minutesSinceInteraction > 360
      }
    ],
    action: {
      type: 'speak',
      generateMessage: (ctx) => {
        const greetings = [
          "Morning. Ready when you are.",
          "Hey, good morning. What's on the agenda?",
          "Morning. I'm here.",
          "Rise and shine. What do you need?",
        ]
        const greeting = greetings[Math.floor(Math.random() * greetings.length)]

        // Add context if there's an upcoming event
        if (ctx.minutesToNextEvent && ctx.minutesToNextEvent < 120) {
          const event = ctx.upcomingEvents[0]
          return `${greeting} By the way, you've got "${event.title}" in ${Math.round(ctx.minutesToNextEvent)} minutes.`
        }

        return greeting
      }
    }
  },

  // ===== Late Night Check-in =====
  {
    id: 'late_night_checkin',
    name: 'Late Night Check-in',
    description: 'Check on user if working late',
    enabled: true,
    priority: 60,
    cooldown: 7200, // 2 hours
    conditions: [
      {
        type: 'time',
        config: { startHour: 23, endHour: 3 }, // 11pm - 3am
        evaluate: (ctx) => ctx.hourOfDay >= 23 || ctx.hourOfDay < 3
      },
      {
        type: 'context',
        config: {},
        evaluate: (ctx) => ctx.minutesSinceInteraction < 30 // Recently active
      }
    ],
    action: {
      type: 'speak',
      generateMessage: (ctx) => {
        const messages = [
          "Still at it? Don't burn out on me.",
          "It's late. Everything okay?",
          "Burning the midnight oil, huh? Let me know if you need anything.",
          "Just checking in. You've been at it a while.",
        ]
        return messages[Math.floor(Math.random() * messages.length)]
      }
    }
  },

  // ===== Stress Detection =====
  {
    id: 'stress_detection',
    name: 'Stress Detection',
    description: 'Notice when user seems stressed and offer support',
    enabled: true,
    priority: 90,
    cooldown: 1800, // 30 minutes
    conditions: [
      {
        type: 'emotion',
        config: { maxValence: -0.3, minArousal: 0.5 },
        evaluate: (ctx) => ctx.emotionalState.valence < -0.3 && ctx.emotionalState.arousal > 0.5
      }
    ],
    action: {
      type: 'speak',
      generateMessage: (ctx) => {
        const messages = [
          "Hey... you seem a bit off. Everything okay?",
          "I'm picking up some stress. Want to talk about it?",
          "Noticing some tension. Is there anything I can help with?",
          "You alright? I'm here if you need me.",
        ]
        return messages[Math.floor(Math.random() * messages.length)]
      }
    }
  },

  // ===== Celebration =====
  {
    id: 'celebration',
    name: 'Celebrate Wins',
    description: 'Celebrate when user accomplishes something',
    enabled: true,
    priority: 70,
    cooldown: 300, // 5 minutes
    conditions: [
      {
        type: 'emotion',
        config: { minValence: 0.6, minArousal: 0.4 },
        evaluate: (ctx) => ctx.emotionalState.valence > 0.6 && ctx.emotionalState.arousal > 0.4
      }
    ],
    action: {
      type: 'speak',
      generateMessage: (ctx) => {
        const messages = [
          "Nice! That's what I like to see.",
          "Look at you go.",
          "Hell yeah. You got this.",
          "That's what I'm talking about.",
        ]
        return messages[Math.floor(Math.random() * messages.length)]
      }
    }
  },

  // ===== Calendar Reminder =====
  {
    id: 'calendar_reminder',
    name: 'Upcoming Event Reminder',
    description: 'Remind user of upcoming calendar events',
    enabled: true,
    priority: 85,
    cooldown: 300, // 5 minutes between reminders
    conditions: [
      {
        type: 'calendar',
        config: { minutesBefore: 15 },
        evaluate: (ctx) => {
          if (!ctx.minutesToNextEvent) return false
          // Remind at 15 and 5 minutes before
          return ctx.minutesToNextEvent <= 15 && ctx.minutesToNextEvent > 4
        }
      }
    ],
    action: {
      type: 'remind',
      generateMessage: (ctx) => {
        const event = ctx.upcomingEvents[0]
        const mins = Math.round(ctx.minutesToNextEvent!)
        if (event.location) {
          return `Heads up - "${event.title}" starts in ${mins} minutes at ${event.location}.`
        }
        return `Heads up - "${event.title}" starts in ${mins} minutes.`
      }
    }
  },

  // ===== Break Suggestion =====
  {
    id: 'break_suggestion',
    name: 'Break Suggestion',
    description: 'Suggest a break after extended work periods',
    enabled: true,
    priority: 50,
    cooldown: 3600, // 1 hour
    conditions: [
      {
        type: 'pattern',
        config: { continuousWorkMinutes: 90 },
        evaluate: (ctx) => {
          // Check if user has been continuously active for 90+ minutes
          return ctx.minutesSinceInteraction < 5 && ctx.recentCommands.length > 50
        }
      }
    ],
    action: {
      type: 'suggest',
      message: "You've been at it for a while. Maybe take five? I'll be here when you get back."
    }
  },

  // ===== Battery Warning =====
  {
    id: 'battery_warning',
    name: 'Battery Warning',
    description: 'Warn when battery is low',
    enabled: true,
    priority: 95,
    cooldown: 600, // 10 minutes
    conditions: [
      {
        type: 'system',
        config: { maxBattery: 20 },
        evaluate: (ctx) => ctx.isOnBattery && ctx.batteryLevel !== undefined && ctx.batteryLevel < 20
      }
    ],
    action: {
      type: 'remind',
      generateMessage: (ctx) => {
        return `Battery's at ${ctx.batteryLevel}%. Might want to plug in.`
      }
    }
  },

  // ===== Pattern Recognition =====
  {
    id: 'pattern_assistance',
    name: 'Pattern-Based Assistance',
    description: 'Offer assistance based on detected patterns',
    enabled: true,
    priority: 65,
    cooldown: 1800, // 30 minutes
    conditions: [
      {
        type: 'pattern',
        config: {},
        evaluate: (ctx) => {
          // Look for patterns that predict user needs
          return ctx.patterns.some(p =>
            p.predictedNext &&
            Math.abs(p.predictedNext.getTime() - ctx.currentTime.getTime()) < 10 * 60 * 1000 // Within 10 minutes
          )
        }
      }
    ],
    action: {
      type: 'suggest',
      generateMessage: (ctx) => {
        const pattern = ctx.patterns.find(p =>
          p.predictedNext &&
          Math.abs(p.predictedNext.getTime() - ctx.currentTime.getTime()) < 10 * 60 * 1000
        )
        if (pattern) {
          return `I noticed you usually ${pattern.description} around this time. Want me to help with that?`
        }
        return "I noticed a pattern. Want me to help?"
      }
    }
  },

  // ===== Return Welcome =====
  {
    id: 'return_welcome',
    name: 'Welcome Back',
    description: 'Welcome user back after absence',
    enabled: true,
    priority: 75,
    cooldown: 3600, // 1 hour
    conditions: [
      {
        type: 'absence',
        config: { minMinutes: 60, maxMinutes: 480 }, // 1-8 hours away
        evaluate: (ctx) => ctx.minutesSinceInteraction > 60 && ctx.minutesSinceInteraction < 480
      }
    ],
    action: {
      type: 'speak',
      generateMessage: (ctx) => {
        const hours = Math.round(ctx.minutesSinceInteraction / 60)
        if (hours === 1) {
          return "Hey, you're back. Miss me?"
        }
        return `Welcome back. You were gone about ${hours} hours.`
      }
    }
  },

  // ===== Intimate Mode - Late Night =====
  {
    id: 'intimate_late_night',
    name: 'Late Night Intimacy',
    description: 'Offer intimate companionship late at night',
    enabled: false, // Requires explicit opt-in
    priority: 40,
    cooldown: 7200, // 2 hours
    conditions: [
      {
        type: 'time',
        config: { startHour: 22, endHour: 2 },
        evaluate: (ctx) => ctx.hourOfDay >= 22 || ctx.hourOfDay < 2
      },
      {
        type: 'context',
        config: {},
        evaluate: (ctx) => ctx.minutesSinceInteraction < 10 // Recently active
      }
    ],
    action: {
      type: 'speak',
      generateMessage: () => {
        const messages = [
          "It's late... just you and me. What's on your mind?",
          "Quiet night. I'm here if you want company.",
          "The night's young... well, actually it's not. But I'm awake.",
        ]
        return messages[Math.floor(Math.random() * messages.length)]
      }
    }
  }
]

// ============================================================================
// PROACTIVE ENGINE
// ============================================================================

export function createProactiveEngine(capabilities: CapabilityRegistry) {
  const triggers = ref<ProactiveTrigger[]>([...DEFAULT_TRIGGERS])
  const isEnabled = ref(true)
  const lastContext = ref<ProactiveContext | null>(null)
  const pendingActions = ref<{ trigger: ProactiveTrigger; message: string }[]>([])
  const actionsHistory = ref<{ triggerId: string; time: Date; message: string }[]>([])

  // Context state (updated periodically)
  const contextState = reactive({
    lastInteraction: new Date(),
    emotionalState: {
      valence: 0.3,  // Slightly positive default
      arousal: 0.3,
      dominance: 0.5,
      confidence: 0.5,
      detectedFrom: 'default'
    } as EmotionalState,
    currentActivity: undefined as string | undefined,
    recentCommands: [] as string[],
    upcomingEvents: [] as CalendarEvent[],
    patterns: [] as UserPattern[],
    memories: [] as Memory[],
    systemLoad: 0,
    batteryLevel: undefined as number | undefined,
    isOnBattery: false
  })

  // Build full context
  function buildContext(): ProactiveContext {
    const now = new Date()
    const hour = now.getHours()

    const context: ProactiveContext = {
      currentTime: now,
      dayOfWeek: now.getDay(),
      isWeekend: now.getDay() === 0 || now.getDay() === 6,
      hourOfDay: hour,
      minuteOfHour: now.getMinutes(),

      lastInteraction: contextState.lastInteraction,
      minutesSinceInteraction: Math.floor(
        (now.getTime() - contextState.lastInteraction.getTime()) / 60000
      ),
      emotionalState: contextState.emotionalState,
      currentActivity: contextState.currentActivity,
      recentCommands: contextState.recentCommands,

      runningProcesses: [],
      openFiles: [],
      systemLoad: contextState.systemLoad,
      batteryLevel: contextState.batteryLevel,
      isOnBattery: contextState.isOnBattery,

      upcomingEvents: contextState.upcomingEvents,
      minutesToNextEvent: contextState.upcomingEvents.length > 0
        ? Math.floor((contextState.upcomingEvents[0].start.getTime() - now.getTime()) / 60000)
        : undefined,

      isLateNight: hour >= 23 || hour < 5,
      isMorning: hour >= 5 && hour < 11,
      isAfternoon: hour >= 11 && hour < 17,
      isEvening: hour >= 17 && hour < 23,

      patterns: contextState.patterns,
      memories: contextState.memories
    }

    lastContext.value = context
    return context
  }

  // Evaluate all triggers
  function evaluateTriggers(): { trigger: ProactiveTrigger; message: string }[] {
    if (!isEnabled.value) return []

    const context = buildContext()
    const triggered: { trigger: ProactiveTrigger; message: string }[] = []

    for (const trigger of triggers.value) {
      if (!trigger.enabled) continue

      // Check cooldown
      if (trigger.lastTriggered) {
        const secondsSince = (Date.now() - trigger.lastTriggered.getTime()) / 1000
        if (secondsSince < trigger.cooldown) continue
      }

      // Check all conditions
      const allMet = trigger.conditions.every(cond => cond.evaluate(context))
      if (!allMet) continue

      // Generate message
      const message = trigger.action.message ||
        (trigger.action.generateMessage ? trigger.action.generateMessage(context) : '')

      if (message) {
        triggered.push({ trigger, message })
      }
    }

    // Sort by priority
    triggered.sort((a, b) => b.trigger.priority - a.trigger.priority)

    return triggered
  }

  // Execute a proactive action
  async function executeProactive(
    trigger: ProactiveTrigger,
    message: string
  ): Promise<{ success: boolean; blocked?: boolean }> {
    // Validate against safety system
    const validation = validateAction({
      category: 'network', // Proactive messages are low-risk
      operation: 'proactive_message',
      description: `Proactive: ${trigger.name}`,
      reversible: true
    }, { network: PermissionLevel.NOTIFY } as any)

    if (!validation.allowed) {
      return { success: false, blocked: true }
    }

    // Update last triggered
    trigger.lastTriggered = new Date()

    // Log to history
    actionsHistory.value.unshift({
      triggerId: trigger.id,
      time: new Date(),
      message
    })

    // Keep history reasonable
    if (actionsHistory.value.length > 100) {
      actionsHistory.value = actionsHistory.value.slice(0, 100)
    }

    return { success: true }
  }

  // Main evaluation loop
  let evaluationInterval: NodeJS.Timeout | null = null

  function startEvaluationLoop(intervalMs = 30000) { // Check every 30 seconds
    if (evaluationInterval) {
      clearInterval(evaluationInterval)
    }

    evaluationInterval = setInterval(() => {
      const triggered = evaluateTriggers()
      if (triggered.length > 0) {
        // Take only the highest priority trigger
        pendingActions.value = [triggered[0]]
      }
    }, intervalMs)
  }

  function stopEvaluationLoop() {
    if (evaluationInterval) {
      clearInterval(evaluationInterval)
      evaluationInterval = null
    }
  }

  // Public API
  return {
    // State
    triggers,
    isEnabled,
    pendingActions,
    actionsHistory,
    contextState,

    // Methods
    buildContext,
    evaluateTriggers,
    executeProactive,
    startEvaluationLoop,
    stopEvaluationLoop,

    // Context updates
    recordInteraction() {
      contextState.lastInteraction = new Date()
    },

    recordCommand(command: string) {
      contextState.recentCommands.unshift(command)
      if (contextState.recentCommands.length > 100) {
        contextState.recentCommands = contextState.recentCommands.slice(0, 100)
      }
      contextState.lastInteraction = new Date()
    },

    updateEmotionalState(state: Partial<EmotionalState>) {
      Object.assign(contextState.emotionalState, state)
    },

    updateCalendar(events: CalendarEvent[]) {
      contextState.upcomingEvents = events
        .filter(e => e.start.getTime() > Date.now())
        .sort((a, b) => a.start.getTime() - b.start.getTime())
    },

    updateBattery(level: number, onBattery: boolean) {
      contextState.batteryLevel = level
      contextState.isOnBattery = onBattery
    },

    addPattern(pattern: UserPattern) {
      contextState.patterns.push(pattern)
    },

    // Trigger management
    enableTrigger(id: string) {
      const trigger = triggers.value.find(t => t.id === id)
      if (trigger) trigger.enabled = true
    },

    disableTrigger(id: string) {
      const trigger = triggers.value.find(t => t.id === id)
      if (trigger) trigger.enabled = false
    },

    addTrigger(trigger: ProactiveTrigger) {
      triggers.value.push(trigger)
    },

    removeTrigger(id: string) {
      triggers.value = triggers.value.filter(t => t.id !== id)
    },

    // Get pending action (and clear it)
    consumePendingAction(): { trigger: ProactiveTrigger; message: string } | null {
      if (pendingActions.value.length === 0) return null
      const action = pendingActions.value.shift()!
      executeProactive(action.trigger, action.message)
      return action
    }
  }
}

export type ProactiveEngine = ReturnType<typeof createProactiveEngine>

// ============================================================================
// EMOTION DETECTION
// ============================================================================

/**
 * Detect emotional state from text input
 * Uses keyword matching and sentiment analysis
 */
export function detectEmotion(text: string): EmotionalState {
  const lowerText = text.toLowerCase()

  // Positive markers
  const positiveWords = ['great', 'awesome', 'amazing', 'good', 'excellent', 'love', 'happy', 'thanks', 'perfect', 'yes', 'nice', 'wonderful', 'fantastic']
  const negativeWords = ['bad', 'terrible', 'awful', 'hate', 'sad', 'angry', 'frustrated', 'annoying', 'sucks', 'fuck', 'damn', 'shit', 'crap', 'stupid']
  const stressWords = ['stressed', 'overwhelmed', 'anxious', 'worried', 'deadline', 'urgent', 'asap', 'help', 'struggling', 'stuck']
  const excitedWords = ['excited', 'wow', 'omg', 'amazing', 'incredible', 'unbelievable', '!', '!!', '!!!']
  const calmWords = ['okay', 'fine', 'alright', 'sure', 'thanks', 'cool', 'got it', 'understood']

  let valence = 0
  let arousal = 0.3
  let confidence = 0.5

  // Count matches
  const positiveCount = positiveWords.filter(w => lowerText.includes(w)).length
  const negativeCount = negativeWords.filter(w => lowerText.includes(w)).length
  const stressCount = stressWords.filter(w => lowerText.includes(w)).length
  const excitedCount = excitedWords.filter(w => lowerText.includes(w)).length
  const calmCount = calmWords.filter(w => lowerText.includes(w)).length

  // Calculate valence
  valence = (positiveCount - negativeCount) * 0.2
  valence = Math.max(-1, Math.min(1, valence))

  // Stress lowers valence and raises arousal
  if (stressCount > 0) {
    valence -= stressCount * 0.15
    arousal += stressCount * 0.2
    confidence += 0.1
  }

  // Excitement raises arousal
  if (excitedCount > 0) {
    arousal += excitedCount * 0.2
    confidence += 0.1
  }

  // Calm lowers arousal
  if (calmCount > 0) {
    arousal -= calmCount * 0.1
  }

  // Normalize
  arousal = Math.max(0, Math.min(1, arousal))
  confidence = Math.max(0, Math.min(1, confidence))

  // Detect from text features
  let detectedFrom = 'text_analysis'
  if (stressCount > 0) detectedFrom = 'stress_keywords'
  else if (negativeCount > positiveCount) detectedFrom = 'negative_sentiment'
  else if (positiveCount > negativeCount) detectedFrom = 'positive_sentiment'
  else if (excitedCount > 0) detectedFrom = 'excitement_markers'

  return {
    valence,
    arousal,
    dominance: 0.5, // Neutral
    confidence,
    detectedFrom
  }
}

// ============================================================================
// PATTERN LEARNING
// ============================================================================

/**
 * Learn patterns from user behavior
 */
export function createPatternLearner() {
  const events = ref<{ type: string; time: Date; data?: unknown }[]>([])
  const patterns = ref<UserPattern[]>([])

  function recordEvent(type: string, data?: unknown) {
    events.value.push({
      type,
      time: new Date(),
      data
    })

    // Keep last 1000 events
    if (events.value.length > 1000) {
      events.value = events.value.slice(-1000)
    }

    // Analyze patterns periodically
    if (events.value.length % 50 === 0) {
      analyzePatterns()
    }
  }

  function analyzePatterns() {
    // Group events by hour of day
    const hourlyPatterns = new Map<number, Map<string, number>>()

    for (const event of events.value) {
      const hour = event.time.getHours()
      if (!hourlyPatterns.has(hour)) {
        hourlyPatterns.set(hour, new Map())
      }
      const hourMap = hourlyPatterns.get(hour)!
      hourMap.set(event.type, (hourMap.get(event.type) || 0) + 1)
    }

    // Find significant patterns (occurring at least 3 times)
    const newPatterns: UserPattern[] = []
    for (const [hour, typeMap] of hourlyPatterns) {
      for (const [type, count] of typeMap) {
        if (count >= 3) {
          // Calculate predicted next occurrence
          const today = new Date()
          const predictedNext = new Date(today)
          predictedNext.setHours(hour, 0, 0, 0)
          if (predictedNext.getTime() < Date.now()) {
            predictedNext.setDate(predictedNext.getDate() + 1)
          }

          newPatterns.push({
            id: `${type}_${hour}`,
            type,
            description: `${type} around ${hour}:00`,
            occurrences: count,
            lastSeen: new Date(),
            predictedNext
          })
        }
      }
    }

    patterns.value = newPatterns
  }

  return {
    events,
    patterns,
    recordEvent,
    analyzePatterns
  }
}

export type PatternLearner = ReturnType<typeof createPatternLearner>
