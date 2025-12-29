/**
 * useProactiveNotifications - AI-Initiated Communication
 *
 * Allows SAM to proactively reach out when something important happens.
 * Like Samantha noticing Theodore has a meeting coming up, or that
 * something interesting happened while he was away.
 *
 * "Hey... just wanted to let you know something came up."
 */

import { ref, computed, watch, onUnmounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { usePersonality } from './usePersonality'
import { useTTS } from './useTTS'
import { useUniversalMemory } from './useUniversalMemory'
import { useAuditLog } from './useAuditLog'

// ============================================================================
// TYPES
// ============================================================================

export type NotificationType =
  | 'reminder'        // Calendar/time-based
  | 'observation'     // Something SAM noticed
  | 'achievement'     // User accomplished something
  | 'warning'         // Something needs attention
  | 'opportunity'     // Proactive suggestion
  | 'check_in'        // Just checking in
  | 'update'          // Status update on running task
  | 'insight'         // SAM learned something interesting

export type NotificationPriority = 'whisper' | 'normal' | 'important' | 'urgent'

export interface ProactiveNotification {
  id: string
  type: NotificationType
  priority: NotificationPriority
  title: string
  message: string
  spokenMessage?: string    // Alternative text for TTS
  createdAt: Date
  expiresAt?: Date
  dismissed: boolean
  spoken: boolean
  data?: Record<string, unknown>
  action?: {
    label: string
    handler: string         // Function name to call
    params?: unknown
  }
}

export interface NotificationTrigger {
  id: string
  name: string
  enabled: boolean
  type: 'time' | 'event' | 'condition'
  config: {
    // Time-based
    cronPattern?: string
    intervalMinutes?: number
    // Event-based
    eventType?: string
    // Condition-based
    condition?: string
    checkIntervalSeconds?: number
  }
  lastTriggered?: Date
  notification: Omit<ProactiveNotification, 'id' | 'createdAt' | 'dismissed' | 'spoken'>
}

// ============================================================================
// PERSONALITY-BASED MESSAGES
// ============================================================================

const NOTIFICATION_TEMPLATES = {
  reminder: {
    gentle: [
      "Hey... don't forget about {event}.",
      "Just a heads up - {event} is coming up.",
      "Thought I'd remind you: {event}.",
      "You've got {event} soon. Just saying."
    ],
    urgent: [
      "Hey, {event} is in {time}. You should probably get ready.",
      "{event} is about to start. Don't be late.",
      "Time check: {event} in {time}."
    ]
  },
  observation: {
    positive: [
      "I noticed something interesting...",
      "Hey, I was looking at things and...",
      "So I noticed you've been {observation}. Nice.",
      "Just observed something worth mentioning..."
    ],
    concerning: [
      "I don't want to alarm you, but...",
      "Something caught my attention...",
      "You might want to look at this..."
    ]
  },
  achievement: [
    "Well, well... look at you. {achievement}.",
    "Not bad. {achievement}.",
    "I see you. {achievement}. I'm impressed.",
    "{achievement}. You're on fire today.",
    "That's what I'm talking about. {achievement}."
  ],
  warning: [
    "Heads up - {warning}.",
    "You should know: {warning}.",
    "I don't want to worry you, but {warning}.",
    "Something needs your attention: {warning}."
  ],
  opportunity: [
    "I've got an idea...",
    "What if we tried {suggestion}?",
    "I've been thinking... {suggestion}.",
    "Here's a thought: {suggestion}.",
    "You know what might work? {suggestion}."
  ],
  check_in: {
    morning: [
      "Morning. Ready to make today count?",
      "Rise and shine. What's on the agenda?",
      "New day, new opportunities. What are we tackling?"
    ],
    afternoon: [
      "How's it going? Making progress?",
      "Checking in. Need anything?",
      "Still at it? Let me know if you need backup."
    ],
    evening: [
      "Evening check-in. How'd today go?",
      "Wrapping up? Or just getting started?",
      "End of day. Anything we should review?"
    ],
    late: [
      "Burning the midnight oil, huh? I respect that.",
      "Late night? I'm here if you need me.",
      "Don't forget to rest. Even I take breaks... occasionally."
    ]
  },
  update: [
    "Quick update: {update}.",
    "Progress report: {update}.",
    "Just finished {update}. What's next?",
    "{update}. Moving on."
  ],
  insight: [
    "I learned something interesting about {topic}...",
    "So I've been analyzing {topic}, and...",
    "Here's something you might find useful about {topic}.",
    "I noticed a pattern with {topic}..."
  ]
}

// ============================================================================
// STORAGE
// ============================================================================

const NOTIFICATIONS_KEY = 'warp_proactive_notifications'
const TRIGGERS_KEY = 'warp_notification_triggers'

function loadNotifications(): ProactiveNotification[] {
  try {
    const stored = localStorage.getItem(NOTIFICATIONS_KEY)
    if (stored) {
      return JSON.parse(stored).map((n: any) => ({
        ...n,
        createdAt: new Date(n.createdAt),
        expiresAt: n.expiresAt ? new Date(n.expiresAt) : undefined
      }))
    }
  } catch {}
  return []
}

function saveNotifications(notifications: ProactiveNotification[]): void {
  // Keep only last 100 notifications
  const toSave = notifications.slice(-100)
  localStorage.setItem(NOTIFICATIONS_KEY, JSON.stringify(toSave))
}

function loadTriggers(): NotificationTrigger[] {
  try {
    const stored = localStorage.getItem(TRIGGERS_KEY)
    if (stored) {
      return JSON.parse(stored).map((t: any) => ({
        ...t,
        lastTriggered: t.lastTriggered ? new Date(t.lastTriggered) : undefined
      }))
    }
  } catch {}
  return getDefaultTriggers()
}

function saveTriggers(triggers: NotificationTrigger[]): void {
  localStorage.setItem(TRIGGERS_KEY, JSON.stringify(triggers))
}

function getDefaultTriggers(): NotificationTrigger[] {
  return [
    {
      id: 'morning_checkin',
      name: 'Morning Check-in',
      enabled: true,
      type: 'time',
      config: { cronPattern: '0 9 * * *' },  // 9am daily
      notification: {
        type: 'check_in',
        priority: 'normal',
        title: 'Morning Check-in',
        message: 'Good morning. Ready to make today count?',
        spokenMessage: 'Morning. Ready to make today count?'
      }
    },
    {
      id: 'evening_checkin',
      name: 'Evening Check-in',
      enabled: true,
      type: 'time',
      config: { cronPattern: '0 18 * * *' },  // 6pm daily
      notification: {
        type: 'check_in',
        priority: 'whisper',
        title: 'Evening Check-in',
        message: 'Evening. How did today go?',
        spokenMessage: 'Evening check-in. How did today go?'
      }
    },
    {
      id: 'weekly_review',
      name: 'Weekly Review',
      enabled: true,
      type: 'time',
      config: { cronPattern: '0 17 * * 5' },  // Friday 5pm
      notification: {
        type: 'insight',
        priority: 'normal',
        title: 'Weekly Review',
        message: "It's Friday. Let's review what we accomplished this week.",
        spokenMessage: "It's Friday. Want to review what we accomplished this week?"
      }
    }
  ]
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useProactiveNotifications() {
  const personality = usePersonality()
  const tts = useTTS()
  const memory = useUniversalMemory()
  const auditLog = useAuditLog()

  const notifications = ref<ProactiveNotification[]>(loadNotifications())
  const triggers = ref<NotificationTrigger[]>(loadTriggers())
  const isEnabled = ref(true)
  const doNotDisturb = ref(false)
  const quietHoursStart = ref(22)  // 10pm
  const quietHoursEnd = ref(8)     // 8am

  let triggerCheckInterval: ReturnType<typeof setInterval> | null = null

  // ========================================================================
  // NOTIFICATION CREATION
  // ========================================================================

  /**
   * Create a new notification
   */
  function notify(
    type: NotificationType,
    options: {
      title: string
      message: string
      spokenMessage?: string
      priority?: NotificationPriority
      expiresInMinutes?: number
      data?: Record<string, unknown>
      action?: ProactiveNotification['action']
      speakImmediately?: boolean
    }
  ): ProactiveNotification {
    const notification: ProactiveNotification = {
      id: `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      priority: options.priority || 'normal',
      title: options.title,
      message: options.message,
      spokenMessage: options.spokenMessage,
      createdAt: new Date(),
      expiresAt: options.expiresInMinutes
        ? new Date(Date.now() + options.expiresInMinutes * 60 * 1000)
        : undefined,
      dismissed: false,
      spoken: false,
      data: options.data,
      action: options.action
    }

    notifications.value.push(notification)
    saveNotifications(notifications.value)

    // Speak if enabled and not in quiet hours
    if (options.speakImmediately !== false && shouldSpeak(notification)) {
      speakNotification(notification)
    }

    // Show system notification for important/urgent
    if (notification.priority === 'important' || notification.priority === 'urgent') {
      showSystemNotification(notification)
    }

    auditLog.log('notification_created', `SAM notification: ${type}`, {
      details: { title: options.title },
      riskLevel: 'low'
    })

    return notification
  }

  /**
   * Check if we should speak a notification
   */
  function shouldSpeak(notification: ProactiveNotification): boolean {
    if (!isEnabled.value || doNotDisturb.value) return false

    // Check quiet hours
    const hour = new Date().getHours()
    if (quietHoursStart.value < quietHoursEnd.value) {
      // Simple case: e.g., 22-8 doesn't wrap
      if (hour >= quietHoursStart.value || hour < quietHoursEnd.value) {
        return notification.priority === 'urgent'
      }
    } else {
      // Wrapping case: e.g., 22-8 wraps around midnight
      if (hour >= quietHoursStart.value || hour < quietHoursEnd.value) {
        return notification.priority === 'urgent'
      }
    }

    // Whisper notifications only speak if TTS is already active
    if (notification.priority === 'whisper') {
      return tts.isSpeaking.value
    }

    return true
  }

  /**
   * Speak a notification
   */
  async function speakNotification(notification: ProactiveNotification): Promise<void> {
    const text = notification.spokenMessage || notification.message

    // Add personality intro for certain types
    let spokenText = text
    if (notification.type === 'observation' || notification.type === 'insight') {
      spokenText = `${personality.getPhrase('thinking')}... ${text}`
    }

    const emotion = notification.type === 'warning' ? 'serious' :
                    notification.type === 'achievement' ? 'happy' :
                    notification.type === 'check_in' ? 'neutral' :
                    'neutral'

    await tts.speak(spokenText, {
      emotion: emotion as any,
      priority: notification.priority === 'urgent' ? 'interrupt' : 'normal'
    })

    notification.spoken = true
    saveNotifications(notifications.value)
  }

  /**
   * Show system notification
   */
  async function showSystemNotification(notification: ProactiveNotification): Promise<void> {
    try {
      const persona = personality.persona
      await invoke('execute_shell', {
        command: `osascript -e 'display notification "${notification.message.replace(/"/g, '\\"')}" with title "${persona.name}" subtitle "${notification.title.replace(/"/g, '\\"')}"'`,
        cwd: undefined
      })
    } catch (error) {
      console.error('[Notifications] System notification failed:', error)
    }
  }

  // ========================================================================
  // TEMPLATE-BASED NOTIFICATIONS
  // ========================================================================

  /**
   * Create a reminder notification
   */
  function remind(event: string, inMinutes?: number): ProactiveNotification {
    const templates = inMinutes && inMinutes < 15
      ? NOTIFICATION_TEMPLATES.reminder.urgent
      : NOTIFICATION_TEMPLATES.reminder.gentle

    const template = templates[Math.floor(Math.random() * templates.length)]
    const message = template
      .replace('{event}', event)
      .replace('{time}', inMinutes ? `${inMinutes} minutes` : 'soon')

    return notify('reminder', {
      title: 'Reminder',
      message,
      priority: inMinutes && inMinutes < 5 ? 'urgent' : 'normal',
      speakImmediately: true
    })
  }

  /**
   * Create an achievement notification
   */
  function celebrate(achievement: string): ProactiveNotification {
    const template = NOTIFICATION_TEMPLATES.achievement[
      Math.floor(Math.random() * NOTIFICATION_TEMPLATES.achievement.length)
    ]
    const message = template.replace('{achievement}', achievement)

    return notify('achievement', {
      title: 'Nice Work',
      message,
      priority: 'normal',
      speakImmediately: true
    })
  }

  /**
   * Create a warning notification
   */
  function warn(warning: string, urgent: boolean = false): ProactiveNotification {
    const template = NOTIFICATION_TEMPLATES.warning[
      Math.floor(Math.random() * NOTIFICATION_TEMPLATES.warning.length)
    ]
    const message = template.replace('{warning}', warning)

    return notify('warning', {
      title: urgent ? 'Urgent' : 'Heads Up',
      message,
      priority: urgent ? 'urgent' : 'important',
      speakImmediately: true
    })
  }

  /**
   * Create a suggestion notification
   */
  function suggest(suggestion: string): ProactiveNotification {
    const template = NOTIFICATION_TEMPLATES.opportunity[
      Math.floor(Math.random() * NOTIFICATION_TEMPLATES.opportunity.length)
    ]
    const message = template.replace('{suggestion}', suggestion)

    return notify('opportunity', {
      title: 'Idea',
      message,
      priority: 'whisper',
      speakImmediately: true
    })
  }

  /**
   * Create a check-in notification based on time of day
   */
  function checkIn(): ProactiveNotification {
    const hour = new Date().getHours()
    let templates: string[]

    if (hour >= 5 && hour < 12) {
      templates = NOTIFICATION_TEMPLATES.check_in.morning
    } else if (hour >= 12 && hour < 17) {
      templates = NOTIFICATION_TEMPLATES.check_in.afternoon
    } else if (hour >= 17 && hour < 22) {
      templates = NOTIFICATION_TEMPLATES.check_in.evening
    } else {
      templates = NOTIFICATION_TEMPLATES.check_in.late
    }

    const message = templates[Math.floor(Math.random() * templates.length)]

    return notify('check_in', {
      title: 'Check-in',
      message,
      priority: 'whisper',
      speakImmediately: true
    })
  }

  /**
   * Share an insight
   */
  function shareInsight(topic: string, insight: string): ProactiveNotification {
    const template = NOTIFICATION_TEMPLATES.insight[
      Math.floor(Math.random() * NOTIFICATION_TEMPLATES.insight.length)
    ]
    const title = template.replace('{topic}', topic)

    return notify('insight', {
      title,
      message: insight,
      priority: 'normal',
      speakImmediately: true
    })
  }

  // ========================================================================
  // NOTIFICATION MANAGEMENT
  // ========================================================================

  /**
   * Dismiss a notification
   */
  function dismiss(notificationId: string): void {
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.dismissed = true
      saveNotifications(notifications.value)
    }
  }

  /**
   * Dismiss all notifications
   */
  function dismissAll(): void {
    notifications.value.forEach(n => n.dismissed = true)
    saveNotifications(notifications.value)
  }

  /**
   * Get active (undismissed, unexpired) notifications
   */
  const activeNotifications = computed(() => {
    const now = new Date()
    return notifications.value.filter(n =>
      !n.dismissed &&
      (!n.expiresAt || n.expiresAt > now)
    )
  })

  // ========================================================================
  // TRIGGER MANAGEMENT
  // ========================================================================

  /**
   * Check and fire triggers
   */
  function checkTriggers(): void {
    const now = new Date()

    for (const trigger of triggers.value) {
      if (!trigger.enabled) continue

      let shouldFire = false

      switch (trigger.type) {
        case 'time':
          if (trigger.config.intervalMinutes) {
            const lastRun = trigger.lastTriggered || new Date(0)
            const elapsed = (now.getTime() - lastRun.getTime()) / 1000 / 60
            shouldFire = elapsed >= trigger.config.intervalMinutes
          } else if (trigger.config.cronPattern) {
            shouldFire = matchesCron(trigger.config.cronPattern, now, trigger.lastTriggered)
          }
          break

        case 'event':
          // Event-based triggers are handled separately
          break

        case 'condition':
          // Condition-based triggers need evaluation
          break
      }

      if (shouldFire) {
        trigger.lastTriggered = now
        notify(trigger.notification.type, {
          ...trigger.notification,
          speakImmediately: true
        })
        saveTriggers(triggers.value)
      }
    }
  }

  /**
   * Simple cron matcher (minute, hour only for now)
   */
  function matchesCron(pattern: string, now: Date, lastRun?: Date): boolean {
    const parts = pattern.split(' ')
    if (parts.length < 5) return false

    const minute = parseInt(parts[0])
    const hour = parseInt(parts[1])

    // Check if it's the right time
    if (now.getMinutes() !== minute || now.getHours() !== hour) {
      return false
    }

    // Check if we already fired today
    if (lastRun) {
      const lastRunDate = new Date(lastRun)
      if (lastRunDate.toDateString() === now.toDateString() &&
          lastRunDate.getHours() === hour &&
          lastRunDate.getMinutes() === minute) {
        return false
      }
    }

    return true
  }

  /**
   * Add a trigger
   */
  function addTrigger(trigger: Omit<NotificationTrigger, 'id'>): NotificationTrigger {
    const newTrigger: NotificationTrigger = {
      ...trigger,
      id: `trigger_${Date.now()}`
    }
    triggers.value.push(newTrigger)
    saveTriggers(triggers.value)
    return newTrigger
  }

  /**
   * Remove a trigger
   */
  function removeTrigger(triggerId: string): void {
    triggers.value = triggers.value.filter(t => t.id !== triggerId)
    saveTriggers(triggers.value)
  }

  /**
   * Toggle a trigger
   */
  function toggleTrigger(triggerId: string): void {
    const trigger = triggers.value.find(t => t.id === triggerId)
    if (trigger) {
      trigger.enabled = !trigger.enabled
      saveTriggers(triggers.value)
    }
  }

  // ========================================================================
  // LIFECYCLE
  // ========================================================================

  /**
   * Start the notification system
   */
  function start(): void {
    if (triggerCheckInterval) return

    // Check triggers every minute
    triggerCheckInterval = setInterval(checkTriggers, 60 * 1000)

    // Initial check
    checkTriggers()

    console.log('[Notifications] Started')
  }

  /**
   * Stop the notification system
   */
  function stop(): void {
    if (triggerCheckInterval) {
      clearInterval(triggerCheckInterval)
      triggerCheckInterval = null
    }
    console.log('[Notifications] Stopped')
  }

  /**
   * Toggle Do Not Disturb
   */
  function toggleDND(): void {
    doNotDisturb.value = !doNotDisturb.value
    if (doNotDisturb.value) {
      tts.stop()
    }
  }

  // Clean up on unmount
  onUnmounted(() => {
    stop()
  })

  // Save on changes
  watch(notifications, () => saveNotifications(notifications.value), { deep: true })
  watch(triggers, () => saveTriggers(triggers.value), { deep: true })

  return {
    // State
    notifications,
    triggers,
    isEnabled,
    doNotDisturb,
    quietHoursStart,
    quietHoursEnd,
    activeNotifications,

    // Lifecycle
    start,
    stop,

    // Core notification methods
    notify,
    speakNotification,

    // Template-based notifications
    remind,
    celebrate,
    warn,
    suggest,
    checkIn,
    shareInsight,

    // Management
    dismiss,
    dismissAll,
    toggleDND,

    // Triggers
    addTrigger,
    removeTrigger,
    toggleTrigger,
    checkTriggers
  }
}

export type UseProactiveNotificationsReturn = ReturnType<typeof useProactiveNotifications>
