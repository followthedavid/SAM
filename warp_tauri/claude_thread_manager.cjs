#!/usr/bin/env node
/**
 * Claude Thread Manager
 *
 * Manages persistent Claude.ai threads for browser-based communication.
 * Mirror of chatgpt_thread_manager.cjs but for Claude.
 *
 * Usage:
 *   node claude_thread_manager.cjs list                    # List recent threads
 *   node claude_thread_manager.cjs read <thread_id>        # Read a thread
 *   node claude_thread_manager.cjs send <thread_id> "msg"  # Send to a thread
 *   node claude_thread_manager.cjs new "message"           # Start new thread
 */

const { chromium } = require('playwright-extra');
const stealth = require('puppeteer-extra-plugin-stealth')();
const path = require('path');
const fs = require('fs');
const os = require('os');

chromium.use(stealth);

const CONFIG = {
  browserPath: null,  // Use Playwright's bundled Chromium
  userDataDir: path.join(os.homedir(), '.claude-stealth-profile-chromium'),
  windowPosition: { x: -3000, y: -3000 },
  baseUrl: 'https://claude.ai',
  stateFile: path.join(os.homedir(), '.claude-thread-state.json'),
  pollInterval: 5000,

  // Claude.ai selectors (may need adjustment based on UI changes)
  selectors: {
    conversationLinks: 'a[href^="/chat/"]',
    userMessage: '[data-testid="user-message"], .user-message, div[class*="human"]',
    assistantMessage: '[data-testid="assistant-message"], .assistant-message, div[class*="assistant"]',
    textArea: 'div[contenteditable="true"], textarea[placeholder*="Reply"], div[class*="ProseMirror"]',
    sendButton: 'button[aria-label*="Send"], button[type="submit"]',
  },
};

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function launchBrowser() {
  // Create profile dir if needed (user needs to login once)
  if (!fs.existsSync(CONFIG.userDataDir)) {
    fs.mkdirSync(CONFIG.userDataDir, { recursive: true });
    console.error('[INFO] First run - you may need to login to Claude.ai');
  }

  const launchOptions = {
    headless: false,
    args: [
      '--window-position=10000,10000',
      '--window-size=1280,800',
      '--disable-blink-features=AutomationControlled',
      '--no-first-run',
      '--no-default-browser-check',
      '--no-sandbox',
      '--disable-setuid-sandbox',
    ],
    viewport: { width: 1280, height: 800 },
    ignoreDefaultArgs: ['--enable-automation'],
  };

  if (CONFIG.browserPath) {
    launchOptions.executablePath = CONFIG.browserPath;
  }

  const context = await chromium.launchPersistentContext(CONFIG.userDataDir, launchOptions);

  // Hide window after launch
  await sleep(500);
  try {
    require('child_process').execSync(
      `osascript -e 'tell application "System Events" to set visible of process "Chromium" to false'`,
      { stdio: 'ignore' }
    );
  } catch (e) {}

  return context;
}

let sharedContext = null;
let sharedPage = null;

async function getSharedBrowser() {
  if (sharedContext) {
    try {
      await sharedContext.pages();
      return { context: sharedContext, page: sharedPage };
    } catch (e) {
      sharedContext = null;
      sharedPage = null;
    }
  }

  sharedContext = await launchBrowser();
  sharedPage = sharedContext.pages()[0] || await sharedContext.newPage();
  return { context: sharedContext, page: sharedPage };
}

async function closeBrowser() {
  if (sharedContext) {
    try {
      await sharedContext.close();
    } catch (e) {}
    sharedContext = null;
    sharedPage = null;
  }
}

process.on('exit', closeBrowser);
process.on('SIGINT', async () => { await closeBrowser(); process.exit(); });
process.on('SIGTERM', async () => { await closeBrowser(); process.exit(); });

// List recent conversations
async function listThreads(keepOpen = false) {
  const { page } = await getSharedBrowser();

  try {
    await page.goto(CONFIG.baseUrl);
    await sleep(3000);

    const threads = await page.evaluate((selector) => {
      const links = document.querySelectorAll(selector);
      return Array.from(links).slice(0, 15).map(a => {
        const href = a.getAttribute('href');
        const id = href.replace('/chat/', '');
        return {
          id,
          title: a.innerText.trim().substring(0, 60),
          url: 'https://claude.ai' + href,
        };
      });
    }, CONFIG.selectors.conversationLinks);

    return threads;
  } finally {
    if (!keepOpen) await closeBrowser();
  }
}

