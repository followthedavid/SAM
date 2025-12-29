<script setup lang="ts">
/**
 * CharacterCreator - Sims 4-Style Character Customization UI
 *
 * Features:
 * - Responsive: Works beautifully on desktop, tablet, and phone
 * - Touch-optimized sliders and gestures
 * - Save unlimited characters with thumbnails
 * - Natural language input ("make him taller with a beard")
 * - Presets with instant preview
 * - Undo/redo support
 * - Real-time sync to avatar
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useCharacterCustomization } from '../composables/useCharacterCustomization'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const customization = useCharacterCustomization()

// UI State
const nlInput = ref('')
const nlFeedback = ref<{ applied: string[], notUnderstood: string[] } | null>(null)
const activeView = ref<'edit' | 'presets' | 'saved'>('edit')
const saveDialogOpen = ref(false)
const saveName = ref('')
const searchQuery = ref('')
const expandedCategory = ref<string | null>(null)
const isMobile = ref(false)
const showMobileMenu = ref(false)

// Undo/Redo
const history = ref<string[]>([])
const historyIndex = ref(-1)
const maxHistory = 50

// Touch handling
const touchStartY = ref(0)
const isDragging = ref(false)

// Tab definitions with better organization
const allCategories = {
  body: {
    label: 'Body',
    icon: '🧍',
    subcategories: [
      { id: 'overall', label: 'Build', icon: '📏', description: 'Height, weight, muscularity' },
      { id: 'upperBody', label: 'Upper Body', icon: '💪', description: 'Chest, arms, shoulders' },
      { id: 'core', label: 'Torso', icon: '🎯', description: 'Abs, waist, back' },
      { id: 'lowerBody', label: 'Lower Body', icon: '🦵', description: 'Butt, thighs, calves' },
      { id: 'anatomy', label: 'Anatomy', icon: '🍆', description: 'Intimate details' },
      { id: 'skin', label: 'Skin & Hair', icon: '✨', description: 'Tone, body hair, texture' },
      { id: 'posture', label: 'Posture', icon: '🚶', description: 'Stance, confidence' }
    ]
  },
  face: {
    label: 'Face',
    icon: '😊',
    subcategories: [
      { id: 'faceShape', label: 'Face Shape', icon: '🗿', description: 'Jaw, chin, cheeks' },
      { id: 'eyes', label: 'Eyes', icon: '👁️', description: 'Size, color, brows' },
      { id: 'nose', label: 'Nose', icon: '👃', description: 'Shape, size, bridge' },
      { id: 'mouth', label: 'Mouth', icon: '👄', description: 'Lips, width' },
      { id: 'facialHair', label: 'Facial Hair', icon: '🧔', description: 'Beard, stubble' },
      { id: 'hair', label: 'Hair', icon: '💇', description: 'Style, color, length' },
      { id: 'age', label: 'Age', icon: '⏳', description: 'Wrinkles, maturity' }
    ]
  }
}

// Get current parameters for active subcategory
const currentParams = computed(() => {
  if (customization.activeCategory.value === 'body') {
    const cat = customization.activeSubCategory.value as keyof typeof customization.bodyCategories
    return customization.bodyCategories[cat] || []
  } else {
    const cat = customization.activeSubCategory.value as keyof typeof customization.faceCategories
    return customization.faceCategories[cat] || []
  }
})

// Filtered saved characters
const filteredSaved = computed(() => {
  if (!searchQuery.value) return customization.savedCharacters.value
  const q = searchQuery.value.toLowerCase()
  return customization.savedCharacters.value.filter(c =>
    c.name.toLowerCase().includes(q)
  )
})

// Check mobile on mount and resize
onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  saveToHistory()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

// History management
function saveToHistory() {
  const state = JSON.stringify(customization.config.value)

  // Remove any future states if we're not at the end
  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }

  history.value.push(state)
  if (history.value.length > maxHistory) {
    history.value.shift()
  }
  historyIndex.value = history.value.length - 1
}

function undo() {
  if (historyIndex.value > 0) {
    historyIndex.value--
    const state = JSON.parse(history.value[historyIndex.value])
    Object.assign(customization.config.value, state)
    customization.syncToAvatar()
  }
}

function redo() {
  if (historyIndex.value < history.value.length - 1) {
    historyIndex.value++
    const state = JSON.parse(history.value[historyIndex.value])
    Object.assign(customization.config.value, state)
    customization.syncToAvatar()
  }
}

// NL Input
async function handleNLSubmit() {
  if (!nlInput.value.trim()) return

  nlFeedback.value = await customization.applyDescription(nlInput.value)
  saveToHistory()
  nlInput.value = ''

  setTimeout(() => { nlFeedback.value = null }, 4000)
}

// Save character
function handleSave() {
  const name = saveName.value.trim() || `Character ${customization.savedCharacters.value.length + 1}`
  customization.saveCharacter(name)
  saveDialogOpen.value = false
  saveName.value = ''
  activeView.value = 'saved'
}

// Slider value change with history
function handleSliderChange(param: string, value: number) {
  if (customization.activeCategory.value === 'body') {
    customization.setBodyParam(param as any, value)
  } else {
    customization.setFaceParam(param as any, value)
  }
}

function handleSliderEnd() {
  saveToHistory()
}

// Get slider config
function getSliderConfig(param: string) {
  const bipolar = ['penisCurvature', 'penisCurvatureUp', 'shoulderRoll', 'hipTilt', 'headTilt', 'eyeTilt', 'mouthCorners']
  return {
    min: bipolar.includes(param) ? -1 : 0,
    max: 1,
    step: 0.01,
    isBipolar: bipolar.includes(param)
  }
}

// Format display value
function formatValue(param: string, value: number): string {
  if (param === 'height') return customization.heightDisplay.value
  if (param === 'circumcised') return value > 0.5 ? 'Cut' : 'Uncut'
  return `${Math.round(value * 100)}%`
}

// Get current value
function getValue(param: string): number {
  if (customization.activeCategory.value === 'body') {
    return customization.config.value.body[param as keyof typeof customization.config.value.body] as number
  }
  return customization.config.value.face[param as keyof typeof customization.config.value.face] as number
}

// Quick preset application
function quickPreset(id: string) {
  customization.applyPreset(id)
  saveToHistory()
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
  if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
    e.preventDefault()
    if (e.shiftKey) redo()
    else undo()
  }
}

// Touch gestures for mobile slider enhancement
function handleTouchStart(e: TouchEvent) {
  touchStartY.value = e.touches[0].clientY
  isDragging.value = true
}

function handleTouchMove(e: TouchEvent, param: string, currentVal: number) {
  if (!isDragging.value) return
  const delta = (touchStartY.value - e.touches[0].clientY) / 200
  const config = getSliderConfig(param)
  const newVal = Math.max(config.min, Math.min(config.max, currentVal + delta))
  handleSliderChange(param, newVal)
  touchStartY.value = e.touches[0].clientY
}

function handleTouchEnd() {
  isDragging.value = false
  handleSliderEnd()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="visible"
        class="cc-overlay"
        @keydown="handleKeydown"
        tabindex="0"
      >
        <div class="cc-container" :class="{ 'cc-mobile': isMobile }">

          <!-- Header -->
          <header class="cc-header">
            <div class="cc-header-left">
              <button v-if="isMobile" class="cc-icon-btn" @click="showMobileMenu = !showMobileMenu">
                ☰
              </button>
              <h1>{{ isMobile ? 'Character' : 'Character Creator' }}</h1>
            </div>

            <div class="cc-header-center" v-if="!isMobile">
              <button
                v-for="view in [
                  { id: 'edit', label: 'Edit', icon: '✏️' },
                  { id: 'presets', label: 'Presets', icon: '🎭' },
                  { id: 'saved', label: 'Saved', icon: '💾' }
                ]"
                :key="view.id"
                :class="['cc-view-tab', { active: activeView === view.id }]"
                @click="activeView = view.id as any"
              >
                <span class="icon">{{ view.icon }}</span>
                <span class="label">{{ view.label }}</span>
              </button>
            </div>

            <div class="cc-header-right">
              <button class="cc-icon-btn" @click="undo" :disabled="historyIndex <= 0" title="Undo (⌘Z)">↶</button>
              <button class="cc-icon-btn" @click="redo" :disabled="historyIndex >= history.length - 1" title="Redo (⌘⇧Z)">↷</button>
              <button class="cc-icon-btn" @click="customization.randomize()" title="Randomize">🎲</button>
              <button class="cc-icon-btn close" @click="$emit('close')">✕</button>
            </div>
          </header>

          <!-- Mobile Navigation -->
          <nav v-if="isMobile" class="cc-mobile-nav">
            <button
              v-for="view in [
                { id: 'edit', label: 'Edit', icon: '✏️' },
                { id: 'presets', label: 'Presets', icon: '🎭' },
                { id: 'saved', label: 'Saved', icon: '💾' }
              ]"
              :key="view.id"
              :class="['cc-mobile-nav-btn', { active: activeView === view.id }]"
              @click="activeView = view.id as any"
            >
              <span class="icon">{{ view.icon }}</span>
              <span class="label">{{ view.label }}</span>
            </button>
          </nav>

          <!-- NL Input (always visible) -->
          <div class="cc-nl-bar">
            <div class="cc-nl-input-wrap">
              <input
                v-model="nlInput"
                type="text"
                placeholder="Describe changes... 'taller with bigger arms'"
                @keyup.enter="handleNLSubmit"
                class="cc-nl-input"
              />
              <button class="cc-nl-submit" @click="handleNLSubmit" :disabled="!nlInput.trim()">
                Apply
              </button>
            </div>
            <Transition name="fade">
              <div v-if="nlFeedback" class="cc-nl-feedback" :class="{ error: nlFeedback.notUnderstood.length }">
                {{ nlFeedback.applied.length ? `✓ ${nlFeedback.applied.join(', ')}` : `? Couldn't understand that` }}
              </div>
            </Transition>
          </div>

          <!-- Main Content -->
          <main class="cc-main">

            <!-- EDIT VIEW -->
            <div v-if="activeView === 'edit'" class="cc-edit-view">

              <!-- Sidebar: Categories (desktop) or collapsible (mobile) -->
              <aside class="cc-sidebar" :class="{ open: showMobileMenu || !isMobile }">
                <div class="cc-category-group" v-for="(cat, catKey) in allCategories" :key="catKey">
                  <button
                    class="cc-category-header"
                    :class="{ active: customization.activeCategory.value === catKey }"
                    @click="customization.activeCategory.value = catKey; expandedCategory = expandedCategory === catKey ? null : catKey"
                  >
                    <span class="icon">{{ cat.icon }}</span>
                    <span class="label">{{ cat.label }}</span>
                    <span class="chevron">{{ expandedCategory === catKey || customization.activeCategory.value === catKey ? '▼' : '▶' }}</span>
                  </button>

                  <Transition name="expand">
                    <div
                      v-if="expandedCategory === catKey || customization.activeCategory.value === catKey"
                      class="cc-subcategory-list"
                    >
                      <button
                        v-for="sub in cat.subcategories"
                        :key="sub.id"
                        :class="['cc-subcategory-btn', {
                          active: customization.activeCategory.value === catKey && customization.activeSubCategory.value === sub.id
                        }]"
                        @click="customization.activeCategory.value = catKey; customization.activeSubCategory.value = sub.id; showMobileMenu = false"
                      >
                        <span class="icon">{{ sub.icon }}</span>
                        <div class="text">
                          <span class="label">{{ sub.label }}</span>
                          <span class="desc">{{ sub.description }}</span>
                        </div>
                      </button>
                    </div>
                  </Transition>
                </div>
              </aside>

              <!-- Sliders Panel -->
              <section class="cc-sliders-section">
                <div class="cc-section-header">
                  <h2>{{ customization.parameterLabels[customization.activeSubCategory.value] || customization.activeSubCategory.value }}</h2>
                  <button class="cc-reset-btn" @click="customization.resetToDefaults(); saveToHistory()">
                    Reset All
                  </button>
                </div>

                <div class="cc-sliders-grid">
                  <div
                    v-for="param in currentParams"
                    :key="param"
                    class="cc-slider-card"
                    @touchstart="(e) => handleTouchStart(e)"
                    @touchmove="(e) => handleTouchMove(e, param, getValue(param))"
                    @touchend="handleTouchEnd"
                  >
                    <div class="cc-slider-header">
                      <label>{{ customization.parameterLabels[param] || param }}</label>
                      <span class="cc-slider-value">{{ formatValue(param, getValue(param)) }}</span>
                    </div>

                    <div class="cc-slider-track-wrap">
                      <input
                        type="range"
                        class="cc-slider"
                        :class="{ bipolar: getSliderConfig(param).isBipolar }"
                        :min="getSliderConfig(param).min"
                        :max="getSliderConfig(param).max"
                        :step="getSliderConfig(param).step"
                        :value="getValue(param)"
                        @input="(e) => handleSliderChange(param, parseFloat((e.target as HTMLInputElement).value))"
                        @change="handleSliderEnd"
                      />
                      <div
                        class="cc-slider-fill"
                        :style="{
                          width: getSliderConfig(param).isBipolar
                            ? `${Math.abs(getValue(param)) * 50}%`
                            : `${getValue(param) * 100}%`,
                          left: getSliderConfig(param).isBipolar
                            ? (getValue(param) < 0 ? `${50 + getValue(param) * 50}%` : '50%')
                            : '0'
                        }"
                      />
                    </div>

                    <!-- Quick adjust buttons for mobile -->
                    <div class="cc-quick-adjust" v-if="isMobile">
                      <button @click="handleSliderChange(param, Math.max(getSliderConfig(param).min, getValue(param) - 0.1)); handleSliderEnd()">−</button>
                      <button @click="handleSliderChange(param, Math.min(getSliderConfig(param).max, getValue(param) + 0.1)); handleSliderEnd()">+</button>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <!-- PRESETS VIEW -->
            <div v-else-if="activeView === 'presets'" class="cc-presets-view">
              <div class="cc-presets-grid">
                <button
                  v-for="preset in customization.presets"
                  :key="preset.id"
                  :class="['cc-preset-card', { active: customization.currentPreset.value === preset.id }]"
                  @click="quickPreset(preset.id)"
                >
                  <div class="cc-preset-icon">{{ preset.name[0] }}</div>
                  <div class="cc-preset-info">
                    <h3>{{ preset.name }}</h3>
                    <p>{{ preset.description }}</p>
                  </div>
                  <div class="cc-preset-check" v-if="customization.currentPreset.value === preset.id">✓</div>
                </button>
              </div>
            </div>

            <!-- SAVED VIEW -->
            <div v-else-if="activeView === 'saved'" class="cc-saved-view">
              <div class="cc-saved-header">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Search saved characters..."
                  class="cc-search-input"
                />
                <button class="cc-btn primary" @click="saveDialogOpen = true">
                  <span class="icon">+</span> Save Current
                </button>
              </div>

              <div class="cc-saved-grid" v-if="filteredSaved.length">
                <div
                  v-for="char in filteredSaved"
                  :key="char.name"
                  class="cc-saved-card"
                >
                  <div class="cc-saved-preview">
                    <div class="cc-saved-avatar">{{ char.name[0] }}</div>
                  </div>
                  <div class="cc-saved-info">
                    <h3>{{ char.name }}</h3>
                    <p class="cc-saved-date">{{ new Date(char.updatedAt).toLocaleDateString() }}</p>
                    <p class="cc-saved-desc">{{ char.presetBase ? `Based on ${char.presetBase}` : 'Custom' }}</p>
                  </div>
                  <div class="cc-saved-actions">
                    <button class="cc-btn small" @click="customization.loadCharacter(char.name); activeView = 'edit'">
                      Load
                    </button>
                    <button class="cc-btn small danger" @click="customization.deleteCharacter(char.name)">
                      🗑
                    </button>
                  </div>
                </div>
              </div>

              <div v-else class="cc-empty-state">
                <div class="cc-empty-icon">💾</div>
                <h3>No saved characters{{ searchQuery ? ' found' : ' yet' }}</h3>
                <p>{{ searchQuery ? 'Try a different search' : 'Create your perfect character and save it here' }}</p>
                <button v-if="!searchQuery" class="cc-btn primary" @click="saveDialogOpen = true">
                  Save Current Character
                </button>
              </div>
            </div>
          </main>

          <!-- Footer -->
          <footer class="cc-footer">
            <div class="cc-footer-info">
              <span class="cc-height">{{ customization.heightDisplay.value }}</span>
              <span class="cc-divider">•</span>
              <span class="cc-name">{{ customization.config.value.name }}</span>
            </div>
            <button class="cc-btn primary large" @click="customization.syncToAvatar()">
              Apply to Avatar
            </button>
          </footer>

          <!-- Save Dialog -->
          <Transition name="modal">
            <div v-if="saveDialogOpen" class="cc-modal-overlay" @click.self="saveDialogOpen = false">
              <div class="cc-modal">
                <h2>Save Character</h2>
                <p>Give your character a name to save it for later.</p>
                <input
                  v-model="saveName"
                  type="text"
                  placeholder="Character name..."
                  class="cc-modal-input"
                  @keyup.enter="handleSave"
                  autofocus
                />
                <div class="cc-modal-preview">
                  <div class="cc-preview-stat">Height: {{ customization.heightDisplay.value }}</div>
                  <div class="cc-preview-stat">Build: {{ customization.generateDescription().split(',').slice(0, 3).join(', ') }}</div>
                </div>
                <div class="cc-modal-actions">
                  <button class="cc-btn" @click="saveDialogOpen = false">Cancel</button>
                  <button class="cc-btn primary" @click="handleSave">Save Character</button>
                </div>
              </div>
            </div>
          </Transition>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* CSS Variables */
