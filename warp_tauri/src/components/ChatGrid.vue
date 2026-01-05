<template>
  <div class="chat-grid-overlay" @click.self="$emit('close')">
    <div class="chat-grid-container">
      <!-- Header -->
      <div class="grid-header">
        <h2>💬 Conversations</h2>
        <div class="header-actions">
          <button class="new-chat-btn" @click="addNewChat">
            + New Chat
          </button>
          <button class="close-grid-btn" @click="$emit('close')">✕</button>
        </div>
      </div>

      <!-- Grid of Chats -->
      <div class="chats-grid" :class="`grid-${Math.min(chats.length, 4)}`">
        <div
          v-for="chat in chats"
          :key="chat.id"
          class="chat-cell"
          :class="{ active: activeChat === chat.id }"
        >
          <!-- Chat Header -->
          <div class="cell-header" @click="activeChat = chat.id">
            <span class="cell-icon">{{ chat.icon }}</span>
            <input
              v-model="chat.title"
              class="cell-title"
              @click.stop
              @focus="activeChat = chat.id"
            />
            <button class="cell-close" @click.stop="removeChat(chat.id)" title="Close">✕</button>
          </div>

          <!-- Messages -->
          <div class="cell-messages" ref="messageContainers">
            <div v-if="chat.messages.length === 0" class="cell-empty">
              Start a conversation...
            </div>
            <div
              v-for="msg in chat.messages"
              :key="msg.id"
              class="cell-msg"
              :class="msg.role"
            >
              <span class="msg-role">{{ msg.role === 'user' ? '👤' : '🤖' }}</span>
              <span class="msg-text">{{ msg.content }}</span>
            </div>
            <div v-if="chat.isThinking" class="cell-msg assistant">
              <span class="msg-role">🤖</span>
              <span class="thinking-dots"><span></span><span></span><span></span></span>
            </div>
          </div>

          <!-- Input -->
          <div class="cell-input">
            <textarea
              v-model="chat.inputText"
              placeholder="Type a message..."
              rows="1"
              @keydown.enter.exact.prevent="sendMessage(chat)"
              @input="autoResize($event)"
              @focus="activeChat = chat.id"
            ></textarea>
            <button
              class="cell-send"
              :disabled="!chat.inputText.trim() || chat.isThinking"
              @click="sendMessage(chat)"
            >
              →
            </button>
          </div>
        </div>

        <!-- Add Chat Card -->
        <div v-if="chats.length < 6" class="chat-cell add-cell" @click="addNewChat">
          <div class="add-icon">+</div>
          <div class="add-label">New Conversation</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface Chat {
  id: string
  title: string
  icon: string
  messages: Message[]
  inputText: string
  isThinking: boolean
}

const emit = defineEmits<{
  (e: 'close'): void
}>()

// State
const chats = reactive<Chat[]>([
  createNewChat('General')
])
const activeChat = ref(chats[0].id)
const messageContainers = ref<HTMLElement[]>([])

