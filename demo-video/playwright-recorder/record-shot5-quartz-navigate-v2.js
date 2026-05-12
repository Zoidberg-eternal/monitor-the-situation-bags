// Shot 5 v2 — Quartz graph navigation against the Bags-narrative Quartz mock.
// Lands on the persona page, sweeps the persona graph, scrolls through belief
// trajectory + 5-layer grounding. Target ~15s. Replaces the earlier recording
// that captured the off-narrative Iran/sanctions Quartz site.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot5');
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = 'http://127.0.0.1:8004';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: OUT_DIR, size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();
  const pause = (ms) => page.waitForTimeout(ms);

  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
  await pause(1800);

  // Sweep across the persona graph viewport
  const graph = page.locator('.graph').first();
  if (await graph.count()) {
    const box = await graph.boundingBox();
    if (box) {
      const cx = box.x + box.width / 2;
      const cy = box.y + box.height / 2;
      await page.mouse.move(cx - 220, cy - 60, { steps: 18 });
      await pause(550);
      await page.mouse.move(cx + 60, cy - 70, { steps: 22 });
      await pause(550);
      await page.mouse.move(cx + 220, cy + 80, { steps: 22 });
      await pause(700);
    }
  }

  // Scroll into belief trajectory
  await page.evaluate(() => window.scrollToSection('trajectory'));
  await pause(2200);

  // Scroll into 5-layer grounding
  await page.evaluate(() => window.scrollToSection('context'));
  await pause(2400);

  // Slow drift through the rest
  for (let i = 0; i < 3; i++) {
    await page.mouse.wheel(0, 180);
    await pause(700);
  }

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR)
    .filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO PRODUCED'); process.exit(1); }
  const finalPath = path.join(OUT_DIR, 'raw-shot5-quartz-navigate-v2.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), finalPath);
  console.log('VIDEO:', finalPath);
})();
