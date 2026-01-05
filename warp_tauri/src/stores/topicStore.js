// Topic Store - Project Dashboard for SAM
// Each topic is a project with its own chat, progress, and documentation
import { reactive, computed } from 'vue'

const state = reactive({
  topics: [],
  activeTopic: null,
  loading: false
})

function getInitialTopics() {
  return [
    // Tier 1: Core Infrastructure
    {
      id: '1',
      name: 'SAM Terminal',
      icon: '🤖',
      progress: 85,
      status: 'Building',
      tier: 'Core',
      tags: ['core', 'tauri', 'rust'],
      description: 'Main AI terminal application with orchestrator',
      nextSteps: ['Complete Tauri build', 'Test orchestrator routing', 'Verify bridge connections'],
      path: '~/ReverseLab/SAM/warp_tauri',
      llm: 'Ollama + Claude',
      updated: new Date().toISOString()
    },
    {
      id: '2',
      name: 'Orchestrator',
      icon: '🎛️',
      progress: 90,
      status: 'Active',
      tier: 'Core',
      tags: ['core', 'rust', 'routing'],
      description: 'Hybrid AI router - routes to best model automatically',
      nextSteps: ['Add streaming support', 'Improve VRAM management', 'Add metrics dashboard'],
      path: 'SAM/scaffolding/orchestrator.rs',
      llm: 'Claude',
      updated: new Date().toISOString()
    },
    {
      id: '3',
      name: 'SSOT System',
      icon: '📚',
      progress: 75,
      status: 'Active',
      tier: 'Core',
      tags: ['core', 'knowledge', 'persistence'],
      description: 'Single Source of Truth - shared knowledge across all LLMs',
      nextSteps: ['Add semantic search', 'Build embeddings index', 'Create handoff automation'],
      path: '/Volumes/Plex/SSOT',
      llm: 'All',
      updated: new Date().toISOString()
    },

    // Tier 2: AI/ML Training
    {
      id: '4',
      name: 'RVC Voice Training',
      icon: '🎤',
      progress: 60,
      status: 'Training',
      tier: 'AI/ML',
      tags: ['ai', 'voice', 'training'],
      description: 'Voice cloning with Retrieval-based Voice Conversion',
      nextSteps: ['Complete Dustin Steele model', 'Test inference quality', 'Add batch processing'],
      path: '~/Projects/RVC',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '5',
      name: 'ComfyUI + LoRA',
      icon: '🎨',
      progress: 45,
      status: 'Setup',
      tier: 'AI/ML',
      tags: ['ai', 'image', 'training'],
      description: 'Image generation with custom LoRA training',
      nextSteps: ['Download Tumblr training data', 'Set up kohya_ss', 'Train aesthetic LoRA'],
      path: '~/ai-studio/ComfyUI',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '6',
      name: 'Motion Pipeline',
      icon: '🎬',
      progress: 30,
      status: 'Idle',
      tier: 'AI/ML',
      tags: ['video', 'animation'],
      description: 'Video frame interpolation and motion analysis',
      nextSteps: ['Integrate with Topaz', 'Add batch processing', 'Build queue system'],
      path: '~/Projects/motion-pipeline',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '7',
      name: 'Topaz Parity',
      icon: '📹',
      progress: 80,
      status: 'Research',
      tier: 'AI/ML',
      tags: ['video', 'upscaling', 're'],
      description: 'Open-source alternative to Topaz Video AI',
      nextSteps: ['Complete OpenVINO integration', 'Match quality metrics', 'Build CLI'],
      path: '/Volumes/Plex/DevSymlinks/topaz_parity',
      llm: 'Claude',
      updated: new Date().toISOString()
    },

    // Tier 3: Media Services
    {
      id: '8',
      name: 'Stash Enhancement',
      icon: '🎬',
      progress: 85,
      status: 'Active',
      tier: 'Media',
      tags: ['media', 'stash', 'docker'],
      description: 'Personal media manager with AI tagging',
      nextSteps: ['Enable addiction mode', 'Optimize previews', 'Add cache warming'],
      path: 'Docker/stash',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '9',
      name: 'Music Library',
      icon: '🎵',
      progress: 90,
      status: 'Migrating',
      tier: 'Media',
      tags: ['media', 'beets', 'lossless'],
      description: '4TB lossless music library with beets management',
      nextSteps: ['Complete rsync transfer', 'Run beets import', 'Verify quality analysis'],
      path: '/Volumes/Music',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '10',
      name: 'Animated Covers',
      icon: '💿',
      progress: 40,
      status: 'Idle',
      tier: 'Media',
      tags: ['media', 'apple-music', 'animation'],
      description: 'Fetch animated album artwork from Apple Music',
      nextSteps: ['Resume fetcher', 'Add to Navidrome', 'Create fallback generator'],
      path: 'Apple-Music-Animated-Artwork-Fetcher',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },

    // Tier 4: Automation
    {
      id: '11',
      name: 'Account Automation',
      icon: '🔐',
      progress: 60,
      status: 'Active',
      tier: 'Automation',
      tags: ['automation', 'playwright', 'accounts'],
      description: 'Automated account creation with Hide My Email',
      nextSteps: ['Fix email generator', 'Add tracker signups', 'Build dashboard'],
      path: '/Volumes/Plex/DevSymlinks/account_automation',
      llm: 'Playwright',
      updated: new Date().toISOString()
    },
    {
      id: '12',
      name: 'ChatGPT Bridge',
      icon: '🌉',
      progress: 100,
      status: 'Complete',
      tier: 'Automation',
      tags: ['automation', 'bridge', 'ai'],
      description: 'Browser automation bridge to ChatGPT (no API needed)',
      nextSteps: ['Monitor for UI changes', 'Add error recovery', 'Improve response parsing'],
      path: 'SAM/claude_chatgpt_bridge.cjs',
      llm: 'Puppeteer',
      updated: new Date().toISOString()
    },
    {
      id: '13',
      name: 'Claude Bridge',
      icon: '🔗',
      progress: 100,
      status: 'Complete',
      tier: 'Automation',
      tags: ['automation', 'bridge', 'ai'],
      description: 'Browser automation bridge to Claude.ai (no API needed)',
      nextSteps: ['Test with queue processor', 'Add session recovery', 'Monitor for changes'],
      path: 'SAM/claude_bridge.cjs',
      llm: 'Puppeteer',
      updated: new Date().toISOString()
    },

    // Tier 5: Game/Character Dev
    {
      id: '14',
      name: 'Character Pipeline',
      icon: '🎭',
      progress: 70,
      status: 'Ready',
      tier: 'Game Dev',
      tags: ['game', 'characters', 'ai'],
      description: 'AI character personality and dialogue system',
      nextSteps: ['Define character templates', 'Add memory system', 'Build relationship tracking'],
      path: 'SAM/character_pipeline',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '15',
      name: 'Unity Project',
      icon: '🎮',
      progress: 10,
      status: 'Planned',
      tier: 'Game Dev',
      tags: ['game', 'unity', '3d'],
      description: 'Unity game with AI companions',
      nextSteps: ['Set up project structure', 'Import character assets', 'Build AI integration'],
      path: 'SAM/unity_project',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },
    {
      id: '16',
      name: 'iOS Companion',
      icon: '📱',
      progress: 5,
      status: 'Planned',
      tier: 'Game Dev',
      tags: ['mobile', 'ios', 'companion'],
      description: 'iOS app for AI companion interaction',
      nextSteps: ['Design SwiftUI interface', 'Add voice input', 'Connect to SAM backend'],
      path: 'SAM/ios-companion',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },

    // Tier 6: Platform
    {
      id: '17',
      name: 'StashGrid tvOS',
      icon: '📺',
      progress: 5,
      status: 'Planned',
      tier: 'Platform',
      tags: ['tvos', 'apple-tv', 'stash'],
      description: 'Apple TV app for Stash with multi-video grid',
      nextSteps: ['Set up Xcode project', 'Add TVVLCKit', 'Build grid UI'],
      path: 'SSOT/STASH_GRIDPLAYER_TVOS.md',
      llm: 'Claude',
      updated: new Date().toISOString()
    },
    {
      id: '18',
      name: 'Cloudflare Tunnel',
      icon: '☁️',
      progress: 95,
      status: 'Active',
      tier: 'Platform',
      tags: ['infrastructure', 'cloudflare', 'tunnel'],
      description: 'Secure remote access via Cloudflare tunnels',
      nextSteps: ['Add cache rules', 'Monitor performance', 'Set up alerts'],
      path: '~/.cloudflared',
      llm: 'Ollama',
      updated: new Date().toISOString()
    },

    // Tier 7: Reverse Engineering
    {
      id: '19',
      name: 'ReverseLab',
      icon: '🔬',
      progress: 80,
      status: 'Active',
      tier: 'RE',
      tags: ['re', 'frida', 'security'],
      description: 'Reverse engineering tools and research',
      nextSteps: ['Document Topaz findings', 'Add new targets', 'Build analysis tools'],
      path: '~/ReverseLab',
      llm: 'Claude',
      updated: new Date().toISOString()
    },

    // Tier 8: Data
    {
      id: '20',
      name: 'Training Data',
      icon: '📊',
      progress: 50,
      status: 'Collecting',
      tier: 'Data',
      tags: ['data', 'tumblr', 'training'],
      description: 'Collecting training data for LoRA and voice models',
      nextSteps: ['Complete Tumblr download', 'Organize by category', 'Prepare for training'],
      path: '/Volumes/David External/ai-studio/training_data',
      llm: 'Ollama',
      updated: new Date().toISOString()
    }
  ]
}

