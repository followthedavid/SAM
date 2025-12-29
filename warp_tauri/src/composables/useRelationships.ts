/**
 * useRelationships - Relationship Context & Social Intelligence
 *
 * Tracks the people in your life, their importance, and context.
 * Allows SAM to understand social dynamics and provide better support.
 *
 * "That's your mom, right? You should probably call her back."
 */

import { ref, computed, watch } from 'vue'
import { useAuditLog } from './useAuditLog'

// ============================================================================
// TYPES
// ============================================================================

export type RelationshipType =
  | 'family'
  | 'friend'
  | 'romantic'
  | 'colleague'
  | 'professional'
  | 'acquaintance'
  | 'other'

export type ContactImportance = 'critical' | 'high' | 'medium' | 'low'

export interface Person {
  id: string
  name: string
  nicknames: string[]
  relationship: RelationshipType
  importance: ContactImportance
  email?: string
  phone?: string
  company?: string
  role?: string
  notes: string[]
  traits: string[]         // Personality traits you've noted
  topics: string[]         // Topics they care about
  boundaries: string[]     // Things to avoid
  lastMentioned?: Date
  lastContact?: Date
  contactFrequency?: 'daily' | 'weekly' | 'monthly' | 'rarely'
  birthday?: Date
  anniversaries?: Array<{ name: string; date: Date }>
  preferences: Record<string, string>  // e.g., { coffee: "black", pronoun: "they" }
  history: InteractionRecord[]
}

export interface InteractionRecord {
  id: string
  timestamp: Date
  type: 'mention' | 'call' | 'message' | 'meeting' | 'note'
  summary: string
  sentiment?: 'positive' | 'neutral' | 'negative'
  context?: string
}

export interface RelationshipInsight {
  personId: string
  type: 'reminder' | 'suggestion' | 'observation' | 'warning'
  message: string
  priority: 'low' | 'medium' | 'high'
  createdAt: Date
}

// ============================================================================
// STORAGE
// ============================================================================

const PEOPLE_KEY = 'warp_relationships_people'
const INSIGHTS_KEY = 'warp_relationships_insights'

function loadPeople(): Person[] {
  try {
    const stored = localStorage.getItem(PEOPLE_KEY)
    if (stored) {
      return JSON.parse(stored).map((p: any) => ({
        ...p,
        lastMentioned: p.lastMentioned ? new Date(p.lastMentioned) : undefined,
        lastContact: p.lastContact ? new Date(p.lastContact) : undefined,
        birthday: p.birthday ? new Date(p.birthday) : undefined,
        anniversaries: p.anniversaries?.map((a: any) => ({
          ...a,
          date: new Date(a.date)
        })),
        history: p.history?.map((h: any) => ({
          ...h,
          timestamp: new Date(h.timestamp)
        })) || []
      }))
    }
  } catch {}
  return []
}

function savePeople(people: Person[]): void {
  localStorage.setItem(PEOPLE_KEY, JSON.stringify(people))
}

function loadInsights(): RelationshipInsight[] {
  try {
    const stored = localStorage.getItem(INSIGHTS_KEY)
    if (stored) {
      return JSON.parse(stored).map((i: any) => ({
        ...i,
        createdAt: new Date(i.createdAt)
      }))
    }
  } catch {}
  return []
}

