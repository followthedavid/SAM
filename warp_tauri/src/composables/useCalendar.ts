/**
 * useCalendar - Calendar Integration & Schedule Management
 *
 * Integrates with Apple Calendar, Google Calendar, and other providers.
 * Allows SAM to remind you of events and manage your schedule.
 *
 * "You've got a meeting in 15 minutes. Just thought you should know."
 */

import { ref, computed, watch, onUnmounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { useProactiveNotifications } from './useProactiveNotifications'
import { useAuditLog } from './useAuditLog'

// ============================================================================
// TYPES
// ============================================================================

export interface CalendarEvent {
  id: string
  title: string
  description?: string
  location?: string
  startTime: Date
  endTime: Date
  isAllDay: boolean
  calendar: string
  status: 'confirmed' | 'tentative' | 'cancelled'
  reminders: number[]  // Minutes before event
  attendees?: Array<{
    name: string
    email: string
    status: 'accepted' | 'declined' | 'tentative' | 'pending'
  }>
  url?: string
  notes?: string
  isRecurring: boolean
}

export interface CalendarConfig {
  enabled: boolean
  providers: Array<{
    type: 'apple' | 'google' | 'outlook' | 'caldav'
    name: string
    enabled: boolean
    credentials?: Record<string, string>
  }>
  defaultReminders: number[]  // Minutes before: [15, 60, 1440]
  fetchIntervalMinutes: number
  lookAheadDays: number
}

export interface DaySchedule {
  date: Date
  events: CalendarEvent[]
  freeSlots: Array<{ start: Date; end: Date; duration: number }>
}

// ============================================================================
// STORAGE
// ============================================================================

const CONFIG_KEY = 'warp_calendar_config'
const EVENTS_KEY = 'warp_calendar_events'

function loadConfig(): CalendarConfig {
  try {
    const stored = localStorage.getItem(CONFIG_KEY)
    if (stored) return JSON.parse(stored)
  } catch {}
  return {
    enabled: true,
    providers: [
      { type: 'apple', name: 'Apple Calendar', enabled: true }
    ],
    defaultReminders: [15, 60, 1440],  // 15 min, 1 hour, 1 day
    fetchIntervalMinutes: 15,
    lookAheadDays: 7
  }
}

function saveConfig(config: CalendarConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
}

function loadEvents(): CalendarEvent[] {
  try {
    const stored = localStorage.getItem(EVENTS_KEY)
    if (stored) {
      return JSON.parse(stored).map((e: any) => ({
        ...e,
        startTime: new Date(e.startTime),
        endTime: new Date(e.endTime)
      }))
    }
  } catch {}
  return []
}

function saveEvents(events: CalendarEvent[]): void {
  localStorage.setItem(EVENTS_KEY, JSON.stringify(events))
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useCalendar() {
  const notifications = useProactiveNotifications()
  const auditLog = useAuditLog()

  const config = ref<CalendarConfig>(loadConfig())
  const events = ref<CalendarEvent[]>(loadEvents())
  const isLoading = ref(false)
  const lastFetch = ref<Date | null>(null)

  let fetchInterval: ReturnType<typeof setInterval> | null = null
  let reminderCheckInterval: ReturnType<typeof setInterval> | null = null
  const firedReminders = new Set<string>()

  // ========================================================================
  // APPLE CALENDAR INTEGRATION
  // ========================================================================

  /**
   * Fetch events from Apple Calendar using AppleScript
   */
  async function fetchAppleCalendarEvents(): Promise<CalendarEvent[]> {
    const startDate = new Date()
    const endDate = new Date()
    endDate.setDate(endDate.getDate() + config.value.lookAheadDays)

    const script = `
      set startDate to current date
      set endDate to startDate + (${config.value.lookAheadDays} * days)

      set eventList to {}

      tell application "Calendar"
        repeat with cal in calendars
          set calName to name of cal
          set calEvents to (every event of cal whose start date >= startDate and start date <= endDate)

          repeat with evt in calEvents
            set evtStart to start date of evt
            set evtEnd to end date of evt
            set evtTitle to summary of evt
            set evtDesc to description of evt
            set evtLoc to location of evt
            set evtAllDay to allday event of evt

            set evtInfo to "{" & ¬
              "\\"title\\": \\"" & evtTitle & "\\", " & ¬
              "\\"calendar\\": \\"" & calName & "\\", " & ¬
              "\\"startTime\\": \\"" & (evtStart as «class isot» as string) & "\\", " & ¬
              "\\"endTime\\": \\"" & (evtEnd as «class isot» as string) & "\\", " & ¬
              "\\"isAllDay\\": " & evtAllDay & ", " & ¬
              "\\"location\\": \\"" & (evtLoc as string) & "\\", " & ¬
              "\\"description\\": \\"" & (evtDesc as string) & "\\"" & ¬
              "}"

            set end of eventList to evtInfo
          end repeat
        end repeat
      end tell

      set AppleScript's text item delimiters to ","
      return "[" & (eventList as string) & "]"
    `

    try {
      const result = await invoke<string>('execute_shell', {
        command: `osascript -e '${script.replace(/'/g, "'\\''")}'`,
        cwd: undefined
      })

      // Parse the JSON result
      const parsed = JSON.parse(result || '[]')
      return parsed.map((e: any, index: number) => ({
        id: `apple_${Date.now()}_${index}`,
        title: e.title || 'Untitled',
        description: e.description,
        location: e.location,
        startTime: new Date(e.startTime),
        endTime: new Date(e.endTime),
        isAllDay: e.isAllDay === 'true' || e.isAllDay === true,
        calendar: e.calendar,
        status: 'confirmed' as const,
        reminders: config.value.defaultReminders,
        isRecurring: false
      }))
    } catch (error) {
      console.error('[Calendar] Failed to fetch Apple Calendar:', error)
      return []
    }
  }

  /**
   * Create an event in Apple Calendar
   */
  async function createAppleCalendarEvent(event: Partial<CalendarEvent>): Promise<boolean> {
    const startDate = event.startTime || new Date()
    const endDate = event.endTime || new Date(startDate.getTime() + 60 * 60 * 1000)

    const script = `
      tell application "Calendar"
        tell calendar "Calendar"
          make new event with properties {summary:"${event.title || 'New Event'}", start date:date "${startDate.toLocaleString()}", end date:date "${endDate.toLocaleString()}", location:"${event.location || ''}", description:"${event.description || ''}"}
        end tell
      end tell
    `

    try {
      await invoke('execute_shell', {
        command: `osascript -e '${script.replace(/'/g, "'\\''")}'`,
        cwd: undefined
      })

      await auditLog.log('calendar_create', `Created event: ${event.title}`, {
        riskLevel: 'low'
      })

      // Refresh events
      await fetchEvents()
      return true
    } catch (error) {
      console.error('[Calendar] Failed to create event:', error)
      return false
    }
  }

  // ========================================================================
  // EVENT MANAGEMENT
  // ========================================================================

  /**
   * Fetch events from all enabled providers
   */
  async function fetchEvents(): Promise<void> {
    if (!config.value.enabled) return

    isLoading.value = true

    try {
      const allEvents: CalendarEvent[] = []

      for (const provider of config.value.providers) {
        if (!provider.enabled) continue

        switch (provider.type) {
          case 'apple':
            const appleEvents = await fetchAppleCalendarEvents()
            allEvents.push(...appleEvents)
            break
          // Add other providers here
        }
      }

      events.value = allEvents.sort((a, b) =>
        a.startTime.getTime() - b.startTime.getTime()
      )

      saveEvents(events.value)
      lastFetch.value = new Date()

      console.log(`[Calendar] Fetched ${allEvents.length} events`)
    } catch (error) {
      console.error('[Calendar] Fetch failed:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get today's events
   */
  const todayEvents = computed(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)

    return events.value.filter(e =>
      e.startTime >= today && e.startTime < tomorrow
    )
  })

  /**
   * Get upcoming events (next N hours)
   */
  function getUpcoming(hours: number = 24): CalendarEvent[] {
    const now = new Date()
    const cutoff = new Date(now.getTime() + hours * 60 * 60 * 1000)

    return events.value.filter(e =>
      e.startTime >= now && e.startTime <= cutoff
    )
  }

  /**
   * Get the next event
   */
  const nextEvent = computed(() => {
    const now = new Date()
    return events.value.find(e => e.startTime > now)
  })

  /**
   * Get schedule for a specific day
   */
  function getDaySchedule(date: Date): DaySchedule {
    const dayStart = new Date(date)
    dayStart.setHours(0, 0, 0, 0)
    const dayEnd = new Date(dayStart)
    dayEnd.setDate(dayEnd.getDate() + 1)

    const dayEvents = events.value.filter(e =>
      e.startTime >= dayStart && e.startTime < dayEnd
    )

    // Calculate free slots (simplified - between events)
    const freeSlots: Array<{ start: Date; end: Date; duration: number }> = []
    const workStart = new Date(dayStart)
    workStart.setHours(9, 0, 0, 0)
    const workEnd = new Date(dayStart)
    workEnd.setHours(18, 0, 0, 0)

    let currentTime = workStart

    for (const event of dayEvents) {
      if (event.startTime > currentTime && event.startTime <= workEnd) {
        freeSlots.push({
          start: currentTime,
          end: event.startTime,
          duration: (event.startTime.getTime() - currentTime.getTime()) / 1000 / 60
        })
      }
      if (event.endTime > currentTime) {
        currentTime = event.endTime
      }
    }

    if (currentTime < workEnd) {
      freeSlots.push({
        start: currentTime,
        end: workEnd,
        duration: (workEnd.getTime() - currentTime.getTime()) / 1000 / 60
      })
    }

    return {
      date: dayStart,
      events: dayEvents,
      freeSlots
    }
  }

  // ========================================================================
  // REMINDERS
  // ========================================================================

  /**
   * Check for upcoming reminders
   */
  function checkReminders(): void {
    const now = new Date()

    for (const event of events.value) {
      for (const minutesBefore of event.reminders) {
        const reminderTime = new Date(event.startTime.getTime() - minutesBefore * 60 * 1000)
        const reminderKey = `${event.id}_${minutesBefore}`

        // Check if reminder should fire (within 1 minute window)
        const diff = Math.abs(now.getTime() - reminderTime.getTime()) / 1000 / 60

        if (diff < 1 && !firedReminders.has(reminderKey)) {
          firedReminders.add(reminderKey)
          fireReminder(event, minutesBefore)
        }
      }
    }
  }

  /**
   * Fire a reminder notification
   */
  function fireReminder(event: CalendarEvent, minutesBefore: number): void {
    const timeText = minutesBefore < 60
      ? `${minutesBefore} minute${minutesBefore === 1 ? '' : 's'}`
      : `${Math.round(minutesBefore / 60)} hour${minutesBefore >= 120 ? 's' : ''}`

    notifications.remind(`${event.title} in ${timeText}`, minutesBefore)

    console.log(`[Calendar] Reminder: ${event.title} in ${timeText}`)
  }

  /**
   * Get time until next event as human-readable string
   */
  function getTimeUntilNext(): string | null {
    const next = nextEvent.value
    if (!next) return null

    const now = new Date()
    const diff = next.startTime.getTime() - now.getTime()

    if (diff < 0) return null

    const minutes = Math.floor(diff / 1000 / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) {
      return `${days} day${days === 1 ? '' : 's'}`
    } else if (hours > 0) {
      return `${hours} hour${hours === 1 ? '' : 's'}`
    } else {
      return `${minutes} minute${minutes === 1 ? '' : 's'}`
    }
  }

  // ========================================================================
  // SCHEDULING ASSISTANCE
  // ========================================================================

  /**
   * Find a free slot of given duration
   */
  function findFreeSlot(
    durationMinutes: number,
    options?: {
      afterDate?: Date
      beforeDate?: Date
      preferredHours?: { start: number; end: number }
    }
  ): { start: Date; end: Date } | null {
    const searchStart = options?.afterDate || new Date()
    const searchEnd = options?.beforeDate || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
    const prefStart = options?.preferredHours?.start ?? 9
    const prefEnd = options?.preferredHours?.end ?? 18

    let currentDate = new Date(searchStart)
    currentDate.setHours(Math.max(currentDate.getHours(), prefStart), 0, 0, 0)

    while (currentDate < searchEnd) {
      const schedule = getDaySchedule(currentDate)

      for (const slot of schedule.freeSlots) {
        if (slot.duration >= durationMinutes) {
          // Check if within preferred hours
          const slotHour = slot.start.getHours()
          if (slotHour >= prefStart && slotHour + durationMinutes / 60 <= prefEnd) {
            return {
              start: slot.start,
              end: new Date(slot.start.getTime() + durationMinutes * 60 * 1000)
            }
          }
        }
      }

      // Move to next day
      currentDate.setDate(currentDate.getDate() + 1)
      currentDate.setHours(prefStart, 0, 0, 0)
    }

    return null
  }

  /**
   * Check if a time is free
   */
  function isTimeFree(time: Date, durationMinutes: number = 60): boolean {
    const endTime = new Date(time.getTime() + durationMinutes * 60 * 1000)

    return !events.value.some(e =>
      (time >= e.startTime && time < e.endTime) ||
      (endTime > e.startTime && endTime <= e.endTime) ||
      (time <= e.startTime && endTime >= e.endTime)
    )
  }

  /**
   * Get schedule summary for briefing
   */
  function getScheduleSummary(): string {
    const today = todayEvents.value
    const upcoming = getUpcoming(4) // Next 4 hours

    if (upcoming.length === 0 && today.length === 0) {
      return "Your schedule is clear today."
    }

    let summary = ""

    if (upcoming.length > 0) {
      const next = upcoming[0]
      const timeUntil = getTimeUntilNext()
      summary += `Next up: ${next.title} in ${timeUntil}. `
    }

    if (today.length > upcoming.length) {
      const remaining = today.length - upcoming.length
      summary += `${remaining} more event${remaining === 1 ? '' : 's'} later today.`
    }

    return summary.trim()
  }

  // ========================================================================
  // LIFECYCLE
  // ========================================================================

  /**
   * Start calendar service
   */
  function start(): void {
    if (!config.value.enabled) return

    // Initial fetch
    fetchEvents()

    // Set up periodic fetch
    fetchInterval = setInterval(
      fetchEvents,
      config.value.fetchIntervalMinutes * 60 * 1000
    )

    // Set up reminder check (every minute)
    reminderCheckInterval = setInterval(checkReminders, 60 * 1000)

    console.log('[Calendar] Started')
  }

  /**
   * Stop calendar service
   */
  function stop(): void {
    if (fetchInterval) {
      clearInterval(fetchInterval)
      fetchInterval = null
    }

    if (reminderCheckInterval) {
      clearInterval(reminderCheckInterval)
      reminderCheckInterval = null
    }

    console.log('[Calendar] Stopped')
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
    events,
    isLoading,
    lastFetch,
    todayEvents,
    nextEvent,

    // Lifecycle
    start,
    stop,
    fetchEvents,

    // Queries
    getUpcoming,
    getDaySchedule,
    getTimeUntilNext,
    getScheduleSummary,
    findFreeSlot,
    isTimeFree,

    // Mutations
    createAppleCalendarEvent
  }
}

export type UseCalendarReturn = ReturnType<typeof useCalendar>
