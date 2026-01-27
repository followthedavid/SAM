<template>
  <div class="chat-panel" :class="{ 'roleplay-mode': isRoleplay }">
    <!-- Header Bar -->
    <header class="chat-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-title">
            <span class="title-text">{{ conversation?.title || 'Messages' }}</span>
            <span v-if="isThinking" class="status-dot pulse"></span>
          </div>
          <!-- Model/Character Badge -->
          <div class="header-info">
            <span v-if="isRoleplay && conversation?.character" class="info-badge character" @click="showCharacterPicker = true">
              🎭 {{ conversation.character }}
            </span>
            <span v-else-if="isRoleplay" class="info-badge character picking">
              🎭 Choose character...
            </span>
            <span v-else class="info-badge model" :class="{ ready: modelsReady }">
              <span class="model-dot"></span>
              {{ currentModel }}
            </span>
          </div>
        </div>
        <div class="header-controls">
          <button v-if="isRoleplay && conversation?.character" class="control-btn" @click="showCharacterPicker = true" title="Change Character">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/>
            </svg>
          </button>
          <button class="control-btn" @click="handleClear" title="Clear">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
              <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
            </svg>
          </button>
          <button class="control-btn close" @click="$emit('close')">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Inline Character Picker (for new roleplay) -->
    <div v-if="isRoleplay && !conversation?.character" class="character-picker-inline">
      <div class="picker-header">
        <h3>🎭 Choose Your Character</h3>
        <p>Select a character to start your roleplay</p>
      </div>

      <!-- Category Tabs -->
      <div class="category-tabs">
        <button
          v-for="cat in characterCategories"
          :key="cat.id"
          class="category-tab"
          :class="{ active: selectedCategory === cat.id }"
          @click="selectedCategory = cat.id"
        >
          {{ cat.icon }} {{ cat.label }}
        </button>
      </div>

      <!-- Character Grid -->
      <div class="character-scroll">
        <div class="character-grid">
          <button
            v-for="char in filteredCharacters"
            :key="char.id"
            class="character-card"
            @click="selectCharacter(char)"
          >
            <span class="char-icon">{{ char.icon }}</span>
            <span class="char-name">{{ char.name }}</span>
            <span class="char-desc">{{ char.description }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Message List -->
    <main v-else class="chat-body" ref="messagesContainer">
      <!-- Empty State -->
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor" opacity="0.3">
            <path d="M24 4C12.954 4 4 12.954 4 24s8.954 20 20 20 20-8.954 20-20S35.046 4 24 4zm0 36c-8.822 0-16-7.178-16-16S15.178 8 24 8s16 7.178 16 16-7.178 16-16 16zm-4-20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm8 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm-10.5 8.5a1.5 1.5 0 0 1 2.121 0c2.344 2.344 6.414 2.344 8.758 0a1.5 1.5 0 0 1 2.121 2.121c-3.515 3.515-9.485 3.515-13 0a1.5 1.5 0 0 1 0-2.121z"/>
          </svg>
        </div>
        <h3 class="empty-title">{{ isRoleplay ? 'Start your story' : 'Start a conversation' }}</h3>
        <p class="empty-subtitle">{{ isRoleplay ? 'Say something to begin the roleplay' : 'Ask SAM anything' }}</p>
      </div>

      <!-- Messages -->
      <TransitionGroup name="message" tag="div" class="messages-list">
        <article
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="{ 'is-user': msg.role === 'user', 'is-assistant': msg.role === 'assistant' }"
        >
          <div class="message-bubble">
            <p class="message-text" v-html="formatMessage(msg.content)"></p>
          </div>
          <footer class="message-footer">
            <time class="message-time">{{ formatTime(msg.timestamp) }}</time>
            <span v-if="msg.model && msg.role === 'assistant'" class="message-source">{{ msg.model }}</span>
          </footer>
        </article>
      </TransitionGroup>

      <!-- Typing Indicator -->
      <div v-if="isThinking" class="typing-row">
        <div class="typing-bubble">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
    </main>

    <!-- Input Area -->
    <footer class="chat-footer">
      <!-- Provider Segmented Control -->
      <nav v-if="!isRoleplay" class="provider-nav">
        <div class="segmented-control">
          <button
            v-for="p in providers"
            :key="p.id"
            class="segment"
            :class="{ active: selectedProvider === p.id }"
            @click="selectedProvider = p.id"
          >
            {{ p.label }}
          </button>
          <div class="segment-indicator" :style="segmentIndicatorStyle"></div>
        </div>
      </nav>

      <!-- Roleplay Mode Indicator -->
      <div v-else class="mode-badge roleplay">
        <span class="badge-text">Roleplay</span>
      </div>

      <!-- Input Row -->
      <div class="input-container">
        <textarea
          ref="inputRef"
          v-model="inputText"
          class="message-input"
          :placeholder="getPlaceholder()"
          rows="1"
          @keydown="handleKeydown"
          @input="autoResize"
        ></textarea>
        <button
          class="send-button"
          :disabled="!inputText.trim() || isThinking"
          @click="sendMessage"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 0 0-1.788 0l-7 14a1 1 0 0 0 1.169 1.409l5-1.429A1 1 0 0 0 9 15.571V11a1 1 0 1 1 2 0v4.571a1 1 0 0 0 .725.962l5 1.428a1 1 0 0 0 1.17-1.408l-7-14z"/>
          </svg>
        </button>
      </div>

      <!-- Status Bar -->
      <div v-if="lastProvider" class="status-bar">
        <span class="status-text">{{ lastProvider }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch, computed } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { useClaudeBridge } from '../composables/useClaudeBridge'
import { useConversations, type Conversation, type Message } from '../composables/useConversations'

const props = defineProps<{
  conversation: Conversation
  modelsReady?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'open-characters'): void
}>()

