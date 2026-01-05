<template>
  <div class="tab-bar" ref="tabBar">
    <!-- Left scroll indicator -->
    <button
      v-if="canScrollLeft"
      class="scroll-btn scroll-left"
      @click="scrollLeft"
      title="Scroll tabs left"
    >
      ‹
    </button>

    <div class="tabs" ref="tabsContainer" @scroll="updateScrollState">
      <div
        v-for="(tab, index) in tabs"
        :key="tab.id"
        :ref="el => { if (tab.id === activeTabId) activeTabEl = el }"
        :class="['tab', { active: tab.id === activeTabId }]"
        @click="$emit('switch-tab', tab.id)"
        data-testid="tab-item"
      >
        <span class="tab-kind">{{ kindIcon(tab.kind) }}</span>
        <span class="tab-name" @dblclick.stop="handleRename(tab.id, tab.name)">{{ tab.name }}</span>
        <button
          class="close-btn"
          @click.stop="$emit('close-tab', tab.id)"
          v-if="tabs.length > 1"
          title="Close tab"
        >
          ✕
        </button>
        <button
          v-if="index > 0"
          class="reorder-btn"
          @click.stop="$emit('reorder-tab', index, index - 1)"
          title="Move left"
        >
          ←
        </button>
        <button
          v-if="index < tabs.length - 1"
          class="reorder-btn"
          @click.stop="$emit('reorder-tab', index, index + 1)"
          title="Move right"
        >
          →
        </button>
      </div>
      <button class="new-tab-btn" @click="$emit('new-tab')" title="New Terminal">
        +
      </button>
    </div>

    <!-- Right scroll indicator -->
    <button
      v-if="canScrollRight"
      class="scroll-btn scroll-right"
      @click="scrollRight"
      title="Scroll tabs right"
    >
      ›
    </button>

    <!-- Tab count indicator when overflowing -->
    <div v-if="isOverflowing" class="tab-count">
      {{ tabs.length }} tabs
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import type { PropType } from 'vue'
import type { Tab } from '../composables/useTabs'

const props = defineProps({
  tabs: {
    type: Array as PropType<Tab[]>,
    required: true
  },
  activeTabId: {
    type: String as PropType<string | null>,
    default: null
  }
})

const emit = defineEmits(['new-tab', 'close-tab', 'switch-tab', 'rename-tab', 'reorder-tab'])

const tabsContainer = ref<HTMLElement | null>(null)
const activeTabEl = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)
const isOverflowing = ref(false)

function updateScrollState() {
  if (!tabsContainer.value) return

  const { scrollLeft, scrollWidth, clientWidth } = tabsContainer.value
  const tolerance = 5 // pixels tolerance for edge detection

  canScrollLeft.value = scrollLeft > tolerance
  canScrollRight.value = scrollLeft < scrollWidth - clientWidth - tolerance
  isOverflowing.value = scrollWidth > clientWidth + tolerance
}

function scrollLeft() {
  if (!tabsContainer.value) return
  tabsContainer.value.scrollBy({ left: -150, behavior: 'smooth' })
}

function scrollRight() {
  if (!tabsContainer.value) return
  tabsContainer.value.scrollBy({ left: 150, behavior: 'smooth' })
}

function scrollActiveTabIntoView() {
  nextTick(() => {
    if (activeTabEl.value && tabsContainer.value) {
      const container = tabsContainer.value
      const tab = activeTabEl.value
      const tabRect = tab.getBoundingClientRect()
      const containerRect = container.getBoundingClientRect()

      // Check if tab is out of view
      if (tabRect.left < containerRect.left) {
        // Tab is to the left of visible area
        container.scrollBy({
          left: tabRect.left - containerRect.left - 10,
          behavior: 'smooth'
        })
      } else if (tabRect.right > containerRect.right) {
        // Tab is to the right of visible area
        container.scrollBy({
          left: tabRect.right - containerRect.right + 10,
          behavior: 'smooth'
        })
      }
    }
  })
}