:root {
  --cc-bg: #0f0f1a;
  --cc-bg-secondary: #1a1a2e;
  --cc-bg-tertiary: #252542;
  --cc-border: #2d2d4a;
  --cc-primary: #6366f1;
  --cc-primary-hover: #7c7ff1;
  --cc-text: #ffffff;
  --cc-text-secondary: #9ca3af;
  --cc-text-muted: #6b7280;
  --cc-success: #10b981;
  --cc-danger: #ef4444;
  --cc-radius: 12px;
  --cc-radius-sm: 8px;
}

/* Base */
.cc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.cc-container {
  width: 100%;
  height: 100%;
  max-width: 1600px;
  max-height: 1000px;
  margin: 0 auto;
  background: var(--cc-bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@media (min-width: 768px) {
  .cc-container {
    width: 95vw;
    height: 90vh;
    border-radius: var(--cc-radius);
    box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
  }
}

/* Header */
.cc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--cc-bg-secondary);
  border-bottom: 1px solid var(--cc-border);
  gap: 16px;
}

.cc-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cc-header h1 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--cc-text);
}

.cc-header-center {
  display: flex;
  gap: 4px;
  background: var(--cc-bg-tertiary);
  padding: 4px;
  border-radius: var(--cc-radius);
}

.cc-view-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: none;
  border-radius: var(--cc-radius-sm);
  background: transparent;
  color: var(--cc-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.cc-view-tab:hover {
  color: var(--cc-text);
}

.cc-view-tab.active {
  background: var(--cc-primary);
  color: white;
}

.cc-header-right {
  display: flex;
  gap: 8px;
}

/* Icon Button */
.cc-icon-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--cc-radius-sm);
  background: var(--cc-bg-tertiary);
  color: var(--cc-text-secondary);
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.2s;
}