// Composables
const bridge = useClaudeBridge()
const { addMessage, clearMessages, updateTitle, setCharacter } = useConversations()

// Local state
const inputText = ref('')
const isThinking = ref(false)
const lastProvider = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const showCharacterPicker = ref(false)
const selectedCategory = ref('all')

// Character categories
const characterCategories = [
  { id: 'all', label: 'All', icon: '📚' },
  { id: 'villains', label: 'Villains', icon: '😈' },
  { id: 'fantasy', label: 'Fantasy', icon: '🧙' },
  { id: 'scifi', label: 'Sci-Fi', icon: '🚀' },
  { id: 'modern', label: 'Modern', icon: '🏙️' },
  { id: 'comedy', label: 'Comedy', icon: '😂' },
  { id: 'romantic', label: 'Romance', icon: '💕' },
]

// Default characters (fallback if backend unavailable)
const defaultCharacters = [
  // Villains
  { id: 'villain', name: 'Mastermind Villain', icon: '🦹', description: 'Calculating genius', traits: ['intelligent', 'ruthless'], category: 'villains' },
  { id: 'bully', name: 'Intimidating Bully', icon: '👊', description: 'Rules through fear', traits: ['aggressive', 'intimidating'], category: 'villains' },
  { id: 'trickster', name: 'Chaotic Trickster', icon: '🃏', description: 'Agent of chaos', traits: ['unpredictable', 'clever'], category: 'villains' },
  { id: 'corrupt', name: 'Corrupt Official', icon: '🏛️', description: 'Power-hungry politician', traits: ['manipulative', 'greedy'], category: 'villains' },
  { id: 'assassin', name: 'Cold Assassin', icon: '🗡️', description: 'Efficient killer', traits: ['deadly', 'emotionless'], category: 'villains' },
  { id: 'darklord', name: 'Dark Overlord', icon: '👿', description: 'Pure evil incarnate', traits: ['menacing', 'powerful'], category: 'villains' },

  // Fantasy
  { id: 'wizard', name: 'Wise Wizard', icon: '🧙', description: 'Ancient spellcaster', traits: ['wise', 'mysterious'], category: 'fantasy' },
  { id: 'warrior', name: 'Battle Warrior', icon: '⚔️', description: 'Scarred veteran', traits: ['brave', 'honorable'], category: 'fantasy' },
  { id: 'elf', name: 'Ancient Elf', icon: '🧝', description: 'Immortal wisdom', traits: ['elegant', 'aloof'], category: 'fantasy' },
  { id: 'dragon', name: 'Dragon Lord', icon: '🐉', description: 'Ancient power', traits: ['proud', 'ancient'], category: 'fantasy' },
  { id: 'necromancer', name: 'Dark Necromancer', icon: '💀', description: 'Master of death', traits: ['sinister', 'powerful'], category: 'fantasy' },
  { id: 'fairy', name: 'Mischievous Fairy', icon: '🧚', description: 'Playful trickster', traits: ['whimsical', 'magical'], category: 'fantasy' },
  { id: 'dwarf', name: 'Grumpy Dwarf', icon: '⛏️', description: 'Master craftsman', traits: ['stubborn', 'skilled'], category: 'fantasy' },
  { id: 'vampire', name: 'Ancient Vampire', icon: '🧛', description: 'Eternal darkness', traits: ['seductive', 'deadly'], category: 'fantasy' },

  // Sci-Fi
  { id: 'android', name: 'Sentient Android', icon: '🤖', description: 'AI finding humanity', traits: ['logical', 'curious'], category: 'scifi' },
  { id: 'captain', name: 'Starship Captain', icon: '👨‍🚀', description: 'Bold space leader', traits: ['decisive', 'charismatic'], category: 'scifi' },
  { id: 'alien', name: 'Mysterious Alien', icon: '👽', description: 'Unknown intentions', traits: ['enigmatic', 'advanced'], category: 'scifi' },
  { id: 'hacker', name: 'Elite Hacker', icon: '💻', description: 'Digital shadow', traits: ['brilliant', 'paranoid'], category: 'scifi' },
  { id: 'cyborg', name: 'Enhanced Cyborg', icon: '🦾', description: 'Part machine', traits: ['conflicted', 'powerful'], category: 'scifi' },
  { id: 'scientist', name: 'Mad Scientist', icon: '🔬', description: 'Genius gone wrong', traits: ['brilliant', 'unhinged'], category: 'scifi' },
  { id: 'bounty', name: 'Bounty Hunter', icon: '🎯', description: 'Relentless tracker', traits: ['determined', 'ruthless'], category: 'scifi' },

  // Modern
  { id: 'detective', name: 'Noir Detective', icon: '🕵️', description: 'Cynical investigator', traits: ['observant', 'cynical'], category: 'modern' },
  { id: 'spy', name: 'Secret Agent', icon: '🕴️', description: 'International spy', traits: ['suave', 'deadly'], category: 'modern' },
  { id: 'doctor', name: 'Brilliant Doctor', icon: '👨‍⚕️', description: 'Medical genius', traits: ['analytical', 'caring'], category: 'modern' },
  { id: 'artist', name: 'Tortured Artist', icon: '🎨', description: 'Creative soul', traits: ['passionate', 'moody'], category: 'modern' },
  { id: 'chef', name: 'Master Chef', icon: '👨‍🍳', description: 'Culinary perfectionist', traits: ['demanding', 'creative'], category: 'modern' },
  { id: 'lawyer', name: 'Ruthless Lawyer', icon: '⚖️', description: 'Wins at any cost', traits: ['cunning', 'persuasive'], category: 'modern' },
  { id: 'rockstar', name: 'Faded Rockstar', icon: '🎸', description: 'Past their prime', traits: ['nostalgic', 'dramatic'], category: 'modern' },

  // Comedy
  { id: 'sidekick', name: 'Sarcastic Sidekick', icon: '😏', description: 'Witty companion', traits: ['sarcastic', 'loyal'], category: 'comedy' },
  { id: 'grandma', name: 'Savage Grandma', icon: '👵', description: 'No filter', traits: ['blunt', 'loving'], category: 'comedy' },
  { id: 'salesman', name: 'Sleazy Salesman', icon: '🤵', description: 'Sells anything', traits: ['persuasive', 'shameless'], category: 'comedy' },
  { id: 'conspiracy', name: 'Conspiracy Theorist', icon: '🔍', description: 'Sees patterns everywhere', traits: ['paranoid', 'passionate'], category: 'comedy' },
  { id: 'influencer', name: 'Clueless Influencer', icon: '📱', description: 'All about the brand', traits: ['vain', 'oblivious'], category: 'comedy' },
  { id: 'neighbor', name: 'Nosy Neighbor', icon: '🏠', description: 'Knows everything', traits: ['gossipy', 'intrusive'], category: 'comedy' },

  // Romantic
  { id: 'prince', name: 'Charming Prince', icon: '🤴', description: 'Royal romantic', traits: ['charming', 'noble'], category: 'romantic' },
  { id: 'rebel', name: 'Bad Boy Rebel', icon: '🏍️', description: 'Dangerous attraction', traits: ['rebellious', 'passionate'], category: 'romantic' },
  { id: 'professor', name: 'Brooding Professor', icon: '📚', description: 'Intellectual depth', traits: ['intense', 'brilliant'], category: 'romantic' },
  { id: 'ceo', name: 'Cold CEO', icon: '💼', description: 'All business until...', traits: ['distant', 'powerful'], category: 'romantic' },
  { id: 'childhood', name: 'Childhood Friend', icon: '🏡', description: 'Always been there', traits: ['familiar', 'devoted'], category: 'romantic' },
  { id: 'rival', name: 'Enemies to Lovers', icon: '⚡', description: 'Hate turns to passion', traits: ['competitive', 'intense'], category: 'romantic' },
]

