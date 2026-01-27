<script setup lang="ts">
/**
 * RoleplayCharacters - Character Archetype Library for Roleplay Mode
 *
 * Features:
 * - Browse 60+ character archetypes (villains, fantasy, comedy, etc.)
 * - Category tabs with icons
 * - Search and filter
 * - Quick preview of character traits
 * - Create character from archetype with custom name
 * - Manage saved characters (favorites, delete, edit)
 */

import { ref, computed, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

interface Archetype {
  id: string
  name: string
  icon: string
  description: string
  gender: string
  traits?: string[]
  category?: string
}

interface SavedCharacter {
  id: string
  name: string
  archetype?: string
  gender: string
  traits: string[]
  speech_style: string
  catchphrases: string[]
  favorite: boolean
  times_used: number
}

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
  selectCharacter: [character: SavedCharacter]
}>()

// State
const archetypes = ref<Archetype[]>([])
const savedCharacters = ref<SavedCharacter[]>([])
const selectedArchetype = ref<Archetype | null>(null)
const selectedCharacter = ref<SavedCharacter | null>(null)
const customName = ref('')
const searchQuery = ref('')
const activeCategory = ref('all')
const activeTab = ref<'browse' | 'saved'>('browse')
const isLoading = ref(false)
const error = ref('')

// Categories with icons
const categories = [
  { id: 'all', label: 'All', icon: '📚' },
  { id: 'villains', label: 'Villains', icon: '😈' },
  { id: 'fantasy', label: 'Fantasy', icon: '🧙' },
  { id: 'scifi', label: 'Sci-Fi', icon: '🚀' },
  { id: 'comedy', label: 'Comedy', icon: '😂' },
  { id: 'modern', label: 'Modern', icon: '🏙️' },
]

// Filtered archetypes based on search and category
const filteredArchetypes = computed(() => {
  let result = archetypes.value

  // Filter by search
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(a =>
      a.name.toLowerCase().includes(q) ||
      a.description.toLowerCase().includes(q) ||
      (a.traits && a.traits.some(t => t.toLowerCase().includes(q)))
    )
  }

  return result
})

// Filtered saved characters
const filteredSaved = computed(() => {
  if (!searchQuery.value) return savedCharacters.value
  const q = searchQuery.value.toLowerCase()
  return savedCharacters.value.filter(c =>
    c.name.toLowerCase().includes(q) ||
    (c.archetype && c.archetype.toLowerCase().includes(q))
  )
})

// Fallback archetypes if backend unavailable
const defaultArchetypes: Archetype[] = [
  { id: 'villain_mastermind', name: 'Mastermind Villain', icon: '🦹', description: 'Calculating genius with world domination plans', gender: 'any', traits: ['intelligent', 'ruthless', 'charismatic'], category: 'villains' },
  { id: 'villain_bully', name: 'Intimidating Bully', icon: '👊', description: 'Aggressive antagonist who uses fear and force', gender: 'any', traits: ['aggressive', 'intimidating', 'cruel'], category: 'villains' },
  { id: 'villain_trickster', name: 'Chaotic Trickster', icon: '🃏', description: 'Unpredictable agent of chaos', gender: 'any', traits: ['unpredictable', 'mischievous', 'clever'], category: 'villains' },
  { id: 'fantasy_wizard', name: 'Wise Wizard', icon: '🧙', description: 'Ancient spellcaster with mysterious knowledge', gender: 'any', traits: ['wise', 'mysterious', 'powerful'], category: 'fantasy' },
  { id: 'fantasy_warrior', name: 'Battle-Hardened Warrior', icon: '⚔️', description: 'Veteran fighter with countless battles', gender: 'any', traits: ['brave', 'skilled', 'honorable'], category: 'fantasy' },
  { id: 'fantasy_elf', name: 'Ethereal Elf', icon: '🧝', description: 'Ageless being with deep connection to nature', gender: 'any', traits: ['graceful', 'ancient', 'mystical'], category: 'fantasy' },
  { id: 'scifi_android', name: 'Sentient Android', icon: '🤖', description: 'AI questioning its own existence', gender: 'any', traits: ['logical', 'curious', 'evolving'], category: 'scifi' },
  { id: 'scifi_captain', name: 'Starship Captain', icon: '👨‍🚀', description: 'Bold leader of a space crew', gender: 'any', traits: ['decisive', 'charismatic', 'adventurous'], category: 'scifi' },
  { id: 'scifi_alien', name: 'Mysterious Alien', icon: '👽', description: 'Extraterrestrial with unknown motives', gender: 'any', traits: ['enigmatic', 'powerful', 'ancient'], category: 'scifi' },
  { id: 'comedy_sarcastic', name: 'Sarcastic Sidekick', icon: '😏', description: 'Witty companion with sharp tongue', gender: 'any', traits: ['sarcastic', 'loyal', 'funny'], category: 'comedy' },
  { id: 'comedy_eccentric', name: 'Eccentric Professor', icon: '🤪', description: 'Brilliant but bizarre academic', gender: 'any', traits: ['brilliant', 'chaotic', 'forgetful'], category: 'comedy' },
  { id: 'modern_detective', name: 'Noir Detective', icon: '🕵️', description: 'Cynical investigator in a corrupt world', gender: 'any', traits: ['observant', 'cynical', 'persistent'], category: 'modern' },
  { id: 'modern_hacker', name: 'Elite Hacker', icon: '💻', description: 'Digital shadow who can breach any system', gender: 'any', traits: ['brilliant', 'rebellious', 'paranoid'], category: 'modern' },
  { id: 'modern_ceo', name: 'Ruthless CEO', icon: '🏢', description: 'Corporate power player who always wins', gender: 'any', traits: ['ambitious', 'calculating', 'charming'], category: 'modern' },
]