function loadTopics() {
  state.loading = true
  try {
    // Always use fresh data for now to ensure updates show
    state.topics = getInitialTopics()
    localStorage.setItem('sam_topics', JSON.stringify(state.topics))
  } catch (e) {
    state.topics = getInitialTopics()
  }
  state.loading = false
}

function saveTopics() {
  localStorage.setItem('sam_topics', JSON.stringify(state.topics))
}

function addTopic(topic) {
  const newTopic = { ...topic, id: Date.now().toString(), updated: new Date().toISOString() }
  state.topics.push(newTopic)
  saveTopics()
  return newTopic
}

function updateTopic(id, updates) {
  const idx = state.topics.findIndex(t => t.id === id)
  if (idx >= 0) {
    state.topics[idx] = { ...state.topics[idx], ...updates, updated: new Date().toISOString() }
    saveTopics()
  }
}

function deleteTopic(id) {
  state.topics = state.topics.filter(t => t.id !== id)
  saveTopics()
}

function archiveTopic(id) { updateTopic(id, { archived: true }) }

function duplicateTopic(id) {
  const topic = state.topics.find(t => t.id === id)
  if (topic) addTopic({ ...topic, name: `${topic.name} (Copy)` })
}

function mergeTopics(ids, newName) {
  const toMerge = state.topics.filter(t => ids.includes(t.id))
  if (toMerge.length < 2) return
  const merged = {
    id: Date.now().toString(),
    name: newName,
    icon: toMerge[0].icon,
    progress: Math.round(toMerge.reduce((s, t) => s + t.progress, 0) / toMerge.length),
    tags: [...new Set(toMerge.flatMap(t => t.tags || []))],
    updated: new Date().toISOString()
  }
  state.topics = state.topics.filter(t => !ids.includes(t.id))
  state.topics.push(merged)
  saveTopics()
  return merged
}

function openTopic(id) {
  const topic = state.topics.find(t => t.id === id)
  if (!topic) return

  state.activeTopic = topic

  // Emit event for App.vue to create a dedicated chat tab for this topic
  window.dispatchEvent(new CustomEvent('open-topic-chat', {
    detail: {
      id: topic.id,
      name: topic.name,
      icon: topic.icon,
      context: `You are working on the "${topic.name}" project.

Description: ${topic.description}
Status: ${topic.status}
Progress: ${topic.progress}%
Path: ${topic.path}
Tags: ${(topic.tags || []).join(', ')}

Next Steps:
${(topic.nextSteps || []).map((s, i) => `${i + 1}. ${s}`).join('\n')}

Help the user make progress on this project.`
    }
  }))
}

export function useTopicStore() {
  return {
    topics: computed(() => state.topics),
    activeTopic: computed(() => state.activeTopic),
    loading: computed(() => state.loading),
    loadTopics, addTopic, updateTopic, deleteTopic, archiveTopic,
    duplicateTopic, mergeTopics, openTopic,
    getTopicById: (id) => state.topics.find(t => t.id === id)
  }
}
