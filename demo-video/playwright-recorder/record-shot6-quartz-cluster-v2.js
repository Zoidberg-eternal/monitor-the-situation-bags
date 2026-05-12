// Shot 6 v2 — Quartz cluster + ReACT consensus against the Bags-narrative mock.
// Briefly re-establishes the graph, then jumps to cluster convergence and the
// ReACT consensus card. Target ~10s.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot6');
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
  await pause(1200);

  // Quick graph cluster sweep
  const graph = page.locator('.graph').first();
  if (await graph.count()) {
    const box = await graph.boundingBox();
    if (box) {
      const cx = box.x + box.width / 2;
      const cy = box.y + box.height / 2;
      await page.mouse.move(cx + 200, cy - 80, { steps: 18 });
      await pause(450);
      await page.mouse.move(cx - 200, cy + 60, { steps: 20 });
      await pause(700);
    }
  }

  // Cluster convergence section
  await page.evaluate(() => window.scrollToSection('cluster'));
  await pause(2400);

  // ReACT consensus card
  await page.evaluate(() => window.scrollToSection('react'));
  await pause(3200);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR)
    .filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO PRODUCED'); process.exit(1); }
  const finalPath = path.join(OUT_DIR, 'raw-shot6-quartz-report-v2.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), finalPath);
  console.log('VIDEO:', finalPath);
})();
