#!/usr/bin/env node
/**
 * Quick Local Ladder - Uses Ollama instead of ChatGPT
 * Runs a single iteration using local SAM for task selection
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawn } = require('child_process');
const http = require('http');

const CONFIG = {
  registryPath: path.join(process.env.HOME, '.sam/projects/registry.json'),
  ollamaUrl: 'http://localhost:11434',
  model: 'sam-coder:latest',
};

function loadRegistry() {
  return JSON.parse(fs.readFileSync(CONFIG.registryPath, 'utf8'));
}

async function askOllama(prompt) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      model: CONFIG.model,
      prompt: prompt,
      stream: false,
      options: { num_predict: 300 }
    });

    const req = http.request('http://localhost:11434/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          resolve(json.response);
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function runClaudeCode(task, projectPath) {
  console.log(`\n🤖 Running Claude Code in ${projectPath}...`);
  console.log(`   Task: ${task}\n`);

  return new Promise((resolve) => {
    const proc = spawn('claude', ['-p', task], {
      cwd: projectPath,
      stdio: 'inherit',
      timeout: 300000,
    });

    proc.on('close', (code) => {
      resolve({ success: code === 0, code });
    });

    proc.on('error', (err) => {
      console.error('Claude Code error:', err.message);
      resolve({ success: false, error: err.message });
    });
  });
}

async function main() {
  console.log('\n═══════════════════════════════════════');
  console.log('    LOCAL PERPETUAL LADDER (Ollama)');
  console.log('═══════════════════════════════════════\n');

  const registry = loadRegistry();

  // Get active projects
  const projects = registry.projects
    .filter(p => p.status === 'active')
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 5);

  console.log('📊 Active Projects:');
  projects.forEach(p => console.log(`   ${p.priority}. ${p.name} - ${p.currentFocus}`));

  // Ask SAM for next task
  console.log('\n🧠 Asking SAM for next task...');

  const prompt = `You are SAM, helping manage these projects:
${projects.map(p => `- ${p.name}: ${p.description}. Focus: ${p.currentFocus}`).join('\n')}

Pick ONE project and suggest ONE specific, actionable coding task.
Format: PROJECT_NAME: <specific task>
Be concise.`;

  try {
    const response = await askOllama(prompt);
    console.log('\n📝 SAM suggests:');
    console.log(response);

    // Parse response to get project and task
    const lines = response.split('\n').filter(l => l.trim());
    const taskLine = lines.find(l => l.includes(':')) || lines[0];

    if (taskLine) {
      // Find matching project
      const projectName = projects.find(p => 
        taskLine.toLowerCase().includes(p.name.toLowerCase())
      );

      if (projectName) {
        const task = taskLine.split(':').slice(1).join(':').trim() || 
                     'Review code and suggest improvements';

        console.log(`\n✅ Selected: ${projectName.name}`);
        console.log(`   Task: ${task}`);
        console.log(`   Path: ${projectName.path}`);

        // Run Claude Code
        const result = await runClaudeCode(task, projectName.path);
        console.log('\n' + (result.success ? '✓ Task completed' : '✗ Task failed'));
      } else {
        // Default to first project
        const defaultProject = projects[0];
        console.log(`\n⚡ Defaulting to: ${defaultProject.name}`);
        const result = await runClaudeCode(
          'Review the codebase and identify one improvement to make',
          defaultProject.path
        );
        console.log('\n' + (result.success ? '✓ Task completed' : '✗ Task failed'));
      }
    }
  } catch (e) {
    console.error('Error:', e.message);
    
    // Fallback: just run on first project
    const fallback = projects[0];
    console.log(`\n⚡ Fallback: Running on ${fallback.name}`);
    await runClaudeCode('Run tests and fix any issues found', fallback.path);
  }

  console.log('\n═══════════════════════════════════════\n');
}

main().catch(console.error);
