import { test, expect } from '@playwright/test';

test('replay UI renders blocks', async ({ page }) => {
  // Adjust URL to your dev server; serve built assets on port 4000
  await page.goto('http://localhost:4000');
  
  // Wait for the replay loader to register a block item
  await page.waitForSelector('.warp-block, .block', { timeout: 10000 });
  
  const blocks = await page.$$eval('.warp-block, .block', els => els.length);
  expect(blocks).toBeGreaterThan(0);
});
