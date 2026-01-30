<template>
  <div class="project-gallery" :class="{ collapsed: isCollapsed }">
    <div class="gallery-header" @click="toggleCollapsed">
      <div class="header-left">
        <span class="icon">{{ isCollapsed ? '▶' : '▼' }}</span>
        <span class="title">Projects</span>
        <span class="count">{{ activeCount }}/{{ projects.length }}</span>
      </div>
      <div class="header-right">
        <button class="refresh-btn" @click.stop="loadProjects" title="Refresh">⟳</button>
      </div>
    </div>

    <div class="gallery-content" v-if="!isCollapsed">
      <!-- Tier Groups -->
      <div v-for="tier in groupedProjects" :key="tier.name" class="tier-group">
        <div class="tier-header">{{ tier.name }}</div>
        <div class="project-grid">
          <div
            v-for="project in tier.projects"
            :key="project.name"
            class="project-card"
            :class="[getStatusClass(project.status)]"
            @click="selectProject(project)"
          >
            <div class="project-name">{{ project.name }}</div>
            <div class="project-status">
              <span class="status-dot" :class="getStatusClass(project.status)"></span>
              {{ project.status }}
            </div>
            <div class="project-llm" v-if="project.llm">{{ project.llm }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Project {
  name: string
  path: string
  status: 'Active' | 'Building' | 'Ready' | 'Idle' | 'Planned' | 'Done' | 'Research' | 'Setup' | 'Migrating'
  tier: string
  llm?: string
}

const isCollapsed = ref(false)
const projects = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)

// Load projects from SSOT or localStorage
async function loadProjects() {
  // Try to load from SSOT via Tauri command
  try {
    const { invoke } = await import('@tauri-apps/api/tauri')
    const ssotProjects = await invoke('load_ssot_projects')
    if (Array.isArray(ssotProjects) && ssotProjects.length > 0) {
      projects.value = ssotProjects
      return
    }
  } catch (e) {
    // Fallback to defaults
  }

  // Default projects based on PROJECT_REGISTRY.md
  projects.value = [
    // Tier 1: Core Infrastructure
    { name: 'SAM Terminal', path: '~/ReverseLab/SAM/warp_tauri', status: 'Building', tier: 'Core', llm: 'MLX' },
    { name: 'Orchestrator', path: 'SAM/scaffolding', status: 'Active', tier: 'Core', llm: 'Claude' },
    { name: 'SSOT System', path: '/Volumes/Plex/SSOT', status: 'Active', tier: 'Core', llm: 'All' },

    // Tier 2: AI/ML Training
    { name: 'RVC Voice', path: '~/Projects/RVC', status: 'Ready', tier: 'AI/ML', llm: 'MLX' },
    { name: 'ComfyUI/LoRA', path: '~/ai-studio/ComfyUI', status: 'Setup', tier: 'AI/ML', llm: 'MLX' },
    { name: 'Motion Pipeline', path: '~/Projects/motion-pipeline', status: 'Idle', tier: 'AI/ML', llm: 'MLX' },
    { name: 'Topaz Parity', path: 'DevSymlinks/topaz_parity', status: 'Research', tier: 'AI/ML', llm: 'Claude' },

    // Tier 3: Media Services
    { name: 'Stash Enhancement', path: 'Docker/stash', status: 'Active', tier: 'Media', llm: 'MLX' },
    { name: 'Plex Integration', path: 'Docker/plex', status: 'Active', tier: 'Media', llm: 'MLX' },
    { name: 'Navidrome', path: 'Docker/navidrome', status: 'Active', tier: 'Media', llm: 'MLX' },
    { name: 'Music Library', path: '/Volumes/Music', status: 'Migrating', tier: 'Media', llm: 'MLX' },

    // Tier 4: Automation
    { name: 'Account Automation', path: 'DevSymlinks/account_automation', status: 'Active', tier: 'Automation', llm: 'Playwright' },
    { name: 'Warp Auto', path: '~/ReverseLab/warp_auto', status: 'Idle', tier: 'Automation', llm: 'MLX' },

    // Tier 5: Game/Character Dev
    { name: 'Character Pipeline', path: 'SAM/character_pipeline', status: 'Ready', tier: 'Game Dev', llm: 'MLX' },
    { name: 'Unity Project', path: 'SAM/unity_project', status: 'Planned', tier: 'Game Dev', llm: 'MLX' },
    { name: 'Unreal Project', path: 'SAM/unreal_project', status: 'Planned', tier: 'Game Dev', llm: 'MLX' },
    { name: 'iOS Companion', path: 'SAM/ios-companion', status: 'Planned', tier: 'Game Dev', llm: 'MLX' },

    // Tier 6: Reverse Engineering
    { name: 'ReverseLab', path: '~/ReverseLab', status: 'Active', tier: 'RE', llm: 'Claude' },

    // Tier 7: Data Acquisition
    { name: 'Tumblr Likes', path: 'David External/ai-studio', status: 'Active', tier: 'Data', llm: 'MLX' },

    // Tier 8: Multi-Platform
    { name: 'StashGrid tvOS', path: 'SSOT/STASH_GRIDPLAYER_TVOS', status: 'Planned', tier: 'Platform', llm: 'Claude' },
  ]
}

