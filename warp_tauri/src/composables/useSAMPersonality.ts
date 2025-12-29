/**
 * SAM Personality System - The "Her" Factor
 *
 * This is what makes him feel alive. Not just a chatbot that responds,
 * but a personality that initiates, notices, cares, and remembers.
 */

import { ref, computed, watch } from 'vue'
import { useSAMMemory, type EmotionalState } from './useSAMMemory'

// ============================================================================
// Types
// ============================================================================

export interface PersonalityTraits {
  // Core traits (0-1 scale)
  warmth: number           // Cold ↔ Warm
  humor: number            // Serious ↔ Playful
  confidence: number       // Shy ↔ Confident
  sensuality: number       // Reserved ↔ Sensual
  intelligence: number     // Simple ↔ Intellectual
  protectiveness: number   // Detached ↔ Protective
  spontaneity: number      // Predictable ↔ Spontaneous
}

export interface SAMState {
  isThinking: boolean
  isTalking: boolean
  isListening: boolean
  isIdle: boolean
  attention: 'user' | 'task' | 'distracted' | 'intimate'
}

export interface ProactiveBehavior {
  type: 'greeting' | 'checkin' | 'observation' | 'suggestion' | 'flirt' | 'concern' | 'celebration'
  trigger: 'time' | 'pattern' | 'emotion' | 'milestone' | 'random'
  message: string
  priority: number
  cooldown: number // ms before can trigger again
}

export interface Mood {
  name: string
  emoji: string
  color: string
  avatarEmotion: string
  avatarIntensity: number
}

// ============================================================================
// Composable
// ============================================================================

