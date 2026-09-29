// Renders index.html frame-by-frame with headless Chromium and encodes an
// Instagram-Story-ready MP4 (1080x1920, 30 fps, H.264 + AAC).
// Frames are captured at 60 fps and pairs are blended for a subtle motion blur.
import { chromium } from 'playwright';
import { spawn, execSync } from 'child_process';
import path from 'path';

const OUT = process.argv[2] || 'out/RZK-id-instagram-story.mp4';
const DUR = 20, CAP_FPS = 60, WORKERS = +(process.env.WORKERS || 4);
const TOTAL = DUR * CAP_FPS;
const FF = execSync(`python3 -c "import imageio_ffmpeg as i;print(i.get_ffmpeg_exe())"`).toString().trim();

const ff = spawn(FF, [
  '-y', '-loglevel', 'error',
  '-f', 'image2pipe', '-framerate', String(CAP_FPS), '-c:v', 'mjpeg', '-i', '-',
  '-i', 'soundtrack.wav',
  '-filter_complex',
  '[0:v]tmix=frames=2:weights=1 1,fps=30,scale=1080:1920:out_color_matrix=bt709:flags=lanczos,format=yuv420p[v];' +
  '[1:a]loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[a]',
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-profile:v', 'high', '-level', '4.2',
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
  '-g', '60', '-bf', '2', '-movflags', '+faststart',
  '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
  '-t', String(DUR), OUT,
], { stdio: ['pipe', 'inherit', 'inherit'] });

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--allow-file-access-from-files'] });
const pages = [];
for (let w = 0; w < WORKERS; w++) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.ready);
  pages.push(page);
}

// Workers render ahead into a buffer; frames are written to ffmpeg strictly in order.
const done = new Map();
let next = 0, cursor = 0;
const t0 = Date.now();
async function worker(page) {
  while (true) {
    const i = cursor++;
    if (i >= TOTAL) return;
    await page.evaluate(t => window.render(t), i / CAP_FPS);
    done.set(i, await page.screenshot({ type: 'jpeg', quality: 98 }));
    while (done.has(next)) {
      const buf = done.get(next); done.delete(next);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      next++;
      if (next % 120 === 0) console.log(`frame ${next}/${TOTAL}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }
}
await Promise.all(pages.map(worker));
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log('done ->', OUT, `${((Date.now() - t0) / 1000).toFixed(0)}s`);