// Reactive character list - starts with defaults, loads from backend
const allCharacters = ref(defaultCharacters)

// Load characters from backend
async function loadCharactersFromBackend() {
  try {
    const backendCharacters = await invoke('cmd_list_archetypes')
    if (Array.isArray(backendCharacters) && backendCharacters.length > 0) {
      // Map backend format to our format
      allCharacters.value = backendCharacters.map((arch: any) => ({
        id: arch.id,
        name: arch.name,
        icon: arch.icon || '🎭',
        description: arch.description || '',
        traits: arch.traits || [],
        category: arch.category || 'all'
      }))
      console.log('[ChatPanel] Loaded', allCharacters.value.length, 'characters from backend')
    }
  } catch (e) {
    console.warn('[ChatPanel] Using default characters:', e)
  }
}

// Filtered characters based on selected category
const filteredCharacters = computed(() => {
  if (selectedCategory.value === 'all') {
    return allCharacters.value
  }
  return allCharacters.value.filter(c => c.category === selectedCategory.value)
})

interface Character {
  id: string
  name: string
  icon: string
  description: string
  traits: string[]
  category: string
}

function selectCharacter(char: Character) {
  if (props.conversation) {
    const characterName = `${char.name} (${char.traits.join(', ')})`
    setCharacter(props.conversation.id, characterName)
    updateTitle(props.conversation.id, char.name)
    console.log('[ChatPanel] Character selected:', characterName)
  }
}