function handleRename(tabId: string, currentName: string) {
  const newName = prompt('Rename tab:', currentName)
  if (newName && newName !== currentName) {
    emit('rename-tab', tabId, newName)
  }
}

function kindIcon(kind: Tab['kind']) {
  switch (kind) {
    case 'editor':
      return '📝'
    case 'terminal':
      return '⌘'
    case 'ai':
      return '🤖'
    case 'developer':
      return '🛠'
    case 'topics':
      return '📊'
    default:
      return '•'
  }
}

// Handle window resize
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  updateScrollState()

  // Watch for container size changes
  if (tabsContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      updateScrollState()
    })
    resizeObserver.observe(tabsContainer.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

// Watch for active tab changes to scroll into view
watch(() => props.activeTabId, () => {
  scrollActiveTabIntoView()
  nextTick(updateScrollState)
})

// Watch for tab count changes
watch(() => props.tabs.length, () => {
  nextTick(updateScrollState)
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   Apple-Inspired Premium Tab Bar
   Inspired by: Safari, Finder, Apple TV
   ═══════════════════════════════════════════════════════════ */

.tab-bar {
  background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex;
  align-items: center;
  flex: 1;
  height: 44px;
  user-select: none;
  position: relative;
  padding: 0 8px;
}

.tabs {
  display: flex;
  align-items: center;
  height: 100%;
  overflow-x: auto;
  flex: 1;
  scroll-behavior: smooth;
  scrollbar-width: none;
  -ms-overflow-style: none;
  gap: 4px;
  padding: 6px 0;
}

.tabs::-webkit-scrollbar {
  display: none;
}

.tab {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  height: 32px;
  background: rgba(255,255,255,0.05);
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 100px;
  max-width: 200px;
  color: rgba(255,255,255,0.7);
  flex-shrink: 0;
  position: relative;
}

.tab:hover {
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.9);
  border-color: rgba(255,255,255,0.1);
}

.tab.active {
  background: rgba(10, 132, 255, 0.2);
  border-color: rgba(10, 132, 255, 0.4);
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(10, 132, 255, 0.2);
}

.tab.active::before {
  content: '';
  position: absolute;
  bottom: -7px;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  background: linear-gradient(90deg, #0a84ff, #5ac8fa);
  border-radius: 2px;
}

.tab-kind {
  font-size: 14px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.tab-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: -0.2px;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  padding: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: 12px;
  transition: all 0.2s;
  opacity: 0;
}

.tab:hover .close-btn {
  opacity: 1;
}

.close-btn:hover {
  background: rgba(255, 69, 58, 0.3);
  color: #ff453a;
}

.reorder-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.3);
  cursor: pointer;
  padding: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: 11px;
  transition: all 0.2s;
  opacity: 0;
}

.tab:hover .reorder-btn {
  opacity: 1;
}

.reorder-btn:hover {
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.8);
}

.new-tab-btn {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  font-size: 18px;
  font-weight: 300;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 4px;
}

.new-tab-btn:hover {
  background: rgba(10, 132, 255, 0.2);
  border-color: rgba(10, 132, 255, 0.4);
  color: #0a84ff;
  transform: scale(1.05);
}

.new-tab-btn:active {
  transform: scale(0.95);
}

/* Scroll buttons */
.scroll-btn {
  background: linear-gradient(to right, rgba(10,10,15,0.95), transparent);
  border: none;
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  padding: 0 12px;
  height: 100%;
  font-size: 18px;
  font-weight: 500;
  transition: all 0.2s;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scroll-btn.scroll-left {
  background: linear-gradient(to right, rgba(10,10,15,0.98) 40%, transparent);
}

.scroll-btn.scroll-right {
  background: linear-gradient(to left, rgba(10,10,15,0.98) 40%, transparent);
}

.scroll-btn:hover {
  color: #0a84ff;
}

/* Tab count indicator */
.tab-count {
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.4);
  background: rgba(255,255,255,0.05);
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 8px;
}
</style>
