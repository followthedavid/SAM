<script setup lang="ts">
/**
 * Quick Chat Overlay
 *
 * A minimal, always-on-top chat input that appears with ⌘⇧A.
 * Think Spotlight/Alfred but for talking to SAM.
 */

import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useSAM } from '@/composables/useSAM'
import { appWindow } from '@tauri-apps/api/window'
import { emit } from '@tauri-apps/api/event'

const sam = useSAM()

const input = ref('')
const inputEl = ref<HTMLInputElement>()
const isProcessing = ref(false)
const response = ref('')
const showResponse = ref(false)

// Computed mood indicator
const moodEmoji = computed(() => {
  const mood = sam.enhanced.personality.determineMood()
  return mood.emoji
})

const moodColor = computed(() => {
  const mood = sam.enhanced.personality.determineMood()
  return mood.color
})

// Submit message
async function submit() {
  if (!input.value.trim() || isProcessing.value) return

  const message = input.value
  input.value = ''
  isProcessing.value = true

  try {
    // Quick commands
    if (message.startsWith('/')) {
      await handleCommand(message)
      return
    }

    // Send to SAM
    await sam.handleUserMessage(message)

    // Get the last response
    const lastMessage = sam.conversationHistory.value.slice(-1)[0]
    if (lastMessage?.role === 'sam') {
      response.value = lastMessage.content
      showResponse.value = true

      // Auto-hide after showing response
      setTimeout(() => {
        close()
      }, 3000)
    }
  } finally {
    isProcessing.value = false
  }
}

// Handle slash commands
async function handleCommand(cmd: string) {
  const [command, ...args] = cmd.slice(1).split(' ')

  switch (command.toLowerCase()) {
    case 'mood':
      const mood = args[0] || 'neutral'
      sam.setMood(mood as any)
      response.value = `Mood set to ${mood}`
      showResponse.value = true
      break

    case 'flirt':
      await sam.flirt()
      break

    case 'voice':
      sam.voice.toggleMute()
      response.value = sam.voice.isEnabled.value ? 'Voice enabled' : 'Voice muted'
      showResponse.value = true
      break

    case 'avatar':
      await emit('sam:toggle_avatar')
      close()
      break

    case 'customize':
      await emit('sam:open_customizer')
      close()
      break

    case 'clear':
      sam.conversationHistory.value = []
      response.value = 'Conversation cleared'
      showResponse.value = true
      break

    case 'memories':
      const count = sam.memory.memoryCount.value
      response.value = `${count} memories stored`
      showResponse.value = true
      break

    default:
      response.value = `Unknown command: ${command}`
      showResponse.value = true
  }

  isProcessing.value = false
  setTimeout(close, 1500)
}

// Close overlay
async function close() {
  showResponse.value = false
  response.value = ''
  input.value = ''
  await appWindow.hide()
}

// Handle escape key
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
  }
}

// Focus input on mount
onMounted(async () => {
  await nextTick()
  inputEl.value?.focus()
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="quick-chat" @click.self="close">
    <div class="chat-container">
      <!-- Mood indicator -->
      <div class="mood-indicator" :style="{ backgroundColor: moodColor }">
        {{ moodEmoji }}
      </div>

      <!-- Input -->
      <div class="input-wrapper">
        <input
          ref="inputEl"
          v-model="input"
          type="text"
          :placeholder="isProcessing ? 'Thinking...' : 'Ask SAM anything...'"
          :disabled="isProcessing"
          @keydown.enter="submit"
          class="chat-input"
        />

        <!-- Submit button -->
        <button
          @click="submit"
          :disabled="isProcessing || !input.trim()"
          class="submit-btn"
        >
          <span v-if="isProcessing" class="spinner"></span>
          <span v-else>↵</span>
        </button>
      </div>

      <!-- Response -->
      <transition name="slide">
        <div v-if="showResponse" class="response">
          {{ response }}
        </div>
      </transition>

      <!-- Hints -->
      <div class="hints">
        <span class="hint">/mood playful</span>
        <span class="hint">/voice</span>
        <span class="hint">/avatar</span>
        <span class="hint">esc to close</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quick-chat {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 20vh;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.chat-container {
  width: 100%;
  max-width: 600px;
  background: rgba(30, 30, 35, 0.95);
  border-radius: 16px;
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.mood-indicator {
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  padding: 4px;
}

.chat-input {
  flex: 1;
  padding: 16px 20px;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 18px;
  font-family: inherit;
  outline: none;
}

.chat-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.chat-input:disabled {
  opacity: 0.6;
}

.submit-btn {
  width: 40px;
  height: 40px;
  margin-right: 8px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.response {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.05);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
  line-height: 1.5;
}

.hints {
  display: flex;
  gap: 12px;
  padding: 8px 20px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.hint {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  font-family: 'SF Mono', monospace;
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