async function loadArchetypes() {
  isLoading.value = true
  error.value = ''

  // Helper to filter defaults by category
  const getFilteredDefaults = () => {
    if (activeCategory.value === 'all') {
      return defaultArchetypes
    }
    return defaultArchetypes.filter(a => a.category === activeCategory.value)
  }

  try {
    let result: Archetype[] = []
    if (activeCategory.value === 'all') {
      result = await invoke('cmd_list_archetypes')
    } else {
      result = await invoke('cmd_get_archetypes_by_category', {
        category: activeCategory.value
      })
    }

    // If backend returns empty, use filtered defaults
    if (!result || result.length === 0) {
      archetypes.value = getFilteredDefaults()
    } else {
      archetypes.value = result
    }
  } catch (e) {
    console.warn('Backend archetypes unavailable, using defaults:', e)
    // Use filtered fallback archetypes
    archetypes.value = getFilteredDefaults()
  }
  isLoading.value = false
}

async function loadSavedCharacters() {
  try {
    savedCharacters.value = await invoke('cmd_list_saved_characters')
  } catch (e) {
    console.error('Failed to load saved characters:', e)
  }
}

// Initialize on mount - load fallbacks immediately, then try backend
onMounted(async () => {
  // Set fallbacks immediately so user sees something
  archetypes.value = defaultArchetypes
  isLoading.value = false

  // Then try to load from backend (will replace if successful)
  await loadArchetypes()
  await loadSavedCharacters()
})

async function selectCategory(categoryId: string) {
  activeCategory.value = categoryId
  selectedArchetype.value = null
  await loadArchetypes()
}

async function searchArchetypes() {
  if (!searchQuery.value) {
    await loadArchetypes()
    return
  }
  try {
    archetypes.value = await invoke('cmd_search_archetypes', {
      query: searchQuery.value
    })
  } catch (e) {
    console.error('Search failed:', e)
  }
}

function selectArchetypeCard(archetype: Archetype) {
  selectedArchetype.value = archetype
  customName.value = ''
}

// Quick start roleplay without saving to backend
function quickStartRoleplay(archetype: Archetype) {
  const quickCharacter = {
    id: `quick_${Date.now()}`,
    name: archetype.name,
    archetype: archetype.name,
    gender: archetype.gender || 'any',
    traits: archetype.traits || [],
    speech_style: '',
    catchphrases: [],
    favorite: false,
    times_used: 1
  }
  emit('selectCharacter', quickCharacter)
  emit('close')
}