.cc-icon-btn:hover:not(:disabled) {
  background: var(--cc-border);
  color: var(--cc-text);
}

.cc-icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cc-icon-btn.close {
  background: var(--cc-danger);
  color: white;
}

/* Mobile Nav */
.cc-mobile-nav {
  display: flex;
  background: var(--cc-bg-secondary);
  border-bottom: 1px solid var(--cc-border);
}

.cc-mobile-nav-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  border: none;
  background: transparent;
  color: var(--cc-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.cc-mobile-nav-btn.active {
  color: var(--cc-primary);
  border-bottom: 2px solid var(--cc-primary);
}

.cc-mobile-nav-btn .icon {
  font-size: 1.25rem;
}

.cc-mobile-nav-btn .label {
  font-size: 0.75rem;
}

/* NL Bar */
.cc-nl-bar {
  padding: 12px 16px;
  background: var(--cc-bg-tertiary);
}

.cc-nl-input-wrap {
  display: flex;
  gap: 8px;
}

.cc-nl-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--cc-border);
  border-radius: var(--cc-radius);
  background: var(--cc-bg);
  color: var(--cc-text);
  font-size: 0.95rem;
}

.cc-nl-input::placeholder {
  color: var(--cc-text-muted);
}

.cc-nl-submit {
  padding: 12px 20px;
  border: none;
  border-radius: var(--cc-radius);
  background: var(--cc-primary);
  color: white;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.cc-nl-submit:hover:not(:disabled) {
  background: var(--cc-primary-hover);
}

.cc-nl-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cc-nl-feedback {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: var(--cc-radius-sm);
  background: rgba(16, 185, 129, 0.2);
  color: var(--cc-success);
  font-size: 0.85rem;
}

.cc-nl-feedback.error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--cc-danger);
}

