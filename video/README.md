# RZK.id — Instagram Story promo (1080×1920, 20 s)

Final video: `out/RZK-id-instagram-story.mp4` (H.264 High + AAC, 30 fps, 9:16, −14 LUFS, no watermark).
Cover frame: `out/RZK-id-cover.jpg`.

The video is made in code, so every Indonesian word renders as sharp, correctly spelled text:

| File | Purpose |
|---|---|
| `index.html` | All scenes (CSS 3D devices, glass UI, particles, kinetic type) driven by a deterministic `render(t)` |
| `audio.py` | Original synthesized music + whooshes/clicks/UI sounds synced to the timeline (royalty-free) |
| `render.mjs` | Captures 60 fps frames in headless Chromium, blends to 30 fps motion blur, encodes MP4 |
| `stills.mjs`, `sheet.sh` | Preview single frames / contact sheets |

Rebuild:
```bash
npm install
pip install numpy scipy imageio-ffmpeg
python3 audio.py soundtrack.wav
node render.mjs out/RZK-id-instagram-story.mp4
```
Live preview in a browser: open `index.html?play` (or `index.html?t=12.5` for a single moment).
Text or timings can be edited directly in `index.html` (scene blocks are commented `SCENE 1` … `SCENE 6`).