async function createFromArchetype() {
  if (!selectedArchetype.value) return

  try {
    const character: SavedCharacter = await invoke('cmd_create_from_archetype', {
      archetypeId: selectedArchetype.value.id,
      customName: customName.value || null
    })

    // Save to library
    await invoke('cmd_save_character', { character })

    // Reload saved characters
    await loadSavedCharacters()

    // Switch to saved tab and select the new character
    activeTab.value = 'saved'
    selectedCharacter.value = character
    selectedArchetype.value = null
  } catch (e) {
    error.value = `Failed to create character: ${e}`
    console.error(e)
  }
}

async function useCharacter(character: SavedCharacter) {
  try {
    await invoke('cmd_record_character_usage', { id: character.id })
    emit('selectCharacter', character)
    emit('close')
  } catch (e) {
    console.error('Failed to record usage:', e)
  }
}

async function toggleFavorite(character: SavedCharacter) {
  try {
    const newStatus = await invoke('cmd_toggle_favorite', { id: character.id })
    character.favorite = newStatus as boolean
    await loadSavedCharacters()
  } catch (e) {
    console.error('Failed to toggle favorite:', e)
  }
}

async function deleteCharacter(character: SavedCharacter) {
  if (!confirm(`Delete "${character.name}"?`)) return
  try {
    await invoke('cmd_delete_character', { id: character.id })
    if (selectedCharacter.value?.id === character.id) {
      selectedCharacter.value = null
    }
    await loadSavedCharacters()
  } catch (e) {
    console.error('Failed to delete character:', e)
  }
}

// Edit functionality
const editingCharacter = ref<SavedCharacter | null>(null)
const editForm = ref({
  name: '',
  traits: [] as string[],
  speech_style: '',
  catchphrases: [] as string[],
  newTrait: '',
  newCatchphrase: ''
})

function startEditing(character: SavedCharacter) {
  editingCharacter.value = { ...character }
  editForm.value = {
    name: character.name,
    traits: [...character.traits],
    speech_style: character.speech_style,
    catchphrases: [...character.catchphrases],
    newTrait: '',
    newCatchphrase: ''
  }
}

function cancelEditing() {
  editingCharacter.value = null
  editForm.value = {
    name: '',
    traits: [],
    speech_style: '',
    catchphrases: [],
    newTrait: '',
    newCatchphrase: ''
  }
}

function addTrait() {
  if (editForm.value.newTrait.trim()) {
    editForm.value.traits.push(editForm.value.newTrait.trim())
    editForm.value.newTrait = ''
  }
}

function removeTrait(index: number) {
  editForm.value.traits.splice(index, 1)
}

function addCatchphrase() {
  if (editForm.value.newCatchphrase.trim()) {
    editForm.value.catchphrases.push(editForm.value.newCatchphrase.trim())
    editForm.value.newCatchphrase = ''
  }
}

function removeCatchphrase(index: number) {
  editForm.value.catchphrases.splice(index, 1)
}

async function saveEditedCharacter() {
  if (!editingCharacter.value) return

  try {
    const updatedCharacter: SavedCharacter = {
      ...editingCharacter.value,
      name: editForm.value.name,
      traits: editForm.value.traits,
      speech_style: editForm.value.speech_style,
      catchphrases: editForm.value.catchphrases
    }

    await invoke('cmd_update_character', { character: updatedCharacter })
    await loadSavedCharacters()
    cancelEditing()
    error.value = ''
  } catch (e) {
    error.value = `Failed to save character: ${e}`
    console.error(e)
  }
}
</script>

