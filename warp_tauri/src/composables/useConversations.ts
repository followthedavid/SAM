/**
 * useConversations - Multi-chat conversation management
 *
 * Like ChatGPT - multiple threads, characters, subjects
 */

import { ref, computed, watch } from 'vue'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  model?: string
  taskType?: string
  provider?: 'sam' | 'claude'
}

export interface Conversation {
  id: string
  title: string
  type: 'chat' | 'roleplay' | 'code'
  character?: string  // For roleplay conversations
  messages: Message[]
  createdAt: Date
  updatedAt: Date
  pinned: boolean
}

const STORAGE_KEY = 'sam_conversations'

// Shared state across all instances
const conversations = ref<Conversation[]>([])
const activeConversationId = ref<string | null>(null)
let initialized = false

function loadFromStorage(): void {
  if (initialized) return

  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      conversations.value = parsed.map((c: any) => ({
        ...c,
        createdAt: new Date(c.createdAt),
        updatedAt: new Date(c.updatedAt),
        messages: c.messages.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }))
      }))

      // Set active to most recent if none selected
      if (!activeConversationId.value && conversations.value.length > 0) {
        const sorted = [...conversations.value].sort((a, b) =>
          b.updatedAt.getTime() - a.updatedAt.getTime()
        )
        activeConversationId.value = sorted[0].id
      }
    }
    initialized = true
  } catch (e) {
    console.error('Failed to load conversations:', e)
    conversations.value = []
  }
}

function saveToStorage(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.value))
  } catch (e) {
    console.error('Failed to save conversations:', e)
  }
}

export function useConversations() {
  // Initialize on first use
  loadFromStorage()

  // Auto-save on changes
  watch(conversations, saveToStorage, { deep: true })

  // Computed
  const activeConversation = computed(() =>
    conversations.value.find(c => c.id === activeConversationId.value) || null
  )

  const sortedConversations = computed(() => {
    const pinned = conversations.value.filter(c => c.pinned)
    const unpinned = conversations.value.filter(c => !c.pinned)

    const sortByDate = (a: Conversation, b: Conversation) =>
      b.updatedAt.getTime() - a.updatedAt.getTime()

    return [...pinned.sort(sortByDate), ...unpinned.sort(sortByDate)]
  })

  const chatConversations = computed(() =>
    sortedConversations.value.filter(c => c.type === 'chat')
  )

  const roleplayConversations = computed(() =>
    sortedConversations.value.filter(c => c.type === 'roleplay')
  )

  // Actions
  function createConversation(options: {
    title?: string
    type?: 'chat' | 'roleplay' | 'code'
    character?: string
  } = {}): Conversation {
    console.log('[useConversations] createConversation called:', options)
    const now = new Date()
    const conv: Conversation = {
      id: `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      title: options.title || 'New Chat',
      type: options.type || 'chat',
      character: options.character,
      messages: [],
      createdAt: now,
      updatedAt: now,
      pinned: false
    }

    conversations.value.unshift(conv)
    activeConversationId.value = conv.id
    console.log('[useConversations] Created conversation:', conv.id, 'Total:', conversations.value.length)
    saveToStorage()

    return conv
  }

  function createRoleplay(character: string): Conversation {
    return createConversation({
      title: character,
      type: 'roleplay',
      character
    })
  }

  function selectConversation(id: string): void {
    console.log('[useConversations] selectConversation called:', id)
    if (conversations.value.some(c => c.id === id)) {
      activeConversationId.value = id
      console.log('[useConversations] activeConversationId set to:', activeConversationId.value)
    } else {
      console.warn('[useConversations] Conversation not found:', id)
    }
  }

  function deleteConversation(id: string): void {
    const index = conversations.value.findIndex(c => c.id === id)
    if (index === -1) return

    conversations.value.splice(index, 1)

    // Select another conversation if we deleted the active one
    if (activeConversationId.value === id) {
      activeConversationId.value = conversations.value[0]?.id || null
    }

    saveToStorage()
  }

  function updateTitle(id: string, title: string): void {
    const conv = conversations.value.find(c => c.id === id)
    if (conv) {
      conv.title = title
      saveToStorage()
    }
  }

  function setCharacter(id: string, character: string): void {
    const conv = conversations.value.find(c => c.id === id)
    if (conv) {
      conv.character = character
      console.log('[useConversations] setCharacter:', id, character)
      saveToStorage()
    }
  }

  function togglePin(id: string): void {
    const conv = conversations.value.find(c => c.id === id)
    if (conv) {
      conv.pinned = !conv.pinned
      saveToStorage()
    }
  }

  function addMessage(conversationId: string, message: Omit<Message, 'id'>): Message {
    const conv = conversations.value.find(c => c.id === conversationId)
    if (!conv) throw new Error('Conversation not found')

    const msg: Message = {
      ...message,
      id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    }

    conv.messages.push(msg)
    conv.updatedAt = new Date()

    // Auto-generate title from first user message
    if (conv.title === 'New Chat' && message.role === 'user') {
      conv.title = message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '')
    }

    saveToStorage()
    return msg
  }

  function clearMessages(conversationId: string): void {
    const conv = conversations.value.find(c => c.id === conversationId)
    if (conv) {
      conv.messages = []
      conv.updatedAt = new Date()
      saveToStorage()
    }
  }

  function getLastMessage(conversationId: string): Message | null {
    const conv = conversations.value.find(c => c.id === conversationId)
    if (!conv || conv.messages.length === 0) return null
    return conv.messages[conv.messages.length - 1]
  }

  return {
    // State
    conversations,
    activeConversationId,
    activeConversation,
    sortedConversations,
    chatConversations,
    roleplayConversations,

    // Actions
    createConversation,
    createRoleplay,
    selectConversation,
    deleteConversation,
    updateTitle,
    setCharacter,
    togglePin,
    addMessage,
    clearMessages,
    getLastMessage
  }
}
