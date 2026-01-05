#!/usr/bin/env node
/**
 * Perpetual Ladder - Multi-LLM Project Orchestrator
 *
 * Continuously improves all projects by:
 * 1. ChatGPT: Brainstorming, planning, architecture decisions
 * 2. Claude Code (CLI): Actual code execution and implementation
 * 3. SAM: Coordination, routing, and progress tracking
 *
 * Usage:
 *   node perpetual_ladder.cjs                    # Run continuous loop
 *   node perpetual_ladder.cjs --once             # Single iteration
 *   node perpetual_ladder.cjs --project <id>     # Focus on specific project
 *   node perpetual_ladder.cjs --status           # Show current status
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawn } = require('child_process');

// Configuration
const CONFIG = {
  registryPath: path.join(process.env.HOME, '.sam/projects/registry.json'),
  statePath: path.join(process.env.HOME, '.sam/state/ladder.json'),
  logsPath: path.join(process.env.HOME, '.sam/logs'),

  // LLM routing
  llmRouting: {
    brainstorm: 'chatgpt',      // Ideation, architecture, planning
    implement: 'claude-code',   // Code writing, debugging, testing
    review: 'claude-code',      // Code review, refactoring
    quick: 'ollama',            // Quick queries, status checks
  },

  // Timing
  iterationDelay: 60000,        // 1 minute between iterations
  chatgptTimeout: 120000,       // 2 minutes for ChatGPT responses
  claudeCodeTimeout: 600000,    // 10 minutes for Claude Code tasks

  // Prompts
  prompts: {
    brainstorm: (project, recentWork) => `
You are helping build "${project.name}" - ${project.description}

Goals:
${project.goals.map((g, i) => `${i + 1}. ${g}`).join('\n')}

Current focus: ${project.currentFocus}
Tech stack: ${project.techStack.join(', ')}

${recentWork ? `Recent work:\n${recentWork}\n` : ''}

What are the top 3 most impactful tasks to work on next? Be specific and actionable.
Format as numbered list with clear, implementable steps.
`.trim(),

    nextTask: (projects, completedTasks) => `
I'm managing these active projects:
${projects.map(p => `- ${p.name}: ${p.currentFocus} (priority ${p.priority})`).join('\n')}

${completedTasks.length > 0 ? `Recently completed:\n${completedTasks.map(t => `✓ ${t.project}: ${t.task}`).join('\n')}\n` : ''}

Which project needs attention most urgently? Suggest ONE specific task to execute.
Format: PROJECT_ID: <task description>
`.trim(),

    claudeCodeTask: (project, task) => `
cd ${project.path}

${task}

After completing, summarize what was done in 1-2 sentences.
`.trim(),
  }
};

// Load/save functions
function loadRegistry() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG.registryPath, 'utf8'));
  } catch (e) {
    console.error('Failed to load registry:', e.message);
    process.exit(1);
  }
}

function saveRegistry(registry) {
  registry.lastUpdated = new Date().toISOString();
  fs.writeFileSync(CONFIG.registryPath, JSON.stringify(registry, null, 2));
}

function loadState() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG.statePath, 'utf8'));
  } catch (e) {
    return {
      lastIteration: null,
      completedTasks: [],
      pendingTasks: [],
      failedTasks: [],
      chatgptThreadId: null,
      claudeThreadId: null,
      totalIterations: 0,
    };
  }
}

function saveState(state) {
  fs.writeFileSync(CONFIG.statePath, JSON.stringify(state, null, 2));
}

function log(message, type = 'info') {
  const timestamp = new Date().toISOString();
  const prefix = {
    info: '📋',
    success: '✅',
    error: '❌',
    llm: '🤖',
    task: '🔨',
  }[type] || '•';

  console.log(`[${timestamp.split('T')[1].split('.')[0]}] ${prefix} ${message}`);

  // Also write to log file
  const logFile = path.join(CONFIG.logsPath, `ladder_${timestamp.split('T')[0]}.log`);
  fs.appendFileSync(logFile, `[${timestamp}] [${type.toUpperCase()}] ${message}\n`);
}

// LLM interaction functions
async function askChatGPT(prompt, threadId = null) {
  log('Sending to ChatGPT...', 'llm');

  try {
    const chatgptBridge = path.join(__dirname, 'chatgpt_thread_manager.cjs');
    const threadManager = require(chatgptBridge);

    const result = await threadManager.sendToThread(threadId, prompt, true);

    log('ChatGPT responded', 'success');
    return {
      success: true,
      response: result.response,
      threadId: result.threadId,
    };
  } catch (e) {
    log(`ChatGPT error: ${e.message}`, 'error');
    return { success: false, error: e.message };
  }
}

async function runClaudeCode(task, projectPath) {
  log(`Running Claude Code in ${projectPath}...`, 'llm');

  return new Promise((resolve) => {
    const startTime = Date.now();
    let output = '';

    // Run claude CLI with the task
    const proc = spawn('claude', ['-p', task], {
      cwd: projectPath,
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: CONFIG.claudeCodeTimeout,
    });

    proc.stdout.on('data', (data) => {
      output += data.toString();
    });

    proc.stderr.on('data', (data) => {
      output += data.toString();
    });

    proc.on('close', (code) => {
      const duration = Math.round((Date.now() - startTime) / 1000);

      if (code === 0) {
        log(`Claude Code completed in ${duration}s`, 'success');
        resolve({
          success: true,
          output: output.slice(-2000), // Last 2000 chars
          duration,
        });
      } else {
        log(`Claude Code failed (exit ${code})`, 'error');
        resolve({
          success: false,
          output: output.slice(-1000),
          error: `Exit code ${code}`,
        });
      }
    });

    proc.on('error', (e) => {
      log(`Claude Code spawn error: ${e.message}`, 'error');
      resolve({
        success: false,
        error: e.message,
      });
    });

    // Timeout
    setTimeout(() => {
      proc.kill();
      resolve({
        success: false,
        error: 'Timeout',
        output: output.slice(-1000),
      });
    }, CONFIG.claudeCodeTimeout);
  });
}

// Parse task from ChatGPT response
function parseNextTask(response) {
  // Look for PROJECT_ID: task format
  const match = response.match(/([a-z-]+):\s*(.+)/i);
  if (match) {
    return {
      projectId: match[1].toLowerCase().replace(/\s/g, '-'),
      task: match[2].trim(),
    };
  }

  // Fallback: find numbered items
  const lines = response.split('\n');
  for (const line of lines) {
    const numbered = line.match(/^\d+[.\)]\s*(.+)/);
    if (numbered) {
      return {
        projectId: null, // Will use highest priority project
        task: numbered[1].trim(),
      };
    }
  }

  return null;
}

// Get project health summary
function getProjectHealth(project) {
  const healthChecks = [];

  // Check if path exists
  if (!fs.existsSync(project.path)) {
    healthChecks.push('⚠️ Path not found');
    return { healthy: false, issues: healthChecks };
  }

  // Check for common health indicators
  const checks = [
    { file: 'package.json', type: 'npm' },
    { file: 'Cargo.toml', type: 'rust' },
    { file: 'requirements.txt', type: 'python' },
    { file: '.git', type: 'git' },
  ];

  for (const check of checks) {
    const fullPath = path.join(project.path, check.file);
    if (fs.existsSync(fullPath)) {
      healthChecks.push(`✓ ${check.type}`);
    }
  }

  return {
    healthy: healthChecks.length > 0,
    indicators: healthChecks,
  };
}

// Main iteration
async function runIteration(focusProjectId = null) {
  const registry = loadRegistry();
  const state = loadState();

  log('═══════════════════════════════════════', 'info');
  log(`ITERATION #${state.totalIterations + 1}`, 'info');
  log('═══════════════════════════════════════', 'info');

  // Get active projects sorted by priority
  let projects = registry.projects
    .filter(p => p.status === 'active' || p.status === 'training')
    .sort((a, b) => a.priority - b.priority);

  if (focusProjectId) {
    const focus = projects.find(p => p.id === focusProjectId);
    if (focus) {
      projects = [focus, ...projects.filter(p => p.id !== focusProjectId)];
      log(`Focusing on: ${focus.name}`, 'info');
    }
  }

  // Step 1: Ask ChatGPT what to work on next
  log('Step 1: Consulting ChatGPT for next task...', 'task');

  const recentCompleted = state.completedTasks.slice(-5);
  const prompt = CONFIG.prompts.nextTask(projects, recentCompleted);

  const chatgptResult = await askChatGPT(prompt, state.chatgptThreadId);

  if (!chatgptResult.success) {
    log('Failed to get task from ChatGPT, using fallback...', 'error');
    // Fallback: work on highest priority project
    const fallbackTask = {
      projectId: projects[0].id,
      task: `Review ${projects[0].name} and identify any issues or improvements needed.`,
    };
    return await executeTask(fallbackTask, registry, state);
  }

  state.chatgptThreadId = chatgptResult.threadId;

  // Step 2: Parse the task
  const nextTask = parseNextTask(chatgptResult.response);

  if (!nextTask) {
    log('Could not parse task from ChatGPT response', 'error');
    log(`Response: ${chatgptResult.response.slice(0, 200)}...`, 'info');
    state.totalIterations++;
    saveState(state);
    return;
  }

  log(`Parsed task: ${nextTask.projectId || 'auto'}: ${nextTask.task.slice(0, 100)}...`, 'info');

  // Step 3: Execute the task with Claude Code
  await executeTask(nextTask, registry, state);

  state.totalIterations++;
  state.lastIteration = new Date().toISOString();
  saveState(state);
}

async function executeTask(task, registry, state) {
  // Find the project
  let project;
  if (task.projectId) {
    project = registry.projects.find(p =>
      p.id === task.projectId ||
      p.name.toLowerCase().includes(task.projectId.toLowerCase())
    );
  }

  if (!project) {
    // Use highest priority active project
    project = registry.projects
      .filter(p => p.status === 'active')
      .sort((a, b) => a.priority - b.priority)[0];
  }

  if (!project) {
    log('No project found for task', 'error');
    return;
  }

  log(`Step 2: Executing task on ${project.name}...`, 'task');
  log(`Task: ${task.task}`, 'info');

  // Run Claude Code
  const claudeResult = await runClaudeCode(task.task, project.path);

  // Record result
  const taskRecord = {
    project: project.name,
    projectId: project.id,
    task: task.task,
    timestamp: new Date().toISOString(),
    success: claudeResult.success,
    duration: claudeResult.duration,
    output: claudeResult.output?.slice(0, 500),
  };

  if (claudeResult.success) {
    state.completedTasks.push(taskRecord);
    // Keep only last 50 completed tasks
    if (state.completedTasks.length > 50) {
      state.completedTasks = state.completedTasks.slice(-50);
    }
    log(`Task completed: ${task.task.slice(0, 50)}...`, 'success');
  } else {
    state.failedTasks.push(taskRecord);
    if (state.failedTasks.length > 20) {
      state.failedTasks = state.failedTasks.slice(-20);
    }
    log(`Task failed: ${claudeResult.error}`, 'error');
  }

  saveState(state);

  // Step 3: Report back to ChatGPT
  log('Step 3: Reporting result to ChatGPT...', 'task');

  const reportPrompt = claudeResult.success
    ? `✅ Completed task on ${project.name}: ${task.task}\n\nResult: ${claudeResult.output?.slice(0, 500) || 'Task completed successfully'}\n\nWhat should we work on next?`
    : `❌ Task failed on ${project.name}: ${task.task}\n\nError: ${claudeResult.error}\n\nShould we retry, try a different approach, or move to a different task?`;

  await askChatGPT(reportPrompt, state.chatgptThreadId);
}

// Show status
function showStatus() {
  const registry = loadRegistry();
  const state = loadState();

  console.log('\n═══════════════════════════════════════');
  console.log('       PERPETUAL LADDER STATUS');
  console.log('═══════════════════════════════════════\n');

  console.log('📊 PROJECTS:\n');
  for (const project of registry.projects) {
    const health = getProjectHealth(project);
    const status = project.status === 'active' ? '🟢' : project.status === 'training' ? '🟡' : '⚪';
    console.log(`${status} ${project.name} (P${project.priority})`);
    console.log(`   ${project.description}`);
    console.log(`   Focus: ${project.currentFocus}`);
    console.log(`   Path: ${project.path}`);
    console.log(`   Health: ${health.indicators?.join(', ') || health.issues?.join(', ')}`);
    console.log('');
  }

  console.log('📈 STATISTICS:\n');
  console.log(`   Total iterations: ${state.totalIterations}`);
  console.log(`   Last iteration: ${state.lastIteration || 'Never'}`);
  console.log(`   Completed tasks: ${state.completedTasks.length}`);
  console.log(`   Failed tasks: ${state.failedTasks.length}`);
  console.log(`   ChatGPT thread: ${state.chatgptThreadId || 'None'}`);

  if (state.completedTasks.length > 0) {
    console.log('\n📝 RECENT COMPLETIONS:\n');
    for (const task of state.completedTasks.slice(-5)) {
      console.log(`   ✓ ${task.project}: ${task.task.slice(0, 60)}...`);
    }
  }

  console.log('\n═══════════════════════════════════════\n');
}

// CLI
async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`Perpetual Ladder - Multi-LLM Project Orchestrator

Usage:
  node perpetual_ladder.cjs                    # Run continuous loop
  node perpetual_ladder.cjs --once             # Single iteration
  node perpetual_ladder.cjs --project <id>     # Focus on specific project
  node perpetual_ladder.cjs --status           # Show current status

Options:
  --once              Run single iteration then exit
  --project <id>      Focus on specific project (e.g., 'sam', 'character-pipeline')
  --status            Show current status and exit
  --reset             Reset state (clear history)

Projects are defined in ~/.sam/projects/registry.json
`);
    process.exit(0);
  }

  if (args.includes('--status')) {
    showStatus();
    process.exit(0);
  }

  if (args.includes('--reset')) {
    fs.writeFileSync(CONFIG.statePath, JSON.stringify({
      lastIteration: null,
      completedTasks: [],
      pendingTasks: [],
      failedTasks: [],
      chatgptThreadId: null,
      claudeThreadId: null,
      totalIterations: 0,
    }, null, 2));
    console.log('State reset.');
    process.exit(0);
  }

  const onceMode = args.includes('--once');
  let focusProject = null;

  const projectIdx = args.indexOf('--project');
  if (projectIdx !== -1 && args[projectIdx + 1]) {
    focusProject = args[projectIdx + 1];
  }

  console.log('═══════════════════════════════════════════════');
  console.log('  PERPETUAL LADDER - Multi-LLM Orchestrator');
  console.log('═══════════════════════════════════════════════');
  console.log('');
  console.log('  ChatGPT: Brainstorming, planning');
  console.log('  Claude Code: Implementation, execution');
  console.log('  SAM: Coordination, tracking');
  console.log('');
  console.log('  Press Ctrl+C to stop');
  console.log('───────────────────────────────────────────────\n');

  if (onceMode) {
    await runIteration(focusProject);
    console.log('\nSingle iteration complete.');
    process.exit(0);
  }

  // Continuous loop
  while (true) {
    try {
      await runIteration(focusProject);
    } catch (e) {
      log(`Iteration error: ${e.message}`, 'error');
    }

    log(`Waiting ${CONFIG.iterationDelay / 1000}s before next iteration...`, 'info');
    await new Promise(r => setTimeout(r, CONFIG.iterationDelay));
  }
}

// Cleanup
process.on('SIGINT', () => {
  console.log('\n\n👋 Shutting down Perpetual Ladder...');
  process.exit(0);
});

main().catch(console.error);
