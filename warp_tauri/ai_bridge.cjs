#!/usr/bin/env node
/**
 * SAM AI Bridge - Unified bridge for ChatGPT and Claude
 *
 * Actually extracts responses from AI providers instead of returning placeholders.
 * Uses Playwright with stealth for browser automation.
 *
 * Usage:
 *   node ai_bridge.cjs daemon          # Run as daemon processing queue
 *   node ai_bridge.cjs send "prompt"   # Send single prompt to ChatGPT
 *   node ai_bridge.cjs send "prompt" --claude   # Send to Claude
 *   node ai_bridge.cjs status          # Check daemon status
 */

const { chromium } = require('playwright-extra');
const stealth = require('puppeteer-extra-plugin-stealth')();
const path = require('path');
const fs = require('fs');
const os = require('os');

chromium.use(stealth);

const CONFIG = {
  userDataDir: path.join(os.homedir(), '.sam-ai-bridge-automation'),  // Dedicated automation profile
  queueFile: path.join(os.homedir(), '.sam_chatgpt_queue.json'),
  responseFile: path.join(os.homedir(), '.sam_chatgpt_responses.json'),
  logFile: '/tmp/sam_ai_bridge.log',
  pidFile: path.join(os.homedir(), '.sam_ai_bridge.pid'),

  pollInterval: 3000,  // 3 seconds
  responseTimeout: 120000,  // 2 minutes max wait for response

  providers: {
    chatgpt: {
      url: 'https://chatgpt.com',
      selectors: {
        textarea: '#prompt-textarea, textarea[placeholder*="anything"], div[contenteditable="true"]',
        sendButton: 'button[data-testid="send-button"], button[aria-label*="Send"]',
        assistantMessage: '[data-message-author-role="assistant"]',
        streamingIndicator: '.result-streaming, [class*="streaming"]',
      }
    },
    claude: {
      url: 'https://claude.ai/new',
      selectors: {
        textarea: 'div[contenteditable="true"], textarea[placeholder*="Reply"]',
        sendButton: 'button[aria-label="Send Message"], button[type="submit"]',
        assistantMessage: '[data-testid="assistant-message"], .font-claude-message',
        streamingIndicator: '[data-is-streaming="true"], .animate-pulse',
      }
    }
  }
};

// Logging
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.error(line);
  fs.appendFileSync(CONFIG.logFile, line + '\n');
}

// Sleep utility
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// Browser management
let browser = null;
let page = null;

async function launchBrowser() {
  if (browser) {
    try {
      await browser.contexts();
      return { browser, page };
    } catch (e) {
      browser = null;
      page = null;
    }
  }

  // Create profile dir if needed
  if (!fs.existsSync(CONFIG.userDataDir)) {
    fs.mkdirSync(CONFIG.userDataDir, { recursive: true });
  }

  // Use stealth settings to avoid Cloudflare detection
  const context = await chromium.launchPersistentContext(CONFIG.userDataDir, {
    headless: false,
    executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    args: [
      '--window-position=100,100',  // Visible for login
      '--window-size=1280,800',
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-web-security',
      '--disable-site-isolation-trials',
    ],
    viewport: { width: 1280, height: 800 },
    ignoreDefaultArgs: ['--enable-automation'],
    // Mimic real user
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
  });

  browser = context;
  page = context.pages()[0] || await context.newPage();

  // Hide window
  await sleep(500);
  try {
    require('child_process').execSync(
      `osascript -e 'tell application "System Events" to set visible of process "Chromium" to false'`,
      { stdio: 'ignore' }
    );
  } catch (e) {}

  return { browser, page };
}

async function closeBrowser() {
  if (browser) {
    try { await browser.close(); } catch (e) {}
    browser = null;
    page = null;
  }
}

