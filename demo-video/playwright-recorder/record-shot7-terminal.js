// Shot 7 — Terminal x402 402 → pay → 200 walkthrough.
// Plays a scripted terminal animation (HTML/JS) and records the viewport.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot7');
fs.mkdirSync(OUT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: OUT_DIR, size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();

  await page.goto('http://localhost:8003/', { waitUntil: 'domcontentloaded' });

  // The terminal animation runs ~17s. Capture 17s of it.
  await page.waitForTimeout(17000);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO'); process.exit(1); }
  const final = path.join(OUT_DIR, 'raw-shot7-terminal-x402.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), final);
  console.log('VIDEO:', final);
})();