/* Main */
.cc-main {
  flex: 1;
  overflow: hidden;
  display: flex;
}

/* Edit View */
.cc-edit-view {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.cc-sidebar {
  width: 280px;
  background: var(--cc-bg-secondary);
  border-right: 1px solid var(--cc-border);
  overflow-y: auto;
  flex-shrink: 0;
}

.cc-mobile .cc-sidebar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
  transform: translateX(-100%);
  transition: transform 0.3s ease;
}

.cc-mobile .cc-sidebar.open {
  transform: translateX(0);
}

.cc-category-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 16px;
  border: none;
  background: transparent;
  color: var(--cc-text);
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  text-align: left;
  transition: all 0.2s;
}

.cc-category-header:hover {
  background: var(--cc-bg-tertiary);
}

.cc-category-header.active {
  background: var(--cc-bg-tertiary);
  color: var(--cc-primary);
}

.cc-category-header .chevron {
  margin-left: auto;
  font-size: 0.7rem;
  color: var(--cc-text-muted);
}

.cc-subcategory-list {
  padding: 0 8px 8px;
}

.cc-subcategory-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: var(--cc-radius-sm);
  background: transparent;
  color: var(--cc-text-secondary);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.cc-subcategory-btn:hover {
  background: var(--cc-bg);
  color: var(--cc-text);
}

