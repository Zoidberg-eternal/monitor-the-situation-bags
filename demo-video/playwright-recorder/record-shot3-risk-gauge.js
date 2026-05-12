// Shot 3 — Composite risk gauge flip: green → amber → red on the WIRED token.
// Close-up on the gauge panel; the rest of the dashboard scrolls offscreen.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot3');
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

  // Zoom in on the right column (gauge + log). We do this by enlarging the right panel.
  await page.evaluate(() => {
    document.querySelector('.main').style.gridTemplateColumns = '0fr 1fr';
    document.querySelector('.right').style.transform = 'scale(1.15)';
    document.querySelector('.right').style.transformOrigin = 'top left';
  });
  await pause(1200);

  // Animate the gauge: 12 (green) → 38 (amber) → 72 (red), then settle at 64 (red).
  const steps = [
    { v: 12, color: '#4ade80', label: 'SAFE · monitoring' },
    { v: 22, color: '#4ade80', label: 'SAFE · monitoring' },
    { v: 38, color: '#f59e0b', label: 'WATCH · investigating' },
    { v: 52, color: '#f59e0b', label: 'WATCH · investigating' },
    { v: 72, color: '#ef4444', label: 'RISK · swarm triggered' },
    { v: 64, color: '#ef4444', label: 'RISK · swarm running' },
  ];
  for (const s of steps) {
    await page.evaluate(({ v, color, label }) => {
      // expose setRisk via window for the inline script
      const arc = document.getElementById('arc');
      const needle = document.getElementById('needle');
      const score = document.getElementById('score');
      const verdict = document.getElementById('verdict');
      const off = Math.max(0, Math.min(283, 283 - v * 2.83));
      arc.setAttribute('stroke-dashoffset', off);
      arc.style.stroke = color;
      needle.style.background = color;
      needle.style.transform = `rotate(${-78 + (v / 100) * 156}deg)`;
      score.textContent = v;
      verdict.className = 'verdict ' + (v < 30 ? 'green' : v < 60 ? 'amber' : 'red');
      verdict.textContent = label;
    }, s);
    await pause(1100);
  }
  // hold the final state
  await pause(2500);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (!files.length) { console.error('NO VIDEO'); process.exit(1); }
  const final = path.join(OUT_DIR, 'raw-shot3-risk-gauge.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), final);
  console.log('VIDEO:', final);
})();
