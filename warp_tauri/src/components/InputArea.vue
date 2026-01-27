<template>
  <div
    class="input-area"
    @drop.prevent="handleDrop"
    @dragover.prevent="isDragging = true"
    @dragleave="isDragging = false"
    :class="{ dragging: isDragging }"
  >
    <!-- Image Preview (Phase 3) -->
    <div v-if="selectedImage" class="image-preview">
      <img :src="selectedImage.preview" alt="Selected image" />
      <button @click="clearImage" class="remove-image-btn">✕</button>
    </div>

    <div class="input-row">
      <!-- Image Upload Button -->
      <button @click="triggerImageUpload" class="attach-btn" title="Attach image">
        📷
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        @change="handleFileSelect"
        style="display: none"
      />

      <textarea
        ref="inputRef"
        v-model="input"
        @keydown="handleKeyDown"
        @paste="handlePaste"
        :placeholder="placeholder"
        rows="1"
        autofocus
      ></textarea>
      <button @click="sendMessage" :disabled="!canSend" class="send-btn">
        <span v-if="!sending">Send</span>
        <span v-else>...</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'

interface ImageData {
  file: File | null
  path: string | null
  preview: string
  base64?: string
}

const emit = defineEmits<{
  (e: 'send', message: string, image?: ImageData): void
}>()

const input = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const sending = ref(false)
const isDragging = ref(false)
const selectedImage = ref<ImageData | null>(null)

const placeholder = computed(() => {
  if (selectedImage.value) {
    return 'Describe or ask about this image...'
  }
  return 'Type a message, drop an image, or /shell <command>...'
})

const canSend = computed(() => {
  return input.value.trim() || selectedImage.value
})

function handleKeyDown(e: KeyboardEvent) {
  // Enter without shift sends message
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }

  // Auto-resize textarea
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
      inputRef.value.style.height = inputRef.value.scrollHeight + 'px'
    }
  })
}

// Image handling functions (Phase 3)
function triggerImageUpload() {
  fileInputRef.value?.click()
}

async function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    await processImageFile(target.files[0])
  }
}

async function handleDrop(e: DragEvent) {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files[0] && files[0].type.startsWith('image/')) {
    await processImageFile(files[0])
  }
}

async function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await processImageFile(file)
      }
      break
    }
  }
}

async function processImageFile(file: File) {
  // Create preview
  const preview = URL.createObjectURL(file)

  // Convert to base64 for API
  const base64 = await fileToBase64(file)

  selectedImage.value = {
    file,
    path: null,
    preview,
    base64
  }
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Remove data URL prefix
      const base64 = result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function clearImage() {
  if (selectedImage.value?.preview) {
    URL.revokeObjectURL(selectedImage.value.preview)
  }
  selectedImage.value = null
}

async function sendMessage() {
  if (!canSend.value || sending.value) return

  const message = input.value.trim()
  const image = selectedImage.value

  input.value = ''
  clearImage()

  // Reset textarea height
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }

  sending.value = true
  emit('send', message || 'Describe this image', image || undefined)

  // Reset sending state after a short delay
  setTimeout(() => {
    sending.value = false
  }, 500)
}

// Focus input on mount
nextTick(() => {
  inputRef.value?.focus()
})
</script>

<style scoped>
.input-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background-color: #1e1e1e;
  border-top: 1px solid #404040;
  transition: background-color 0.2s;
}

.input-area.dragging {
  background-color: #2a4a6a;
  border-top-color: #0084ff;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

/* Image preview (Phase 3) */
.image-preview {
  position: relative;
  max-width: 200px;
  max-height: 150px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #404040;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-image-btn:hover {
  background: rgba(255, 0, 0, 0.7);
}

.attach-btn {
  padding: 10px 12px;
  background-color: #2d2d2d;
  color: #e0e0e0;
  border: 1px solid #404040;
  border-radius: 8px;
  font-size: 18px;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.attach-btn:hover {
  background-color: #3d3d3d;
  border-color: #0084ff;
}

textarea {
  flex: 1;
  min-height: 40px;
  max-height: 200px;
  padding: 10px 12px;
  background-color: #2d2d2d;
  color: #e0e0e0;
  border: 1px solid #404040;
  border-radius: 8px;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  line-height: 1.4;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
}

textarea:focus {
  border-color: #0084ff;
}

textarea::placeholder {
  color: #666;
}

.send-btn {
  padding: 10px 20px;
  background-color: #0084ff;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s, opacity 0.2s;
  white-space: nowrap;
}

.send-btn:hover:not(:disabled) {
  background-color: #0073e6;
}

.send-btn:active:not(:disabled) {
  background-color: #0062cc;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
