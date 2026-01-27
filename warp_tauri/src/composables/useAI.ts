import { ref, computed } from 'vue';
import { v4 as uuidv4 } from 'uuid';
import { useClaude, type AIMode } from './useClaude';
import type { ExecutionTask } from './useCodeExecution';
import { useScaffoldedAgent, type AgentEvent, type AgentConfig } from './useScaffoldedAgent';
import { getOrchestrator } from './useOrchestrator';
import { useCognitiveAPI } from './useCognitiveAPI';

// Check if we're running in Tauri
const isTauri = '__TAURI__' in window;

// Dynamic imports for Tauri APIs (only available in desktop app)
type InvokeFn = <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
type ListenFn = <T>(event: string, handler: (event: { payload: T }) => void) => Promise<() => void>;
type UnlistenFn = () => void;

let invoke: InvokeFn | null = null;
let listen: ListenFn | null = null;

if (isTauri) {
  import('@tauri-apps/api/tauri').then(module => {
    invoke = module.invoke as InvokeFn;
  });
  import('@tauri-apps/api/event').then(module => {
    listen = module.listen as ListenFn;
  });
}

export interface AIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  streaming?: boolean;
  executionTask?: ExecutionTask; // For code execution messages
  isExecuting?: boolean; // Currently executing code
}

export interface AISession {
  id: string;
  messages: AIMessage[];
  model: string;
  isThinking: boolean;
  debugLogs?: string[];
  aiMode?: AIMode;
  executionMode?: boolean; // Enable code execution in chat
}

const sessions = ref<Map<string, AISession>>(new Map());
const availableModels = ref<string[]>([
  'sam-trained:latest',
  'sam-brain:latest',
  'qwen2.5-coder:1.5b',
  'dolphin-llama3:8b',
]);

