<template>
  <div class="scraper-dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-content">
        <h1>📊 Content Pipeline</h1>
        <p class="subtitle">Training data collection status</p>
      </div>
      <button @click="refreshAll" class="refresh-btn" :class="{ spinning: loading }">
        🔄
      </button>
    </header>

    <!-- Summary Cards -->
    <div class="summary-row">
      <div class="summary-card">
        <span class="summary-emoji">📚</span>
        <div class="summary-data">
          <span class="summary-value">{{ totalIndexed.toLocaleString() }}</span>
          <span class="summary-label">Indexed</span>
        </div>
      </div>
      <div class="summary-card">
        <span class="summary-emoji">⬇️</span>
        <div class="summary-data">
          <span class="summary-value">{{ totalDownloaded.toLocaleString() }}</span>
          <span class="summary-label">Downloaded</span>
        </div>
      </div>
      <div class="summary-card">
        <span class="summary-emoji">⏳</span>
        <div class="summary-data">
          <span class="summary-value">{{ totalPending.toLocaleString() }}</span>
          <span class="summary-label">Remaining</span>
        </div>
      </div>
      <div class="summary-card highlight">
        <span class="summary-emoji">🧠</span>
        <div class="summary-data">
          <span class="summary-value">{{ totalProcessed.toLocaleString() }}</span>
          <span class="summary-label">Processed</span>
        </div>
      </div>
    </div>

    <!-- Scraper Cards -->
    <div class="scrapers-grid">
      <!-- Nifty Archive -->
      <div class="scraper-card" :class="{ active: scrapers.nifty.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">📖</span>
            <div>
              <h2>Nifty Archive</h2>
              <span class="source-url">nifty.org</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.nifty.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.nifty.running ? 'Active' : 'Idle' }}
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-icon">🔍</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.nifty.indexed.toLocaleString() }}</span>
              <span class="stat-label">Indexed</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">✅</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.nifty.downloaded.toLocaleString() }}</span>
              <span class="stat-label">Downloaded</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">📋</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.nifty.pending.toLocaleString() }}</span>
              <span class="stat-label">Remaining</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚡</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.nifty.processed.toLocaleString() }}</span>
              <span class="stat-label">Processed</span>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span>Download Progress</span>
            <span class="progress-percent">{{ getProgress(scrapers.nifty).toFixed(1) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill nifty" :style="{ width: getProgress(scrapers.nifty) + '%' }"></div>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="scrapers.nifty.running" @click="stopScraper('nifty')" class="action-btn stop">
            ⏹️ Stop
          </button>
          <button v-else-if="startingScrapers['nifty']" class="action-btn starting" disabled>
            ⏳ Starting...
          </button>
          <button v-else @click="startScraper('nifty')" class="action-btn start">
            ▶️ Start
          </button>
          <button @click="viewLogs('nifty')" class="action-btn logs">
            📜 Logs
          </button>
        </div>
      </div>

      <!-- V Magazine -->
      <div class="scraper-card" :class="{ active: scrapers.vmag.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">👗</span>
            <div>
              <h2>V Magazine</h2>
              <span class="source-url">vmagazine.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.vmag.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.vmag.running ? 'Active' : 'Idle' }}
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-icon">🔍</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.vmag.indexed.toLocaleString() }}</span>
              <span class="stat-label">Indexed</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">✅</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.vmag.downloaded.toLocaleString() }}</span>
              <span class="stat-label">Downloaded</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">📋</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.vmag.pending.toLocaleString() }}</span>
              <span class="stat-label">Remaining</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚡</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.vmag.processed.toLocaleString() }}</span>
              <span class="stat-label">Processed</span>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span>Download Progress</span>
            <span class="progress-percent">{{ getProgress(scrapers.vmag).toFixed(1) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill vmag" :style="{ width: getProgress(scrapers.vmag) + '%' }"></div>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="scrapers.vmag.running" @click="stopScraper('vmag')" class="action-btn stop">
            ⏹️ Stop
          </button>
          <button v-else-if="startingScrapers['vmag']" class="action-btn starting" disabled>
            ⏳ Starting...
          </button>
          <button v-else @click="startScraper('vmag')" class="action-btn start">
            ▶️ Start
          </button>
          <button @click="viewLogs('vmag')" class="action-btn logs">
            📜 Logs
          </button>
        </div>
      </div>

      <!-- W Magazine -->
      <div class="scraper-card" :class="{ active: scrapers.wmag.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">👠</span>
            <div>
              <h2>W Magazine</h2>
              <span class="source-url">wmagazine.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.wmag.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.wmag.running ? 'Active' : 'Idle' }}
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-icon">🔍</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wmag.indexed.toLocaleString() }}</span>
              <span class="stat-label">Indexed</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">✅</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wmag.downloaded.toLocaleString() }}</span>
              <span class="stat-label">Downloaded</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">📋</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wmag.pending.toLocaleString() }}</span>
              <span class="stat-label">Remaining</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚡</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wmag.processed.toLocaleString() }}</span>
              <span class="stat-label">Processed</span>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span>Download Progress</span>
            <span class="progress-percent">{{ getProgress(scrapers.wmag).toFixed(1) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill wmag" :style="{ width: getProgress(scrapers.wmag) + '%' }"></div>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="scrapers.wmag.running" @click="stopScraper('wmag')" class="action-btn stop">
            ⏹️ Stop
          </button>
          <button v-else-if="startingScrapers['wmag']" class="action-btn starting" disabled>
            ⏳ Starting...
          </button>
          <button v-else @click="startScraper('wmag')" class="action-btn start">
            ▶️ Start
          </button>
          <button @click="viewLogs('wmag')" class="action-btn logs">
            📜 Logs
          </button>
        </div>
      </div>

      <!-- WWD (Women's Wear Daily) -->
      <div class="scraper-card" :class="{ active: scrapers.wwd.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">📰</span>
            <div>
              <h2>WWD</h2>
              <span class="source-url">wwd.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.wwd.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.wwd.running ? 'Active' : 'Idle' }}
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-icon">🔍</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wwd.indexed.toLocaleString() }}</span>
              <span class="stat-label">Indexed</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">✅</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wwd.downloaded.toLocaleString() }}</span>
              <span class="stat-label">Downloaded</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">📋</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wwd.pending.toLocaleString() }}</span>
              <span class="stat-label">Remaining</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚡</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.wwd.processed.toLocaleString() }}</span>
              <span class="stat-label">Processed</span>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span>Download Progress</span>
            <span class="progress-percent">{{ getProgress(scrapers.wwd).toFixed(1) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill wwd" :style="{ width: getProgress(scrapers.wwd) + '%' }"></div>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="scrapers.wwd.running" @click="stopScraper('wwd')" class="action-btn stop">
            ⏹️ Stop
          </button>
          <button v-else-if="startingScrapers['wwd']" class="action-btn starting" disabled>
            ⏳ Starting...
          </button>
          <button v-else @click="startScraper('wwd')" class="action-btn start">
            ▶️ Start
          </button>
          <button @click="viewLogs('wwd')" class="action-btn logs">
            📜 Logs
          </button>
        </div>
      </div>

      <!-- FirstView (Fashion Photos) -->
      <div class="scraper-card" :class="{ active: scrapers.firstview.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">📸</span>
            <div>
              <h2>FirstView</h2>
              <span class="source-url">firstview.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.firstview.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.firstview.running ? 'Active' : 'Idle' }}
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-icon">🔍</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.firstview.indexed.toLocaleString() }}</span>
              <span class="stat-label">Photos</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">✅</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.firstview.downloaded.toLocaleString() }}</span>
              <span class="stat-label">Downloaded</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">📋</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.firstview.pending.toLocaleString() }}</span>
              <span class="stat-label">Remaining</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚡</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.firstview.processed.toLocaleString() }}</span>
              <span class="stat-label">Processed</span>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span>Download Progress</span>
            <span class="progress-percent">{{ getProgress(scrapers.firstview).toFixed(1) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill firstview" :style="{ width: getProgress(scrapers.firstview) + '%' }"></div>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="scrapers.firstview.running" @click="stopScraper('firstview')" class="action-btn stop">
            ⏹️ Stop
          </button>
          <button v-else-if="startingScrapers['firstview']" class="action-btn starting" disabled>
            ⏳ Starting...
          </button>
          <button v-else @click="startScraper('firstview')" class="action-btn start">
            ▶️ Start
          </button>
          <button @click="viewLogs('firstview')" class="action-btn logs">
            📜 Logs
          </button>
        </div>
      </div>

      <!-- AO3 -->
      <div class="scraper-card" :class="{ active: scrapers.ao3.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">✍️</span>
            <div>
              <h2>Archive of Our Own</h2>
              <span class="source-url">archiveofourown.org</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.ao3.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.ao3.running ? 'Active' : 'Idle' }}
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-icon">🔍</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.ao3.indexed.toLocaleString() }}</span>
              <span class="stat-label">Indexed</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">✅</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.ao3.downloaded.toLocaleString() }}</span>
              <span class="stat-label">Downloaded</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">📋</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.ao3.pending.toLocaleString() }}</span>
              <span class="stat-label">Remaining</span>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚡</span>
            <div class="stat-content">
              <span class="stat-number">{{ scrapers.ao3.processed.toLocaleString() }}</span>
              <span class="stat-label">Processed</span>
            </div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span>Download Progress</span>
            <span class="progress-percent">{{ getProgress(scrapers.ao3).toFixed(1) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill ao3" :style="{ width: getProgress(scrapers.ao3) + '%' }"></div>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="scrapers.ao3.running" @click="stopScraper('ao3')" class="action-btn stop">
            ⏹️ Stop
          </button>
          <button v-else-if="startingScrapers['ao3']" class="action-btn starting" disabled>
            ⏳ Starting...
          </button>
          <button v-else @click="startScraper('ao3')" class="action-btn start">
            ▶️ Start
          </button>
          <button @click="viewLogs('ao3')" class="action-btn logs">
            📜 Logs
          </button>
        </div>
      </div>

      <!-- Dark Psychology (PRIMARY) -->
      <div class="scraper-card featured" :class="{ active: scrapers.darkpsych.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">🧠</span>
            <div>
              <h2>Dark Psychology</h2>
              <span class="source-url">manipulation, control, trauma</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.darkpsych.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.darkpsych.running ? 'Active' : 'Idle' }}
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-item"><span class="stat-icon">🔍</span><div class="stat-content"><span class="stat-number">{{ scrapers.darkpsych.indexed.toLocaleString() }}</span><span class="stat-label">Indexed</span></div></div>
          <div class="stat-item"><span class="stat-icon">✅</span><div class="stat-content"><span class="stat-number">{{ scrapers.darkpsych.downloaded.toLocaleString() }}</span><span class="stat-label">Downloaded</span></div></div>
          <div class="stat-item"><span class="stat-icon">📋</span><div class="stat-content"><span class="stat-number">{{ scrapers.darkpsych.pending.toLocaleString() }}</span><span class="stat-label">Remaining</span></div></div>
          <div class="stat-item"><span class="stat-icon">⚡</span><div class="stat-content"><span class="stat-number">{{ scrapers.darkpsych.processed.toLocaleString() }}</span><span class="stat-label">Processed</span></div></div>
        </div>
        <div class="progress-section">
          <div class="progress-header"><span>Progress</span><span class="progress-percent">{{ getProgress(scrapers.darkpsych).toFixed(1) }}%</span></div>
          <div class="progress-track"><div class="progress-fill darkpsych" :style="{ width: getProgress(scrapers.darkpsych) + '%' }"></div></div>
        </div>
        <div class="card-actions">
          <button v-if="scrapers.darkpsych.running" @click="stopScraper('darkpsych')" class="action-btn stop">⏹️ Stop</button>
          <button v-else-if="startingScrapers['darkpsych']" class="action-btn starting" disabled>⏳ Starting...</button>
          <button v-else @click="startScraper('darkpsych')" class="action-btn start">▶️ Start</button>
          <button @click="viewLogs('darkpsych')" class="action-btn logs">📜 Logs</button>
        </div>
      </div>

      <!-- Literotica -->
      <div class="scraper-card" :class="{ active: scrapers.literotica.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">📚</span>
            <div>
              <h2>Literotica</h2>
              <span class="source-url">literotica.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.literotica.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.literotica.running ? 'Active' : 'Idle' }}
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-item"><span class="stat-icon">🔍</span><div class="stat-content"><span class="stat-number">{{ scrapers.literotica.indexed.toLocaleString() }}</span><span class="stat-label">Indexed</span></div></div>
          <div class="stat-item"><span class="stat-icon">✅</span><div class="stat-content"><span class="stat-number">{{ scrapers.literotica.downloaded.toLocaleString() }}</span><span class="stat-label">Downloaded</span></div></div>
          <div class="stat-item"><span class="stat-icon">📋</span><div class="stat-content"><span class="stat-number">{{ scrapers.literotica.pending.toLocaleString() }}</span><span class="stat-label">Remaining</span></div></div>
          <div class="stat-item"><span class="stat-icon">⚡</span><div class="stat-content"><span class="stat-number">{{ scrapers.literotica.processed.toLocaleString() }}</span><span class="stat-label">Processed</span></div></div>
        </div>
        <div class="progress-section">
          <div class="progress-header"><span>Progress</span><span class="progress-percent">{{ getProgress(scrapers.literotica).toFixed(1) }}%</span></div>
          <div class="progress-track"><div class="progress-fill literotica" :style="{ width: getProgress(scrapers.literotica) + '%' }"></div></div>
        </div>
        <div class="card-actions">
          <button v-if="scrapers.literotica.running" @click="stopScraper('literotica')" class="action-btn stop">⏹️ Stop</button>
          <button v-else-if="startingScrapers['literotica']" class="action-btn starting" disabled>⏳ Starting...</button>
          <button v-else @click="startScraper('literotica')" class="action-btn start">▶️ Start</button>
          <button @click="viewLogs('literotica')" class="action-btn logs">📜 Logs</button>
        </div>
      </div>

      <!-- Reddit RP -->
      <div class="scraper-card" :class="{ active: scrapers.reddit.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">🎭</span>
            <div>
              <h2>Reddit Roleplay</h2>
              <span class="source-url">r/DirtyPenPals etc</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.reddit.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.reddit.running ? 'Active' : 'Idle' }}
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-item"><span class="stat-icon">🔍</span><div class="stat-content"><span class="stat-number">{{ scrapers.reddit.indexed.toLocaleString() }}</span><span class="stat-label">Indexed</span></div></div>
          <div class="stat-item"><span class="stat-icon">✅</span><div class="stat-content"><span class="stat-number">{{ scrapers.reddit.downloaded.toLocaleString() }}</span><span class="stat-label">Downloaded</span></div></div>
          <div class="stat-item"><span class="stat-icon">📋</span><div class="stat-content"><span class="stat-number">{{ scrapers.reddit.pending.toLocaleString() }}</span><span class="stat-label">Remaining</span></div></div>
          <div class="stat-item"><span class="stat-icon">⚡</span><div class="stat-content"><span class="stat-number">{{ scrapers.reddit.processed.toLocaleString() }}</span><span class="stat-label">Processed</span></div></div>
        </div>
        <div class="progress-section">
          <div class="progress-header"><span>Progress</span><span class="progress-percent">{{ getProgress(scrapers.reddit).toFixed(1) }}%</span></div>
          <div class="progress-track"><div class="progress-fill reddit" :style="{ width: getProgress(scrapers.reddit) + '%' }"></div></div>
        </div>
        <div class="card-actions">
          <button v-if="scrapers.reddit.running" @click="stopScraper('reddit')" class="action-btn stop">⏹️ Stop</button>
          <button v-else-if="startingScrapers['reddit']" class="action-btn starting" disabled>⏳ Starting...</button>
          <button v-else @click="startScraper('reddit')" class="action-btn start">▶️ Start</button>
          <button @click="viewLogs('reddit')" class="action-btn logs">📜 Logs</button>
        </div>
      </div>

      <!-- F-List -->
      <div class="scraper-card" :class="{ active: scrapers.flist.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">👤</span>
            <div>
              <h2>F-List Characters</h2>
              <span class="source-url">f-list.net</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.flist.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.flist.running ? 'Active' : 'Idle' }}
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-item"><span class="stat-icon">🔍</span><div class="stat-content"><span class="stat-number">{{ scrapers.flist.indexed.toLocaleString() }}</span><span class="stat-label">Indexed</span></div></div>
          <div class="stat-item"><span class="stat-icon">✅</span><div class="stat-content"><span class="stat-number">{{ scrapers.flist.downloaded.toLocaleString() }}</span><span class="stat-label">Downloaded</span></div></div>
          <div class="stat-item"><span class="stat-icon">📋</span><div class="stat-content"><span class="stat-number">{{ scrapers.flist.pending.toLocaleString() }}</span><span class="stat-label">Remaining</span></div></div>
          <div class="stat-item"><span class="stat-icon">⚡</span><div class="stat-content"><span class="stat-number">{{ scrapers.flist.processed.toLocaleString() }}</span><span class="stat-label">Processed</span></div></div>
        </div>
        <div class="progress-section">
          <div class="progress-header"><span>Progress</span><span class="progress-percent">{{ getProgress(scrapers.flist).toFixed(1) }}%</span></div>
          <div class="progress-track"><div class="progress-fill flist" :style="{ width: getProgress(scrapers.flist) + '%' }"></div></div>
        </div>
        <div class="card-actions">
          <button v-if="scrapers.flist.running" @click="stopScraper('flist')" class="action-btn stop">⏹️ Stop</button>
          <button v-else-if="startingScrapers['flist']" class="action-btn starting" disabled>⏳ Starting...</button>
          <button v-else @click="startScraper('flist')" class="action-btn start">▶️ Start</button>
          <button @click="viewLogs('flist')" class="action-btn logs">📜 Logs</button>
        </div>
      </div>

      <!-- GQ/Esquire -->
      <div class="scraper-card" :class="{ active: scrapers.gq.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">🎩</span>
            <div>
              <h2>GQ / Esquire</h2>
              <span class="source-url">gq.com, esquire.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.gq.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.gq.running ? 'Active' : 'Idle' }}
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-item"><span class="stat-icon">🔍</span><div class="stat-content"><span class="stat-number">{{ scrapers.gq.indexed.toLocaleString() }}</span><span class="stat-label">Indexed</span></div></div>
          <div class="stat-item"><span class="stat-icon">✅</span><div class="stat-content"><span class="stat-number">{{ scrapers.gq.downloaded.toLocaleString() }}</span><span class="stat-label">Downloaded</span></div></div>
          <div class="stat-item"><span class="stat-icon">📋</span><div class="stat-content"><span class="stat-number">{{ scrapers.gq.pending.toLocaleString() }}</span><span class="stat-label">Remaining</span></div></div>
          <div class="stat-item"><span class="stat-icon">⚡</span><div class="stat-content"><span class="stat-number">{{ scrapers.gq.processed.toLocaleString() }}</span><span class="stat-label">Processed</span></div></div>
        </div>
        <div class="progress-section">
          <div class="progress-header"><span>Progress</span><span class="progress-percent">{{ getProgress(scrapers.gq).toFixed(1) }}%</span></div>
          <div class="progress-track"><div class="progress-fill gq" :style="{ width: getProgress(scrapers.gq) + '%' }"></div></div>
        </div>
        <div class="card-actions">
          <button v-if="scrapers.gq.running" @click="stopScraper('gq')" class="action-btn stop">⏹️ Stop</button>
          <button v-else-if="startingScrapers['gq']" class="action-btn starting" disabled>⏳ Starting...</button>
          <button v-else @click="startScraper('gq')" class="action-btn start">▶️ Start</button>
          <button @click="viewLogs('gq')" class="action-btn logs">📜 Logs</button>
        </div>
      </div>

      <!-- The Cut -->
      <div class="scraper-card" :class="{ active: scrapers.thecut.running }">
        <div class="card-header">
          <div class="source-info">
            <span class="source-emoji">✂️</span>
            <div>
              <h2>The Cut</h2>
              <span class="source-url">thecut.com</span>
            </div>
          </div>
          <div class="status-indicator" :class="scrapers.thecut.running ? 'running' : 'stopped'">
            <span class="status-dot"></span>
            {{ scrapers.thecut.running ? 'Active' : 'Idle' }}
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-item"><span class="stat-icon">🔍</span><div class="stat-content"><span class="stat-number">{{ scrapers.thecut.indexed.toLocaleString() }}</span><span class="stat-label">Indexed</span></div></div>
          <div class="stat-item"><span class="stat-icon">✅</span><div class="stat-content"><span class="stat-number">{{ scrapers.thecut.downloaded.toLocaleString() }}</span><span class="stat-label">Downloaded</span></div></div>
          <div class="stat-item"><span class="stat-icon">📋</span><div class="stat-content"><span class="stat-number">{{ scrapers.thecut.pending.toLocaleString() }}</span><span class="stat-label">Remaining</span></div></div>
          <div class="stat-item"><span class="stat-icon">⚡</span><div class="stat-content"><span class="stat-number">{{ scrapers.thecut.processed.toLocaleString() }}</span><span class="stat-label">Processed</span></div></div>
        </div>
        <div class="progress-section">
          <div class="progress-header"><span>Progress</span><span class="progress-percent">{{ getProgress(scrapers.thecut).toFixed(1) }}%</span></div>
          <div class="progress-track"><div class="progress-fill thecut" :style="{ width: getProgress(scrapers.thecut) + '%' }"></div></div>
        </div>
        <div class="card-actions">
          <button v-if="scrapers.thecut.running" @click="stopScraper('thecut')" class="action-btn stop">⏹️ Stop</button>
          <button v-else-if="startingScrapers['thecut']" class="action-btn starting" disabled>⏳ Starting...</button>
          <button v-else @click="startScraper('thecut')" class="action-btn start">▶️ Start</button>
          <button @click="viewLogs('thecut')" class="action-btn logs">📜 Logs</button>
        </div>
      </div>
    </div>

    <!-- Live Activity Feed -->
    <div class="activity-section">
      <div class="activity-header">
        <h2>⚡ Live Activity</h2>
        <span class="activity-pulse" :class="{ active: hasActiveScrapers }"></span>
      </div>

      <div class="activity-feed">
        <!-- Current Processing -->
        <div v-for="item in liveActivity" :key="item.id" class="activity-item" :class="item.type">
          <div class="activity-icon">
            <span v-if="item.type === 'current'">🔄</span>
            <span v-else-if="item.type === 'success'">✅</span>
            <span v-else-if="item.type === 'error'">⚠️</span>
            <span v-else>📋</span>
          </div>
          <div class="activity-content">
            <span class="activity-source" :class="item.source">{{ item.source }}</span>
            <span class="activity-title">{{ item.title }}</span>
            <span v-if="item.details" class="activity-details">{{ item.details }}</span>
          </div>
          <span class="activity-time">{{ item.time }}</span>
        </div>

        <div v-if="liveActivity.length === 0" class="activity-empty">
          <span>No active scrapers</span>
        </div>
      </div>
    </div>

    <!-- Training Data Section -->
    <div class="training-section">
      <h2>🧠 Training Data Overview</h2>
      <div class="training-cards">
        <div class="training-card">
          <div class="training-icon">📝</div>
          <div class="training-value">{{ estimatedWords }}</div>
          <div class="training-label">Est. Words</div>
        </div>
        <div class="training-card">
          <div class="training-icon">🎯</div>
          <div class="training-value">{{ estimatedTokens }}</div>
          <div class="training-label">Est. Tokens</div>
        </div>
        <div class="training-card">
          <div class="training-icon">💾</div>
          <div class="training-value">{{ estimatedSize }}</div>
          <div class="training-label">Est. Size</div>
        </div>
        <div class="training-card">
          <div class="training-icon">📈</div>
          <div class="training-value">{{ processingRate }}</div>
          <div class="training-label">Rate</div>
        </div>
      </div>
    </div>

    <!-- Log Viewer Modal -->
    <Teleport to="body">
      <div v-if="showLogViewer" class="modal-overlay" @click.self="showLogViewer = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>📜 {{ currentLogSource }} Logs</h3>
            <button @click="showLogViewer = false" class="close-btn">✕</button>
          </div>
          <div class="modal-body">
            <pre>{{ currentLogs }}</pre>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'

