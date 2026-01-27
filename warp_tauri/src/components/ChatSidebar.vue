<template>
  <aside class="chat-sidebar" :class="{ collapsed: isCollapsed }">
    <!-- Header -->
    <header class="sidebar-header">
      <button class="toggle-btn" @click="isCollapsed = !isCollapsed">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
          <path d="M2.5 4a.5.5 0 0 1 .5-.5h12a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zm0 5a.5.5 0 0 1 .5-.5h12a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zm0 5a.5.5 0 0 1 .5-.5h12a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5z"/>
        </svg>
      </button>
      <span v-if="!isCollapsed" class="header-title">Chats</span>
      <div v-if="!isCollapsed" class="header-actions">
        <button class="new-chat-btn" @click="handleNewChat" title="New Chat">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
          </svg>
        </button>
        <button class="new-roleplay-btn" @click="handleNewRoleplay" title="New Roleplay">
          🎭
        </button>
      </div>
    </header>

    <!-- Search -->
    <div v-if="!isCollapsed" class="search-container">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="Search..."
      />
    </div>

    <!-- Conversations List -->
    <nav v-if="!isCollapsed" class="conversations-list">
      <!-- Pinned Section -->
      <section v-if="pinnedConversations.length > 0" class="section">
        <h3 class="section-title">Pinned</h3>
        <ConversationItem
          v-for="conv in pinnedConversations"
          :key="conv.id"
          :conversation="conv"
          :active="conv.id === activeConversationId"
          @select="selectConversation(conv.id)"
          @delete="handleDelete(conv.id)"
          @pin="togglePin(conv.id)"
          @rename="handleRename(conv.id)"
        />
      </section>

      <!-- Roleplay Section -->
      <section v-if="filteredRoleplay.length > 0" class="section">
        <h3 class="section-title">Characters</h3>
        <ConversationItem
          v-for="conv in filteredRoleplay"
          :key="conv.id"
          :conversation="conv"
          :active="conv.id === activeConversationId"
          @select="selectConversation(conv.id)"
          @delete="handleDelete(conv.id)"
          @pin="togglePin(conv.id)"
          @rename="handleRename(conv.id)"
        />
      </section>

      <!-- Recent Chats Section -->
      <section v-if="filteredChats.length > 0" class="section">
        <h3 class="section-title">Recent</h3>
        <ConversationItem
          v-for="conv in filteredChats"
          :key="conv.id"
          :conversation="conv"
          :active="conv.id === activeConversationId"
          @select="selectConversation(conv.id)"
          @delete="handleDelete(conv.id)"
          @pin="togglePin(conv.id)"
          @rename="handleRename(conv.id)"
        />
      </section>

      <!-- Empty State -->
      <div v-if="filteredConversations.length === 0" class="empty-state">
        <p v-if="searchQuery">No results found</p>
        <p v-else>No conversations yet</p>
        <button class="start-btn" @click="handleNewChat">Start a chat</button>
      </div>
    </nav>

    <!-- Collapsed Icons -->
    <div v-if="isCollapsed" class="collapsed-actions">
      <button class="collapsed-btn" @click="handleNewChat" title="New Chat">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 5a.5.5 0 0 1 .5.5v4h4a.5.5 0 0 1 0 1h-4v4a.5.5 0 0 1-1 0v-4h-4a.5.5 0 0 1 0-1h4v-4A.5.5 0 0 1 10 5z"/>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConversations, type Conversation } from '../composables/useConversations'
import ConversationItem from './ConversationItem.vue'

const emit = defineEmits<{
  (e: 'new-chat'): void
  (e: 'new-roleplay'): void
}>()

const {
  sortedConversations,
  activeConversationId,
  selectConversation,
  deleteConversation,
  togglePin,
  updateTitle,
  createConversation
} = useConversations()

const isCollapsed = ref(false)
const searchQuery = ref('')

// Filtered conversations
const filteredConversations = computed(() => {
  if (!searchQuery.value) return sortedConversations.value

  const query = searchQuery.value.toLowerCase()
  return sortedConversations.value.filter(c =>
    c.title.toLowerCase().includes(query) ||
    c.character?.toLowerCase().includes(query)
  )
})

const pinnedConversations = computed(() =>
  filteredConversations.value.filter(c => c.pinned)
)

const filteredRoleplay = computed(() =>
  filteredConversations.value.filter(c => c.type === 'roleplay' && !c.pinned)
)

const filteredChats = computed(() =>
  filteredConversations.value.filter(c => c.type !== 'roleplay' && !c.pinned)
)

function handleNewChat() {
  createConversation({ title: 'New Chat', type: 'chat' })
  emit('new-chat')
}

function handleNewRoleplay() {
  emit('new-roleplay')
}

function handleDelete(id: string) {
  deleteConversation(id)
}

function handleRename(id: string) {
  const conv = sortedConversations.value.find(c => c.id === id)
  if (!conv) return

  const newTitle = prompt('Rename conversation:', conv.title)
  if (newTitle && newTitle.trim()) {
    updateTitle(id, newTitle.trim())
  }
}
</script>

<style scoped>
.chat-sidebar {
  width: 260px;
  height: 100%;
  background: rgba(28, 28, 30, 0.95);
  backdrop-filter: blur(20px);
  border-right: 0.5px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
}

.chat-sidebar.collapsed {
  width: 56px;
}

/* Header */
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-bottom: 0.5px solid rgba(255, 255, 255, 0.06);
}

.toggle-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.header-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.new-chat-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: rgba(10, 132, 255, 0.15);
  color: #0a84ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.new-chat-btn:hover {
  background: rgba(10, 132, 255, 0.25);
}

.new-roleplay-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: rgba(155, 89, 182, 0.15);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.new-roleplay-btn:hover {
  background: rgba(155, 89, 182, 0.25);
}

/* Search */
.search-container {
  padding: 8px 12px;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
  font-size: 13px;
  outline: none;
  transition: all 0.15s ease;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.search-input:focus {
  background: rgba(255, 255, 255, 0.1);
}

/* Conversations List */
.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversations-list::-webkit-scrollbar {
  width: 4px;
}

.conversations-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

/* Section */
.section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 8px;
  margin: 0 0 4px;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 32px 16px;
}

.empty-state p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0 0 12px;
}

.start-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: rgba(10, 132, 255, 0.15);
  color: #0a84ff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.start-btn:hover {
  background: rgba(10, 132, 255, 0.25);
}

/* Collapsed State */
.collapsed-actions {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  gap: 8px;
}

.collapsed-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.collapsed-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
}
</style>