// Read messages from a thread
async function readThread(threadId, keepOpen = false) {
  const { page } = await getSharedBrowser();

  try {
    const url = `${CONFIG.baseUrl}/chat/${threadId}`;
    await page.goto(url, { waitUntil: 'domcontentloaded' });

    let messages = [];
    for (let attempt = 0; attempt < 10; attempt++) {
      await sleep(2000);

      messages = await page.evaluate((selectors) => {
        const msgs = [];

        // Try to find all message containers
        const allElements = document.querySelectorAll('[class*="message"], [data-testid*="message"]');

        allElements.forEach((m, idx) => {
          const text = m.innerText.trim();
          if (!text) return;

          // Detect role from class names or attributes
          const classList = m.className.toLowerCase();
          const testId = m.getAttribute('data-testid') || '';

          let role = 'unknown';
          if (classList.includes('human') || classList.includes('user') || testId.includes('user')) {
            role = 'user';
          } else if (classList.includes('assistant') || testId.includes('assistant')) {
            role = 'assistant';
          }

          if (role !== 'unknown') {
            msgs.push({ index: idx, role, text });
          }
        });

        return msgs;
      }, CONFIG.selectors);

      if (messages.length > 0) {
        await sleep(1000);
        break;
      }

      console.error(`[INFO] Waiting for messages... attempt ${attempt + 1}/10`);
    }

    return { threadId, url: `${CONFIG.baseUrl}/chat/${threadId}`, messages };
  } finally {
    if (!keepOpen) await closeBrowser();
  }
}

// Send a message to a thread
async function sendToThread(threadId, message, keepOpen = false) {
  const { page } = await getSharedBrowser();

  try {
    const url = threadId ? `${CONFIG.baseUrl}/chat/${threadId}` : `${CONFIG.baseUrl}/new`;
    await page.goto(url);
    await sleep(3000);

    // Find and fill textarea
    const typed = await page.evaluate((msg, selectors) => {
      const textarea = document.querySelector(selectors.textArea);
      if (textarea) {
        textarea.focus();
        if (textarea.tagName === 'TEXTAREA') {
          textarea.value = msg;
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
        } else {
          // contenteditable div
          textarea.innerText = msg;
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
        return true;
      }
      return false;
    }, message, CONFIG.selectors);

    if (!typed) {
      throw new Error('Could not find input field');
    }

    await sleep(300);

    // Send
    try {
      const sendBtn = await page.waitForSelector(CONFIG.selectors.sendButton, { timeout: 3000 });
      await sendBtn.click();
    } catch (e) {
      await page.keyboard.press('Enter');
    }

    // Wait for response
    await sleep(2000);
    let lastContent = '';
    let stableCount = 0;

    for (let i = 0; i < 60; i++) {
      const isStreaming = await page.evaluate(() => {
        return !!document.querySelector('[class*="streaming"], [class*="typing"]');
      });

      const content = await page.evaluate((selectors) => {
        const msgs = document.querySelectorAll(selectors.assistantMessage);
        if (msgs.length === 0) {
          // Fallback: find any assistant-like message
          const fallback = document.querySelectorAll('[class*="assistant"]');
          if (fallback.length > 0) {
            return fallback[fallback.length - 1].innerText.trim();
          }
          return '';
        }
        return msgs[msgs.length - 1].innerText.trim();
      }, CONFIG.selectors);

      if (content && content === lastContent && !isStreaming) {
        stableCount++;
        if (stableCount >= 2) break;
      } else {
        stableCount = 0;
        lastContent = content;
      }

      await sleep(2000);
    }

    // Get new thread ID if this was a new conversation
    const newUrl = page.url();
    const newThreadId = newUrl.includes('/chat/') ? newUrl.split('/chat/')[1].split('?')[0] : null;

    return {
      threadId: newThreadId || threadId,
      response: lastContent,
    };
  } finally {
    if (!keepOpen) await closeBrowser();
  }
}

// CLI
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command) {
    console.log(`Claude Thread Manager

Usage:
  list                     List recent threads
  read <thread_id>         Read messages from a thread
  send <thread_id> "msg"   Send message to a thread
  new "msg"                Start new thread

Examples:
  node claude_thread_manager.cjs list
  node claude_thread_manager.cjs read abc123
  node claude_thread_manager.cjs send abc123 "hello"
  node claude_thread_manager.cjs new "Start a new conversation"`);
    process.exit(0);
  }

  try {
    switch (command) {
      case 'list': {
        console.error('[INFO] Fetching threads...');
        const threads = await listThreads();
        console.log(JSON.stringify(threads, null, 2));
        break;
      }

      case 'read': {
        const threadId = args[1];
        if (!threadId) {
          console.error('Usage: read <thread_id>');
          process.exit(1);
        }
        console.error('[INFO] Reading thread...');
        const thread = await readThread(threadId);
        console.log(JSON.stringify(thread, null, 2));
        break;
      }

      case 'send': {
        const threadId = args[1];
        const message = args[2];
        if (!threadId || !message) {
          console.error('Usage: send <thread_id> "message"');
          process.exit(1);
        }
        console.error('[INFO] Sending message...');
        const result = await sendToThread(threadId, message);
        console.log(JSON.stringify(result, null, 2));
        break;
      }

      case 'new': {
        const message = args[1];
        if (!message) {
          console.error('Usage: new "message"');
          process.exit(1);
        }
        console.error('[INFO] Starting new thread...');
        const result = await sendToThread(null, message);
        console.log(JSON.stringify(result, null, 2));
        break;
      }

      default:
        console.error(`Unknown command: ${command}`);
        process.exit(1);
    }
  } catch (error) {
    console.error('[ERROR]', error.message);
    process.exit(1);
  }
}

module.exports = {
  listThreads,
  readThread,
  sendToThread,
  closeBrowser,
  CONFIG,
};

if (require.main === module) {
  main();
}
