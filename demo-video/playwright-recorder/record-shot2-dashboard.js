// Shot 2 — Monitor dashboard, Bags.fm feed scrolling, anomaly highlight.
// Records the styled Monitor risk console mock with deliberate scroll + anomaly pulse.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot2');
fs.mkdirSync(OUT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: OUT_DIR, size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();
  const pause = (ms) => page.waitForTimeout(ms);

  await page.goto('http://localhost:8002/', { waitUntil: 'networkidle' });
  await pause(2000);

  // Scroll the feed slightly so it looks "alive"
  await page.evaluate(() => document.getElementById('feed').scrollTo({ top: 80, behavior: 'smooth' }));
  await pause(1800);
  await page.evaluate(() => document.getElementById('feed').scrollTo({ top: 160, behavior: 'smooth' }));
  await pause(1800);
  await page.evaluate(() => document.getElementById('feed').scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(2000);

  // Pulse the WIRED row (anomaly highlight)
  await page.evaluate(() => {
    const row = document.querySelector('.row[data-sym="WIRED"]');
    if (row) row.classList.add('pulse-row');
  });
  await pause(2800);

  // Show a quick anomaly log append
  await page.evaluate(() => {
    const log = document.getElementById('log');
    const e = document.createElement('div');
    e.className = 'entry warn';
    e.innerHTML = `<span class="ts">${new Date().toTimeString().slice(0,8)}</span>WIRED · velocity z-score breach detected — escalating to swarm`;
    log.appendChild(e);
  });
  await pause(2500);

  await page.evaluate(() => {
    const log = document.getElementById('log');
    const e = document.createElement('div');
    e.className = 'entry alert';
    e.innerHTML = `<span class="ts">${new Date().toTimeString().slice(0,8)}</span>WIRED · MiroShark swarm spinning up — 137 personas`;
    log.appendChild(e);
  });
  await pause(2500);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO'); process.exit(1); }
  const final = path.join(OUT_DIR, 'raw-shot2-dashboard.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), final);
  console.log('VIDEO:', final);
})();