.cc-subcategory-btn.active {
  background: var(--cc-primary);
  color: white;
}

.cc-subcategory-btn .icon {
  font-size: 1.25rem;
}

.cc-subcategory-btn .text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cc-subcategory-btn .label {
  font-weight: 500;
}

.cc-subcategory-btn .desc {
  font-size: 0.75rem;
  opacity: 0.7;
}

/* Sliders Section */
.cc-sliders-section {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.cc-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.cc-section-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--cc-text);
  text-transform: capitalize;
}

.cc-reset-btn {
  padding: 8px 16px;
  border: 1px solid var(--cc-border);
  border-radius: var(--cc-radius-sm);
  background: transparent;
  color: var(--cc-text-secondary);
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.cc-reset-btn:hover {
  border-color: var(--cc-danger);
  color: var(--cc-danger);
}

/* Sliders Grid */
.cc-sliders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.cc-slider-card {
  background: var(--cc-bg-secondary);
  border-radius: var(--cc-radius);
  padding: 16px;
  transition: all 0.2s;
}

.cc-slider-card:hover {
  background: var(--cc-bg-tertiary);
}

.cc-slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.cc-slider-header label {
  font-size: 0.9rem;
  color: var(--cc-text);
  font-weight: 500;
}

.cc-slider-value {
  font-size: 0.85rem;
  color: var(--cc-primary);
  font-family: monospace;
  font-weight: 600;
}

.cc-slider-track-wrap {
  position: relative;
  height: 8px;
  background: var(--cc-bg);
  border-radius: 4px;
  overflow: hidden;
}

.cc-slider {
  position: absolute;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
  z-index: 2;
}

.cc-slider-fill {
  position: absolute;
  height: 100%;
  background: var(--cc-primary);
  border-radius: 4px;
  transition: width 0.1s ease;
  pointer-events: none;
}

/* Quick adjust for mobile */
.cc-quick-adjust {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.cc-quick-adjust button {
  flex: 1;
  padding: 12px;
  border: 1px solid var(--cc-border);
  border-radius: var(--cc-radius-sm);
  background: transparent;
  color: var(--cc-text);
  font-size: 1.25rem;
  cursor: pointer;
  transition: all 0.2s;
}

.cc-quick-adjust button:active {
  background: var(--cc-primary);
  border-color: var(--cc-primary);
}

/* Presets View */
.cc-presets-view {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.cc-presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.cc-preset-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 2px solid var(--cc-border);
  border-radius: var(--cc-radius);
  background: var(--cc-bg-secondary);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.cc-preset-card:hover {
  border-color: var(--cc-primary);
  background: var(--cc-bg-tertiary);
}

.cc-preset-card.active {
  border-color: var(--cc-primary);
  background: rgba(99, 102, 241, 0.1);
}

.cc-preset-icon {
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--cc-bg-tertiary);
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--cc-primary);
}

.cc-preset-info {
  flex: 1;
}

.cc-preset-info h3 {
  margin: 0 0 4px;
  font-size: 1rem;
  color: var(--cc-text);
}

.cc-preset-info p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--cc-text-secondary);
}

