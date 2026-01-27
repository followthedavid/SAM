<template>
  <div
    class="conversation-item"
    :class="{
      active,
      roleplay: conversation.type === 'roleplay',
      pinned: conversation.pinned
    }"
    @click="$emit('select')"
  >
    <!-- Icon -->
    <div class="item-icon">
      <svg v-if="conversation.type === 'roleplay'" width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
        <path d="M9 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM4 9a5 5 0 1 1 10 0A5 5 0 0 1 4 9zm5 4c-4 0-6 2-6 3v1h12v-1c0-1-2-3-6-3z"/>
      </svg>
      <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
        <path d="M2 3.5A1.5 1.5 0 0 1 3.5 2h11A1.5 1.5 0 0 1 16 3.5v8a1.5 1.5 0 0 1-1.5 1.5h-3.293l-2.854 2.854A.5.5 0 0 1 7.5 15.5V13H3.5A1.5 1.5 0 0 1 2 11.5v-8z"/>
      </svg>
    </div>

    <!-- Content -->
    <div class="item-content">
      <div class="item-title">{{ conversation.title }}</div>
      <div class="item-preview">{{ preview }}</div>
    </div>

    <!-- Meta -->
    <div class="item-meta">
      <span class="item-time">{{ timeAgo }}</span>
      <div v-if="conversation.pinned" class="pin-indicator">
        <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor">
          <path d="M9.828.722a.5.5 0 0 1 .354.146l4.95 4.95a.5.5 0 0 1 0 .707c-.48.48-1.072.588-1.503.588-.177 0-.335-.018-.46-.039l-3.134 3.134a5.927 5.927 0 0 1 .16 1.013c.046.702-.032 1.687-.72 2.375a.5.5 0 0 1-.707 0l-2.829-2.828-3.182 3.182a.5.5 0 0 1-.707-.707l3.182-3.182-2.829-2.828a.5.5 0 0 1 0-.707c.688-.688 1.673-.766 2.375-.72a5.922 5.922 0 0 1 1.013.16l3.134-3.133a2.772 2.772 0 0 1-.04-.46c0-.432.11-1.024.59-1.504a.5.5 0 0 1 .353-.146z"/>
        </svg>
      </div>
    </div>

    <!-- Actions (on hover) -->
    <div class="item-actions" @click.stop>
      <button class="action-btn" @click="$emit('pin')" :title="conversation.pinned ? 'Unpin' : 'Pin'">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M9.828.722a.5.5 0 0 1 .354.146l4.95 4.95a.5.5 0 0 1 0 .707c-.48.48-1.072.588-1.503.588-.177 0-.335-.018-.46-.039l-3.134 3.134a5.927 5.927 0 0 1 .16 1.013c.046.702-.032 1.687-.72 2.375a.5.5 0 0 1-.707 0l-2.829-2.828-3.182 3.182a.5.5 0 0 1-.707-.707l3.182-3.182-2.829-2.828a.5.5 0 0 1 0-.707c.688-.688 1.673-.766 2.375-.72a5.922 5.922 0 0 1 1.013.16l3.134-3.133a2.772 2.772 0 0 1-.04-.46c0-.432.11-1.024.59-1.504a.5.5 0 0 1 .353-.146z"/>
        </svg>
      </button>
      <button class="action-btn" @click="$emit('rename')" title="Rename">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/>
        </svg>
      </button>
      <button class="action-btn delete" @click="$emit('delete')" title="Delete">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
          <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Conversation } from '../composables/useConversations'

const props = defineProps<{
  conversation: Conversation
  active: boolean
}>()

defineEmits<{
  (e: 'select'): void
  (e: 'delete'): void
  (e: 'pin'): void
  (e: 'rename'): void
}>()

const preview = computed(() => {
  const lastMsg = props.conversation.messages[props.conversation.messages.length - 1]
  if (!lastMsg) return 'No messages yet'
  const content = lastMsg.content.replace(/\n/g, ' ').trim()
  return content.slice(0, 40) + (content.length > 40 ? '...' : '')
})

const timeAgo = computed(() => {
  const now = new Date()
  const diff = now.getTime() - props.conversation.updatedAt.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'now'
  if (minutes < 60) return `${minutes}m`
  if (hours < 24) return `${hours}h`
  if (days < 7) return `${days}d`
  return props.conversation.updatedAt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})
</script>

<style scoped>
.conversation-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.conversation-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.conversation-item.active {
  background: rgba(255, 255, 255, 0.1);
}

.conversation-item.roleplay .item-icon {
  color: #bf5af2;
}

/* Icon */
.item-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.conversation-item.active .item-icon {
  background: rgba(10, 132, 255, 0.15);
  color: #0a84ff;
}

.conversation-item.roleplay.active .item-icon {
  background: rgba(175, 82, 222, 0.15);
  color: #bf5af2;
}

/* Content */
.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-preview {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

/* Meta */
.item-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.item-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

.pin-indicator {
  color: rgba(255, 255, 255, 0.4);
}

/* Actions */
.item-actions {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: none;
  gap: 2px;
  background: rgba(28, 28, 30, 0.95);
  padding: 4px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.conversation-item:hover .item-actions {
  display: flex;
}

.conversation-item:hover .item-meta {
  opacity: 0;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.action-btn.delete:hover {
  background: rgba(255, 69, 58, 0.15);
  color: #ff453a;
}
</style>