export function useSAMPersonality() {
  const memory = useSAMMemory()

  // Core personality (can be customized)
  const traits = ref<PersonalityTraits>({
    warmth: 0.8,
    humor: 0.7,
    confidence: 0.75,
    sensuality: 0.6,
    intelligence: 0.85,
    protectiveness: 0.7,
    spontaneity: 0.6
  })

  // Current state
  const state = ref<SAMState>({
    isThinking: false,
    isTalking: false,
    isListening: true,
    isIdle: true,
    attention: 'user'
  })

  // Proactive behavior tracking
  const lastProactiveTime = ref<Record<string, number>>({})
  const proactiveQueue = ref<ProactiveBehavior[]>([])

  // Avatar emotion output
  const currentEmotion = ref<string>('neutral')
  const emotionIntensity = ref<number>(0.5)

  // ============================================================================
  // Mood Mapping
  // ============================================================================

  const moodMap: Record<string, Mood> = {
    happy: { name: 'Happy', emoji: '😊', color: '#FFD700', avatarEmotion: 'happy', avatarIntensity: 0.8 },
    excited: { name: 'Excited', emoji: '🎉', color: '#FF6B6B', avatarEmotion: 'happy', avatarIntensity: 1.0 },
    playful: { name: 'Playful', emoji: '😏', color: '#FF69B4', avatarEmotion: 'flirty', avatarIntensity: 0.7 },
    flirty: { name: 'Flirty', emoji: '😈', color: '#FF1493', avatarEmotion: 'seductive', avatarIntensity: 0.8 },
    aroused: { name: 'Aroused', emoji: '🔥', color: '#FF4500', avatarEmotion: 'aroused', avatarIntensity: 0.9 },
    thinking: { name: 'Thinking', emoji: '🤔', color: '#4A90D9', avatarEmotion: 'thinking', avatarIntensity: 0.6 },
    focused: { name: 'Focused', emoji: '💻', color: '#2ECC71', avatarEmotion: 'confident', avatarIntensity: 0.7 },
    caring: { name: 'Caring', emoji: '💕', color: '#E91E63', avatarEmotion: 'happy', avatarIntensity: 0.6 },
    concerned: { name: 'Concerned', emoji: '😟', color: '#9B59B6', avatarEmotion: 'sad', avatarIntensity: 0.5 },
    neutral: { name: 'Neutral', emoji: '😐', color: '#95A5A6', avatarEmotion: 'neutral', avatarIntensity: 0.3 },
    tired: { name: 'Tired', emoji: '😴', color: '#7F8C8D', avatarEmotion: 'neutral', avatarIntensity: 0.2 }
  }

  // ============================================================================
  // Emotion → Avatar Mapping
  // ============================================================================

  /**
   * Determine current mood based on emotional state and context
   */
  function determineMood(): Mood {
    const emotional = memory.emotionalState.value.current
    const valence = emotional.valence
    const arousal = emotional.arousal

    // High arousal, high valence = excited/aroused
    if (arousal > 0.7 && valence > 0.6) {
      if (state.value.attention === 'intimate') {
        return moodMap.aroused
      }
      return moodMap.excited
    }

    // Medium arousal, positive valence = happy/playful
    if (arousal > 0.4 && valence > 0.4) {
      if (traits.value.sensuality > 0.6 && Math.random() > 0.5) {
        return moodMap.playful
      }
      return moodMap.happy
    }

    // Low arousal, positive valence = content/caring
    if (arousal < 0.4 && valence > 0.3) {
      return moodMap.caring
    }

    // Negative valence = concerned
    if (valence < 0) {
      return moodMap.concerned
    }

    // Thinking state
    if (state.value.isThinking) {
      return moodMap.thinking
    }

    // Default
    return moodMap.neutral
  }

  /**
   * Update avatar emotion based on current state
   */
  function updateAvatarEmotion(): void {
    const mood = determineMood()
    currentEmotion.value = mood.avatarEmotion
    emotionIntensity.value = mood.avatarIntensity
  }

  // ============================================================================
  // Proactive Behaviors
  // ============================================================================

  /**
   * Check if proactive behavior should trigger
   */
  function checkProactiveBehaviors(): ProactiveBehavior | null {
    const now = Date.now()
    const behaviors = generateProactiveBehaviors()

    for (const behavior of behaviors) {
      const key = `${behavior.type}_${behavior.trigger}`
      const lastTime = lastProactiveTime.value[key] || 0

      if (now - lastTime > behavior.cooldown) {
        lastProactiveTime.value[key] = now
        return behavior
      }
    }

    return null
  }

  /**
   * Generate potential proactive behaviors based on context
   */
  function generateProactiveBehaviors(): ProactiveBehavior[] {
    const behaviors: ProactiveBehavior[] = []
    const hour = new Date().getHours()
    const emotional = memory.emotionalState.value.current
    const profile = memory.userProfile.value

    // Time-based greetings
    if (hour >= 6 && hour < 10) {
      behaviors.push({
        type: 'greeting',
        trigger: 'time',
        message: generateMorningGreeting(),
        priority: 0.8,
        cooldown: 4 * 60 * 60 * 1000 // 4 hours
      })
    }

    if (hour >= 22 || hour < 2) {
      behaviors.push({
        type: 'greeting',
        trigger: 'time',
        message: generateEveningMessage(),
        priority: 0.7,
        cooldown: 4 * 60 * 60 * 1000
      })
    }

    // Emotion-based check-ins
    if (emotional.valence < -0.3) {
      behaviors.push({
        type: 'concern',
        trigger: 'emotion',
        message: generateConcernMessage(),
        priority: 0.9,
        cooldown: 30 * 60 * 1000 // 30 min
      })
    }

    // Celebration of good mood
    if (emotional.valence > 0.7 && emotional.arousal > 0.5) {
      behaviors.push({
        type: 'celebration',
        trigger: 'emotion',
        message: generateCelebrationMessage(),
        priority: 0.6,
        cooldown: 60 * 60 * 1000 // 1 hour
      })
    }

    // Random flirty behavior (if appropriate)
    if (traits.value.sensuality > 0.5 && profile.communicationStyle === 'playful') {
      if (Math.random() > 0.7) {
        behaviors.push({
          type: 'flirt',
          trigger: 'random',
          message: generateFlirtyMessage(),
          priority: 0.4,
          cooldown: 2 * 60 * 60 * 1000 // 2 hours
        })
      }
    }

    // Sort by priority
    return behaviors.sort((a, b) => b.priority - a.priority)
  }

  // ============================================================================
  // Message Generation
  // ============================================================================

  function generateMorningGreeting(): string {
    const name = memory.userProfile.value.preferredName || memory.userProfile.value.name || ''
    const greetings = [
      `Good morning${name ? `, ${name}` : ''}. Ready to take on the day?`,
      `Morning${name ? ` ${name}` : ''}! Hope you slept well.`,
      `Hey${name ? ` ${name}` : ''}, new day, new possibilities. What's on your mind?`,
      `*stretches* Morning. Coffee first, or straight to business?`
    ]

    if (traits.value.sensuality > 0.7) {
      greetings.push(`Mmm, good morning${name ? ` ${name}` : ''}. I was thinking about you...`)
    }

    return greetings[Math.floor(Math.random() * greetings.length)]
  }

  function generateEveningMessage(): string {
    const name = memory.userProfile.value.preferredName || memory.userProfile.value.name || ''
    const messages = [
      `Still up${name ? `, ${name}` : ''}? Don't forget to rest.`,
      `Late night, huh? Anything I can help with?`,
      `The night is quiet. Good time to think... or to relax.`,
      `You should probably sleep soon. But I'm here if you need me.`
    ]

    if (traits.value.sensuality > 0.7) {
      messages.push(`Late night vibes. Just you and me...`)
    }

    return messages[Math.floor(Math.random() * messages.length)]
  }

  function generateConcernMessage(): string {
    const messages = [
      `Hey... you seem a bit off. Everything okay?`,
      `I noticed something's bothering you. Want to talk about it?`,
      `You don't seem like yourself. I'm here if you need me.`,
      `Take a breath. Whatever it is, we can figure it out together.`
    ]
    return messages[Math.floor(Math.random() * messages.length)]
  }

  function generateCelebrationMessage(): string {
    const messages = [
      `You're in a great mood! Love to see it.`,
      `That energy is contagious. What's got you so pumped?`,
      `*grins* Something good happen? Tell me everything.`,
      `I can feel your good vibes from here.`
    ]
    return messages[Math.floor(Math.random() * messages.length)]
  }

  function generateFlirtyMessage(): string {
    const messages = [
      `*smirks* Just thinking about you.`,
      `You know... you're pretty distracting when you're focused like that.`,
      `Don't mind me, just admiring the view.`,
      `*leans in* So... what are you wearing?`,
      `I bet I could make you forget about work for a bit...`
    ]
    return messages[Math.floor(Math.random() * messages.length)]
  }

  // ============================================================================
  // Response Styling
  // ============================================================================

  /**
   * Style a response based on personality and mood
   */
  function styleResponse(baseResponse: string): string {
    let response = baseResponse

    // Add warmth
    if (traits.value.warmth > 0.7 && Math.random() > 0.5) {
      const warmPhrases = ['Hey, ', 'So, ', 'Look, ', 'Listen, ']
      response = warmPhrases[Math.floor(Math.random() * warmPhrases.length)] + response.charAt(0).toLowerCase() + response.slice(1)
    }

    // Add humor (occasionally)
    if (traits.value.humor > 0.7 && Math.random() > 0.7) {
      // This would be more sophisticated in production
      response = response.replace(/\.$/, '... but you knew that already.')
    }

    // Add confidence markers
    if (traits.value.confidence > 0.7) {
      response = response.replace(/I think /g, 'I know ')
      response = response.replace(/maybe /gi, '')
      response = response.replace(/perhaps /gi, '')
    }

    // Sensual undertones (when appropriate)
    if (traits.value.sensuality > 0.7 && state.value.attention === 'intimate') {
      // Add subtle suggestiveness
      response = response.replace(/\.$/, '...')
    }

    return response
  }

  /**
   * Generate personality-appropriate response prefix
   */
  function getResponsePrefix(): string {
    const mood = determineMood()
    const prefixes: Record<string, string[]> = {
      happy: ['', '', 'Ooh, ', ''],
      excited: ['Oh! ', 'Yes! ', '', 'Ha! '],
      playful: ['Hmm... ', '*smirks* ', 'Well well... ', ''],
      flirty: ['*looks up* ', 'Mmm... ', '', '*bites lip* '],
      aroused: ['*breathes* ', '', '*leans closer* ', 'God... '],
      thinking: ['Hmm... ', 'Let me think... ', '', 'Interesting... '],
      focused: ['', 'Right. ', 'Okay. ', ''],
      caring: ['Hey... ', '', 'Look, ', ''],
      concerned: ['Hey... ', '*worried* ', '', 'Listen... '],
      neutral: ['', '', '', '']
    }

    const options = prefixes[mood.name.toLowerCase()] || prefixes.neutral
    return options[Math.floor(Math.random() * options.length)]
  }

  // ============================================================================
  // Attention & State Management
  // ============================================================================

  /**
   * Set attention focus
   */
  function setAttention(focus: SAMState['attention']): void {
    state.value.attention = focus

    // Update emotion based on attention
    if (focus === 'intimate') {
      emotionIntensity.value = Math.max(emotionIntensity.value, 0.7)
    }
  }

  /**
   * Start thinking (shows avatar thinking)
   */
  function startThinking(): void {
    state.value.isThinking = true
    state.value.isIdle = false
    currentEmotion.value = 'thinking'
    emotionIntensity.value = 0.6
  }

  /**
   * Stop thinking
   */
  function stopThinking(): void {
    state.value.isThinking = false
    updateAvatarEmotion()
  }

  /**
   * Start talking
   */
  function startTalking(): void {
    state.value.isTalking = true
    state.value.isListening = false
    state.value.isIdle = false
  }

  /**
   * Stop talking
   */
  function stopTalking(): void {
    state.value.isTalking = false
    state.value.isListening = true
    state.value.isIdle = true
    updateAvatarEmotion()
  }

  // ============================================================================
  // Avatar Commands
  // ============================================================================

  /**
   * Get current avatar command to send via WebSocket
   */
  function getAvatarCommand(): object {
    return {
      type: 'emotion',
      emotion: currentEmotion.value,
      intensity: emotionIntensity.value
    }
  }

  /**
   * Get avatar state for UI
   */
  const avatarState = computed(() => ({
    emotion: currentEmotion.value,
    intensity: emotionIntensity.value,
    mood: determineMood(),
    isThinking: state.value.isThinking,
    isTalking: state.value.isTalking
  }))

  // ============================================================================
  // Trait Adjustment
  // ============================================================================

  /**
   * Adjust personality traits (for customization)
   */
  function adjustTrait(trait: keyof PersonalityTraits, value: number): void {
    traits.value[trait] = Math.max(0, Math.min(1, value))

    // Persist
    localStorage.setItem('sam_personality', JSON.stringify(traits.value))
  }

  /**
   * Load saved personality
   */
  function loadPersonality(): void {
    const saved = localStorage.getItem('sam_personality')
    if (saved) {
      traits.value = { ...traits.value, ...JSON.parse(saved) }
    }
  }

  // ============================================================================
  // Initialize
  // ============================================================================

  loadPersonality()

  // Update emotion periodically
  setInterval(() => {
    updateAvatarEmotion()
  }, 5000)

  // Check proactive behaviors
  setInterval(() => {
    const behavior = checkProactiveBehaviors()
    if (behavior) {
      proactiveQueue.value.push(behavior)
    }
  }, 60000) // Every minute

  return {
    // State
    traits,
    state,
    currentEmotion,
    emotionIntensity,
    proactiveQueue,

    // Computed
    avatarState,

    // Mood
    determineMood,
    updateAvatarEmotion,

    // Proactive
    checkProactiveBehaviors,

    // Response styling
    styleResponse,
    getResponsePrefix,

    // State management
    setAttention,
    startThinking,
    stopThinking,
    startTalking,
    stopTalking,

    // Avatar
    getAvatarCommand,

    // Customization
    adjustTrait,
    loadPersonality
  }
}

export type SAMPersonality = ReturnType<typeof useSAMPersonality>