interface ScraperStats {
  running: boolean
  pid: number | null
  indexed: number
  downloaded: number
  pending: number
  processed: number
  limit: number
}

const loading = ref(false)
const showLogViewer = ref(false)
const currentLogSource = ref('')
const currentLogs = ref('')
const startingScrapers = ref<Record<string, boolean>>({}) // Track which scrapers are being started

// Live activity feed
interface ActivityItem {
  id: string
  type: 'current' | 'success' | 'error' | 'pending'
  source: string
  title: string
  details?: string
  time: string
}

const liveActivity = ref<ActivityItem[]>([])

const hasActiveScrapers = computed(() =>
  Object.values(scrapers.value).some(s => s.running)
)

const scrapers = ref<Record<string, ScraperStats>>({
  // Fashion/Media scrapers
  nifty: { running: false, pid: null, indexed: 64553, downloaded: 24597, pending: 39956, processed: 9016, limit: 100000 },
  vmag: { running: false, pid: null, indexed: 11392, downloaded: 3871, pending: 7521, processed: 0, limit: 50000 },
  wmag: { running: false, pid: null, indexed: 36094, downloaded: 2681, pending: 33413, processed: 0, limit: 50000 },
  wwd: { running: false, pid: null, indexed: 247181, downloaded: 2709, pending: 244472, processed: 0, limit: 300000 },
  firstview: { running: false, pid: null, indexed: 800, downloaded: 0, pending: 800, processed: 0, limit: 100000 },
  gq: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 50000 },
  thecut: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 50000 },
  // Roleplay scrapers
  ao3: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 100000 },
  darkpsych: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 500000 },
  literotica: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 100000 },
  reddit: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 50000 },
  flist: { running: false, pid: null, indexed: 0, downloaded: 0, pending: 0, processed: 0, limit: 20000 },
})