function saveInsights(insights: RelationshipInsight[]): void {
  localStorage.setItem(INSIGHTS_KEY, JSON.stringify(insights))
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useRelationships() {
  const auditLog = useAuditLog()

  const people = ref<Person[]>(loadPeople())
  const insights = ref<RelationshipInsight[]>(loadInsights())

  // ========================================================================
  // PERSON MANAGEMENT
  // ========================================================================

  /**
   * Add a new person
   */
  function addPerson(data: Partial<Person> & { name: string }): Person {
    const person: Person = {
      id: `person_${Date.now()}`,
      name: data.name,
      nicknames: data.nicknames || [],
      relationship: data.relationship || 'acquaintance',
      importance: data.importance || 'medium',
      email: data.email,
      phone: data.phone,
      company: data.company,
      role: data.role,
      notes: data.notes || [],
      traits: data.traits || [],
      topics: data.topics || [],
      boundaries: data.boundaries || [],
      contactFrequency: data.contactFrequency,
      birthday: data.birthday,
      anniversaries: data.anniversaries || [],
      preferences: data.preferences || {},
      history: []
    }

    people.value.push(person)
    savePeople(people.value)

    auditLog.log('relationship_added', `Added person: ${person.name}`, {
      riskLevel: 'low'
    })

    return person
  }

  /**
   * Update a person
   */
  function updatePerson(personId: string, updates: Partial<Person>): void {
    const person = people.value.find(p => p.id === personId)
    if (person) {
      Object.assign(person, updates)
      savePeople(people.value)
    }
  }

  /**
   * Remove a person
   */
  function removePerson(personId: string): void {
    people.value = people.value.filter(p => p.id !== personId)
    savePeople(people.value)
  }

  /**
   * Find a person by name or nickname
   */
  function findPerson(query: string): Person | undefined {
    const lower = query.toLowerCase()
    return people.value.find(p =>
      p.name.toLowerCase().includes(lower) ||
      p.nicknames.some(n => n.toLowerCase().includes(lower))
    )
  }

  /**
   * Search people
   */
  function searchPeople(query: string): Person[] {
    const lower = query.toLowerCase()
    return people.value.filter(p =>
      p.name.toLowerCase().includes(lower) ||
      p.nicknames.some(n => n.toLowerCase().includes(lower)) ||
      p.company?.toLowerCase().includes(lower) ||
      p.notes.some(n => n.toLowerCase().includes(lower))
    )
  }

  // ========================================================================
  // INTERACTION TRACKING
  // ========================================================================

  /**
   * Record an interaction or mention
   */
  function recordInteraction(
    personId: string,
    type: InteractionRecord['type'],
    summary: string,
    options?: {
      sentiment?: InteractionRecord['sentiment']
      context?: string
    }
  ): void {
    const person = people.value.find(p => p.id === personId)
    if (!person) return

    const record: InteractionRecord = {
      id: `interaction_${Date.now()}`,
      timestamp: new Date(),
      type,
      summary,
      sentiment: options?.sentiment,
      context: options?.context
    }

    person.history.push(record)
    person.lastMentioned = new Date()

    if (type !== 'mention') {
      person.lastContact = new Date()
    }

    // Keep history manageable
    if (person.history.length > 100) {
      person.history = person.history.slice(-100)
    }

    savePeople(people.value)
  }

  /**
   * Extract mentions from text
   */
  function extractMentions(text: string): Person[] {
    const mentions: Person[] = []

    for (const person of people.value) {
      const patterns = [
        person.name.toLowerCase(),
        ...person.nicknames.map(n => n.toLowerCase())
      ]

      for (const pattern of patterns) {
        if (text.toLowerCase().includes(pattern)) {
          if (!mentions.find(m => m.id === person.id)) {
            mentions.push(person)
            recordInteraction(person.id, 'mention', `Mentioned in: "${text.substring(0, 50)}..."`)
          }
          break
        }
      }
    }

    return mentions
  }

  // ========================================================================
  // RELATIONSHIP INTELLIGENCE
  // ========================================================================

  /**
   * Get people who might need attention
   */
  const needsAttention = computed(() => {
    const now = new Date()
    const results: Array<{ person: Person; reason: string; urgency: 'low' | 'medium' | 'high' }> = []

    for (const person of people.value) {
      // Check contact frequency
      if (person.lastContact && person.contactFrequency) {
        const daysSinceContact = Math.floor(
          (now.getTime() - person.lastContact.getTime()) / 1000 / 60 / 60 / 24
        )

        const expectedDays = {
          daily: 2,
          weekly: 10,
          monthly: 45,
          rarely: 180
        }[person.contactFrequency]

        if (daysSinceContact > expectedDays) {
          const urgency = person.importance === 'critical' ? 'high' :
                          person.importance === 'high' ? 'medium' : 'low'

          results.push({
            person,
            reason: `Haven't been in touch for ${daysSinceContact} days`,
            urgency
          })
        }
      }

      // Check upcoming birthdays
      if (person.birthday) {
        const birthday = new Date(person.birthday)
        birthday.setFullYear(now.getFullYear())
        if (birthday < now) {
          birthday.setFullYear(now.getFullYear() + 1)
        }

        const daysUntil = Math.floor(
          (birthday.getTime() - now.getTime()) / 1000 / 60 / 60 / 24
        )

        if (daysUntil <= 7 && daysUntil >= 0) {
          results.push({
            person,
            reason: daysUntil === 0
              ? `It's their birthday today!`
              : `Birthday in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`,
            urgency: daysUntil === 0 ? 'high' : 'medium'
          })
        }
      }

      // Check anniversaries
      if (person.anniversaries) {
        for (const anniversary of person.anniversaries) {
          const annivDate = new Date(anniversary.date)
          annivDate.setFullYear(now.getFullYear())
          if (annivDate < now) {
            annivDate.setFullYear(now.getFullYear() + 1)
          }

          const daysUntil = Math.floor(
            (annivDate.getTime() - now.getTime()) / 1000 / 60 / 60 / 24
          )

          if (daysUntil <= 7 && daysUntil >= 0) {
            results.push({
              person,
              reason: daysUntil === 0
                ? `${anniversary.name} is today!`
                : `${anniversary.name} in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`,
              urgency: daysUntil === 0 ? 'high' : 'medium'
            })
          }
        }
      }
    }

    return results.sort((a, b) => {
      const urgencyOrder = { high: 0, medium: 1, low: 2 }
      return urgencyOrder[a.urgency] - urgencyOrder[b.urgency]
    })
  })

  /**
   * Get context about a person for conversation
   */
  function getPersonContext(personId: string): string {
    const person = people.value.find(p => p.id === personId)
    if (!person) return ''

    const parts: string[] = []

    // Basic info
    parts.push(`${person.name} is your ${person.relationship}.`)

    if (person.company && person.role) {
      parts.push(`They work at ${person.company} as ${person.role}.`)
    }

    // Traits
    if (person.traits.length > 0) {
      parts.push(`Known for being: ${person.traits.join(', ')}.`)
    }

    // Topics
    if (person.topics.length > 0) {
      parts.push(`Interested in: ${person.topics.join(', ')}.`)
    }

    // Boundaries
    if (person.boundaries.length > 0) {
      parts.push(`Avoid discussing: ${person.boundaries.join(', ')}.`)
    }

    // Recent history
    const recentHistory = person.history.slice(-3)
    if (recentHistory.length > 0) {
      parts.push('Recent interactions:')
      for (const h of recentHistory) {
        parts.push(`- ${h.summary}`)
      }
    }

    // Preferences
    const prefs = Object.entries(person.preferences)
    if (prefs.length > 0) {
      parts.push(`Preferences: ${prefs.map(([k, v]) => `${k}: ${v}`).join(', ')}.`)
    }

    return parts.join(' ')
  }

  /**
   * Add an insight about a relationship
   */
  function addInsight(
    personId: string,
    type: RelationshipInsight['type'],
    message: string,
    priority: RelationshipInsight['priority'] = 'medium'
  ): void {
    insights.value.push({
      personId,
      type,
      message,
      priority,
      createdAt: new Date()
    })

    // Keep insights manageable
    if (insights.value.length > 50) {
      insights.value = insights.value.slice(-50)
    }

    saveInsights(insights.value)
  }

  /**
   * Get insights for a person
   */
  function getInsights(personId: string): RelationshipInsight[] {
    return insights.value.filter(i => i.personId === personId)
  }

  /**
   * Get all active insights
   */
  const activeInsights = computed(() => {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    return insights.value.filter(i => i.createdAt > weekAgo)
  })

  // ========================================================================
  // QUICK ACCESS
  // ========================================================================

  /**
   * Get people by importance
   */
  const importantPeople = computed(() =>
    people.value.filter(p =>
      p.importance === 'critical' || p.importance === 'high'
    )
  )

  /**
   * Get people by relationship type
   */
  function getPeopleByType(type: RelationshipType): Person[] {
    return people.value.filter(p => p.relationship === type)
  }

  /**
   * Get family members
   */
  const family = computed(() => getPeopleByType('family'))

  /**
   * Get colleagues
   */
  const colleagues = computed(() => getPeopleByType('colleague'))

  /**
   * Get friends
   */
  const friends = computed(() => getPeopleByType('friend'))

  // ========================================================================
  // NOTES & PREFERENCES
  // ========================================================================

  /**
   * Add a note about a person
   */
  function addNote(personId: string, note: string): void {
    const person = people.value.find(p => p.id === personId)
    if (person) {
      person.notes.push(`${new Date().toLocaleDateString()}: ${note}`)
      savePeople(people.value)
    }
  }

  /**
   * Add a preference
   */
  function addPreference(personId: string, key: string, value: string): void {
    const person = people.value.find(p => p.id === personId)
    if (person) {
      person.preferences[key] = value
      savePeople(people.value)
    }
  }

  /**
   * Add a trait
   */
  function addTrait(personId: string, trait: string): void {
    const person = people.value.find(p => p.id === personId)
    if (person && !person.traits.includes(trait)) {
      person.traits.push(trait)
      savePeople(people.value)
    }
  }

  /**
   * Add a topic of interest
   */
  function addTopic(personId: string, topic: string): void {
    const person = people.value.find(p => p.id === personId)
    if (person && !person.topics.includes(topic)) {
      person.topics.push(topic)
      savePeople(people.value)
    }
  }

  /**
   * Add a boundary
   */
  function addBoundary(personId: string, boundary: string): void {
    const person = people.value.find(p => p.id === personId)
    if (person && !person.boundaries.includes(boundary)) {
      person.boundaries.push(boundary)
      savePeople(people.value)
    }
  }

  // Save on changes
  watch(people, () => savePeople(people.value), { deep: true })
  watch(insights, () => saveInsights(insights.value), { deep: true })

  return {
    // State
    people,
    insights,
    needsAttention,
    activeInsights,
    importantPeople,
    family,
    colleagues,
    friends,

    // Person management
    addPerson,
    updatePerson,
    removePerson,
    findPerson,
    searchPeople,
    getPeopleByType,

    // Interactions
    recordInteraction,
    extractMentions,

    // Intelligence
    getPersonContext,
    addInsight,
    getInsights,

    // Notes & preferences
    addNote,
    addPreference,
    addTrait,
    addTopic,
    addBoundary
  }
}

export type UseRelationshipsReturn = ReturnType<typeof useRelationships>
