// Shot 5 — Quartz graph navigation
// Lands on the Monitor Quartz site, opens an agent node, hovers edges in the graph,
// scrolls through belief/trajectory content.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot5');
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = 'http://localhost:8001';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: OUT_DIR, size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();
  const pause = (ms) => page.waitForTimeout(ms);

  // Open the agents index (rich graph + many nodes for visual density)
  await page.goto(`${BASE}/agents/`, { waitUntil: 'networkidle' });
  await pause(2000);

  // Scroll a touch so the local graph renders into view
  await page.mouse.wheel(0, 250);
  await pause(1200);

  // Hover the graph node area
  const graph = page.locator('.graph').first();
  if (await graph.count()) {
    const box = await graph.boundingBox();
    if (box) {
      // Slow sweep across the graph viewport
      const cx = box.x + box.width / 2;
      const cy = box.y + box.height / 2;
      await page.mouse.move(cx - 80, cy - 40, { steps: 20 });
      await pause(700);
      await page.mouse.move(cx + 60, cy + 30, { steps: 20 });
      await pause(900);
    }
  }

  // Click into one of the agent persona pages (hyperliquid-dex is dense)
  await page.goto(`${BASE}/agents/hyperliquid-dex`, { waitUntil: 'networkidle' });
  await pause(2500);

  // Slow scroll-through to show the belief / state content
  for (let i = 0; i < 5; i++) {
    await page.mouse.wheel(0, 280);
    await pause(1100);
  }

  // Land on a token page to extend the journey
  await page.goto(`${BASE}/agents/iran`, { waitUntil: 'networkidle' });
  await pause(2200);
  await page.mouse.wheel(0, 250);
  await pause(1500);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR)
    .filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO PRODUCED'); process.exit(1); }
  const final = path.join(OUT_DIR, 'raw-shot5-quartz-navigate.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), final);
  console.log('VIDEO:', final);
})();