const groupedProjects = computed(() => {
  const tiers: Record<string, Project[]> = {}
  for (const p of projects.value) {
    if (!tiers[p.tier]) tiers[p.tier] = []
    tiers[p.tier].push(p)
  }
  return Object.entries(tiers).map(([name, ps]) => ({ name, projects: ps }))
})

const activeCount = computed(() =>
  projects.value.filter(p => ['Active', 'Building'].includes(p.status)).length
)

function getStatusClass(status: string): string {
  const map: Record<string, string> = {
    'Active': 'status-active',
    'Building': 'status-building',
    'Ready': 'status-ready',
    'Idle': 'status-idle',
    'Planned': 'status-planned',
    'Done': 'status-done',
    'Research': 'status-research',
    'Setup': 'status-setup',
    'Migrating': 'status-migrating',
  }
  return map[status] || 'status-idle'
}

function toggleCollapsed() {
  isCollapsed.value = !isCollapsed.value
}

function selectProject(project: Project) {
  selectedProject.value = project
  // Emit event or trigger action
}

onMounted(() => {
  loadProjects()
})

defineExpose({
  projects,
  loadProjects,
  selectedProject
})
</script>

<style scoped>
.project-gallery {
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-color, #333);
  border-radius: 8px;
  margin: 8px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-tertiary, #252540);
  cursor: pointer;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 1;
}

.gallery-header:hover {
  background: var(--bg-hover, #2a2a4a);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon {
  font-size: 10px;
  color: var(--text-muted, #888);
}

.title {
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.count {
  color: var(--text-muted, #888);
  font-size: 12px;
}

.refresh-btn {
  background: transparent;
  border: none;
  color: var(--text-muted, #888);
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  border-radius: 4px;
}

.refresh-btn:hover {
  background: var(--bg-hover, rgba(255,255,255,0.1));
  color: var(--text-primary, #fff);
}

.gallery-content {
  padding: 8px;
}

.tier-group {
  margin-bottom: 12px;
}

.tier-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #888);
  text-transform: uppercase;
  padding: 4px 8px;
  margin-bottom: 6px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.project-card {
  background: var(--bg-tertiary, #252540);
  border-radius: 6px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.project-card:hover {
  background: var(--bg-hover, #2a2a4a);
  border-color: var(--accent-color, #60a5fa);
}

.project-name {
  font-weight: 500;
  color: var(--text-primary, #fff);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted, #888);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-active .status-dot,
.status-active { color: #4ade80; }
.status-active .status-dot { background: #4ade80; }

.status-building .status-dot,
.status-building { color: #60a5fa; }
.status-building .status-dot { background: #60a5fa; animation: pulse 1s infinite; }

.status-ready .status-dot,
.status-ready { color: #a78bfa; }
.status-ready .status-dot { background: #a78bfa; }

.status-idle .status-dot,
.status-idle { color: #6b7280; }
.status-idle .status-dot { background: #6b7280; }

.status-planned .status-dot,
.status-planned { color: #fbbf24; }
.status-planned .status-dot { background: #fbbf24; }

.status-done .status-dot,
.status-done { color: #22c55e; }
.status-done .status-dot { background: #22c55e; }

.status-research .status-dot,
.status-research { color: #f472b6; }
.status-research .status-dot { background: #f472b6; }

.status-setup .status-dot,
.status-setup { color: #fb923c; }
.status-setup .status-dot { background: #fb923c; }

.status-migrating .status-dot,
.status-migrating { color: #38bdf8; }
.status-migrating .status-dot { background: #38bdf8; animation: pulse 1s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.project-llm {
  font-size: 10px;
  color: var(--text-muted, #666);
  margin-top: 4px;
}

.collapsed .gallery-content {
  display: none;
}
</style>
