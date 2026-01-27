<template>
  <div class="chat-container" :class="{ open: isOpen }">
    <!-- Sidebar -->
    <ChatSidebar
      v-if="isOpen"
      @new-chat="handleNewChat"
      @new-roleplay="handleNewRoleplay"
    />

    <!-- Main Chat Area -->
    <div v-if="isOpen" class="chat-main">
      <ChatPanel
        v-if="activeConversation"
        :conversation="activeConversation"
        :modelsReady="modelsReady"
        @close="isOpen = false"
        @open-characters="showCharacterPicker = true"
      />

      <!-- No conversation selected -->
      <div v-else class="no-selection">
        <div class="no-selection-content">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="currentColor" opacity="0.2">
            <path d="M32 8C18.745 8 8 18.745 8 32s10.745 24 24 24 24-10.745 24-24S45.255 8 32 8zm0 44c-11.046 0-20-8.954-20-20s8.954-20 20-20 20 8.954 20 20-8.954 20-20 20zm-6-26a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm12 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-15 10a2 2 0 0 1 2.828 0c3.515 3.515 9.485 3.515 13 0a2 2 0 0 1 2.828 2.828c-4.687 4.687-12.969 4.687-17.656 0A2 2 0 0 1 23 36z"/>
          </svg>
          <h2>Select a conversation</h2>
          <p>Or start a new chat</p>
          <div class="start-buttons">
            <button class="start-btn" @click="handleNewChat">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
              </svg>
              New Chat
            </button>
            <button class="start-btn roleplay" @click="showCharacterPicker = true">
              <span>🎭</span>
              Roleplay
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Toggle Button (when closed) -->
    <button v-if="!isOpen" class="open-btn" @click="isOpen = true">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
      </svg>
    </button>

    <!-- Character Picker Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCharacterPicker" class="character-modal-overlay" @click.self="showCharacterPicker = false">
          <div class="character-modal">
            <div class="modal-header">
              <h2>🎭 Choose Character</h2>
              <button class="close-btn" @click="showCharacterPicker = false">×</button>
            </div>
            <RoleplayCharacters
              :visible="true"
              @selectCharacter="handleCharacterSelect"
              @close="showCharacterPicker = false"
            />
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import ChatSidebar from './ChatSidebar.vue'
import ChatPanel from './ChatPanel.vue'
import RoleplayCharacters from './RoleplayCharacters.vue'
import { useConversations } from '../composables/useConversations'
import { useClaudeBridge } from '../composables/useClaudeBridge'

const {
  activeConversation,
  createConversation,
  createRoleplay,
  conversations
} = useConversations()

const { modelsReady } = useClaudeBridge()

const isOpen = ref(true)
const showCharacterPicker = ref(false)

// Auto-create first conversation if none exist
watch(conversations, (convs) => {
  if (convs.length === 0 && isOpen.value) {
    createConversation({ title: 'New Chat', type: 'chat' })
  }
}, { immediate: true })

function handleNewChat() {
  createConversation({ title: 'New Chat', type: 'chat' })
}

function handleNewRoleplay() {
  // Create roleplay without character - user picks inline in ChatPanel
  createConversation({ title: 'New Roleplay', type: 'roleplay' })
  console.log('[ChatContainer] Created new roleplay, character will be selected inline')
}

function handleCharacterSelect(character: any) {
  showCharacterPicker.value = false
  // Create roleplay with character name and store character info
  const conv = createRoleplay(character.name)
  // Store character traits in the conversation for context
  if (character.traits) {
    conv.character = `${character.name} (${character.traits.join(', ')})`
  }
}
</script>

<style scoped>
.chat-container {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 1000;
}

.chat-container.open {
  display: flex;
  width: 680px;
  max-width: calc(100vw - 32px);
  height: 560px;
  max-height: calc(100vh - 100px);
  background: rgba(28, 28, 30, 0.95);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border-radius: 16px;
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  box-shadow:
    0 0 0 0.5px rgba(0, 0, 0, 0.3),
    0 24px 48px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0; /* Critical for flex overflow scrolling */
  overflow: hidden;
}

/* No Selection State */
.no-selection {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.no-selection-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.no-selection h2 {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.no-selection p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

.start-buttons {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.start-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 10px;
  background: #0a84ff;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.start-btn:hover {
  background: #0070e0;
  transform: scale(1.02);
}

.start-btn.roleplay {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
}

.start-btn.roleplay:hover {
  background: linear-gradient(135deg, #8e44ad 0%, #7d3c98 100%);
}

/* Open Button */
.open-btn {
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 28px;
  background: rgba(28, 28, 30, 0.95);
  backdrop-filter: blur(20px);
  color: #0a84ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 0 0 0.5px rgba(255, 255, 255, 0.1),
    0 8px 24px rgba(0, 0, 0, 0.4);
  transition: all 0.2s ease;
}

.open-btn:hover {
  transform: scale(1.05);
  box-shadow:
    0 0 0 0.5px rgba(255, 255, 255, 0.15),
    0 12px 32px rgba(0, 0, 0, 0.5);
}

/* Responsive */
@media (max-width: 720px) {
  .chat-container.open {
    width: calc(100vw - 32px);
    height: calc(100vh - 100px);
    bottom: 16px;
    right: 16px;
  }
}

/* Character Modal */
.character-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.character-modal {
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  background: rgba(28, 28, 30, 0.98);
  border-radius: 16px;
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
}

.character-modal .modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 0.5px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.02);
}

.character-modal .modal-header h2 {
  font-size: 17px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.character-modal .close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.character-modal .close-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

/* Modal transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .character-modal,
.modal-leave-to .character-modal {
  transform: scale(0.95) translateY(20px);
}
</style>