// Computed totals
const totalIndexed = computed(() =>
  Object.values(scrapers.value).reduce((sum, s) => sum + s.indexed, 0)
)
const totalDownloaded = computed(() =>
  Object.values(scrapers.value).reduce((sum, s) => sum + s.downloaded, 0)
)
const totalPending = computed(() =>
  Object.values(scrapers.value).reduce((sum, s) => sum + s.pending, 0)
)
const totalProcessed = computed(() =>
  Object.values(scrapers.value).reduce((sum, s) => sum + s.processed, 0)
)

const estimatedWords = computed(() => {
  const avgWords = 2500
  const total = totalDownloaded.value * avgWords
  if (total >= 1000000000) return (total / 1000000000).toFixed(1) + 'B'
  if (total >= 1000000) return (total / 1000000).toFixed(1) + 'M'
  if (total >= 1000) return (total / 1000).toFixed(1) + 'K'
  return total.toString()
})

const estimatedTokens = computed(() => {
  const avgWords = 2500
  const tokensPerWord = 1.3
  const total = totalDownloaded.value * avgWords * tokensPerWord
  if (total >= 1000000000) return (total / 1000000000).toFixed(1) + 'B'
  if (total >= 1000000) return (total / 1000000).toFixed(1) + 'M'
  if (total >= 1000) return (total / 1000).toFixed(1) + 'K'
  return total.toString()
})

