<template>
  <div class="chat-panel" :class="{ minimized: isMinimized }">
    <!-- Header -->
    <div class="chat-header" @click="isMinimized = !isMinimized">
      <div class="header-left">
        <span class="chat-icon">💬</span>
        <span class="chat-title">{{ projectName || 'SAM Chat' }}</span>
        <span v-if="isThinking" class="thinking-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </span>
      </div>
      <div class="header-actions">
        <button class="header-btn" @click.stop="clearChat" title="Clear chat">🗑</button>
        <button class="header-btn" @click.stop="isMinimized = !isMinimized">
          {{ isMinimized ? '▲' : '▼' }}
        </button>
        <button class="header-btn close" @click.stop="$emit('close')" title="Close">✕</button>
      </div>
    </div>

    <!-- Messages -->
    <div v-if="!isMinimized" class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-chat">
        <div class="empty-icon">🤖</div>
        <div class="empty-text">Start a conversation with SAM</div>
        <div class="empty-hint">Ask questions, give commands, or request tasks</div>
      </div>

      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(msg.content)"></div>
          <div class="message-meta">
            <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
            <span v-if="msg.role === 'assistant' && msg.model" class="message-model">
              via {{ msg.model }}
            </span>
          </div>
        </div>
      </div>

      <!-- Typing indicator -->
      <div v-if="isThinking" class="message assistant typing">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div v-if="!isMinimized" class="chat-input-container">
      <textarea
        ref="inputRef"
        v-model="inputText"
        class="chat-input"
        placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
        rows="1"
        @keydown="handleKeydown"
        @input="autoResize"
      ></textarea>
      <button
        class="send-btn"
        :disabled="!inputText.trim() || isThinking"
        @click="sendMessage"
      >
        {{ isThinking ? '...' : '→' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  model?: string
}

const props = defineProps<{
  projectId?: string
  projectName?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

// State
const messages = ref<Message[]>([])
const inputText = ref('')
const isThinking = ref(false)
const isMinimized = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

// Load saved messages for this project/session
onMounted(() => {
  loadMessages()
  inputRef.value?.focus()
})

// Watch for project changes
watch(() => props.projectId, () => {
  loadMessages()
})

function loadMessages() {
  const key = `sam_chat_${props.projectId || 'global'}`
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      messages.value = parsed.map((m: any) => ({
        ...m,
        timestamp: new Date(m.timestamp)
      }))
    } catch (e) {
      console.error('Failed to load messages:', e)
    }
  }
}

function saveMessages() {
  const key = `sam_chat_${props.projectId || 'global'}`
  localStorage.setItem(key, JSON.stringify(messages.value))
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isThinking.value) return

  // Add user message
  const userMsg: Message = {
    id: `msg-${Date.now()}`,
    role: 'user',
    content: text,
    timestamp: new Date()
  }
  messages.value.push(userMsg)
  inputText.value = ''
  autoResize()

  // Scroll to bottom
  await nextTick()
  scrollToBottom()

  // Think...
  isThinking.value = true

  try {
    // Use the chat-friendly API with optional project context
    const response = await invoke<string>('query_ollama_chat', {
      prompt: text,
      model: 'qwen2.5-coder:1.5b',
      context: props.projectName || null
    })

    // Add assistant response
    const assistantMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: response,
      timestamp: new Date(),
      model: 'qwen2.5-coder:1.5b'
    }
    messages.value.push(assistantMsg)

  } catch (e: any) {
    // Add error message
    const errorMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: `Error: ${e.toString()}`,
      timestamp: new Date()
    }
    messages.value.push(errorMsg)
  } finally {
    isThinking.value = false
    saveMessages()
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
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function clearChat() {
  if (confirm('Clear all messages?')) {
    messages.value = []
    saveMessages()
  }
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

function formatMessage(content: string): string {
  // Basic markdown-like formatting
  return content
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.chat-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 400px;
  max-height: 600px;
  background: linear-gradient(180deg, #1c1c24 0%, #16161e 100%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  overflow: hidden;
}

.chat-panel.minimized {
  max-height: 48px;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-icon {
  font-size: 18px;
}

.chat-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.thinking-indicator {
  display: flex;
  gap: 3px;
  margin-left: 8px;
}

.thinking-indicator .dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #0a84ff;
  animation: bounce 1.4s infinite ease-in-out;
}

.thinking-indicator .dot:nth-child(1) { animation-delay: 0s; }
.thinking-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.header-actions {
  display: flex;
  gap: 4px;
}

.header-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.header-btn.close:hover {
  background: rgba(255, 59, 48, 0.2);
  color: #ff3b30;
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
  max-height: 400px;
}

.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

/* Message */
.message {
  display: flex;
  gap: 10px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: rgba(10, 132, 255, 0.2);
}

.message-content {
  max-width: 80%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-text {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
}

.message.user .message-text {
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-text {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  border-bottom-left-radius: 4px;
}

.message-text :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
  font-size: 13px;
}

.message-meta {
  display: flex;
  gap: 8px;
  padding: 0 4px;
}

.message-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

.message-model {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.25);
  font-style: italic;
}

.message.user .message-meta {
  justify-content: flex-end;
}

/* Typing indicator */
.message.typing .message-content {
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 14px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* Input */
.chat-input-container {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.2);
}

.chat-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 10px 14px;
  color: #ffffff;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  line-height: 1.4;
  min-height: 40px;
  max-height: 150px;
}

.chat-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.chat-input:focus {
  border-color: rgba(10, 132, 255, 0.5);
  background: rgba(255, 255, 255, 0.08);
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  color: #ffffff;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(10, 132, 255, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 480px) {
  .chat-panel {
    width: calc(100% - 20px);
    right: 10px;
    bottom: 10px;
  }
}
</style>