// Send prompt and get response
async function sendPrompt(prompt, provider = 'chatgpt') {
  const config = CONFIG.providers[provider];
  if (!config) {
    throw new Error(`Unknown provider: ${provider}`);
  }

  log(`[SEND] Provider: ${provider}`);
  log(`[SEND] Prompt: ${prompt.substring(0, 100)}...`);

  const { page } = await launchBrowser();

  try {
    // Navigate to provider
    await page.goto(config.url, { waitUntil: 'domcontentloaded' });
    await sleep(3000);

    // Count existing messages before sending
    const initialMessageCount = await page.evaluate((selector) => {
      return document.querySelectorAll(selector).length;
    }, config.selectors.assistantMessage);

    // Find and fill textarea
    const typed = await page.evaluate(({ msg, selectors }) => {
      const textarea = document.querySelector(selectors.textarea);
      if (!textarea) return false;

      textarea.focus();
      if (textarea.tagName === 'TEXTAREA') {
        textarea.value = msg;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
      } else {
        // contenteditable div
        textarea.innerText = msg;
        textarea.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
      }
      return true;
    }, { msg: prompt, selectors: config.selectors });

    if (!typed) {
      throw new Error('Could not find input field');
    }

    await sleep(500);

    // Click send or press Enter
    try {
      const sendBtn = await page.waitForSelector(config.selectors.sendButton, { timeout: 3000 });
      if (sendBtn) {
        await sendBtn.click();
      }
    } catch (e) {
      await page.keyboard.press('Enter');
    }

    log('[SEND] Waiting for response...');

    // Wait for new response
    let response = '';
    let lastContent = '';
    let stableCount = 0;
    const startTime = Date.now();

    while (Date.now() - startTime < CONFIG.responseTimeout) {
      await sleep(2000);

      // Check if still streaming
      const isStreaming = await page.evaluate((selector) => {
        return !!document.querySelector(selector);
      }, config.selectors.streamingIndicator);

      // Get latest assistant message
      const content = await page.evaluate(({ selector, initialCount }) => {
        const msgs = document.querySelectorAll(selector);
        if (msgs.length <= initialCount) return '';
        // Get the newest message (last one)
        const lastMsg = msgs[msgs.length - 1];
        return lastMsg ? lastMsg.innerText.trim() : '';
      }, { selector: config.selectors.assistantMessage, initialCount: initialMessageCount });

      if (content && content === lastContent && !isStreaming) {
        stableCount++;
        if (stableCount >= 2) {
          response = content;
          break;
        }
      } else {
        stableCount = 0;
        lastContent = content;
      }

      log(`[SEND] Waiting... ${Math.round((Date.now() - startTime) / 1000)}s`);
    }

    if (!response) {
      response = lastContent || '[No response received]';
    }

    log(`[SEND] Got response: ${response.substring(0, 100)}...`);
    return { success: true, response, provider };

  } catch (error) {
    log(`[ERROR] ${error.message}`);
    return { success: false, error: error.message, provider };
  }
}

// Queue management
function loadQueue() {
  try {
    if (fs.existsSync(CONFIG.queueFile)) {
      return JSON.parse(fs.readFileSync(CONFIG.queueFile, 'utf8'));
    }
  } catch (e) {}
  return [];
}

function saveQueue(queue) {
  fs.writeFileSync(CONFIG.queueFile, JSON.stringify(queue, null, 2));
}

function loadResponses() {
  try {
    if (fs.existsSync(CONFIG.responseFile)) {
      return JSON.parse(fs.readFileSync(CONFIG.responseFile, 'utf8'));
    }
  } catch (e) {}
  return {};
}

function saveResponses(responses) {
  fs.writeFileSync(CONFIG.responseFile, JSON.stringify(responses, null, 2));
}