const estimatedSize = computed(() => {
  const avgBytes = 15000 // ~15KB per article
  const total = totalDownloaded.value * avgBytes
  if (total >= 1000000000) return (total / 1000000000).toFixed(1) + ' GB'
  if (total >= 1000000) return (total / 1000000).toFixed(0) + ' MB'
  if (total >= 1000) return (total / 1000).toFixed(0) + ' KB'
  return total + ' B'
})

const processingRate = computed(() => {
  const processed = totalProcessed.value
  const downloaded = totalDownloaded.value
  if (downloaded === 0) return '0%'
  return ((processed / downloaded) * 100).toFixed(1) + '%'
})

function getProgress(scraper: ScraperStats): number {
  if (scraper.indexed === 0) return 0
  return (scraper.downloaded / scraper.indexed) * 100
}

let refreshInterval: number | null = null

async function refreshAll() {
  loading.value = true

  try {
    const status = await invoke<any>('get_scraper_status')
    if (status) {
      Object.assign(scrapers.value, status)
    }
  } catch (e) {
    // Use shell fallback
    await refreshViaShell()
  }

  loading.value = false
}

async function refreshViaShell() {
  // Check for running scraper processes
  try {
    const result = await invoke<string>('execute_shell', {
      command: "ps aux | grep -E 'ripper.py|_ripper' | grep -v grep | awk '{print $NF}'"
    })

    // Reset all to not running first
    for (const name of Object.keys(scrapers.value)) {
      scrapers.value[name] = { ...scrapers.value[name], running: false }
    }

    // Mark matching scrapers as running
    const running = result?.split('\n').filter(Boolean) || []
    for (const line of running) {
      if (line.includes('nifty_ripper')) scrapers.value.nifty.running = true
      if (line.includes('vmag_ripper')) scrapers.value.vmag.running = true
      if (line.includes('wmag_ripper')) scrapers.value.wmag.running = true
      if (line.includes('wwd_ripper')) scrapers.value.wwd.running = true
      if (line.includes('firstview_ripper')) scrapers.value.firstview.running = true
      if (line.includes('ao3_roleplay_ripper')) scrapers.value.ao3.running = true
      if (line.includes('dark_psych_ripper')) scrapers.value.darkpsych.running = true
      if (line.includes('literotica_ripper')) scrapers.value.literotica.running = true
      if (line.includes('reddit_roleplay_ripper')) scrapers.value.reddit.running = true
      if (line.includes('flist_ripper')) scrapers.value.flist.running = true
      if (line.includes('gq_esquire_ripper')) scrapers.value.gq.running = true
      if (line.includes('thecut_ripper')) scrapers.value.thecut.running = true
    }
  } catch (e) {
    console.error('Failed to check scraper status:', e)
  }
}

