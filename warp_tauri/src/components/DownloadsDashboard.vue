<template>
  <div class="downloads-dashboard">
    <div class="dashboard-header">
      <h1>Downloads & Media</h1>
      <button @click="refreshAll" class="btn-refresh" :disabled="loading">
        {{ loading ? 'Refreshing...' : 'Refresh All' }}
      </button>
    </div>

    <!-- Service Status Cards -->
    <div class="services-grid">
      <!-- qBittorrent -->
      <div class="service-card" :class="{ online: services.qbit.online }">
        <div class="service-header">
          <span class="service-icon">📥</span>
          <h2>qBittorrent</h2>
          <span class="status-dot" :class="{ online: services.qbit.online }"></span>
        </div>
        <div v-if="services.qbit.online" class="service-stats">
          <div class="stat">
            <span class="label">Download</span>
            <span class="value">{{ formatSpeed(services.qbit.dlSpeed) }}</span>
          </div>
          <div class="stat">
            <span class="label">Upload</span>
            <span class="value">{{ formatSpeed(services.qbit.upSpeed) }}</span>
          </div>
          <div class="stat">
            <span class="label">Active</span>
            <span class="value">{{ services.qbit.active }}</span>
          </div>
        </div>
        <div v-else class="service-offline">Offline or Auth Required</div>
        <a :href="services.qbit.url" target="_blank" class="service-link">Open UI</a>
      </div>

      <!-- Radarr -->
      <div class="service-card" :class="{ online: services.radarr.online }">
        <div class="service-header">
          <span class="service-icon">🎬</span>
          <h2>Radarr</h2>
          <span class="status-dot" :class="{ online: services.radarr.online }"></span>
        </div>
        <div v-if="services.radarr.online" class="service-stats">
          <div class="stat">
            <span class="label">Queue</span>
            <span class="value">{{ services.radarr.queue }}</span>
          </div>
          <div class="stat">
            <span class="label">Movies</span>
            <span class="value">{{ services.radarr.total }}</span>
          </div>
        </div>
        <div v-else class="service-offline">Offline</div>
        <a :href="services.radarr.url" target="_blank" class="service-link">Open UI</a>
      </div>

      <!-- Sonarr -->
      <div class="service-card" :class="{ online: services.sonarr.online }">
        <div class="service-header">
          <span class="service-icon">📺</span>
          <h2>Sonarr</h2>
          <span class="status-dot" :class="{ online: services.sonarr.online }"></span>
        </div>
        <div v-if="services.sonarr.online" class="service-stats">
          <div class="stat">
            <span class="label">Queue</span>
            <span class="value">{{ services.sonarr.queue }}</span>
          </div>
          <div class="stat">
            <span class="label">Series</span>
            <span class="value">{{ services.sonarr.total }}</span>
          </div>
        </div>
        <div v-else class="service-offline">Offline</div>
        <a :href="services.sonarr.url" target="_blank" class="service-link">Open UI</a>
      </div>

      <!-- Lidarr -->
      <div class="service-card" :class="{ online: services.lidarr.online }">
        <div class="service-header">
          <span class="service-icon">🎵</span>
          <h2>Lidarr</h2>
          <span class="status-dot" :class="{ online: services.lidarr.online }"></span>
        </div>
        <div v-if="services.lidarr.online" class="service-stats">
          <div class="stat">
            <span class="label">Queue</span>
            <span class="value">{{ services.lidarr.queue }}</span>
          </div>
          <div class="stat">
            <span class="label">Artists</span>
            <span class="value">{{ services.lidarr.total }}</span>
          </div>
        </div>
        <div v-else class="service-offline">Offline</div>
        <a :href="services.lidarr.url" target="_blank" class="service-link">Open UI</a>
      </div>

      <!-- Prowlarr -->
      <div class="service-card" :class="{ online: services.prowlarr.online }">
        <div class="service-header">
          <span class="service-icon">🔍</span>
          <h2>Prowlarr</h2>
          <span class="status-dot" :class="{ online: services.prowlarr.online }"></span>
        </div>
        <div v-if="services.prowlarr.online" class="service-stats">
          <div class="stat">
            <span class="label">Indexers</span>
            <span class="value">{{ services.prowlarr.indexers }}</span>
          </div>
        </div>
        <div v-else class="service-offline">Offline or Auth Required</div>
        <a :href="services.prowlarr.url" target="_blank" class="service-link">Open UI</a>
      </div>

      <!-- Stash -->
      <div class="service-card" :class="{ online: services.stash.online }">
        <div class="service-header">
          <span class="service-icon">🗄️</span>
          <h2>Stash</h2>
          <span class="status-dot" :class="{ online: services.stash.online }"></span>
        </div>
        <div v-if="services.stash.online" class="service-stats">
          <div class="stat">
            <span class="label">Scenes</span>
            <span class="value">{{ services.stash.scenes }}</span>
          </div>
        </div>
        <div v-else class="service-offline">Offline</div>
        <a :href="services.stash.url" target="_blank" class="service-link">Open UI</a>
      </div>
    </div>

    <!-- Active Downloads List -->
    <div class="downloads-section" v-if="activeDownloads.length > 0">
      <h2>Active Downloads ({{ activeDownloads.length }})</h2>
      <div class="downloads-list">
        <div v-for="dl in activeDownloads" :key="dl.id" class="download-item">
          <div class="download-info">
            <span class="download-name">{{ dl.name }}</span>
            <span class="download-source">{{ dl.source }}</span>
          </div>
          <div class="download-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: dl.progress + '%' }"></div>
            </div>
            <span class="progress-text">{{ dl.progress }}%</span>
          </div>
          <div class="download-stats">
            <span>{{ formatSpeed(dl.speed) }}</span>
            <span>{{ dl.eta }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface ServiceStatus {
  online: boolean
  url: string
  [key: string]: any
}

interface Download {
  id: string
  name: string
  source: string
  progress: number
  speed: number
  eta: string
}

const loading = ref(false)
const services = ref<Record<string, ServiceStatus>>({
  qbit: { online: false, url: 'http://localhost:8081', dlSpeed: 0, upSpeed: 0, active: 0 },
  radarr: { online: false, url: 'http://localhost:7878', queue: 0, total: 0 },
  sonarr: { online: false, url: 'http://localhost:8989', queue: 0, total: 0 },
  lidarr: { online: false, url: 'http://localhost:8686', queue: 0, total: 0 },
  prowlarr: { online: false, url: 'http://localhost:9697', indexers: 0 },
  stash: { online: false, url: 'http://localhost:9999', scenes: 0 }
})

const activeDownloads = ref<Download[]>([])
let refreshInterval: number | null = null

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return `${bytesPerSec} B/s`
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`
  return `${(bytesPerSec / 1024 / 1024).toFixed(1)} MB/s`
}

async function checkService(name: string, url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { method: 'HEAD', mode: 'no-cors' })
    return true
  } catch {
    return false
  }
}

async function fetchQbitStatus() {
  try {
    // Try to get transfer info
    const response = await fetch('http://localhost:8081/api/v2/transfer/info')
    if (response.ok) {
      const data = await response.json()
      services.value.qbit = {
        ...services.value.qbit,
        online: true,
        dlSpeed: data.dl_info_speed || 0,
        upSpeed: data.up_info_speed || 0
      }

      // Get torrent count
      const torrentsResp = await fetch('http://localhost:8081/api/v2/torrents/info?filter=active')
      if (torrentsResp.ok) {
        const torrents = await torrentsResp.json()
        services.value.qbit.active = torrents.length

        // Update active downloads list
        activeDownloads.value = torrents.slice(0, 10).map((t: any) => ({
          id: t.hash,
          name: t.name,
          source: 'qBittorrent',
          progress: Math.round(t.progress * 100),
          speed: t.dlspeed,
          eta: t.eta > 0 ? formatEta(t.eta) : 'Unknown'
        }))
      }
    }
  } catch {
    services.value.qbit.online = false
  }
}

async function fetchArrStatus(name: 'radarr' | 'sonarr' | 'lidarr', port: number) {
  const baseUrl = `http://localhost:${port}`
  try {
    // Just check if responding
    const response = await fetch(baseUrl)
    if (response.ok || response.status === 302) {
      services.value[name].online = true
      // Would need API key to get detailed stats
    }
  } catch {
    services.value[name].online = false
  }
}

