import { test, expect } from '@playwright/test';

test.describe('Warp Replay UI', () => {
  test('renders multiple blocks', async ({ page }) => {
    await page.goto('http://localhost:4000');
    await page.waitForSelector('.warp-block, .block', { timeout: 10000 });
    const blocks = await page.$$eval('.warp-block, .block', els => els.length);
    expect(blocks).toBeGreaterThan(0);
  });

  test('handles long scroll', async ({ page }) => {
    await page.goto('http://localhost:4000');
    await page.waitForSelector('.warp-block', { timeout: 15000 });
    const scrollHeight = await page.evaluate(() => document.body.scrollHeight);
    expect(scrollHeight).toBeGreaterThan(500);
  });
});
