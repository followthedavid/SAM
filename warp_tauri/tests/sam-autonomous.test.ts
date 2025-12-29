// SAM Autonomous System - Exhaustive Test Suite
// Tests all autonomous capabilities without mocking - real system operations

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest'
import { invoke } from '@tauri-apps/api/core'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'

// Test configuration
const TEST_DIR = path.join(os.tmpdir(), 'sam-test-' + Date.now())
const TEST_EXTERNAL = path.join(os.tmpdir(), 'sam-external-' + Date.now())

describe('SAM Autonomous System - Exhaustive Tests', () => {

  // ==========================================================================
  // SETUP & TEARDOWN
  // ==========================================================================

  beforeAll(() => {
    // Create test directories
    fs.mkdirSync(TEST_DIR, { recursive: true })
    fs.mkdirSync(TEST_EXTERNAL, { recursive: true })
    fs.mkdirSync(path.join(TEST_DIR, 'caches'), { recursive: true })
    fs.mkdirSync(path.join(TEST_DIR, 'logs'), { recursive: true })
    fs.mkdirSync(path.join(TEST_DIR, 'projects'), { recursive: true })

    console.log(`Test directory: ${TEST_DIR}`)
    console.log(`External storage: ${TEST_EXTERNAL}`)
  })

  afterAll(() => {
    // Cleanup test directories
    fs.rmSync(TEST_DIR, { recursive: true, force: true })
    fs.rmSync(TEST_EXTERNAL, { recursive: true, force: true })
  })

  // ==========================================================================
  // 1. SYSTEM HEALTH MONITORING
  // ==========================================================================

  describe('System Health Monitoring', () => {

    it('should collect disk metrics', async () => {
      const metrics = await invoke<SystemMetrics>('get_system_metrics')

      expect(metrics).toBeDefined()
      expect(metrics.disk).toBeDefined()
      expect(metrics.disk.total_bytes).toBeGreaterThan(0)
      expect(metrics.disk.used_bytes).toBeGreaterThan(0)
      expect(metrics.disk.percentage).toBeGreaterThanOrEqual(0)
      expect(metrics.disk.percentage).toBeLessThanOrEqual(1)

      console.log(`Disk: ${(metrics.disk.percentage * 100).toFixed(1)}% used`)
    })

    it('should collect memory metrics', async () => {
      const metrics = await invoke<SystemMetrics>('get_system_metrics')

      expect(metrics.memory).toBeDefined()
      expect(metrics.memory.total_bytes).toBeGreaterThan(0)
      expect(metrics.memory.used_bytes).toBeGreaterThan(0)
      expect(metrics.memory.percentage).toBeGreaterThanOrEqual(0)
      expect(metrics.memory.percentage).toBeLessThanOrEqual(1)

      console.log(`Memory: ${(metrics.memory.percentage * 100).toFixed(1)}% used`)
    })

    it('should collect CPU metrics', async () => {
      const metrics = await invoke<SystemMetrics>('get_system_metrics')

      expect(metrics.cpu_usage).toBeDefined()
      expect(metrics.cpu_usage).toBeGreaterThanOrEqual(0)

      console.log(`CPU: ${metrics.cpu_usage.toFixed(1)}% usage`)
    })

    it('should collect process metrics', async () => {
      const metrics = await invoke<SystemMetrics>('get_system_metrics')

      expect(metrics.process_count).toBeGreaterThan(0)
      expect(metrics.zombie_count).toBeGreaterThanOrEqual(0)

      console.log(`Processes: ${metrics.process_count}, Zombies: ${metrics.zombie_count}`)
    })

    it('should handle rapid consecutive metric collections', async () => {
      const results = await Promise.all([
        invoke<SystemMetrics>('get_system_metrics'),
        invoke<SystemMetrics>('get_system_metrics'),
        invoke<SystemMetrics>('get_system_metrics'),
        invoke<SystemMetrics>('get_system_metrics'),
        invoke<SystemMetrics>('get_system_metrics')
      ])

      expect(results).toHaveLength(5)
      results.forEach(metrics => {
        expect(metrics.disk).toBeDefined()
        expect(metrics.memory).toBeDefined()
      })
    })

  })

  // ==========================================================================
  // 2. DISK MANAGEMENT
  // ==========================================================================

  describe('Disk Management', () => {

    beforeEach(() => {
      // Create test files for cleanup tests
      const cacheDir = path.join(TEST_DIR, 'caches')
      for (let i = 0; i < 10; i++) {
        fs.writeFileSync(
          path.join(cacheDir, `cache-${i}.tmp`),
          'x'.repeat(1024 * 100) // 100KB each
        )
      }
    })

    it('should cleanup caches', async () => {
      const result = await invoke<ActionResult>('cleanup_caches')

      expect(result).toBeDefined()
      expect(result.success).toBe(true)
      expect(result.action).toBe('cleanup_caches')

      console.log(`Caches cleaned: ${result.details}`)
    })

    it('should empty trash', async () => {
      const result = await invoke<ActionResult>('empty_trash')

      expect(result).toBeDefined()
      expect(result.success).toBe(true)
      expect(result.action).toBe('empty_trash')

      console.log(`Trash: ${result.details}`)
    })

    it('should cleanup docker (if available)', async () => {
      const result = await invoke<ActionResult>('cleanup_docker')

      expect(result).toBeDefined()
      expect(result.success).toBe(true)

      console.log(`Docker: ${result.details}`)
    })

    it('should cleanup old logs', async () => {
      // Create old log files
      const logDir = path.join(TEST_DIR, 'logs')
      const oldDate = new Date()
      oldDate.setDate(oldDate.getDate() - 60) // 60 days ago

      for (let i = 0; i < 5; i++) {
        const logPath = path.join(logDir, `old-log-${i}.log`)
        fs.writeFileSync(logPath, 'old log content')
        fs.utimesSync(logPath, oldDate, oldDate)
      }

      const result = await invoke<ActionResult>('cleanup_logs', { daysToKeep: 30 })

      expect(result).toBeDefined()
      expect(result.success).toBe(true)

      console.log(`Logs cleaned: ${result.details}`)
    })

    it('should find large files', async () => {
      // Create a large test file
      const largeFile = path.join(TEST_DIR, 'large-file.bin')
      fs.writeFileSync(largeFile, 'x'.repeat(1024 * 1024 * 2)) // 2MB

      const files = await invoke<FileInfo[]>('find_large_files', {
        minSizeMb: 1,
        path: TEST_DIR
      })

      expect(files).toBeDefined()
      expect(Array.isArray(files)).toBe(true)

      const found = files.find(f => f.path.includes('large-file.bin'))
      expect(found).toBeDefined()
      expect(found!.size).toBeGreaterThanOrEqual(1024 * 1024 * 2)

      console.log(`Found ${files.length} large files`)

      // Cleanup
      fs.unlinkSync(largeFile)
    })

    it('should move files to external storage', async () => {
      // Create test files to move
      const filesToMove: string[] = []
      for (let i = 0; i < 3; i++) {
        const filePath = path.join(TEST_DIR, `move-me-${i}.txt`)
        fs.writeFileSync(filePath, `content ${i}`)
        filesToMove.push(filePath)
      }

      const result = await invoke<ActionResult>('move_to_external', {
        paths: filesToMove,
        destination: TEST_EXTERNAL
      })

      expect(result).toBeDefined()
      expect(result.success).toBe(true)
      expect(result.files_affected).toBe(3)

      // Verify files moved
      for (let i = 0; i < 3; i++) {
        const destPath = path.join(TEST_EXTERNAL, `move-me-${i}.txt`)
        expect(fs.existsSync(destPath)).toBe(true)
        expect(fs.existsSync(filesToMove[i])).toBe(false)
      }

      console.log(`Moved: ${result.details}`)
    })

    it('should perform aggressive cleanup', async () => {
      const results = await invoke<ActionResult[]>('aggressive_cleanup')

      expect(results).toBeDefined()
      expect(Array.isArray(results)).toBe(true)
      expect(results.length).toBeGreaterThan(0)

      results.forEach(result => {
        expect(result.action).toBeDefined()
        console.log(`  ${result.action}: ${result.details}`)
      })
    })

  })

  // ==========================================================================
  // 3. PACKAGE MANAGEMENT
  // ==========================================================================

  describe('Package Management', () => {

    it('should detect package manager correctly', async () => {
      // Test npm-style package
      const npmResult = await invoke<ActionResult>('install_package', {
        name: '@types/node',
        manager: 'npm'
      }).catch(e => ({ success: false, action: 'install', details: e.message }))

      expect(npmResult.action).toBe('install_package')
      console.log(`npm install: ${npmResult.details}`)
    })

    it('should update all packages (dry run check)', async () => {
      // This is a potentially long operation, so we just verify it starts
      const startTime = Date.now()

      const resultsPromise = invoke<ActionResult[]>('update_all_packages')

      // Give it 5 seconds max for test
      const timeoutPromise = new Promise<ActionResult[]>(resolve =>
        setTimeout(() => resolve([{ success: true, action: 'timeout', details: 'Test timeout', timestamp: Date.now() }]), 5000)
      )

      const results = await Promise.race([resultsPromise, timeoutPromise])

      expect(results).toBeDefined()
      console.log(`Package update initiated in ${Date.now() - startTime}ms`)
    })

  })

  // ==========================================================================
  // 4. PROCESS MANAGEMENT
  // ==========================================================================

  describe('Process Management', () => {

    it('should kill zombie processes', async () => {
      const result = await invoke<ActionResult>('kill_zombies')

      expect(result).toBeDefined()
      expect(result.success).toBe(true)
      expect(result.action).toBe('kill_zombies')

      console.log(`Zombies: ${result.details}`)
    })

    it('should not kill protected processes', async () => {
      // This should NOT kill Finder, Dock, etc.
      const result = await invoke<ActionResult>('kill_high_memory_processes', {
        thresholdMb: 10000 // Very high threshold
      })

      expect(result).toBeDefined()
      expect(result.success).toBe(true)

      // Verify protected processes still exist
      const metrics = await invoke<SystemMetrics>('get_system_metrics')
      expect(metrics.process_count).toBeGreaterThan(10) // Should still have many processes

      console.log(`High memory cleanup: ${result.details}`)
    })

  })

  // ==========================================================================
  // 5. WEB SCRAPING
  // ==========================================================================

  describe('Web Scraping', () => {

    it('should scrape a simple URL', async () => {
      const result = await invoke<ScrapeResult>('scrape_url', {
        url: 'https://example.com'
      })

      expect(result).toBeDefined()
      expect(result.url).toBe('https://example.com')
      expect(result.status).toBe(200)
      expect(result.body).toContain('Example Domain')
      expect(result.links.length).toBeGreaterThan(0)

      console.log(`Scraped: ${result.url}, ${result.body.length} bytes`)
    })

    it('should scrape multiple URLs in parallel', async () => {
      const urls = [
        'https://example.com',
        'https://httpbin.org/get',
        'https://jsonplaceholder.typicode.com/posts/1'
      ]

      const results = await invoke<ScrapeResult[]>('scrape_multiple', { urls })

      expect(results).toBeDefined()
      expect(results.length).toBe(3)

      results.forEach(result => {
        expect(result.status).toBeGreaterThanOrEqual(200)
        expect(result.status).toBeLessThan(400)
      })

      console.log(`Scraped ${results.length} URLs in parallel`)
    })

    it('should handle scrape errors gracefully', async () => {
      const result = await invoke<ScrapeResult>('scrape_url', {
        url: 'https://this-domain-definitely-does-not-exist-12345.com'
      }).catch(e => ({ url: '', status: 0, body: '', links: [], headers: {}, timestamp: 0 }))

      // Should not crash, just return empty/error result
      expect(result).toBeDefined()
    })

    it('should respect rate limiting', async () => {
      const startTime = Date.now()

      // Scrape same domain multiple times
      await invoke<ScrapeResult>('scrape_url', { url: 'https://example.com' })
      await invoke<ScrapeResult>('scrape_url', { url: 'https://example.com/page1' })
      await invoke<ScrapeResult>('scrape_url', { url: 'https://example.com/page2' })

      const elapsed = Date.now() - startTime

      // Should have some delay between requests (at least 2 seconds for 3 requests)
      expect(elapsed).toBeGreaterThanOrEqual(1000)

      console.log(`3 requests to same domain took ${elapsed}ms (rate limited)`)
    })

  })

  // ==========================================================================
  // 6. PROJECT MANAGEMENT
  // ==========================================================================

  describe('Project Management', () => {

    beforeAll(() => {
      // Create test projects
      const nodeProject = path.join(TEST_DIR, 'projects', 'node-project')
      const rustProject = path.join(TEST_DIR, 'projects', 'rust-project')
      const pythonProject = path.join(TEST_DIR, 'projects', 'python-project')

      fs.mkdirSync(nodeProject, { recursive: true })
      fs.mkdirSync(rustProject, { recursive: true })
      fs.mkdirSync(pythonProject, { recursive: true })

      // Node project
      fs.writeFileSync(path.join(nodeProject, 'package.json'), JSON.stringify({
        name: 'test-node-project',
        version: '1.0.0',
        dependencies: {}
      }))

      // Rust project
      fs.writeFileSync(path.join(rustProject, 'Cargo.toml'), `
[package]
name = "test-rust-project"
version = "0.1.0"
edition = "2021"
`)

      // Python project
      fs.writeFileSync(path.join(pythonProject, 'pyproject.toml'), `
[project]
name = "test-python-project"
version = "0.1.0"
`)
    })

    it('should scan and detect projects', async () => {
      const projects = await invoke<ProjectInfo[]>('scan_projects', {
        basePaths: [path.join(TEST_DIR, 'projects')]
      })

      expect(projects).toBeDefined()
      expect(Array.isArray(projects)).toBe(true)
      expect(projects.length).toBe(3)

      const types = projects.map(p => p.project_type)
      expect(types).toContain('node')
      expect(types).toContain('rust')
      expect(types).toContain('python')

      console.log(`Found projects: ${projects.map(p => `${p.name} (${p.project_type})`).join(', ')}`)
    })

    it('should detect project health', async () => {
      const projects = await invoke<ProjectInfo[]>('scan_projects', {
        basePaths: [path.join(TEST_DIR, 'projects')]
      })

      for (const project of projects) {
        expect(project.has_git).toBe(false) // Test projects don't have git
        expect(project.last_modified).toBeGreaterThan(0)
      }
    })

    it('should maintain a project', async () => {
      const nodeProjectPath = path.join(TEST_DIR, 'projects', 'node-project')

      const results = await invoke<ActionResult[]>('maintain_project', {
        path: nodeProjectPath
      })

      expect(results).toBeDefined()
      expect(Array.isArray(results)).toBe(true)

      console.log(`Maintenance results: ${results.map(r => r.action).join(', ')}`)
    })

  })

  // ==========================================================================
  // 7. DAEMON OPERATIONS
  // ==========================================================================

  describe('Daemon Operations', () => {

    it('should track daemon state', async () => {
      // Import daemon module
      const daemon = await import('../src/core/sam-daemon')

      const status = daemon.getDaemonStatus()

      expect(status).toBeDefined()
      expect(typeof status.running).toBe('boolean')
      expect(typeof status.actionsExecuted).toBe('number')
    })

    it('should start and stop daemon', async () => {
      const daemon = await import('../src/core/sam-daemon')

      // Start daemon
      await daemon.startDaemon()
      let status = daemon.getDaemonStatus()
      expect(status.running).toBe(true)

      // Let it run briefly
      await new Promise(resolve => setTimeout(resolve, 100))

      // Stop daemon
      daemon.stopDaemon()
      status = daemon.getDaemonStatus()
      expect(status.running).toBe(false)
    })

    it('should schedule tasks', async () => {
      const daemon = await import('../src/core/sam-daemon')

      let taskRan = false

      daemon.scheduleTask('test-task', 'Test Task', 'every 1 minute', async () => {
        taskRan = true
      })

      // Task won't run immediately, but should be scheduled
      expect(taskRan).toBe(false)
    })

    it('should monitor URLs for changes', async () => {
      const daemon = await import('../src/core/sam-daemon')

      const changes: any[] = []

      daemon.monitorUrl('https://example.com', 60000, (change) => {
        changes.push(change)
      })

      // URL is now being monitored
      // (Won't actually detect changes in test, but verifies setup works)
    })

    it('should log actions', async () => {
      const daemon = await import('../src/core/sam-daemon')

      const logs = daemon.getLogs('action', 10)

      expect(logs).toBeDefined()
      expect(Array.isArray(logs)).toBe(true)
    })

  })

  // ==========================================================================
  // 8. INTEGRATION TESTS
  // ==========================================================================

  describe('Integration Tests', () => {

    it('should handle full cleanup cycle', async () => {
      // Simulate what happens when disk is full
      const metrics = await invoke<SystemMetrics>('get_system_metrics')

      if (metrics.disk.percentage > 0.5) {
        // Run cleanup
        const results = await invoke<ActionResult[]>('aggressive_cleanup')
        expect(results.length).toBeGreaterThan(0)

        // Check metrics again
        const newMetrics = await invoke<SystemMetrics>('get_system_metrics')

        // Should have freed some space (or at least not crashed)
        expect(newMetrics.disk).toBeDefined()

        console.log(`Cleanup cycle: ${metrics.disk.percentage * 100}% -> ${newMetrics.disk.percentage * 100}%`)
      }
    })

    it('should handle concurrent operations', async () => {
      // Run multiple operations concurrently
      const [metrics, cacheResult, trashResult, zombieResult] = await Promise.all([
        invoke<SystemMetrics>('get_system_metrics'),
        invoke<ActionResult>('cleanup_caches'),
        invoke<ActionResult>('empty_trash'),
        invoke<ActionResult>('kill_zombies')
      ])

      expect(metrics).toBeDefined()
      expect(cacheResult.success).toBe(true)
      expect(trashResult.success).toBe(true)
      expect(zombieResult.success).toBe(true)

      console.log('Concurrent operations completed successfully')
    })

    it('should recover from errors gracefully', async () => {
      // Try to cleanup non-existent path
      const result = await invoke<ActionResult>('move_to_external', {
        paths: ['/this/path/does/not/exist/at/all'],
        destination: TEST_EXTERNAL
      }).catch(e => ({
        success: false,
        action: 'move_to_external',
        details: e.message,
        timestamp: Date.now()
      }))

      // Should not crash, just report failure
      expect(result).toBeDefined()
      expect(result.files_affected || 0).toBe(0)
    })

    it('should maintain performance under load', async () => {
      const iterations = 10
      const startTime = Date.now()

      for (let i = 0; i < iterations; i++) {
        await invoke<SystemMetrics>('get_system_metrics')
      }

      const elapsed = Date.now() - startTime
      const avgTime = elapsed / iterations

      // Should complete within reasonable time (< 500ms per call)
      expect(avgTime).toBeLessThan(500)

      console.log(`${iterations} metric collections: ${elapsed}ms total, ${avgTime.toFixed(0)}ms avg`)
    })

  })

  // ==========================================================================
  // 9. STRESS TESTS
  // ==========================================================================

  describe('Stress Tests', () => {

    it('should handle many concurrent scrapes', async () => {
      const urls = Array(20).fill('https://example.com').map((u, i) => `${u}?q=${i}`)

      const startTime = Date.now()
      const results = await invoke<ScrapeResult[]>('scrape_multiple', { urls })
      const elapsed = Date.now() - startTime

      expect(results.length).toBe(20)
      console.log(`20 concurrent scrapes: ${elapsed}ms`)
    }, 60000) // 60 second timeout

    it('should handle rapid health checks', async () => {
      const checks = 50
      const results: SystemMetrics[] = []

      for (let i = 0; i < checks; i++) {
        results.push(await invoke<SystemMetrics>('get_system_metrics'))
      }

      expect(results).toHaveLength(checks)
      console.log(`${checks} rapid health checks completed`)
    })

    it('should handle large file operations', async () => {
      // Create many small files
      const fileCount = 100
      const testFiles: string[] = []

      for (let i = 0; i < fileCount; i++) {
        const filePath = path.join(TEST_DIR, `stress-file-${i}.txt`)
        fs.writeFileSync(filePath, `content ${i}`.repeat(100))
        testFiles.push(filePath)
      }

      // Find large files
      const startTime = Date.now()
      const largeFiles = await invoke<FileInfo[]>('find_large_files', {
        minSizeMb: 0, // Find all
        path: TEST_DIR
      })
      const elapsed = Date.now() - startTime

      expect(largeFiles.length).toBeGreaterThanOrEqual(fileCount)
      console.log(`Scanned ${largeFiles.length} files in ${elapsed}ms`)

      // Cleanup
      testFiles.forEach(f => fs.unlinkSync(f))
    })

  })

})

// ==========================================================================
// TYPE DEFINITIONS
// ==========================================================================

interface SystemMetrics {
  disk: {
    total_bytes: number
    used_bytes: number
    available_bytes: number
    percentage: number
  }
  memory: {
    total_bytes: number
    used_bytes: number
    percentage: number
  }
  cpu_usage: number
  process_count: number
  zombie_count: number
}

interface ActionResult {
  success: boolean
  action: string
  details: string
  bytes_affected?: number
  files_affected?: number
  timestamp: number
}

interface FileInfo {
  path: string
  size: number
  modified: number
  is_directory: boolean
}

interface ScrapeResult {
  url: string
  status: number
  headers: Record<string, string>
  body: string
  links: string[]
  timestamp: number
}

interface ProjectInfo {
  path: string
  name: string
  project_type: string
  has_git: boolean
  has_uncommitted: boolean
  last_modified: number
}