// Scraper script paths and configs
const scraperConfigs: Record<string, { path: string, logDir: string }> = {
  nifty: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/nifty_ripper.py',
    logDir: '/Volumes/David External/nifty_archive/logs'
  },
  vmag: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/vmag_ripper.py',
    logDir: '/Volumes/#1/vmag_archive/logs'
  },
  wmag: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/wmag_ripper.py',
    logDir: '/Volumes/#1/wmag_archive/logs'
  },
  wwd: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/wwd_ripper.py',
    logDir: '/Volumes/#1/wwd_archive/logs'
  },
  firstview: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/firstview_ripper.py',
    logDir: '/Volumes/David External/firstview_archive/logs'
  },
  ao3: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/ao3_roleplay_ripper.py',
    logDir: '/Volumes/David External/ao3_roleplay/logs'
  },
  darkpsych: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/dark_psych_ripper.py',
    logDir: '/Volumes/David External/dark_psych_archive/logs'
  },
  literotica: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/literotica_ripper.py',
    logDir: '/Volumes/David External/literotica_archive/logs'
  },
  reddit: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/reddit_roleplay_ripper.py',
    logDir: '/Volumes/David External/reddit_roleplay/logs'
  },
  flist: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/flist_ripper.py',
    logDir: '/Volumes/David External/flist_archive/logs'
  },
  gq: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/gq_esquire_ripper.py',
    logDir: '/Volumes/David External/gq_esquire_archive/logs'
  },
  thecut: {
    path: '/Users/davidquinton/ReverseLab/SAM/scrapers/thecut_ripper.py',
    logDir: '/Volumes/David External/thecut_archive/logs'
  },
}

