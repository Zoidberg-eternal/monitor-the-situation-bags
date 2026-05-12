import { chromium } from "playwright";
import { mkdir, rename, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));   // .../scratch-bags/recorder
const OUT  = resolve(ROOT, "..");                       // .../scratch-bags

const MOCKS = [
  { name: "outro", url: "http://localhost:9090/mocks/outro.html", seconds: 32 },
];

const browser = await chromium.launch({ headless: true });

for (const mock of MOCKS) {
  const dir = join(ROOT, "videos", mock.name);
  if (existsSync(dir)) await rm(dir, { recursive: true });
  await mkdir(dir, { recursive: true });

  console.log(`[record] ${mock.name} ← ${mock.url}`);
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir, size: { width: 1920, height: 1080 } },
  });
  const page = await ctx.newPage();
  await page.goto(mock.url, { waitUntil: "load" });
  await page.waitForTimeout(mock.seconds * 1000);
  await page.close();
  await ctx.close();

  // Playwright writes one .webm in dir; find it and move to a stable name
  const fs = await import("node:fs/promises");
  const files = (await fs.readdir(dir)).filter(f => f.endsWith(".webm"));
  if (files.length === 0) { console.error("no video produced for " + mock.name); continue; }
  const src = join(dir, files[0]);
  const dst = join(OUT, `mock-${mock.name}.webm`);
  await rename(src, dst);
  await rm(dir, { recursive: true });
  console.log(`  → ${dst}`);
}

await browser.close();
console.log("done");