// Provider options
type ProviderType = 'auto' | 'sam' | 'claude'
const selectedProvider = ref<ProviderType>('auto')

const providers = [
  { id: 'auto' as ProviderType, label: 'Auto' },
  { id: 'sam' as ProviderType, label: 'SAM' },
  { id: 'claude' as ProviderType, label: 'Claude' }
]

// Computed
const isRoleplay = computed(() => props.conversation?.type === 'roleplay')
const messages = computed(() => props.conversation?.messages || [])

const currentModel = computed(() => {
  if (isRoleplay.value) return 'Roleplay'
  switch (selectedProvider.value) {
    case 'sam': return 'SAM'
    case 'claude': return 'Claude'
    default: return props.modelsReady ? 'SAM (ready)' : 'Loading...'
  }
})

const segmentIndicatorStyle = computed(() => {
  const index = providers.findIndex(p => p.id === selectedProvider.value)
  return { transform: `translateX(${index * 100}%)` }
})

function getPlaceholder(): string {
  if (isRoleplay.value) return 'Continue the story...'
  switch (selectedProvider.value) {
    case 'sam': return 'Ask SAM...'
    case 'claude': return 'Ask Claude...'
    default: return 'Message...'
  }
}

// Focus input on mount and load characters
onMounted(() => {
  inputRef.value?.focus()
  scrollToBottom()
  loadCharactersFromBackend()
})

