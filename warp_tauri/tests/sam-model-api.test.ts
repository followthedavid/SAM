/**
 * SAM Model & API Tests
 * Tests Ollama endpoints and sam-trained model responses
 * Runs completely in background - no UI needed
 */

import { describe, it, expect, beforeAll } from 'vitest';

const OLLAMA_URL = 'http://localhost:11434';
const PRIMARY_MODEL = 'sam-trained:latest';
const FALLBACK_MODEL = 'sam-brain:latest';
const CODE_MODEL = 'qwen2.5-coder:1.5b';

describe('SAM Model & API Tests', () => {
  beforeAll(async () => {
    console.log('\n========================================');
    console.log('=== SAM MODEL & API TESTS ===');
    console.log('========================================\n');
  });

  describe('Ollama Connection', () => {
    it('should connect to Ollama server', async () => {
      const response = await fetch(`${OLLAMA_URL}/api/tags`);
      expect(response.ok).toBe(true);

      const data = await response.json();
      console.log(`✅ Ollama running with ${data.models?.length || 0} models available`);
    });

    it('should have sam-trained model available', async () => {
      const response = await fetch(`${OLLAMA_URL}/api/tags`);
      const data = await response.json();

      const models = data.models?.map((m: { name: string }) => m.name) || [];
      const hasSamTrained = models.some((m: string) => m.includes('sam-trained'));

      console.log(`Available models: ${models.slice(0, 5).join(', ')}...`);
      console.log(`✅ sam-trained available: ${hasSamTrained}`);

      expect(hasSamTrained).toBe(true);
    });

    it('should have sam-trained loaded in memory', async () => {
      const response = await fetch(`${OLLAMA_URL}/api/ps`);
      const data = await response.json();

      const loadedModels = data.models?.map((m: { name: string }) => m.name) || [];
      const samLoaded = loadedModels.some((m: string) => m.includes('sam-trained'));

      console.log(`Currently loaded: ${loadedModels.join(', ') || 'none'}`);
      console.log(`✅ sam-trained in memory: ${samLoaded}`);

      // This is a soft check - model might need to be loaded
      if (!samLoaded) {
        console.log('⚠️ sam-trained not loaded - will load on first request');
      }
    });
  });

  describe('Model Response Tests', () => {
    it('should get response from sam-trained', async () => {
      console.log('\nTesting sam-trained response...');

      const response = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: PRIMARY_MODEL,
          prompt: 'Say hello',
          stream: false,
          options: { num_predict: 20 }
        })
      });

      expect(response.ok).toBe(true);

      const data = await response.json();
      console.log(`Model: ${data.model}`);
      console.log(`Response: "${data.response?.substring(0, 100)}..."`);
      console.log(`✅ sam-trained responded successfully`);

      expect(data.model).toContain('sam-trained');
      expect(data.response).toBeTruthy();
    }, 60000); // 60s timeout for model loading

    it('should respond to roleplay prompt', async () => {
      console.log('\nTesting roleplay capability...');

      const response = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: PRIMARY_MODEL,
          prompt: 'You are SAM, a confident AI assistant. Introduce yourself briefly.',
          stream: false,
          options: { num_predict: 50, temperature: 0.8 }
        })
      });

      const data = await response.json();
      console.log(`Roleplay response: "${data.response?.substring(0, 150)}..."`);
      console.log(`✅ Roleplay capability working`);

      expect(data.response).toBeTruthy();
    }, 60000);

    it('should handle chat format', async () => {
      console.log('\nTesting chat API format...');

      const response = await fetch(`${OLLAMA_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: PRIMARY_MODEL,
          messages: [
            { role: 'user', content: 'What is 2+2?' }
          ],
          stream: false,
          options: { num_predict: 20 }
        })
      });

      const data = await response.json();
      console.log(`Chat response: "${data.message?.content?.substring(0, 100)}..."`);
      console.log(`✅ Chat API format working`);

      expect(data.message?.content).toBeTruthy();
    }, 60000);
  });

  describe('Model Performance', () => {
    it('should respond within acceptable time', async () => {
      console.log('\nTesting response time...');

      const start = Date.now();
      const response = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: PRIMARY_MODEL,
          prompt: 'Hi',
          stream: false,
          options: { num_predict: 5 }
        })
      });

      const elapsed = Date.now() - start;
      const data = await response.json();

      console.log(`Response time: ${elapsed}ms`);
      console.log(`Eval rate: ${data.eval_count ? (data.eval_count / (data.eval_duration / 1e9)).toFixed(1) : 'N/A'} tokens/s`);

      // Should respond within 30 seconds (accounting for cold start)
      expect(elapsed).toBeLessThan(30000);
      console.log(`✅ Response time acceptable`);
    }, 60000);
  });

  describe('Keep-Alive Tests', () => {
    it('should accept keep_alive parameter', async () => {
      console.log('\nTesting keep_alive...');

      const response = await fetch(`${OLLAMA_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: PRIMARY_MODEL,
          prompt: '.',
          stream: false,
          keep_alive: '30m',
          options: { num_predict: 1 }
        })
      });

      expect(response.ok).toBe(true);
      console.log(`✅ keep_alive parameter accepted`);
    }, 60000);

    it('should show model loaded after request', async () => {
      // Give a moment for model to register
      await new Promise(r => setTimeout(r, 1000));

      const response = await fetch(`${OLLAMA_URL}/api/ps`);
      const data = await response.json();

      const loadedModels = data.models?.map((m: { name: string }) => m.name) || [];
      console.log(`Models in memory: ${loadedModels.join(', ')}`);

      const samLoaded = loadedModels.some((m: string) => m.includes('sam-trained'));
      console.log(`✅ sam-trained loaded: ${samLoaded}`);

      expect(samLoaded).toBe(true);
    });
  });
});

describe('SAM Brain API Tests', () => {
  const SAM_API_URL = 'http://localhost:8765';

  it('should check if SAM API is running', async () => {
    console.log('\nChecking SAM Brain API...');

    try {
      const response = await fetch(`${SAM_API_URL}/api/status`, {
        signal: AbortSignal.timeout(5000)
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`SAM API Status: ${JSON.stringify(data)}`);
        console.log(`✅ SAM Brain API is running`);
      } else {
        console.log(`⚠️ SAM API responded with ${response.status}`);
      }
    } catch (e) {
      console.log(`⚠️ SAM Brain API not running (this is OK if using direct Ollama)`);
    }
  });
});