async function startScraper(name: string) {
  const config = scraperConfigs[name]
  if (!config) {
    console.error(`Unknown scraper: ${name}`)
    alert(`Unknown scraper: ${name}`)
    return
  }

  // Check if already running or starting
  if (scrapers.value[name]?.running || startingScrapers.value[name]) {
    console.log(`Scraper ${name} is already running or starting`)
    return
  }

  // Mark as starting for visual feedback
  startingScrapers.value[name] = true
  console.log(`Starting scraper: ${name}`, config)

  try {
    const pythonPath = '/Users/davidquinton/ReverseLab/SAM/scrapers/.venv/bin/python3'
    const logFile = `${config.logDir}/scraper.log`
    const command = `mkdir -p '${config.logDir}' && nohup '${pythonPath}' '${config.path}' download >> '${logFile}' 2>&1 &`

    console.log('Executing:', command)
    const result = await invoke<string>('execute_shell', { command })
    console.log('Result:', result)

    // Update status immediately
    scrapers.value[name].running = true

    // Add to activity feed
    liveActivity.value.unshift({
      id: `start-${Date.now()}`,
      type: 'success',
      source: name,
      title: 'Scraper started',
      time: new Date().toLocaleTimeString()
    })

    // Refresh to confirm actual status
    setTimeout(() => refreshAll(), 2000)
  } catch (e: any) {
    console.error('Failed to start scraper:', e)
    alert(`Failed to start ${name}: ${e?.message || String(e)}`)
    liveActivity.value.unshift({
      id: `error-${Date.now()}`,
      type: 'error',
      source: name,
      title: `Failed: ${e?.message || String(e)}`,
      time: new Date().toLocaleTimeString()
    })
  } finally {
    startingScrapers.value[name] = false
  }
}