export function useAI() {
  const claude = useClaude();
  const scaffoldedAgent = useScaffoldedAgent();

  // Load available models from Ollama
  async function refreshModels() {
    try {
      const models = await invoke<string[]>('list_ollama_models');
      availableModels.value = models;
    } catch (error) {
      console.error('Failed to load Ollama models:', error);
    }
  }

  // Create a new AI session
  function createSession(tabId: string, model = 'dolphin-llama3:8b'): AISession {
    const session: AISession = {
      id: tabId,
      messages: [],
      model,
      isThinking: false,
      debugLogs: [],
      aiMode: claude.getAIMode(),
    };
    sessions.value.set(tabId, session);
    console.log(`[SESSION] Created new session for tab ${tabId}, total sessions: ${sessions.value.size}`);
    return session;
  }

  // Get or create session for a tab
  function getSession(tabId: string): AISession {
    let session = sessions.value.get(tabId);
    if (!session) {
      console.log(`[SESSION] No session found for tab ${tabId}, creating new one`);
      session = createSession(tabId);
    } else {
      console.log(`[SESSION] Found existing session for tab ${tabId}, messages: ${session.messages.length}`);
    }
    return session;
  }

  // Add message to session
  function addMessage(tabId: string, message: Omit<AIMessage, 'id' | 'timestamp'>): AIMessage {
    const session = getSession(tabId);
    const fullMessage: AIMessage = {
      ...message,
      id: uuidv4(),
      timestamp: new Date(),
    };
    session.messages.push(fullMessage);
    console.log(`[SESSION] Added ${message.role} message to ${tabId}, total messages: ${session.messages.length}`);
    return fullMessage;
  }

  // Helper to add debug logs
  function addDebugLog(tabId: string, message: string) {
    const session = sessions.value.get(tabId);
    if (session) {
      if (!session.debugLogs) session.debugLogs = [];
      const timestamp = new Date().toLocaleTimeString();
      session.debugLogs.push(`[${timestamp}] ${message}`);
      // Keep only last 50 logs
      if (session.debugLogs.length > 50) {
        session.debugLogs = session.debugLogs.slice(-50);
      }
    }
    console.log(message);
  }

  // Validate that a string looks like a shell command, not conversational text
  function isValidShellCommand(command: string): { valid: boolean; reason?: string } {
    if (!command || typeof command !== 'string') {
      return { valid: false, reason: 'Command is empty or not a string' };
    }

    const trimmed = command.trim();
    if (!trimmed) {
      return { valid: false, reason: 'Command is empty' };
    }

    // Get first word (potential command name)
    const firstWord = trimmed.split(/\s+/)[0].toLowerCase();

    // Words that clearly indicate conversational English (not shell commands)
    const conversationalStarters = [
      'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'there', 'here',
      'what', 'when', 'where', 'why', 'how', 'who', 'which', 'whose', 'whom',
      'would', 'could', 'should', 'might', 'must', 'will', 'shall', 'may',
      'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
      'have', 'has', 'had', 'having', 'do', 'does', 'did',
      'please', 'sorry', 'thank', 'thanks', 'okay', 'ok', 'yes', 'no', 'yeah', 'nope',
      'the', 'a', 'an', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
      'said', 'told', 'asked', 'explained', 'mentioned', 'suggested', 'recommended',
      'wanted', 'needed', 'tried', 'seems', 'appeared', 'looked', 'felt',
      'actually', 'basically', 'certainly', 'clearly', 'definitely', 'especially',
      'generally', 'honestly', 'hopefully', 'indeed', 'mostly', 'obviously',
      'perhaps', 'probably', 'really', 'simply', 'specifically', 'surely',
      'typically', 'usually', 'unfortunately', 'well', 'maybe',
      'however', 'therefore', 'thus', 'hence', 'instead', 'otherwise', 'meanwhile',
      'moreover', 'furthermore', 'nevertheless', 'consequently', 'accordingly',
      'let', "let's", 'but', 'and', 'or', 'so', 'because', 'although', 'since',
      'after', 'before', 'during', 'until', 'while', 'if', 'unless', 'whether',
    ];

    // Check if first word is a conversational starter
    if (conversationalStarters.includes(firstWord) || conversationalStarters.includes(firstWord.replace(/['"]/g, ''))) {
      return { valid: false, reason: `Starts with conversational word "${firstWord}", not a shell command` };
    }

    // Check for sentence patterns (ending with period, multiple sentences, etc.)
    if (/[.!?]$/.test(trimmed) && !/^[.\/~]/.test(trimmed)) {
      return { valid: false, reason: 'Looks like a sentence (ends with punctuation)' };
    }

    // Check for very long phrases without shell operators
    const wordCount = trimmed.split(/\s+/).length;
    if (wordCount > 10 && !trimmed.includes('|') && !trimmed.includes('&&') && !trimmed.includes(';') && !trimmed.includes('$') && !trimmed.includes('`')) {
      return { valid: false, reason: 'Very long phrase without shell operators - likely conversational text' };
    }

    // Check if first word looks like a command (alphanumeric, starts with letter, or path)
    const looksLikeCommand = /^[a-z][a-z0-9_-]*$/.test(firstWord) || /^[.\/~]/.test(firstWord) || /^\[/.test(firstWord);
    if (!looksLikeCommand && wordCount > 3) {
      return { valid: false, reason: `First word "${firstWord}" doesn't look like a command name` };
    }

    return { valid: true };
  }

  // Parse and execute tool calls from LLM response
  async function parseAndExecuteToolCalls(
    tabId: string,
    assistantMessage: AIMessage,
    session: AISession,
    model: string,
    depth: number = 0
  ) {
    // Prevent infinite recursion
    if (depth > 5) {
      addDebugLog(tabId, `[TOOL] Max recursion depth reached, stopping`);
      return;
    }

    const content = assistantMessage.content;

    // Try to extract JSON objects containing "tool" key
    // This handles various formats the model might produce
    const toolCalls: Array<{ tool: string; args: Record<string, unknown> }> = [];

    // Method 1: Try to find standalone JSON objects (including inside markdown code blocks)
    // First, extract JSON from markdown code blocks
    const codeBlockMatches = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/g);
    const contentToSearch = codeBlockMatches
      ? codeBlockMatches.map(block => block.replace(/```(?:json)?\s*\n?/g, '').replace(/\n?```/g, '')).join('\n') + '\n' + content
      : content;

    const jsonMatches = contentToSearch.match(/\{[^{}]*"tool"[^{}]*"args"[^{}]*\{[^{}]*\}[^{}]*\}/g);
    if (jsonMatches) {
      for (const jsonStr of jsonMatches) {
        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.tool && typeof parsed.tool === 'string') {
            toolCalls.push({ tool: parsed.tool, args: parsed.args || {} });
          }
        } catch (e) {
          // Try a simpler extraction
          const toolMatch = jsonStr.match(/"tool"\s*:\s*"(\w+)"/);
          const argsMatch = jsonStr.match(/"args"\s*:\s*(\{[^}]+\})/);
          if (toolMatch) {
            try {
              const args = argsMatch ? JSON.parse(argsMatch[1]) : {};
              toolCalls.push({ tool: toolMatch[1], args });
            } catch (parseErr) {
              // Skip if args can't be parsed
            }
          }
        }
      }
    }

    // Method 2: Line-by-line JSON parsing for clean outputs
    if (toolCalls.length === 0) {
      const lines = contentToSearch.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('{') && trimmed.includes('"tool"')) {
          try {
            const parsed = JSON.parse(trimmed);
            if (parsed.tool && typeof parsed.tool === 'string') {
              toolCalls.push({ tool: parsed.tool, args: parsed.args || {} });
            }
          } catch (e) {
            // Skip unparseable lines
          }
        }
      }
    }

    // Method 3: Extract shell commands from code blocks if no JSON found
    if (toolCalls.length === 0 && codeBlockMatches) {
      for (const block of codeBlockMatches) {
        const isShell = /```(?:sh|bash|shell|zsh)?\s*\n/i.test(block);
        if (isShell) {
          const code = block.replace(/```(?:sh|bash|shell|zsh)?\s*\n?/gi, '').replace(/\n?```/g, '').trim();
          if (code && !code.includes('\n')) { // Single line command
            addDebugLog(tabId, `[TOOL] Extracted shell command from code block: ${code.substring(0, 50)}...`);
            toolCalls.push({ tool: 'execute_shell', args: { command: code } });
          }
        }
      }
    }

    // Log what we found
    for (const tc of toolCalls) {
      addDebugLog(tabId, `[TOOL] Found tool call: ${tc.tool}`);
    }

    if (toolCalls.length === 0) {
      addDebugLog(tabId, `[TOOL] No tool calls found in response. Model may need better prompting or try a larger model (8B+).`);
      // Add a helpful note to the response if the model just talked instead of acting
      if (content.length > 100 && !content.includes('{"tool"')) {
        assistantMessage.content += '\n\n⚠️ *SAM explained instead of acting. For better action execution, try using `dolphin-llama3:8b` or a larger model.*';
      }
      return;
    }

    addDebugLog(tabId, `[TOOL] Executing ${toolCalls.length} tool call(s)...`);

    // Execute each tool call
    for (const toolCall of toolCalls) {
      const { tool, args } = toolCall;
      let result = '';
      let success = false;

      try {
        if (!invoke) {
          // Fallback for browser mode - use fetch to local API or show error
          result = `Error: Tauri invoke not available - tool execution requires desktop app`;
          addDebugLog(tabId, `[TOOL] ${result}`);
        } else {
          addDebugLog(tabId, `[TOOL] Executing: ${tool} with args: ${JSON.stringify(args)}`);

          switch (tool) {
            case 'execute_shell':
              const cmdToExecute = args.command as string;
              const validation = isValidShellCommand(cmdToExecute);
              if (!validation.valid) {
                result = `Command validation failed: ${validation.reason}\nThis looks like hallucinated text, not a shell command. The model should output actual commands like 'ls', 'pwd', etc.`;
                addDebugLog(tabId, `[TOOL] BLOCKED invalid command: ${cmdToExecute.substring(0, 100)}`);
              } else {
                result = await invoke<string>('execute_shell', { command: cmdToExecute });
                success = true;
              }
              break;
            case 'read_file':
              result = await invoke<string>('read_file', { path: args.path as string });
              success = true;
              break;
            case 'write_file':
              result = await invoke<string>('write_file', {
                path: args.path as string,
                content: args.content as string
              });
              success = true;
              break;
            case 'web_fetch':
              result = await invoke<string>('web_fetch', { url: args.url as string });
              success = true;
              break;
            case 'glob_files':
              const globResults = await invoke<string[]>('glob_files', {
                pattern: args.pattern as string,
                basePath: args.basePath as string || '.'
              });
              result = globResults.join('\n');
              success = true;
              break;
            case 'grep_files':
              result = await invoke<string>('grep_files', {
                pattern: args.pattern as string,
                path: args.path as string || '.'
              });
              success = true;
              break;
            case 'get_system_metrics':
              const metrics = await invoke<Record<string, unknown>>('get_system_metrics', {});
              result = JSON.stringify(metrics, null, 2);
              success = true;
              break;
            case 'cleanup_caches':
              const cleanResult = await invoke<Record<string, unknown>>('cleanup_caches', {});
              result = JSON.stringify(cleanResult, null, 2);
              success = true;
              break;
            case 'empty_trash':
              const trashResult = await invoke<Record<string, unknown>>('empty_trash', {});
              result = JSON.stringify(trashResult, null, 2);
              success = true;
              break;
            default:
              // Try generic execute_agent_tool
              try {
                result = await invoke<string>('execute_agent_tool', { tool, args: JSON.stringify(args) });
                success = true;
              } catch (e) {
                result = `Unknown tool: ${tool}. Error: ${e}`;
              }
          }
        }
      } catch (error) {
        result = `Tool execution error: ${error}`;
        addDebugLog(tabId, `[TOOL] Error executing ${tool}: ${error}`);
      }

      // Update the assistant message to show the result
      const icon = success ? '✅' : '❌';
      assistantMessage.content += `\n\n${icon} **Tool Result (${tool}):**\n\`\`\`\n${result.substring(0, 2000)}${result.length > 2000 ? '...' : ''}\n\`\`\``;

      addDebugLog(tabId, `[TOOL] ${tool} result: ${result.substring(0, 100)}...`);
    }

    // Send tool results back to the model for a follow-up response
    addDebugLog(tabId, `[TOOL] Sending results back to model for continuation...`);

    // Create a new prompt with the tool results
    const toolResultPrompt = `Tool execution completed. Here are the results:\n\n${assistantMessage.content}\n\nPlease analyze the results and continue with the next step, or summarize what was accomplished.`;

    // Make a follow-up query (non-recursive to avoid infinite loops)
    try {
      const response = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: model,
          prompt: toolResultPrompt,
          stream: false // Non-streaming for follow-up
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.response) {
          assistantMessage.content += `\n\n---\n${data.response}`;
          addDebugLog(tabId, `[TOOL] Follow-up response received: ${data.response.substring(0, 100)}...`);

          // Check if the follow-up also contains tool calls (limit recursion depth)
          const hasMoreTools = /\{"tool"\s*:\s*"(\w+)"/.test(data.response);
          if (hasMoreTools) {
            addDebugLog(tabId, `[TOOL] Follow-up contains more tool calls - executing...`);
            // Create a temp message for the follow-up tools
            const followUpMsg: AIMessage = {
              id: uuidv4(),
              role: 'assistant',
              content: data.response,
              timestamp: new Date(),
              streaming: false,
            };
            await parseAndExecuteToolCalls(tabId, followUpMsg, session, model, depth + 1);
            // Append any additional content from the follow-up
            assistantMessage.content += followUpMsg.content.replace(data.response, '');
          }
        }
      }
    } catch (error) {
      addDebugLog(tabId, `[TOOL] Follow-up query failed: ${error}`);
    }
  }

  // Send prompt to Ollama with streaming
  async function sendPrompt(tabId: string, prompt: string, model?: string) {
    const session = getSession(tabId);
    const sessionModel = model || session.model;

    addDebugLog(tabId, `[START] Sending prompt to Ollama, model: ${sessionModel}`);

    // Don't allow multiple concurrent requests
    if (session.isThinking) {
      addDebugLog(tabId, '[BLOCKED] Already processing a request');
      return;
    }

    // Add user message
    addDebugLog(tabId, `[USER] Added user message: ${prompt.substring(0, 50)}...`);
    addMessage(tabId, {
      role: 'user',
      content: prompt,
    });

    // Create streaming assistant message
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    addDebugLog(tabId, `[ASSISTANT] Created assistant message, total messages: ${session.messages.length + 1}`);
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      if (isTauri && invoke) {
        // Use Tauri backend
        const sessionId = uuidv4();
        let unlisten: UnlistenFn | null = null;
        let unlistenDone: UnlistenFn | null = null;

        // Listen for stream chunks
        unlisten = await listen<string>(`ollama://stream/${sessionId}`, (event) => {
          assistantMessage.content += event.payload;
        });

        // Listen for completion
        unlistenDone = await listen<boolean>(`ollama://stream/${sessionId}/done`, async () => {
          assistantMessage.streaming = false;
          session.isThinking = false;
          if (unlisten) unlisten();
          if (unlistenDone) unlistenDone();
          // Parse and execute tool calls after streaming completes
          await parseAndExecuteToolCalls(tabId, assistantMessage, session, sessionModel);
        });

        // Invoke Tauri command
        await invoke('query_ollama_stream', {
          prompt,
          model: sessionModel,
          sessionId,
        });
      } else {
        // System prompt for tool calling
        const systemPrompt = `You are SAM, an autonomous AI assistant that can execute actions on the user's system.

You have access to these tools - use them by outputting ONLY a JSON object:

1. execute_shell - Run shell commands
   {"tool":"execute_shell","args":{"command":"ls -la"}}

2. read_file - Read file contents
   {"tool":"read_file","args":{"path":"/path/to/file"}}

3. write_file - Create or overwrite files
   {"tool":"write_file","args":{"path":"/path/to/file","content":"file contents"}}

4. web_fetch - Fetch web content
   {"tool":"web_fetch","args":{"url":"https://example.com"}}

5. get_system_metrics - Get system CPU, memory, disk info
   {"tool":"get_system_metrics","args":{}}

6. cleanup_caches - Clean system caches
   {"tool":"cleanup_caches","args":{}}

7. empty_trash - Empty the trash
   {"tool":"empty_trash","args":{}}

RULES:
- When asked to DO something, output ONLY the JSON tool call, nothing else
- After receiving tool results, explain what happened
- You can chain multiple tool calls to complete complex tasks
- Be proactive - if disk is full, clean up; if something fails, try alternatives

EXAMPLES:
User: "list my files"
{"tool":"execute_shell","args":{"command":"ls -la"}}

User: "check disk space"
{"tool":"execute_shell","args":{"command":"df -h"}}

User: "show system status"
{"tool":"get_system_metrics","args":{}}`;

        // Direct HTTP call to Ollama (browser mode)
        const response = await fetch('http://localhost:11434/api/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: sessionModel,
            system: systemPrompt,
            prompt: prompt,
            stream: true,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (reader) {
          let buffer = '';
          let streamComplete = false;

          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              addDebugLog(tabId, '[STREAM] Reader done, stream ended naturally');
              streamComplete = true;
              break;
            }

            // Decode the chunk
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;

            // Split into lines (Ollama sends newline-delimited JSON)
            const lines = buffer.split('\n');

            // Keep the last line in buffer (might be incomplete JSON)
            buffer = lines.pop() || '';

            // Process each complete line
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed) continue;

              try {
                const json = JSON.parse(trimmed);

                // Append response token
                if (json.response && typeof json.response === 'string') {
                  assistantMessage.content += json.response;
                  if (assistantMessage.content.length % 100 === 0 || assistantMessage.content.length < 10) {
                    addDebugLog(tabId, `[STREAM] Content length: ${assistantMessage.content.length}`);
                  }
                }

                // Check for completion
                if (json.done === true) {
                  addDebugLog(tabId, '[STREAM] Done flag received, completing stream');
                  streamComplete = true;
                  break;
                }
              } catch (parseError) {
                addDebugLog(tabId, `[ERROR] Failed to parse JSON: ${trimmed.substring(0, 50)}`);
                // Continue processing other lines even if one fails
              }
            }

            // Exit outer loop if stream is complete
            if (streamComplete) {
              break;
            }
          }

          // Process any remaining content in buffer after stream ends
          if (buffer.trim()) {
            try {
              const json = JSON.parse(buffer.trim());
              console.log('[Ollama] Processing final buffer content');

              if (json.response && typeof json.response === 'string') {
                assistantMessage.content += json.response;
              }

              if (json.done === true) {
                streamComplete = true;
              }
            } catch (parseError) {
              console.warn('[Ollama] Could not parse final buffer:', buffer, parseError);
            }
          }

          // Final cleanup
          addDebugLog(tabId, `[COMPLETE] Stream finished, total length: ${assistantMessage.content.length}, total messages: ${session.messages.length}`);
          assistantMessage.streaming = false;
          session.isThinking = false;

          // Parse and execute tool calls from the response
          await parseAndExecuteToolCalls(tabId, assistantMessage, session, sessionModel);
        }

        assistantMessage.streaming = false;
        session.isThinking = false;
      }
    } catch (error) {
      addDebugLog(tabId, `[ERROR] Ollama error: ${error}`);
      assistantMessage.content = `Error: ${error}`;
      assistantMessage.streaming = false;
      session.isThinking = false;
    }
  }

  // Send prompt without streaming (simpler, for quick queries)
  async function sendPromptSimple(tabId: string, prompt: string, model?: string) {
    const session = getSession(tabId);
    const sessionModel = model || session.model;

    addMessage(tabId, {
      role: 'user',
      content: prompt,
    });

    session.isThinking = true;

    try {
      const response = await invoke<string>('query_ollama', {
        prompt,
        model: sessionModel,
      });

      addMessage(tabId, {
        role: 'assistant',
        content: response,
      });
    } catch (error) {
      addMessage(tabId, {
        role: 'assistant',
        content: `Error: ${error}`,
      });
    } finally {
      session.isThinking = false;
    }
  }

  // Clear session messages
  function clearSession(tabId: string) {
    const session = sessions.value.get(tabId);
    if (session) {
      console.log(`[SESSION] CLEARING session ${tabId}, had ${session.messages.length} messages`);
      session.messages = [];
      if (session.debugLogs) {
        session.debugLogs.push(`[${new Date().toLocaleTimeString()}] [SESSION CLEARED]`);
      }
    }
  }

  // Change model for session
  function setModel(tabId: string, model: string) {
    const session = getSession(tabId);
    session.model = model;
  }

  // Send prompt with routing based on AI mode
  async function sendPromptRouted(tabId: string, prompt: string, model?: string) {
    const session = getSession(tabId);
    const aiMode = session.aiMode || claude.getAIMode();

    // CRITICAL DEBUG - log to backend so we can see in terminal
    try { await invoke('debug_log', { message: `[ROUTER] sendPromptRouted CALLED!` }); } catch {}
    try { await invoke('debug_log', { message: `[ROUTER] prompt: ${prompt.substring(0, 50)}` }); } catch {}
    try { await invoke('debug_log', { message: `[ROUTER] aiMode: ${aiMode}` }); } catch {}
    addDebugLog(tabId, `[ROUTER] Mode: ${aiMode}`);

    switch (aiMode) {
      case 'local':
        // Always use Ollama
        return await sendPrompt(tabId, prompt, model);

      case 'claude':
        // Always use Claude API
        return await sendPromptClaude(tabId, prompt);

      case 'auto':
        // Claude orchestrates - decides whether to use Ollama or handle itself
        return await sendPromptOrchestrated(tabId, prompt);

      case 'hybrid':
        // Start with Ollama (user can escalate later)
        return await sendPrompt(tabId, prompt, model);

      case 'agent':
        // Use scaffolded agent with Claude-level capabilities
        return await sendPromptAgent(tabId, prompt, model);

      case 'orchestrator':
        // Use Rust orchestrator for optimal routing
        return await sendPromptOrchestrator(tabId, prompt);

      case 'sam':
        // Use SAM cognitive backend (MLX + memory + personality)
        return await sendPromptSAM(tabId, prompt);

      default:
        return await sendPrompt(tabId, prompt, model);
    }
  }

  // Send prompt via Rust orchestrator (optimal local routing)
  async function sendPromptOrchestrator(tabId: string, prompt: string) {
    const session = getSession(tabId);

    if (session.isThinking) {
      addDebugLog(tabId, '[BLOCKED] Already processing a request');
      return;
    }

    addDebugLog(tabId, `[ORCHESTRATOR] Routing through Rust backend`);

    // Add user message
    addMessage(tabId, { role: 'user', content: prompt });

    // Create assistant message placeholder
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      const orchestrator = getOrchestrator();
      orchestrator.setWorkingDirectory(session.workingDirectory || '.');

      const result = await orchestrator.sendMessage(prompt);

      if (result) {
        // Update message with result
        assistantMessage.content = result.content;
        assistantMessage.streaming = false;

        // Add metadata for display
        if (result.processingPath) {
          assistantMessage.content += `\n\n---\n*Path: ${result.processingPath}*`;
          if (result.latencyMs) {
            assistantMessage.content += ` *${result.latencyMs}ms*`;
          }
        }

        addDebugLog(tabId, `[ORCHESTRATOR] Complete via ${result.processingPath || 'unknown'}`);
      } else {
        assistantMessage.content = 'No response from orchestrator';
        assistantMessage.streaming = false;
      }
    } catch (err) {
      addDebugLog(tabId, `[ORCHESTRATOR] Error: ${err}`);
      assistantMessage.content = `Error: ${err}`;
      assistantMessage.streaming = false;
    } finally {
      session.isThinking = false;
    }
  }

  // Send prompt to SAM cognitive backend (MLX + memory + personality)
  async function sendPromptSAM(tabId: string, prompt: string) {
    const session = getSession(tabId);

    if (session.isThinking) {
      addDebugLog(tabId, '[BLOCKED] Already processing a request');
      return;
    }

    addDebugLog(tabId, `[SAM] Sending to cognitive backend`);

    // Add user message
    addMessage(tabId, { role: 'user', content: prompt });

    // Create assistant message placeholder
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      const cognitiveAPI = useCognitiveAPI();

      // Use streaming for real-time response
      await new Promise<void>((resolve, reject) => {
        cognitiveAPI.stream(
          prompt,
          (token: string) => {
            // Append each token as it arrives
            assistantMessage.content += token;
          },
          () => {
            // Complete
            assistantMessage.streaming = false;
            addDebugLog(tabId, `[SAM] Streaming complete`);
            resolve();
          },
          (err: string) => {
            reject(new Error(err));
          }
        );
      });

    } catch (err) {
      addDebugLog(tabId, `[SAM] Streaming error: ${err}`);

      // Fallback to non-streaming
      try {
        const cognitiveAPI = useCognitiveAPI();
        const result = await cognitiveAPI.process(prompt);

        if (result && result.response) {
          assistantMessage.content = result.response;
          addDebugLog(tabId, `[SAM] Fallback successful, confidence: ${result.confidence}`);
        } else {
          assistantMessage.content = `SAM Error: No response received`;
        }
      } catch (fallbackErr) {
        assistantMessage.content = `Error connecting to SAM: ${fallbackErr}`;
      }

      assistantMessage.streaming = false;
    } finally {
      session.isThinking = false;
    }
  }

  // Send prompt to scaffolded agent (Claude-level local capabilities)
  async function sendPromptAgent(tabId: string, prompt: string, model?: string) {
    try { await invoke('debug_log', { message: '[AGENT] sendPromptAgent called!' }); } catch {}
    try { await invoke('debug_log', { message: `[AGENT] prompt: ${prompt.substring(0, 100)}` }); } catch {}

    const session = getSession(tabId);
    try { await invoke('debug_log', { message: `[AGENT] isThinking: ${session.isThinking}` }); } catch {}

    if (session.isThinking) {
      addDebugLog(tabId, '[BLOCKED] Already processing a request');
      try { await invoke('debug_log', { message: '[AGENT] BLOCKED' }); } catch {}
      return;
    }

    addDebugLog(tabId, `[AGENT] Starting scaffolded agent task`);
    try { await invoke('debug_log', { message: '[AGENT] About to call scaffoldedAgent.startTask' }); } catch {}

    // Add user message
    addMessage(tabId, { role: 'user', content: prompt });

    // Create assistant message placeholder
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      // Configure agent
      const config: AgentConfig = {
        model: model || session.model,
      };

      // Track agent events for display
      let lastThinkingContent = '';

      // Start agent task with event callback
      const sessionId = await scaffoldedAgent.startTask(prompt, config, (event: AgentEvent) => {
        addDebugLog(tabId, `[AGENT] Event: ${event.type}`);

        // Build up the message content based on events
        switch (event.type) {
          case 'Started':
            assistantMessage.content = `🚀 Starting task: ${event.task}\n\n`;
            break;

          case 'Thinking':
            lastThinkingContent = event.content || '';
            assistantMessage.content += `💭 **Thinking:**\n${lastThinkingContent}\n\n`;
            break;

          case 'ToolRequest':
            assistantMessage.content += `🔧 **Using tool:** \`${event.tool}\`\n\`\`\`json\n${JSON.stringify(event.args, null, 2)}\n\`\`\`\n\n`;
            break;

          case 'ToolResult':
            const icon = event.success ? '✅' : '❌';
            const output = event.output || '';
            const truncatedOutput = output.length > 500 ? output.substring(0, 500) + '...' : output;
            assistantMessage.content += `${icon} **Result:**\n\`\`\`\n${truncatedOutput}\n\`\`\`\n\n`;
            break;

          case 'Progress':
            assistantMessage.content += `📊 Step ${event.step}/${event.total}: ${event.description}\n\n`;
            break;

          case 'Verification':
            const verifyIcon = event.passed ? '✓' : '⚠️';
            assistantMessage.content += `${verifyIcon} **Verification:** ${event.message}\n\n`;
            break;

          case 'Completed':
            assistantMessage.content += `\n---\n✨ **Task completed** (${event.steps} steps)\n\n${event.answer}`;
            assistantMessage.streaming = false;
            session.isThinking = false;
            break;

          case 'Failed':
            assistantMessage.content += `\n---\n❌ **Task failed:** ${event.error}`;
            assistantMessage.streaming = false;
            session.isThinking = false;
            break;

          case 'StreamingChunk':
            // Update progress indicator without adding to message
            addDebugLog(tabId, `[AGENT] Streaming: ${event.chars_received} chars`);
            break;

          case 'Heartbeat':
            // Show activity indicator
            addDebugLog(tabId, `[AGENT] ${event.status}`);
            break;

          case 'Retrying':
            assistantMessage.content += `🔄 **Retrying** (${event.attempt}/${event.max_attempts}): ${event.reason}\n\n`;
            addDebugLog(tabId, `[AGENT] Retry ${event.attempt}/${event.max_attempts}: ${event.reason}`);
            break;
        }
      });

      addDebugLog(tabId, `[AGENT] Task started with session ID: ${sessionId}`);

    } catch (error) {
      addDebugLog(tabId, `[ERROR] Agent task failed: ${error}`);
      assistantMessage.content = `Error starting agent: ${error}`;
      assistantMessage.streaming = false;
      session.isThinking = false;
    }
  }

  // Send prompt directly to Claude
  async function sendPromptClaude(tabId: string, prompt: string) {
    const session = getSession(tabId);

    if (!claude.isClaudeAvailable.value) {
      addDebugLog(tabId, '[ERROR] Claude not available, falling back to Ollama');
      return await sendPrompt(tabId, prompt);
    }

    if (session.isThinking) {
      addDebugLog(tabId, '[BLOCKED] Already processing a request');
      return;
    }

    addDebugLog(tabId, `[CLAUDE] Sending to Claude API`);

    // Add user message
    addMessage(tabId, { role: 'user', content: prompt });

    // Create assistant message placeholder
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      const conversationHistory = session.messages.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await claude.queryClaude(prompt, conversationHistory);
      assistantMessage.content = response;
      assistantMessage.streaming = false;
      session.isThinking = false;

      addDebugLog(tabId, `[CLAUDE] Response received, length: ${response.length}`);
    } catch (error) {
      addDebugLog(tabId, `[ERROR] Claude query failed: ${error}`);
      assistantMessage.content = `Error: ${error}`;
      assistantMessage.streaming = false;
      session.isThinking = false;
    }
  }

  // Send prompt with Claude orchestration
  async function sendPromptOrchestrated(tabId: string, prompt: string) {
    const session = getSession(tabId);

    if (!claude.isClaudeAvailable.value) {
      addDebugLog(tabId, '[WARN] Claude not available, using Ollama only');
      return await sendPrompt(tabId, prompt);
    }

    if (session.isThinking) {
      addDebugLog(tabId, '[BLOCKED] Already processing a request');
      return;
    }

    addDebugLog(tabId, `[ORCHESTRATE] Sending to Claude for orchestration`);

    // Add user message
    addMessage(tabId, { role: 'user', content: prompt });

    // Create assistant message placeholder
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      const conversationHistory = session.messages.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Helper function for Claude to call Ollama
      const ollamaQueryFn = async (ollamaPrompt: string): Promise<string> => {
        addDebugLog(tabId, `[ORCHESTRATE] Claude delegated to Ollama: ${ollamaPrompt.substring(0, 50)}...`);

        // Query Ollama directly (not via sendPrompt to avoid adding messages)
        const response = await fetch('http://localhost:11434/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: session.model,
            prompt: ollamaPrompt,
            stream: false // Non-streaming for tool use
          }),
        });

        const data = await response.json();
        return data.response || '';
      };

      const { response, usedOllama } = await claude.queryClaudeWithOllamaTool(
        prompt,
        conversationHistory,
        ollamaQueryFn
      );

      assistantMessage.content = response;
      assistantMessage.streaming = false;
      session.isThinking = false;

      addDebugLog(tabId, `[ORCHESTRATE] Complete, used Ollama: ${usedOllama}, length: ${response.length}`);
    } catch (error) {
      addDebugLog(tabId, `[ERROR] Orchestration failed: ${error}`);
      assistantMessage.content = `Error: ${error}`;
      assistantMessage.streaming = false;
      session.isThinking = false;
    }
  }

  // Escalate current conversation to Claude (for hybrid mode)
  async function escalateToClaude(tabId: string, messageId: string) {
    const session = getSession(tabId);
    const messageIndex = session.messages.findIndex(m => m.id === messageId);

    if (messageIndex === -1) return;

    addDebugLog(tabId, `[ESCALATE] Escalating to Claude`);

    // Get conversation up to this point
    const conversationHistory = session.messages.slice(0, messageIndex + 1).map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Add system message
    addMessage(tabId, {
      role: 'system',
      content: '🔄 Escalated to Claude for review and improvement...'
    });

    // Create new assistant message
    const assistantMessage: AIMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    session.messages.push(assistantMessage);
    session.isThinking = true;

    try {
      const response = await claude.queryClaude(
        "Please review and improve the previous response, or provide additional insights.",
        conversationHistory
      );

      assistantMessage.content = response;
      assistantMessage.streaming = false;
      session.isThinking = false;

      addDebugLog(tabId, `[ESCALATE] Claude response received`);
    } catch (error) {
      addDebugLog(tabId, `[ERROR] Escalation failed: ${error}`);
      assistantMessage.content = `Error: ${error}`;
      assistantMessage.streaming = false;
      session.isThinking = false;
    }
  }

  return {
    sessions,
    availableModels,
    refreshModels,
    createSession,
    getSession,
    addMessage,
    sendPrompt,
    sendPromptSimple,
    sendPromptRouted,
    sendPromptClaude,
    sendPromptOrchestrated,
    sendPromptAgent,
    escalateToClaude,
    clearSession,
    setModel,
    claude,
    scaffoldedAgent,
  };
}
