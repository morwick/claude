# RZK.id — Instagram Story commercial (1080×1920, 20 s)

Final video: `out/RZK-id-instagram-story.mp4` (H.264 High + AAC, 30 fps, 9:16, −14 LUFS).
Cover frame: `out/RZK-id-cover.jpg`.

Concept: **"Dari ide → menjadi website profesional."** A single continuous journey:
idea (geometric seed) → wireframe → polished website → exploded design layers → devices → responsive → brand → CTA.

| Time | Scene | What happens |
|---|---|---|
| 0–3 s | Hook | Square morphs into a wireframe, which becomes a real website. "PUNYA IDE BISNIS?" → "WUJUDKAN JADI WEBSITE." |
| 3–6 s | Design | The site splits into 3D layers with Figma-style selections and redlines, then reassembles and docks into a laptop. "DIRANCANG SESUAI KEBUTUHAN ANDA." |
| 6–11 s | Services | Device carousel: Company Profile (laptop), Toko Online (phone), Web Application (monitor), Sistem Informasi (tablet), Aplikasi Custom (laptop), Landing Page (phone), each with a micro-interaction |
| 11–15 s | Difference | A live browser resize reflows desktop → tablet → phone, then three devices with menu, hover and cursor interactions. MODERN. / RESPONSIF. / PROFESIONAL. / CUSTOM. / SESUAI KEBUTUHAN BISNIS. |
| 15–17.4 s | Brand | All six screens form a grid, then collapse into the dot of **RZK.id**. Tagline: WEBSITE & APLIKASI UNTUK BISNIS ANDA |
| 17.4–20 s | CTA | SIAP PUNYA WEBSITE PROFESIONAL? · Konsultasi Gratis · WhatsApp **081364392661** · RZK.id, then a soft fade |

Every interface is real HTML with real Indonesian copy (Karsa Studio, Kopi Senja, Kasira, SIMPEG, Rancang, Rupa Academy are fictional demo brands). There are no AI-generated images, so all text is sharp and spelled correctly.

| File | Purpose |
|---|---|
| `index.html` | All scenes, driven by a deterministic `render(t)` |
| `audio.py` | Original synthesized music and sound design, synced to the timeline (royalty-free) |
| `render.mjs` | Captures 60 fps frames in headless Chromium, blends them to 30 fps with motion blur, and encodes the MP4 |
| `stills.mjs`, `sheet.sh` | Preview single frames or contact sheets |

Rebuild:
```bash
npm install
pip install numpy scipy imageio-ffmpeg
python3 audio.py soundtrack.wav
node render.mjs out/RZK-id-instagram-story.mp4
```
Live preview: open `index.html?play` (or `index.html?t=12.5` for a single moment).