async function stopScraper(name: string) {
  const config = scraperConfigs[name]
  if (!config) {
    console.error(`Unknown scraper: ${name}`)
    return
  }

  try {
    // Kill the scraper process
    const scriptName = config.path.split('/').pop()
    const command = `pkill -f "${scriptName}" 2>/dev/null || true`
    await invoke('execute_shell', { command })

    // Update status
    scrapers.value[name] = { ...scrapers.value[name], running: false, pid: null }
  } catch (e) {
    console.error('Failed to stop scraper:', e)
  }
}

// Log paths derived from configs
const getLogPath = (name: string) => {
  const config = scraperConfigs[name]
  return config ? `${config.logDir}/scraper.log` : ''
}

async function viewLogs(name: string) {
  currentLogSource.value = name
  const logPath = getLogPath(name)

  try {
    // Try Tauri command first, fall back to shell
    const logs = await invoke<string>('read_file_tail', { path: logPath, lines: 100 })
    currentLogs.value = logs || 'No logs available'
  } catch (e) {
    // Fallback: try reading via shell command
    try {
      const result = await invoke<string>('execute_shell', {
        command: `tail -100 "${logPath}" 2>/dev/null || echo "Log file not found: ${logPath}"`
      })
      currentLogs.value = result || 'No logs available'
    } catch (e2) {
      currentLogs.value = `Log path: ${logPath}\n\nUnable to read logs. The scraper may not have started yet or the log file doesn't exist.`
    }
  }
  showLogViewer.value = true
}

async function fetchLiveActivity() {
  const activity: ActivityItem[] = []

  // Parse recent log entries from active scrapers
  for (const [name, scraper] of Object.entries(scrapers.value)) {
    if (!scraper.running) continue

    const logPath = getLogPath(name)
    try {
      const result = await invoke<string>('execute_shell', {
        command: `tail -5 "${logPath}" 2>/dev/null`
      })

      if (result) {
        const lines = result.trim().split('\n')
        for (const line of lines.slice(-3)) {
          // Parse log line: 2026-01-15 19:28:30,592 [INFO] Downloaded: title (words)
          const match = line.match(/(\d{2}:\d{2}:\d{2}).*\[(INFO|WARNING|ERROR)\]\s*(.+)/)
          if (match) {
            const [, time, level, message] = match

            let type: ActivityItem['type'] = 'success'
            if (level === 'WARNING') type = 'error'
            if (message.includes('Processing:')) type = 'current'

            activity.push({
              id: `${name}-${Date.now()}-${Math.random()}`,
              type,
              source: name,
              title: message.slice(0, 60) + (message.length > 60 ? '...' : ''),
              time
            })
          }
        }
      }
    } catch (e) {
      // Silently ignore - scraper might not have logs yet
    }
  }

  // Sort by time descending and limit to 10
  liveActivity.value = activity.slice(0, 10)
}

let activityInterval: number | null = null

onMounted(() => {
  refreshAll()
  fetchLiveActivity()
  refreshInterval = window.setInterval(refreshAll, 30000)
  activityInterval = window.setInterval(fetchLiveActivity, 5000) // Refresh activity every 5s
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (activityInterval) {
    clearInterval(activityInterval)
  }
})
</script>

<style scoped>
.scraper-dashboard {
  padding: 24px;
  background: #0f0f0f;
  min-height: 100vh;
  max-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  color: #f5f5f7;
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Subtle ambient glow - barely visible */
.scraper-dashboard::before {
  content: '';
  position: fixed;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(ellipse at 30% 20%, rgba(255, 255, 255, 0.01) 0%, transparent 50%),
              radial-gradient(ellipse at 70% 80%, rgba(255, 255, 255, 0.008) 0%, transparent 50%);
  animation: ambientShift 30s ease-in-out infinite;
}

@keyframes ambientShift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(1%, 1%); }
}

/* Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
  margin-bottom: 32px;
}

.header-content h1 {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  letter-spacing: -0.5px;
}

.subtitle {
  color: #86868b;
  font-size: 14px;
  margin: 4px 0 0 0;
}

.refresh-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.04);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: scale(1.05);
}

.refresh-btn.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Summary Row */
.summary-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  position: relative;
  z-index: 1;
  margin-bottom: 32px;
}

.summary-card {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.01) 100%
  );
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.summary-card:hover {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.05) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border-color: rgba(255, 255, 255, 0.1);
}

.summary-card.highlight {
  background: linear-gradient(
    135deg,
    rgba(94, 92, 230, 0.04) 0%,
    rgba(94, 92, 230, 0.01) 100%
  );
  border-color: rgba(94, 92, 230, 0.12);
}

.summary-emoji {
  font-size: 32px;
}

.summary-data {
  display: flex;
  flex-direction: column;
}

.summary-value {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.5px;
}

.summary-label {
  font-size: 12px;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Scrapers Grid */
.scrapers-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

/* Liquid Glass Cards - frosted glass effect */
.scraper-card {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.04) 0%,
    rgba(255, 255, 255, 0.01) 50%,
    rgba(255, 255, 255, 0.03) 100%
  );
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: 20px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s ease;
  position: relative;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.scraper-card:hover {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.06) 0%,
    rgba(255, 255, 255, 0.02) 50%,
    rgba(255, 255, 255, 0.05) 100%
  );
  border-color: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.scraper-card.active {
  border-color: rgba(48, 209, 88, 0.4);
  box-shadow: 0 0 20px rgba(48, 209, 88, 0.15), 0 4px 30px rgba(0, 0, 0, 0.1);
}

/* Featured card - subtle accent */
.scraper-card.featured {
  border-color: rgba(220, 38, 38, 0.25);
  box-shadow: 0 0 25px rgba(220, 38, 38, 0.08), 0 4px 30px rgba(0, 0, 0, 0.1);
}

