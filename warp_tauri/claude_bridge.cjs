#!/usr/bin/env node
/**
 * Claude Bridge
 *
 * Enables SAM to send questions to Claude.ai via browser automation.
 * No API key needed - uses logged-in browser session.
 *
 * Usage:
 *   node claude_bridge.cjs --ask "question"
 *   node claude_bridge.cjs --ask "question" --context "context"
 *   node claude_bridge.cjs --read <thread_id>
 *   node claude_bridge.cjs --latest <thread_id>
 */

const fs = require('fs');
const path = require('path');
const threadManager = require('./claude_thread_manager.cjs');

const CONFIG = {
  stateFile: path.join(process.env.HOME, '.claude-bridge-state.json'),
  defaultThreadId: null,  // Will be set from state or created new
};

// Load/save state
function loadState() {
  try {
    if (fs.existsSync(CONFIG.stateFile)) {
      return JSON.parse(fs.readFileSync(CONFIG.stateFile, 'utf8'));
    }
  } catch (e) {}
  return { activeThreadId: null, history: [] };
}

function saveState(state) {
  fs.writeFileSync(CONFIG.stateFile, JSON.stringify(state, null, 2));
}

// Ask Claude a question
async function askClaude(question, context = null) {
  const state = loadState();

  // Build the message
  let message = question;
  if (context) {
    message = `Context:\n${context}\n\nQuestion:\n${question}`;
  }

  // Use existing thread or create new
  const threadId = state.activeThreadId;

  try {
    const result = await threadManager.sendToThread(threadId, message);

    // Update state with new thread ID
    state.activeThreadId = result.threadId;
    state.history.push({
      timestamp: new Date().toISOString(),
      question: question.substring(0, 100),
      threadId: result.threadId,
    });

    // Keep history bounded
    if (state.history.length > 100) {
      state.history = state.history.slice(-100);
    }

    saveState(state);

    return result;
  } catch (e) {
    throw new Error(`Claude bridge error: ${e.message}`);
  }
}

// Get latest response from Claude
async function getLatestResponse(threadId) {
  const data = await threadManager.readThread(threadId);
  const assistantMessages = data.messages.filter(m => m.role === 'assistant');

  if (assistantMessages.length === 0) {
    return null;
  }

  return assistantMessages[assistantMessages.length - 1].text;
}

// Get thread context
async function getThreadContext(threadId) {
  const data = await threadManager.readThread(threadId);

  return {
    threadId,
    url: data.url,
    messageCount: data.messages.length,
    recentUserMessages: data.messages.filter(m => m.role === 'user').slice(-5).map(m => m.text.substring(0, 200)),
    recentAssistantMessages: data.messages.filter(m => m.role === 'assistant').slice(-5).map(m => m.text.substring(0, 500)),
    lastMessage: data.messages[data.messages.length - 1] || null,
  };
}

// Format conversation for reading
function formatForReading(messages) {
  return messages.map(m => {
    const role = m.role === 'user' ? 'USER' : 'CLAUDE';
    const text = m.text.substring(0, 1000);
    return `[${role}]: ${text}`;
  }).join('\n\n---\n\n');
}

// CLI
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command || command === '--help') {
    console.log(`Claude Bridge

Commands:
  --ask "question"                    Ask Claude a question
  --ask "question" --context "ctx"    Ask with context
  --read <thread_id>                  Read recent conversation
  --latest <thread_id>                Get Claude's latest response
  --context <thread_id>               Get thread context summary
  --list                              List recent threads
  --new-thread                        Start a fresh thread

Examples:
  node claude_bridge.cjs --ask "How do I implement a binary search?"
  node claude_bridge.cjs --ask "Fix this code" --context "function foo() { return }"
  node claude_bridge.cjs --list
`);
    process.exit(0);
  }

  try {
    switch (command) {
      case '--ask': {
        const question = args[1];
        if (!question) throw new Error('Question required');

        let context = null;
        const contextIdx = args.indexOf('--context');
        if (contextIdx !== -1 && args[contextIdx + 1]) {
          context = args[contextIdx + 1];
        }

        console.error('[INFO] Sending to Claude...');
        const result = await askClaude(question, context);
        console.log(result.response);
        break;
      }

      case '--read': {
        const threadId = args[1];
        if (!threadId) {
          const state = loadState();
          if (!state.activeThreadId) throw new Error('Thread ID required (no active thread)');
          const data = await threadManager.readThread(state.activeThreadId);
          console.log(formatForReading(data.messages.slice(-10)));
        } else {
          const data = await threadManager.readThread(threadId);
          console.log(formatForReading(data.messages.slice(-10)));
        }
        break;
      }

      case '--latest': {
        const threadId = args[1];
        if (!threadId) {
          const state = loadState();
          if (!state.activeThreadId) throw new Error('Thread ID required (no active thread)');
          const response = await getLatestResponse(state.activeThreadId);
          console.log(response || 'No response found');
        } else {
          const response = await getLatestResponse(threadId);
          console.log(response || 'No response found');
        }
        break;
      }

      case '--context': {
        const threadId = args[1];
        if (!threadId) {
          const state = loadState();
          if (!state.activeThreadId) throw new Error('Thread ID required (no active thread)');
          const ctx = await getThreadContext(state.activeThreadId);
          console.log(JSON.stringify(ctx, null, 2));
        } else {
          const ctx = await getThreadContext(threadId);
          console.log(JSON.stringify(ctx, null, 2));
        }
        break;
      }

      case '--list': {
        console.error('[INFO] Fetching threads...');
        const threads = await threadManager.listThreads();
        console.log(JSON.stringify(threads, null, 2));
        break;
      }

      case '--new-thread': {
        const state = loadState();
        state.activeThreadId = null;
        saveState(state);
        console.log('Thread cleared. Next --ask will create a new conversation.');
        break;
      }

      default:
        console.error(`Unknown command: ${command}`);
        process.exit(1);
    }
  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  } finally {
    await threadManager.closeBrowser();
  }
}

module.exports = {
  askClaude,
  getLatestResponse,
  getThreadContext,
  formatForReading,
};

if (require.main === module) {
  main();
}
