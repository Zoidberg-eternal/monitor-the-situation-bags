#!/usr/bin/env node
/**
 * Generate hackathon demo video segments using Replicate API
 * Uses Wan 2.1 (text-to-video) — free tier eligible
 *
 * Usage: REPLICATE_API_TOKEN=your_token node scripts/generate-demo-video.mjs
 */

const API_TOKEN = process.env.REPLICATE_API_TOKEN;
if (!API_TOKEN) {
  console.error('Set REPLICATE_API_TOKEN environment variable.');
  process.exit(1);
}

const REPLICATE_API = 'https://api.replicate.com/v1';

async function createPrediction(model, input) {
  const res = await fetch(`${REPLICATE_API}/models/${model}/predictions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_TOKEN}`,
      'Content-Type': 'application/json',
      'Prefer': 'wait'
    },
    body: JSON.stringify({ input })
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err.slice(0, 300)}`);
  }
  return res.json();
}

async function pollPrediction(url) {
  for (let i = 0; i < 120; i++) {
    await new Promise(r => setTimeout(r, 5000));
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${API_TOKEN}` }
    });
    const data = await res.json();
    if (data.status === 'succeeded') return data;
    if (data.status === 'failed' || data.status === 'canceled') {
      throw new Error(`Prediction ${data.status}: ${data.error || 'unknown'}`);
    }
    if (i % 6 === 0) console.log(`  ...polling (${data.status})`);
  }
  throw new Error('Timed out after 10 minutes');
}

async function generateVideo(name, prompt, opts = {}) {
  console.log(`\n>>> ${name}`);
  console.log(`    Prompt: ${prompt.slice(0, 120)}...`);

  // Using bytedance/seedance-1-lite on Replicate
  const model = 'bytedance/seedance-1-lite';
  const input = {
    prompt,
    aspect_ratio: opts.aspect_ratio || '16:9',
    duration: opts.duration || 5,
    seed: opts.seed || -1,
    ...opts.extra
  };

  try {
    let data = await createPrediction(model, input);

    // If not yet succeeded, poll
    if (data.status !== 'succeeded') {
      console.log(`  Request ID: ${data.id}`);
      data = await pollPrediction(data.urls.get);
    }

    const url = Array.isArray(data.output) ? data.output[0] : data.output;
    console.log(`  ✓ Done: ${url}`);
    return { name, url, status: 'ok' };
  } catch (e) {
    console.error(`  ✗ Failed: ${e.message}`);
    return { name, error: e.message, status: 'failed' };
  }
}

// ─── VIDEO SEGMENTS ─────────────────────────────────────────────────

const segments = [
  {
    name: 'Section 1 — Cinematic Intro (5s)',
    prompt: 'Cinematic dark futuristic control room with holographic glowing displays and abstract waveform visualizations. Red warning lights pulse across the room. Camera slowly pushes forward through layers of floating light particles. Dark moody lighting with blue and amber accents. No text, no numbers, no letters, no words anywhere in the scene. Pure abstract visual atmosphere.',
    opts: { duration: 5, aspect_ratio: '16:9' }
  },
  {
    name: 'Section 2 — Terminal Monitoring (5s)',
    prompt: 'Abstract visualization of streaming data as flowing green and cyan light particles moving downward like rain on a dark background. Rows of glowing dots pulse in rhythmic patterns suggesting real-time data processing. Soft monitor glow illuminates a dark room. No readable text, no numbers, no letters. Pure abstract light and motion.',
    opts: { duration: 5, aspect_ratio: '16:9' }
  },
  {
    name: 'Section 2b — Risk Dashboard (5s)',
    prompt: 'Four abstract circular rings of light on a dark background, each a different color: blue, orange, green, red. The rings slowly rotate and pulse. Suddenly the red ring flares brightly and expands with a pulsing glow, while the others dim. Abstract energy visualization, no text, no numbers, no letters, no UI elements. Pure geometric light animation.',
    opts: { duration: 5, aspect_ratio: '16:9' }
  },
  {
    name: 'Section 3 — Multi-Agent Swarm (5s)',
    prompt: 'Abstract constellation of glowing orbs floating in dark space, connected by thin beams of light. Each orb is a different color: amber, green, blue, red, white. Light pulses travel along the connections between orbs. A translucent sphere slowly rotates in the background. No text, no numbers, no letters. Futuristic, clean, cinematic particle effects.',
    opts: { duration: 5, aspect_ratio: '16:9' }
  },
  {
    name: 'Section 4 — x402 Payment Flow (5s)',
    prompt: 'Abstract visualization of energy transfer. A glowing blue light particle travels along a neon pathway, reaches a shimmering translucent barrier, then a golden coin-shaped light appears and the barrier dissolves into sparkling particles. Energy flows through to the other side as golden light streams. Dark space background with purple and gold hexagonal patterns. No text, no numbers, no letters.',
    opts: { duration: 5, aspect_ratio: '16:9' }
  },
  {
    name: 'Section 5 — Cinematic Outro (5s)',
    prompt: 'Camera pulls back from a single bright glowing orb to reveal hundreds of interconnected light points spanning across a dark void, forming the shape of continents. Ribbons of light flow between the points. Epic cinematic scale, dark space with deep blue and gold tones. Large clear dark area in the center. No text, no numbers, no letters. Inspiring mood.',
    opts: { duration: 5, aspect_ratio: '16:9' }
  }
];

// ─── MAIN ───────────────────────────────────────────────────────────

async function main() {
  console.log('=== Monitor the Situation — Demo Video Generator ===');
  console.log(`Using Replicate API with bytedance/seedance-1-lite`);
  console.log(`Generating ${segments.length} segments...\n`);

  const results = [];
  for (let i = 0; i < segments.length; i++) {
    if (i > 0) {
      console.log('  (waiting 15s for rate limit...)');
      await new Promise(r => setTimeout(r, 15000));
    }
    const result = await generateVideo(segments[i].name, segments[i].prompt, segments[i].opts);
    results.push(result);
  }

  console.log('\n\n=== RESULTS ===\n');
  for (const r of results) {
    console.log(`${r.status === 'ok' ? '✓' : '✗'} ${r.name}`);
    console.log(`  ${r.url || r.error}\n`);
  }

  // Save results
  const fs = await import('fs');
  const outPath = new URL('../demo-video-segments.json', import.meta.url).pathname;
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`Results saved to ${outPath}`);
}

main().catch(e => { console.error(e); process.exit(1); });