// Daemon mode
async function runDaemon() {
  // Check for existing daemon
  if (fs.existsSync(CONFIG.pidFile)) {
    const oldPid = fs.readFileSync(CONFIG.pidFile, 'utf8').trim();
    try {
      process.kill(parseInt(oldPid), 0);
      log(`[ERROR] Daemon already running (PID: ${oldPid})`);
      process.exit(1);
    } catch (e) {
      // Process doesn't exist, continue
    }
  }

  // Write PID
  fs.writeFileSync(CONFIG.pidFile, process.pid.toString());

  // Cleanup on exit
  const cleanup = () => {
    try { fs.unlinkSync(CONFIG.pidFile); } catch (e) {}
    closeBrowser();
  };
  process.on('exit', cleanup);
  process.on('SIGINT', () => { cleanup(); process.exit(); });
  process.on('SIGTERM', () => { cleanup(); process.exit(); });

  log('=== SAM AI Bridge Daemon Started ===');

  while (true) {
    try {
      const queue = loadQueue();
      const pending = queue.find(t => t.status === 'pending');

      if (pending) {
        log(`[DAEMON] Processing task: ${pending.id}`);

        // Mark as processing
        pending.status = 'processing';
        saveQueue(queue);

        // Send to AI
        const result = await sendPrompt(pending.prompt, pending.provider || 'chatgpt');

        // Save response
        const responses = loadResponses();
        responses[pending.id] = {
          response: result.response || result.error,
          success: result.success,
          provider: result.provider,
          timestamp: new Date().toISOString(),
        };
        saveResponses(responses);

        // Mark complete
        pending.status = result.success ? 'completed' : 'failed';
        saveQueue(queue);

        log(`[DAEMON] Task ${pending.id} ${pending.status}`);
      }
    } catch (error) {
      log(`[DAEMON ERROR] ${error.message}`);
    }

    await sleep(CONFIG.pollInterval);
  }
}

// CLI
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  switch (command) {
    case 'daemon':
      await runDaemon();
      break;

    case 'send': {
      const prompt = args[1];
      const provider = args.includes('--claude') ? 'claude' : 'chatgpt';

      if (!prompt) {
        console.error('Usage: node ai_bridge.cjs send "prompt" [--claude]');
        process.exit(1);
      }

      const result = await sendPrompt(prompt, provider);
      console.log(JSON.stringify(result, null, 2));
      await closeBrowser();
      break;
    }

    case 'status': {
      const queue = loadQueue();
      const responses = loadResponses();
      const pending = queue.filter(t => t.status === 'pending').length;
      const processing = queue.filter(t => t.status === 'processing').length;
      const completed = Object.keys(responses).length;

      let daemonRunning = false;
      if (fs.existsSync(CONFIG.pidFile)) {
        const pid = fs.readFileSync(CONFIG.pidFile, 'utf8').trim();
        try {
          process.kill(parseInt(pid), 0);
          daemonRunning = true;
        } catch (e) {}
      }

      console.log(JSON.stringify({
        daemon: daemonRunning ? 'running' : 'stopped',
        queue: { pending, processing, total: queue.length },
        responsesCount: completed,
      }, null, 2));
      break;
    }

    case 'test': {
      log('Running quick test...');
      const result = await sendPrompt('Say "Bridge working!" and nothing else.', 'chatgpt');
      console.log(JSON.stringify(result, null, 2));
      await closeBrowser();
      break;
    }

    case 'login': {
      // Open browser for manual login
      const provider = args[1] || 'chatgpt';
      const config = CONFIG.providers[provider];

      if (!config) {
        console.error(`Unknown provider: ${provider}. Use 'chatgpt' or 'claude'.`);
        process.exit(1);
      }

      console.log(`\n🔐 Opening ${provider} for login...`);
      console.log(`\nProfile will be saved to: ${CONFIG.userDataDir}`);
      console.log('\nInstructions:');
      console.log('  1. Complete any Cloudflare verification');
      console.log('  2. Log into your account');
      console.log('  3. Close the browser window when done');
      console.log('\nYour session will be saved for future bridge requests.\n');

      const { browser: ctx, page: p } = await launchBrowser();
      await p.goto(config.url);

      // Wait for user to close browser
      await new Promise((resolve) => {
        ctx.on('close', resolve);
      });

      console.log('✓ Session saved. You can now use the bridge.');
      break;
    }

    default:
      console.log(`SAM AI Bridge

Usage:
  login [provider]    Open browser to log in (saves session)
  daemon              Run as daemon processing queue
  send "prompt"       Send prompt to ChatGPT
  send "prompt" --claude  Send prompt to Claude
  status              Check queue and daemon status
  test                Quick connectivity test

Examples:
  node ai_bridge.cjs login             # Log into ChatGPT (run first!)
  node ai_bridge.cjs login claude      # Log into Claude
  node ai_bridge.cjs daemon
  node ai_bridge.cjs send "Write hello world in Python"
  node ai_bridge.cjs send "Explain quantum computing" --claude`);
  }
}

main().catch(err => {
  console.error('[FATAL]', err);
  process.exit(1);
});