async function fetchStashStatus() {
  try {
    const response = await fetch('http://localhost:9999')
    services.value.stash.online = response.ok || response.status === 302
  } catch {
    services.value.stash.online = false
  }
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

async function refreshAll() {
  loading.value = true
  await Promise.all([
    fetchQbitStatus(),
    fetchArrStatus('radarr', 7878),
    fetchArrStatus('sonarr', 8989),
    fetchArrStatus('lidarr', 8686),
    checkService('prowlarr', 'http://localhost:9697').then(ok => services.value.prowlarr.online = ok),
    fetchStashStatus()
  ])
  loading.value = false
}

onMounted(() => {
  refreshAll()
  // Auto-refresh every 30 seconds
  refreshInterval = window.setInterval(refreshAll, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.downloads-dashboard {
  padding: 1rem;
  background: var(--bg-primary, #1a1a2e);
  min-height: 100%;
  color: var(--text-primary, #e0e0e0);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.btn-refresh {
  padding: 0.5rem 1rem;
  background: var(--accent, #4a9eff);
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  opacity: 0.8;
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.service-card {
  background: var(--bg-secondary, #252542);
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid var(--border, #333);
  transition: border-color 0.2s;
}

.service-card.online {
  border-color: var(--success, #4caf50);
}

.service-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.service-icon {
  font-size: 1.25rem;
}

.service-header h2 {
  margin: 0;
  font-size: 1rem;
  flex: 1;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--error, #f44336);
}

.status-dot.online {
  background: var(--success, #4caf50);
}

.service-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.stat {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.stat .label {
  color: var(--text-secondary, #888);
}

.stat .value {
  font-weight: 500;
}

.service-offline {
  color: var(--text-secondary, #888);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.service-link {
  display: block;
  text-align: center;
  padding: 0.5rem;
  background: var(--bg-tertiary, #1e1e3f);
  border-radius: 6px;
  color: var(--accent, #4a9eff);
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.2s;
}

.service-link:hover {
  background: var(--bg-hover, #2a2a4a);
}

.downloads-section h2 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
}

.downloads-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.download-item {
  background: var(--bg-secondary, #252542);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 1rem;
  align-items: center;
}

.download-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.download-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.download-source {
  font-size: 0.75rem;
  color: var(--text-secondary, #888);
}

.download-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 150px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-tertiary, #1e1e3f);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent, #4a9eff);
  transition: width 0.3s;
}

.progress-text {
  font-size: 0.75rem;
  min-width: 40px;
  text-align: right;
}

.download-stats {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-secondary, #888);
  text-align: right;
}
</style>