<template>
  <div v-if="visible" class="roleplay-overlay" @click.self="emit('close')">
    <div class="roleplay-panel">
      <!-- Header -->
      <div class="panel-header">
        <h2>Character Library</h2>
        <button class="close-btn" @click="emit('close')">×</button>
      </div>

      <!-- Tabs -->
      <div class="tab-bar">
        <button
          :class="['tab', { active: activeTab === 'browse' }]"
          @click="activeTab = 'browse'"
        >
          📚 Browse Archetypes
        </button>
        <button
          :class="['tab', { active: activeTab === 'saved' }]"
          @click="activeTab = 'saved'"
        >
          💾 My Characters ({{ savedCharacters.length }})
        </button>
      </div>

      <!-- Search -->
      <div class="search-bar">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search characters..."
          @input="searchArchetypes"
        />
      </div>

      <!-- Browse Tab -->
      <template v-if="activeTab === 'browse'">
        <!-- Category tabs -->
        <div class="category-bar">
          <button
            v-for="cat in categories"
            :key="cat.id"
            :class="['category-btn', { active: activeCategory === cat.id }]"
            @click="selectCategory(cat.id)"
          >
            {{ cat.icon }} {{ cat.label }}
          </button>
        </div>

        <!-- Content area -->
        <div class="content-area">
          <!-- Loading state -->
          <div v-if="isLoading" class="loading">Loading...</div>

          <!-- Error state -->
          <div v-else-if="error" class="error">{{ error }}</div>

          <!-- Archetype grid -->
          <div v-else class="archetype-grid">
            <div
              v-for="arch in filteredArchetypes"
              :key="arch.id"
              :class="['archetype-card', { selected: selectedArchetype?.id === arch.id }]"
              @click="selectArchetypeCard(arch)"
            >
              <div class="card-icon">{{ arch.icon }}</div>
              <div class="card-content">
                <div class="card-name">{{ arch.name }}</div>
                <div class="card-desc">{{ arch.description }}</div>
                <div class="card-traits" v-if="arch.traits">
                  <span v-for="trait in arch.traits.slice(0, 3)" :key="trait" class="trait-tag">
                    {{ trait }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Selected archetype detail -->
        <div v-if="selectedArchetype" class="detail-panel">
          <div class="detail-header">
            <span class="detail-icon">{{ selectedArchetype.icon }}</span>
            <div>
              <h3>{{ selectedArchetype.name }}</h3>
              <p>{{ selectedArchetype.description }}</p>
            </div>
          </div>

          <div class="detail-traits" v-if="selectedArchetype.traits">
            <strong>Traits:</strong>
            <div class="traits-list">
              <span v-for="trait in selectedArchetype.traits" :key="trait" class="trait-tag">
                {{ trait }}
              </span>
            </div>
          </div>

          <div class="create-form">
            <div class="quick-actions">
              <button class="quick-start-btn" @click="quickStartRoleplay(selectedArchetype!)">
                ▶ Start Now
              </button>
            </div>
            <div class="save-section">
              <label>
                Custom Name (optional):
                <input v-model="customName" type="text" placeholder="Leave blank for default" />
              </label>
              <button class="create-btn" @click="createFromArchetype">
                💾 Save to Library
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- Saved Characters Tab -->
      <template v-else>
        <div class="content-area">
          <div v-if="savedCharacters.length === 0" class="empty-state">
            <p>No saved characters yet.</p>
            <p>Browse archetypes and create your first character!</p>
          </div>

          <div v-else class="saved-grid">
            <div
              v-for="char in filteredSaved"
              :key="char.id"
              :class="['saved-card', { selected: selectedCharacter?.id === char.id }]"
              @click="selectedCharacter = char"
            >
              <div class="saved-header">
                <span class="saved-name">{{ char.name }}</span>
                <button
                  :class="['fav-btn', { favorited: char.favorite }]"
                  @click.stop="toggleFavorite(char)"
                >
                  {{ char.favorite ? '★' : '☆' }}
                </button>
              </div>
              <div class="saved-archetype" v-if="char.archetype">
                Based on: {{ char.archetype }}
              </div>
              <div class="saved-traits">
                <span v-for="trait in char.traits.slice(0, 2)" :key="trait" class="trait-tag">
                  {{ trait }}
                </span>
              </div>
              <div class="saved-stats">
                Used {{ char.times_used }} times
              </div>
            </div>
          </div>
        </div>

        <!-- Selected character actions -->
        <div v-if="selectedCharacter && !editingCharacter" class="detail-panel">
          <div class="detail-header">
            <h3>{{ selectedCharacter.name }}</h3>
            <span v-if="selectedCharacter.favorite" class="fav-badge">★ Favorite</span>
          </div>

          <div class="detail-traits" v-if="selectedCharacter.traits.length">
            <strong>Traits:</strong>
            <div class="traits-list">
              <span v-for="trait in selectedCharacter.traits" :key="trait" class="trait-tag">
                {{ trait }}
              </span>
            </div>
          </div>

          <div class="detail-catchphrases" v-if="selectedCharacter.catchphrases?.length">
            <strong>Catchphrases:</strong>
            <ul>
              <li v-for="phrase in selectedCharacter.catchphrases" :key="phrase">
                "{{ phrase }}"
              </li>
            </ul>
          </div>

          <div class="action-buttons">
            <button class="use-btn" @click="useCharacter(selectedCharacter)">
              🎭 Use This Character
            </button>
            <button class="edit-btn" @click="startEditing(selectedCharacter)">
              ✏️ Edit
            </button>
            <button class="delete-btn" @click="deleteCharacter(selectedCharacter)">
              🗑️ Delete
            </button>
          </div>
        </div>

        <!-- Edit Character Form -->
        <div v-if="editingCharacter" class="detail-panel edit-panel">
          <div class="edit-header">
            <h3>Edit Character</h3>
            <button class="cancel-btn" @click="cancelEditing">×</button>
          </div>

          <div class="edit-form">
            <div class="form-group">
              <label>Name</label>
              <input v-model="editForm.name" type="text" class="form-input" />
            </div>

            <div class="form-group">
              <label>Speech Style</label>
              <input v-model="editForm.speech_style" type="text" class="form-input" placeholder="e.g., gruff, condescending, seductive" />
            </div>

            <div class="form-group">
              <label>Traits</label>
              <div class="editable-tags">
                <span v-for="(trait, idx) in editForm.traits" :key="idx" class="trait-tag editable">
                  {{ trait }}
                  <button class="remove-tag" @click="removeTrait(idx)">×</button>
                </span>
              </div>
              <div class="add-tag-row">
                <input
                  v-model="editForm.newTrait"
                  type="text"
                  placeholder="Add trait..."
                  @keydown.enter="addTrait"
                />
                <button class="add-tag-btn" @click="addTrait">+</button>
              </div>
            </div>

            <div class="form-group">
              <label>Catchphrases</label>
              <div class="catchphrase-list">
                <div v-for="(phrase, idx) in editForm.catchphrases" :key="idx" class="catchphrase-item">
                  "{{ phrase }}"
                  <button class="remove-tag" @click="removeCatchphrase(idx)">×</button>
                </div>
              </div>
              <div class="add-tag-row">
                <input
                  v-model="editForm.newCatchphrase"
                  type="text"
                  placeholder="Add catchphrase..."
                  @keydown.enter="addCatchphrase"
                />
                <button class="add-tag-btn" @click="addCatchphrase">+</button>
              </div>
            </div>

            <div class="edit-actions">
              <button class="save-btn" @click="saveEditedCharacter">
                💾 Save Changes
              </button>
              <button class="cancel-edit-btn" @click="cancelEditing">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.roleplay-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.roleplay-panel {
  background: var(--bg-primary, #1a1a2e);
  border-radius: 16px;
  width: 90%;
  max-width: 900px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-primary, #fff);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary, #888);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary, #fff);
}

.tab-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(0, 0, 0, 0.2);
}

.tab {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary, #888);
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.tab:hover {
  background: rgba(255, 255, 255, 0.1);
}

.tab.active {
  background: var(--accent, #6366f1);
  color: white;
}

.search-bar {
  padding: 12px 20px;
}

.search-bar input {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary, #fff);
  font-size: 0.95rem;
}

.search-bar input::placeholder {
  color: var(--text-secondary, #666);
}

.category-bar {
  display: flex;
  gap: 8px;
  padding: 0 20px 12px;
  overflow-x: auto;
}

.category-btn {
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  background: transparent;
  color: var(--text-secondary, #888);
  cursor: pointer;
  font-size: 0.85rem;
  white-space: nowrap;
  transition: all 0.2s;
}

.category-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.2);
}

.category-btn.active {
  background: var(--accent, #6366f1);
  border-color: var(--accent, #6366f1);
  color: white;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 20px;
}

.loading, .error, .empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary, #888);
}

.error {
  color: #f87171;
}

.archetype-grid, .saved-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.archetype-card, .saved-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.archetype-card:hover, .saved-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.archetype-card.selected, .saved-card.selected {
  border-color: var(--accent, #6366f1);
  background: rgba(99, 102, 241, 0.1);
}

.card-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.card-name, .saved-name {
  font-weight: 600;
  color: var(--text-primary, #fff);
  margin-bottom: 4px;
}

.card-desc, .saved-archetype {
  font-size: 0.85rem;
  color: var(--text-secondary, #888);
  margin-bottom: 8px;
}

.card-traits, .saved-traits, .traits-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.trait-tag {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  font-size: 0.75rem;
  color: var(--text-secondary, #aaa);
}

.saved-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fav-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: var(--text-secondary, #666);
  transition: all 0.2s;
}

.fav-btn.favorited {
  color: #fbbf24;
}

.saved-stats {
  font-size: 0.75rem;
  color: var(--text-tertiary, #666);
  margin-top: 8px;
}

.detail-panel {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.detail-icon {
  font-size: 2.5rem;
}

.detail-header h3 {
  margin: 0;
  color: var(--text-primary, #fff);
}

.detail-header p {
  margin: 4px 0 0;
  color: var(--text-secondary, #888);
}

.fav-badge {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
}

.detail-traits, .detail-catchphrases {
  margin-bottom: 16px;
}

.detail-traits strong, .detail-catchphrases strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary, #888);
  font-size: 0.85rem;
}

.detail-catchphrases ul {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary, #aaa);
  font-style: italic;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quick-actions {
  display: flex;
  justify-content: center;
}

.quick-start-btn {
  padding: 14px 32px;
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 15px rgba(155, 89, 182, 0.3);
}

.quick-start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(155, 89, 182, 0.4);
}

.save-section {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.save-section label {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary, #888);
  font-size: 0.85rem;
}

.create-form input {
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary, #fff);
}

.create-btn, .use-btn {
  padding: 10px 20px;
  background: var(--accent, #6366f1);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.create-btn:hover, .use-btn:hover {
  background: var(--accent-hover, #5558e3);
  transform: translateY(-1px);
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.delete-btn {
  padding: 10px 20px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.2s;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.3);
}

/* Edit button */
.edit-btn {
  padding: 10px 20px;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: #3b82f6;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-btn:hover {
  background: rgba(59, 130, 246, 0.3);
}

/* Edit Panel */
.edit-panel {
  background: rgba(0, 0, 0, 0.3);
}

.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.edit-header h3 {
  margin: 0;
  color: var(--text-primary, #fff);
}

.cancel-btn {
  background: none;
  border: none;
  color: var(--text-secondary, #888);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary, #fff);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: var(--text-secondary, #888);
  font-size: 0.85rem;
  font-weight: 500;
}

.form-input {
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary, #fff);
  font-size: 0.95rem;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent, #6366f1);
}

.editable-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
}

.trait-tag.editable {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-right: 4px;
}

.remove-tag {
  background: none;
  border: none;
  color: var(--text-secondary, #888);
  cursor: pointer;
  padding: 0 4px;
  font-size: 0.9rem;
  opacity: 0.7;
}

.remove-tag:hover {
  opacity: 1;
  color: #ef4444;
}

.add-tag-row {
  display: flex;
  gap: 8px;
}

.add-tag-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary, #fff);
  font-size: 0.9rem;
}

.add-tag-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  cursor: pointer;
  font-size: 1rem;
}

.add-tag-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.catchphrase-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.catchphrase-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  color: var(--text-secondary, #aaa);
  font-style: italic;
}

.edit-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.save-btn {
  flex: 1;
  padding: 12px 20px;
  background: var(--accent, #6366f1);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.save-btn:hover {
  background: var(--accent-hover, #5558e3);
}

.cancel-edit-btn {
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-secondary, #aaa);
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-edit-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

/* Mobile responsive */
@media (max-width: 640px) {
  .roleplay-panel {
    width: 100%;
    height: 100%;
    max-height: 100%;
    border-radius: 0;
  }

  .archetype-grid, .saved-grid {
    grid-template-columns: 1fr;
  }

  .create-form {
    flex-direction: column;
  }

  .action-buttons {
    flex-direction: column;
  }

  .edit-actions {
    flex-direction: column;
  }
}
</style>