.cc-preset-check {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--cc-primary);
  color: white;
  font-weight: bold;
}

/* Saved View */
.cc-saved-view {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.cc-saved-header {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.cc-search-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--cc-border);
  border-radius: var(--cc-radius);
  background: var(--cc-bg-secondary);
  color: var(--cc-text);
  font-size: 0.95rem;
}

.cc-saved-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.cc-saved-card {
  display: flex;
  gap: 16px;
  padding: 16px;
  border-radius: var(--cc-radius);
  background: var(--cc-bg-secondary);
  transition: all 0.2s;
}

.cc-saved-card:hover {
  background: var(--cc-bg-tertiary);
}

.cc-saved-preview {
  flex-shrink: 0;
}

.cc-saved-avatar {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--cc-radius);
  background: var(--cc-bg-tertiary);
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--cc-primary);
}

.cc-saved-info {
  flex: 1;
  min-width: 0;
}

.cc-saved-info h3 {
  margin: 0 0 4px;
  font-size: 1rem;
  color: var(--cc-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cc-saved-date {
  margin: 0;
  font-size: 0.8rem;
  color: var(--cc-text-muted);
}

.cc-saved-desc {
  margin: 4px 0 0;
  font-size: 0.85rem;
  color: var(--cc-text-secondary);
}

.cc-saved-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Empty State */
.cc-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.cc-empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.cc-empty-state h3 {
  margin: 0 0 8px;
  font-size: 1.25rem;
  color: var(--cc-text);
}

.cc-empty-state p {
  margin: 0 0 24px;
  color: var(--cc-text-secondary);
}

/* Buttons */
.cc-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border: 1px solid var(--cc-border);
  border-radius: var(--cc-radius-sm);
  background: transparent;
  color: var(--cc-text);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.cc-btn:hover {
  background: var(--cc-bg-tertiary);
}

.cc-btn.primary {
  background: var(--cc-primary);
  border-color: var(--cc-primary);
  color: white;
}

.cc-btn.primary:hover {
  background: var(--cc-primary-hover);
}

.cc-btn.danger {
  border-color: var(--cc-danger);
  color: var(--cc-danger);
}

.cc-btn.danger:hover {
  background: var(--cc-danger);
  color: white;
}

.cc-btn.small {
  padding: 6px 12px;
  font-size: 0.8rem;
}

.cc-btn.large {
  padding: 14px 28px;
  font-size: 1rem;
}

/* Footer */
.cc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--cc-bg-secondary);
  border-top: 1px solid var(--cc-border);
}