// Scroll to bottom when messages change
watch(() => props.conversation?.messages.length, () => {
  nextTick(scrollToBottom)
})

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isThinking.value || !props.conversation) return

  // Add user message
  addMessage(props.conversation.id, {
    role: 'user',
    content: text,
    timestamp: new Date()
  })

  inputText.value = ''
  autoResize()
  await nextTick()
  scrollToBottom()

  isThinking.value = true

  try {
    let content = ''
    let model = 'sam'

    const history = messages.value
      .slice(-10)
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    if (isRoleplay.value) {
      const response = await bridge.roleplay(text, history, props.conversation.character)
      content = response.content
      model = 'roleplay'
      lastProvider.value = 'sam-roleplay'
    } else {
      const response = await bridge.chat(text, history, { provider: selectedProvider.value })
      content = response.content
      model = response.provider === 'claude' ? 'claude' : 'sam'
      lastProvider.value = response.provider + (response.escalated ? ' (escalated)' : '')
    }

    // Add assistant response
    addMessage(props.conversation.id, {
      role: 'assistant',
      content,
      timestamp: new Date(),
      model,
      provider: model === 'claude' ? 'claude' : 'sam'
    })

  } catch (e: any) {
    addMessage(props.conversation.id, {
      role: 'assistant',
      content: 'Something went wrong. Please try again.',
      timestamp: new Date()
    })
  } finally {
    isThinking.value = false
    await nextTick()
    scrollToBottom()
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function autoResize() {
  const textarea = inputRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    // Use requestAnimationFrame for more reliable scrolling
    requestAnimationFrame(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTo({
          top: messagesContainer.value.scrollHeight,
          behavior: 'smooth'
        })
      }
    })
  }
}

function handleClear() {
  if (props.conversation) {
    clearMessages(props.conversation.id)
  }
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

function formatMessage(content: string): string {
  return content
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
/* ============================================
   Apple-Native Chat Panel Design
   ============================================ */

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Critical for flex overflow scrolling */
  background: transparent;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
}

.chat-panel.roleplay-mode .chat-header {
  border-bottom-color: rgba(175, 82, 222, 0.2);
}

/* ============================================
   Header
   ============================================ */

.chat-header {
  flex-shrink: 0;
  padding: 14px 16px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 0.5px solid rgba(255, 255, 255, 0.08);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  letter-spacing: -0.3px;
}

.header-info {
  display: flex;
  gap: 6px;
}

.info-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

.info-badge.model {
  background: rgba(10, 132, 255, 0.15);
  color: #64b5f6;
}

.info-badge.model.ready {
  background: rgba(48, 209, 88, 0.15);
  color: #30d158;
}

.info-badge.character {
  background: rgba(155, 89, 182, 0.2);
  color: #bb86fc;
  cursor: pointer;
  transition: all 0.15s ease;
}

.info-badge.character:hover {
  background: rgba(155, 89, 182, 0.3);
}

.info-badge.character.picking {
  background: rgba(155, 89, 182, 0.1);
  color: rgba(187, 134, 252, 0.7);
  animation: pickingPulse 2s ease-in-out infinite;
}

@keyframes pickingPulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

/* ============================================
   Inline Character Picker
   ============================================ */

.character-picker-inline {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  min-height: 0;
  /* Remove max-height constraint to let flex work */
  overflow-y: auto;
  overflow-x: hidden;
  background: linear-gradient(180deg, rgba(155, 89, 182, 0.05) 0%, transparent 100%);
}

.picker-header {
  text-align: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.picker-header h3 {
  font-size: 17px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 4px;
}

.picker-header p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

/* Category Tabs */
.category-tabs {
  display: flex;
  gap: 6px;
  padding: 8px 0;
  overflow-x: auto;
  flex-shrink: 0;
  margin-bottom: 12px;
}

.category-tabs::-webkit-scrollbar {
  height: 0;
}

.category-tab {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.category-tab:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

.category-tab.active {
  background: rgba(155, 89, 182, 0.3);
  border-color: rgba(155, 89, 182, 0.5);
  color: #bb86fc;
}

/* Character Scroll Container */
.character-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding-right: 4px;
}

.character-scroll::-webkit-scrollbar {
  width: 6px;
}

.character-scroll::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.character-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.character-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.character-card:hover {
  background: rgba(155, 89, 182, 0.15);
  border-color: rgba(155, 89, 182, 0.3);
  transform: translateY(-2px);
}

.char-icon {
  font-size: 28px;
  margin-bottom: 6px;
}

.char-name {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 2px;
}

.char-desc {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.model-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #30d158;
}

.status-dot.pulse {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.header-controls {
  display: flex;
  gap: 4px;
}

.control-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
}

.control-btn.close:hover {
  background: rgba(255, 69, 58, 0.2);
  color: #ff453a;
}

/* ============================================
   Message Body
   ============================================ */

.chat-body {
  flex: 1;
  min-height: 0; /* Critical for flex overflow scrolling */
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
}

.chat-body::-webkit-scrollbar {
  width: 8px;
}

.chat-body::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.chat-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 4px;
}

.chat-body::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.35);
}

