// Shot 6 — Quartz cluster view + ReACT consensus card
// Open a simulation page (full agent cluster), hover graph, scroll into consensus output.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot6');
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

  // Load a simulation overview — these have the densest graph and the most narrative
  await page.goto(`${BASE}/simulations/sim_582083f0d01a`, { waitUntil: 'networkidle' });
  await pause(2200);

  // Sweep mouse across the graph viewport for the cluster reveal
  const graph = page.locator('.graph').first();
  if (await graph.count()) {
    const box = await graph.boundingBox();
    if (box) {
      const cx = box.x + box.width / 2;
      const cy = box.y + box.height / 2;
      await page.mouse.move(cx - 120, cy - 60, { steps: 25 });
      await pause(800);
      await page.mouse.move(cx + 100, cy + 50, { steps: 25 });
      await pause(900);
    }
  }

  // Scroll down through the narrative + consensus output
  for (let i = 0; i < 5; i++) {
    await page.mouse.wheel(0, 280);
    await pause(800);
  }

  // Land on a token (consensus output context)
  await page.goto(`${BASE}/tokens/`, { waitUntil: 'networkidle' });
  await pause(1500);
  await page.mouse.wheel(0, 250);
  await pause(1500);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR)
    .filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO PRODUCED'); process.exit(1); }
  const final = path.join(OUT_DIR, 'raw-shot6-quartz-report.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), final);
  console.log('VIDEO:', final);
})();