.cc-footer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--cc-text-secondary);
}

.cc-height {
  font-weight: 600;
  color: var(--cc-text);
}

.cc-divider {
  color: var(--cc-text-muted);
}

/* Modal */
.cc-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  padding: 20px;
}

.cc-modal {
  width: 100%;
  max-width: 420px;
  padding: 28px;
  background: var(--cc-bg-secondary);
  border-radius: var(--cc-radius);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.cc-modal h2 {
  margin: 0 0 8px;
  font-size: 1.5rem;
  color: var(--cc-text);
}

.cc-modal > p {
  margin: 0 0 20px;
  color: var(--cc-text-secondary);
}

.cc-modal-input {
  width: 100%;
  padding: 14px 18px;
  margin-bottom: 16px;
  border: 1px solid var(--cc-border);
  border-radius: var(--cc-radius);
  background: var(--cc-bg);
  color: var(--cc-text);
  font-size: 1rem;
}

.cc-modal-input:focus {
  outline: none;
  border-color: var(--cc-primary);
}

.cc-modal-preview {
  padding: 16px;
  margin-bottom: 20px;
  border-radius: var(--cc-radius-sm);
  background: var(--cc-bg);
}

.cc-preview-stat {
  font-size: 0.9rem;
  color: var(--cc-text-secondary);
  margin-bottom: 4px;
}

.cc-preview-stat:last-child {
  margin-bottom: 0;
}

.cc-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Transitions */
.modal-enter-active, .modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

.modal-enter-from .cc-container,
.modal-leave-to .cc-container,
.modal-enter-from .cc-modal,
.modal-leave-to .cc-modal {
  transform: scale(0.95);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.expand-enter-active, .expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from, .expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to, .expand-leave-from {
  max-height: 500px;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--cc-border);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--cc-text-muted);
}

/* Mobile adjustments */
.cc-mobile .cc-sliders-grid {
  grid-template-columns: 1fr;
}

.cc-mobile .cc-presets-grid {
  grid-template-columns: 1fr;
}

.cc-mobile .cc-saved-grid {
  grid-template-columns: 1fr;
}

.cc-mobile .cc-saved-header {
  flex-direction: column;
}

.cc-mobile .cc-footer {
  flex-direction: column;
  gap: 12px;
}

.cc-mobile .cc-footer-info {
  width: 100%;
  justify-content: center;
}

.cc-mobile .cc-btn.large {
  width: 100%;
}
</style>
