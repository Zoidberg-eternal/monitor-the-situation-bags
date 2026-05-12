// Shot 8 — Solana Explorer transaction view
// Records a deliberate walkthrough of a USDC payment tx on Solana Explorer.
// Output: ./videos/<random>.webm (renamed/converted in post)

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, 'videos-shot8');
fs.mkdirSync(OUT_DIR, { recursive: true });

// USDC mainnet token mint - a stable, busy contract for the explorer walkthrough.
// We'll land on the USDC token page, then navigate into a recent transaction.
const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const EXPLORER_BASE = 'https://explorer.solana.com';

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: {
      dir: OUT_DIR,
      size: { width: 1920, height: 1080 },
    },
  });
  const page = await context.newPage();

  const pause = (ms) => page.waitForTimeout(ms);

  // Land on the USDC token page
  await page.goto(`${EXPLORER_BASE}/address/${USDC_MINT}`, { waitUntil: 'domcontentloaded' });
  await pause(3000);

  // Scroll the overview down a bit so the page settles visually
  await page.mouse.wheel(0, 200);
  await pause(2200);
  await page.mouse.wheel(0, 200);
  await pause(2000);

  // Click into the Transactions tab if present (Explorer shows it by default for tokens)
  // Hover over the first transaction row in the Transaction History table
  try {
    const firstTxRow = page.locator('table tbody tr').first();
    await firstTxRow.scrollIntoViewIfNeeded({ timeout: 5000 });
    await pause(800);
    await firstTxRow.hover({ timeout: 3000 }).catch(() => {});
    await pause(1200);
    const firstTxLink = firstTxRow.locator('a').first();
    const hasLink = await firstTxLink.count();
    if (hasLink) {
      await firstTxLink.click({ timeout: 5000 });
      await page.waitForLoadState('domcontentloaded');
      await pause(2500);
      // Scroll through the tx detail card
      await page.mouse.wheel(0, 300);
      await pause(1500);
      await page.mouse.wheel(0, 300);
      await pause(2000);
    } else {
      // Fallback: stay on the token page and scroll
      await page.mouse.wheel(0, 400);
      await pause(2000);
    }
  } catch (err) {
    console.error('navigation fallback:', err.message);
    await pause(2000);
  }

  await context.close();
  await browser.close();

  // The most-recently-written file in OUT_DIR is our recording.
  const files = fs.readdirSync(OUT_DIR)
    .filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (files.length === 0) {
    console.error('NO VIDEO PRODUCED');
    process.exit(1);
  }
  const finalName = path.join(OUT_DIR, 'raw-shot8-solana-explorer.webm');
  fs.renameSync(path.join(OUT_DIR, files[0].f), finalName);
  console.log('VIDEO:', finalName);
})();
