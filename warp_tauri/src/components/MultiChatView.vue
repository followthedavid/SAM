<template>
  <div class="multi-chat-view">
    <!-- No separate header - uses same space as TopicGrid -->
    <div class="chat-grid">
      <div
        v-for="project in projects"
        :key="project.id"
        class="chat-panel"
        :class="{ focused: focusedProject === project.id }"
        @click="focusedProject = project.id"
      >
        <!-- Compact Header -->
        <div class="panel-header">
          <span class="panel-icon">{{ project.icon }}</span>
          <span class="panel-title">{{ project.name }}</span>
          <div class="panel-status" :class="project.status"></div>
          <button
            v-if="getMessages(project.id).length > 0"
            class="clear-btn"
            @click.stop="clearChat(project.id)"
            title="Clear"
          >×</button>
        </div>

        <!-- Messages -->
        <div class="panel-messages" :ref="el => setMessageRef(project.id, el)">
          <div v-if="getMessages(project.id).length === 0" class="empty-chat">
            <span class="empty-icon">{{ project.icon }}</span>
            <span class="empty-text">{{ project.name }}</span>
          </div>
          <div
            v-for="msg in getMessages(project.id)"
            :key="msg.id"
            class="message"
            :class="msg.role"
          >
            <div class="msg-bubble">{{ msg.content }}</div>
          </div>
          <div v-if="thinkingProjects[project.id]" class="message assistant">
            <div class="msg-bubble thinking">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="panel-input">
          <input
            v-model="inputTexts[project.id]"
            :placeholder="project.name"
            @keydown.enter="sendMessage(project.id)"
            @focus="focusedProject = project.id"
          />
          <button
            class="send-btn"
            :disabled="!inputTexts[project.id]?.trim() || thinkingProjects[project.id]"
            @click="sendMessage(project.id)"
          >→</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { useProjectStore, type ChatMessage } from '../stores/projectStore'

const emit = defineEmits<{
  (e: 'back'): void
}>()

const projectStore = useProjectStore()
const projects = computed(() => projectStore.projects.value || [])

const focusedProject = ref<string | null>(null)
const messageRefs = reactive<Record<string, HTMLElement | null>>({})
const inputTexts = reactive<Record<string, string>>({})
const thinkingProjects = reactive<Record<string, boolean>>({})

function getMessages(projectId: string): ChatMessage[] {
  return projectStore.getProjectChat(projectId)
}

function setMessageRef(projectId: string, el: any) {
  if (el) messageRefs[projectId] = el as HTMLElement
}

interface OrchestratorResponse {
  type: 'instant' | 'search' | 'generated' | 'error'
  output?: string
  content?: string
  message?: string
  chunks?: Array<{ file_path: string; content: string; line_start: number }>
  tool_calls?: Array<{ tool: string; result: string; success: boolean }>
}

async function sendMessage(projectId: string) {
  const text = inputTexts[projectId]?.trim()
  if (!text || thinkingProjects[projectId]) return

  const project = projects.value.find(p => p.id === projectId)
  if (!project) return

  projectStore.addChatMessage(projectId, { role: 'user', content: text })
  inputTexts[projectId] = ''
  thinkingProjects[projectId] = true

  await nextTick()
  scrollToBottom(projectId)

  try {
    const detectedProject = projectStore.detectProjectContext(text)
    if (detectedProject && detectedProject !== projectId) {
      projectStore.addChatMessage(detectedProject, {
        role: 'system',
        content: `[From ${project.name}]: ${text}`
      })
    }

    // Use orchestrator for intelligent routing and tool execution
    const response = await invoke<OrchestratorResponse>('orchestrate_request', {
      input: text,
      workingDir: null,
      sessionId: projectId
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

    projectStore.addChatMessage(projectId, { role: 'assistant', content: assistantContent })
  } catch (e: any) {
    projectStore.addChatMessage(projectId, { role: 'assistant', content: `Error: ${e}` })
  } finally {
    thinkingProjects[projectId] = false
    await nextTick()
    scrollToBottom(projectId)
  }
}

function clearChat(projectId: string) {
  projectStore.clearProjectChat(projectId)
}

function scrollToBottom(projectId: string) {
  const el = messageRefs[projectId]
  if (el) el.scrollTop = el.scrollHeight
}

onMounted(async () => {
  await projectStore.loadProjectChats()
  if (projects.value.length > 0) {
    focusedProject.value = projects.value[0].id
  }
})
</script>

<style scoped>
.multi-chat-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Grid - matches TopicGrid exactly */
.chat-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  padding: 24px;
  overflow-y: auto;
}

/* Panel - matches project card */
.chat-panel {
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  min-height: 200px;
  max-height: 400px;
  transition: all 0.2s ease;
}

.chat-panel.focused {
  border-color: rgba(10,132,255,0.5);
  box-shadow: 0 0 0 2px rgba(10,132,255,0.15);
}

/* Header - compact */
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.panel-icon { font-size: 18px; }

.panel-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-status {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34c759;
}
.panel-status.warning { background: #ff9500; }
.panel-status.error { background: #ff3b30; }
.panel-status.idle { background: rgba(255,255,255,0.3); }

.clear-btn {
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: rgba(255,255,255,0.3);
  font-size: 14px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s;
}
.chat-panel:hover .clear-btn { opacity: 1; }
.clear-btn:hover { background: rgba(255,59,48,0.2); color: #ff3b30; }

/* Messages */
.panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  opacity: 0.3;
}
.empty-icon { font-size: 28px; }
.empty-text { font-size: 11px; }

.message {
  display: flex;
}
.message.user { justify-content: flex-end; }
.message.system { justify-content: center; }

.msg-bubble {
  max-width: 85%;
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.4;
  word-wrap: break-word;
}

.message.user .msg-bubble {
  background: linear-gradient(135deg, #0a84ff, #5ac8fa);
  color: #fff;
  border-bottom-right-radius: 3px;
}

.message.assistant .msg-bubble {
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.9);
  border-bottom-left-radius: 3px;
}

.message.system .msg-bubble {
  background: rgba(255,149,0,0.1);
  color: rgba(255,149,0,0.7);
  font-size: 10px;
  font-style: italic;
}

/* Thinking */
.msg-bubble.thinking {
  display: flex;
  gap: 3px;
  padding: 8px 12px;
}
.msg-bubble.thinking span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255,255,255,0.4);
  animation: bounce 1.4s infinite ease-in-out;
}
.msg-bubble.thinking span:nth-child(1) { animation-delay: 0s; }
.msg-bubble.thinking span:nth-child(2) { animation-delay: 0.2s; }
.msg-bubble.thinking span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-4px); }
}

/* Input */
.panel-input {
  display: flex;
  gap: 6px;
  padding: 8px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.panel-input input {
  flex: 1;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 8px 10px;
  color: #fff;
  font-size: 12px;
  outline: none;
}
.panel-input input::placeholder { color: rgba(255,255,255,0.3); }
.panel-input input:focus { border-color: rgba(10,132,255,0.5); }

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #0a84ff, #5ac8fa);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.15s;
}
.send-btn:hover:not(:disabled) { transform: scale(1.05); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* iPhone 16 Pro Max / Wallpaper mode - single column tall panels */
@media (max-width: 430px), (max-aspect-ratio: 9/16) {
  .chat-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px;
  }

  .chat-panel {
    min-height: 150px;
    max-height: none;
  }
}
</style>