.scraper-card.featured:hover {
  border-color: rgba(220, 38, 38, 0.35);
  box-shadow: 0 0 30px rgba(220, 38, 38, 0.12), 0 8px 32px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.source-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.source-emoji {
  font-size: 28px;
}

.source-info h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.source-url {
  font-size: 11px;
  color: #86868b;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 16px;
  font-weight: 500;
}

.status-indicator.running {
  background: rgba(48, 209, 88, 0.08);
  color: #30d158;
}

.status-indicator.stopped {
  background: rgba(142, 142, 147, 0.08);
  color: #8e8e93;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-indicator.running .status-dot {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Compact Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  background: rgba(255, 255, 255, 0.008);
  border-radius: 10px;
}

.stat-icon {
  font-size: 14px;
}

.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-number {
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 9px;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.2px;
}

/* Progress Section */
.progress-section {
  margin-bottom: 12px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #86868b;
  margin-bottom: 6px;
}

.progress-percent {
  font-weight: 600;
  color: #f5f5f7;
}

.progress-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-fill.nifty {
  background: linear-gradient(90deg, #ff6b6b, #ffa502);
}

.progress-fill.vmag {
  background: linear-gradient(90deg, #a855f7, #6366f1);
}

.progress-fill.wmag {
  background: linear-gradient(90deg, #06b6d4, #3b82f6);
}

.progress-fill.wwd {
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.progress-fill.firstview {
  background: linear-gradient(90deg, #ec4899, #8b5cf6);
}

.progress-fill.ao3 {
  background: linear-gradient(90deg, #22c55e, #14b8a6);
}

.progress-fill.darkpsych {
  background: linear-gradient(90deg, #dc2626, #7c2d12);
}

.progress-fill.literotica {
  background: linear-gradient(90deg, #f97316, #ea580c);
}

.progress-fill.reddit {
  background: linear-gradient(90deg, #ff4500, #ff6b35);
}

.progress-fill.flist {
  background: linear-gradient(90deg, #8b5cf6, #7c3aed);
}

.progress-fill.gq {
  background: linear-gradient(90deg, #0ea5e9, #0284c7);
}

.progress-fill.thecut {
  background: linear-gradient(90deg, #f43f5e, #e11d48);
}

/* Card Actions */
.card-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.action-btn.start {
  background: rgba(48, 209, 88, 0.12);
  color: #30d158;
}

.action-btn.start:hover {
  background: rgba(48, 209, 88, 0.2);
}

.action-btn.stop {
  background: rgba(255, 69, 58, 0.12);
  color: #ff453a;
}

.action-btn.stop:hover {
  background: rgba(255, 69, 58, 0.2);
}

.action-btn.logs {
  background: rgba(255, 255, 255, 0.06);
  color: #f5f5f7;
}

.action-btn.logs:hover {
  background: rgba(255, 255, 255, 0.1);
}

.action-btn.starting {
  background: rgba(255, 204, 0, 0.15);
  color: #ffcc00;
  cursor: wait;
  animation: pulse-starting 1.5s ease-in-out infinite;
}

@keyframes pulse-starting {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Training Section */
.training-section {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.01) 100%
  );
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.training-section h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
}

.training-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.training-card {
  text-align: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.005);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.02);
}

.training-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.training-value {
  font-size: 24px;
  font-weight: 600;
  color: #5e5ce6;
  margin-bottom: 4px;
}

.training-label {
  font-size: 12px;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Live Activity Feed */
.activity-section {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.01) 100%
  );
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.activity-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.activity-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.activity-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #8e8e93;
}

.activity-pulse.active {
  background: #30d158;
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(48, 209, 88, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(48, 209, 88, 0); }
}

.activity-feed {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.01);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.activity-item:hover {
  background: rgba(255, 255, 255, 0.02);
}

.activity-item.current {
  border-left: 3px solid #5e5ce6;
}

.activity-item.success {
  border-left: 3px solid #30d158;
}

.activity-item.error {
  border-left: 3px solid #ff9500;
}

.activity-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.activity-source {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
}

.activity-source.nifty { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
.activity-source.vmag { background: rgba(168, 85, 247, 0.2); color: #a855f7; }
.activity-source.wmag { background: rgba(6, 182, 212, 0.2); color: #06b6d4; }
.activity-source.wwd { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.activity-source.firstview { background: rgba(236, 72, 153, 0.2); color: #ec4899; }
.activity-source.ao3 { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
.activity-source.darkpsych { background: rgba(220, 38, 38, 0.2); color: #dc2626; }
.activity-source.literotica { background: rgba(249, 115, 22, 0.2); color: #f97316; }
.activity-source.reddit { background: rgba(255, 69, 0, 0.2); color: #ff4500; }
.activity-source.flist { background: rgba(139, 92, 246, 0.2); color: #8b5cf6; }
.activity-source.gq { background: rgba(14, 165, 233, 0.2); color: #0ea5e9; }
.activity-source.thecut { background: rgba(244, 63, 94, 0.2); color: #f43f5e; }

.activity-title {
  font-size: 13px;
  color: #f5f5f7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-details {
  font-size: 11px;
  color: #86868b;
}

.activity-time {
  font-size: 11px;
  color: #86868b;
  font-family: 'SF Mono', monospace;
  flex-shrink: 0;
}

.activity-empty {
  text-align: center;
  padding: 24px;
  color: #86868b;
  font-size: 14px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: rgba(28, 28, 30, 0.95);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border-radius: 16px;
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #f5f5f7;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.modal-body {
  flex: 1;
  overflow: auto;
  padding: 20px 24px;
}

.modal-body pre {
  margin: 0;
  font-family: 'SF Mono', Monaco, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  color: #98989d;
}

/* Responsive */
@media (max-width: 1200px) {
  .scrapers-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .summary-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .training-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