function createNewChat(title: string = 'New Chat'): Chat {
  const icons = ['💬', '🎯', '🔧', '📝', '🎨', '🚀', '💡', '🔍']
  return {
    id: `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    title,
    icon: icons[Math.floor(Math.random() * icons.length)],
    messages: [],
    inputText: '',
    isThinking: false
  }
}

function addNewChat() {
  if (chats.length >= 6) return
  const newChat = createNewChat(`Chat ${chats.length + 1}`)
  chats.push(newChat)
  activeChat.value = newChat.id
}

function removeChat(id: string) {
  const index = chats.findIndex(c => c.id === id)
  if (index !== -1) {
    chats.splice(index, 1)
    if (chats.length === 0) {
      addNewChat()
    } else if (activeChat.value === id) {
      activeChat.value = chats[0].id
    }
  }
}

interface OrchestratorResponse {
  type: 'instant' | 'search' | 'generated' | 'error'
  output?: string
  content?: string
  message?: string
  chunks?: Array<{ file_path: string; content: string; line_start: number }>
  tool_calls?: Array<{ tool: string; result: string; success: boolean }>
}

async function sendMessage(chat: Chat) {
  const text = chat.inputText.trim()
  if (!text || chat.isThinking) return

  // Add user message
  chat.messages.push({
    id: `msg-${Date.now()}`,
    role: 'user',
    content: text,
    timestamp: new Date()
  })
  chat.inputText = ''
  chat.isThinking = true

  await nextTick()
  scrollToBottom(chat.id)

  try {
    // Use orchestrator for intelligent routing and tool execution
    const response = await invoke<OrchestratorResponse>('orchestrate_request', {
      input: text,
      workingDir: null,
      sessionId: chat.id
    })

    let assistantContent = ''
    switch (response.type) {
      case 'instant':
        assistantContent = response.output || 'Done.'
        break
      case 'search':
        assistantContent = response.chunks?.map(c => `📄 ${c.file_path}:${c.line_start}\n${c.content.slice(0, 200)}...`).join('\n\n') || 'No results.'
        break
      case 'generated':
        assistantContent = response.content || ''
        if (response.tool_calls?.length) {
          assistantContent += '\n\n📋 Tools: ' + response.tool_calls.map(t => `${t.success ? '✅' : '❌'} ${t.tool}`).join(', ')
        }
        break
      case 'error':
        assistantContent = `❌ ${response.message}`
        break
    }

    chat.messages.push({
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: assistantContent,
      timestamp: new Date()
    })
  } catch (e: any) {
    chat.messages.push({
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: `Error: ${e.toString()}`,
      timestamp: new Date()
    })
  } finally {
    chat.isThinking = false
    await nextTick()
    scrollToBottom(chat.id)
  }
}

function scrollToBottom(chatId: string) {
  const index = chats.findIndex(c => c.id === chatId)
  if (index !== -1 && messageContainers.value[index]) {
    messageContainers.value[index].scrollTop = messageContainers.value[index].scrollHeight
  }
}

function autoResize(event: Event) {
  const textarea = event.target as HTMLTextAreaElement
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px'
}
</script>

<style scoped>
.chat-grid-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(10px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.chat-grid-container {
  width: 100%;
  max-width: 1400px;
  max-height: 90vh;
  background: linear-gradient(180deg, #1c1c24 0%, #12121a 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.grid-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.new-chat-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  border: none;
  border-radius: 10px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(10, 132, 255, 0.4);
}

.close-grid-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.6);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.close-grid-btn:hover {
  background: rgba(255, 59, 48, 0.2);
  color: #ff3b30;
}

/* Chat Grid */
.chats-grid {
  display: grid;
  gap: 16px;
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.chats-grid.grid-1 { grid-template-columns: 1fr; }
.chats-grid.grid-2 { grid-template-columns: repeat(2, 1fr); }
.chats-grid.grid-3 { grid-template-columns: repeat(3, 1fr); }
.chats-grid.grid-4 { grid-template-columns: repeat(2, 1fr); }

/* Chat Cell */
.chat-cell {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  min-height: 300px;
  max-height: 400px;
  transition: all 0.2s ease;
}

.chat-cell.active {
  border-color: rgba(10, 132, 255, 0.4);
  box-shadow: 0 0 0 2px rgba(10, 132, 255, 0.15);
}

.chat-cell:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

/* Cell Header */
.cell-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.cell-icon {
  font-size: 20px;
}

.cell-title {
  flex: 1;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  outline: none;
}

.cell-title:focus {
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 6px;
}

.cell-close {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.3);
  font-size: 14px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.chat-cell:hover .cell-close {
  opacity: 1;
}

.cell-close:hover {
  background: rgba(255, 59, 48, 0.2);
  color: #ff3b30;
}

/* Messages */
.cell-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cell-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
}

.cell-msg {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.cell-msg.user {
  flex-direction: row-reverse;
}

.msg-role {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.msg-text {
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.4;
  max-width: 85%;
  word-wrap: break-word;
}

.cell-msg.user .msg-text {
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.cell-msg.assistant .msg-text {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  border-bottom-left-radius: 4px;
}

/* Thinking dots */
.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
}

.thinking-dots span {
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  animation: dot-bounce 1.4s infinite ease-in-out;
}

.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-4px); }
}

/* Input */
.cell-input {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.cell-input textarea {
  flex: 1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 10px 12px;
  color: #ffffff;
  font-size: 13px;
  resize: none;
  outline: none;
  font-family: inherit;
  min-height: 40px;
  max-height: 100px;
}

.cell-input textarea::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.cell-input textarea:focus {
  border-color: rgba(10, 132, 255, 0.5);
}

.cell-send {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #0a84ff 0%, #5ac8fa 100%);
  color: #ffffff;
  font-size: 18px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.cell-send:hover:not(:disabled) {
  transform: scale(1.05);
}

.cell-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Add Chat Cell */
.add-cell {
  background: rgba(255, 255, 255, 0.02);
  border: 2px dashed rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-height: 200px;
}

.add-cell:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(10, 132, 255, 0.4);
}

.add-icon {
  font-size: 40px;
  color: rgba(255, 255, 255, 0.3);
  margin-bottom: 8px;
}

.add-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
}

.add-cell:hover .add-icon,
.add-cell:hover .add-label {
  color: #0a84ff;
}

/* Responsive */
@media (max-width: 900px) {
  .chats-grid.grid-3,
  .chats-grid.grid-4 {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .chats-grid {
    grid-template-columns: 1fr !important;
  }

  .chat-grid-overlay {
    padding: 20px;
  }
}
</style>