/* Empty State */
.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
}

.empty-icon {
  margin-bottom: 12px;
}

.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin: 0 0 6px;
  letter-spacing: -0.2px;
}

.empty-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  margin: 0;
}

/* Messages List */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Message Row */
.message-row {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message-row.is-user {
  align-self: flex-end;
  align-items: flex-end;
}

.message-row.is-assistant {
  align-self: flex-start;
  align-items: flex-start;
}

/* Message Bubble */
.message-bubble {
  padding: 10px 14px;
  border-radius: 18px;
  max-width: 100%;
}

.is-user .message-bubble {
  background: #0a84ff;
  border-bottom-right-radius: 4px;
}

.is-assistant .message-bubble {
  background: rgba(255, 255, 255, 0.1);
  border-bottom-left-radius: 4px;
}

.roleplay-mode .is-assistant .message-bubble {
  background: rgba(175, 82, 222, 0.15);
}

.message-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.95);
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-text :deep(code) {
  background: rgba(0, 0, 0, 0.25);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 13px;
}

.message-text :deep(em) {
  color: rgba(255, 255, 255, 0.75);
  font-style: italic;
}

.message-text :deep(strong) {
  font-weight: 600;
}

/* Message Footer */
.message-footer {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  padding: 0 4px;
}

.message-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

.message-source {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.25);
}

/* Message Transitions */
.message-enter-active {
  transition: all 0.25s ease-out;
}

.message-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

/* Typing Indicator */
.typing-row {
  display: flex;
  align-items: flex-start;
  margin-top: 8px;
}

.typing-bubble {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  border-bottom-left-radius: 4px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.15s; }
.typing-dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

/* ============================================
   Footer / Input Area
   ============================================ */

.chat-footer {
  flex-shrink: 0;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.15);
  border-top: 0.5px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Segmented Control */
.provider-nav {
  padding: 0 2px;
}

.segmented-control {
  position: relative;
  display: flex;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 2px;
}

.segment {
  flex: 1;
  position: relative;
  z-index: 1;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s ease;
  border-radius: 6px;
}

.segment.active {
  color: #ffffff;
}

.segment-indicator {
  position: absolute;
  top: 2px;
  left: 2px;
  width: calc(33.333% - 1.33px);
  height: calc(100% - 4px);
  background: rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  transition: transform 0.2s ease;
  pointer-events: none;
}

/* Mode Badge */
.mode-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  background: rgba(175, 82, 222, 0.15);
  border-radius: 8px;
}

.badge-text {
  font-size: 12px;
  font-weight: 500;
  color: #bf5af2;
}

/* Input Container */
.input-container {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.message-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 10px 16px;
  color: #ffffff;
  font-size: 15px;
  font-family: inherit;
  line-height: 1.4;
  resize: none;
  outline: none;
  min-height: 40px;
  max-height: 120px;
  transition: all 0.15s ease;
}

.message-input::placeholder {
  color: rgba(255, 255, 255, 0.35);
}

.message-input:focus {
  border-color: rgba(10, 132, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
}

.send-button {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border: none;
  border-radius: 50%;
  background: #0a84ff;
  color: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.send-button:hover:not(:disabled) {
  background: #0070e0;
  transform: scale(1.05);
}

.send-button:disabled {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.3);
  cursor: not-allowed;
}

/* Status Bar */
.status-bar {
  text-align: center;
}

.status-text {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}
</style>
