"""Original soundtrack + sound design for the RZK.id story (20 s, 48 kHz stereo).

Everything is synthesized here (no samples), so the audio is royalty-free.
Timings mirror the animation timeline in index.html.
"""
import numpy as np
from scipy import signal
import wave, sys

SR = 48000
DUR = 20.0
N = int(SR * DUR)
BPM = 120
BEAT = 60 / BPM
rng = np.random.default_rng(7)

L = np.zeros(N); Rr = np.zeros(N)            # dry stereo bus
revL = np.zeros(N); revR = np.zeros(N)       # reverb send
duck_src = np.zeros(N)                       # kick envelope used for side-chain


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    if i < 0:
        sig = sig[-i:]; i = 0; j = min(N, len(sig))
    buf[i:j] += sig[: j - i] * gain


def put(sig, t0, gain=1.0, pan=0.0, rev=0.0):
    gl = gain * np.cos((pan + 1) * np.pi / 4)
    gr = gain * np.sin((pan + 1) * np.pi / 4)
    add(L, sig, t0, gl); add(Rr, sig, t0, gr)
    if rev:
        add(revL, sig, t0, gl * rev); add(revR, sig, t0, gr * rev)


def env_adsr(n, a, d, s, r, sus_len):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sl = max(0, int(sus_len * SR) - a - d)
    e = np.concatenate([np.linspace(0, 1, max(a, 1)), np.linspace(1, s, max(d, 1)), np.full(sl, s), np.linspace(s, 0, max(r, 1))])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def lp(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR / 2 - 100), 'low', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc, 'high', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def bp(x, f1, f2, order=2):
    sos = signal.butter(order, [f1, f2], 'band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def svf_sweep(x, f_curve, q=0.7, mode='bp'):
    """Time-varying state-variable filter (Chamberlin)."""
    low = band = 0.0
    out = np.empty_like(x)
    damp = 1 / q
    for i in range(len(x)):
        f = 2 * np.sin(np.pi * min(f_curve[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        out[i] = band if mode == 'bp' else (low if mode == 'lp' else high)
    return out


def saw(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((freq * t + phase) % 1.0) - 1


# ------------------------------------------------------------------ instruments
def kick(level=1.0, length=0.45):
    n = int(length * SR); t = np.arange(n) / SR
    f = 42 + 110 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7.5)
    click = hp(rng.standard_normal(n), 3000) * np.exp(-t * 400) * 0.25
    return np.tanh((body + click) * 1.6) * level


def hat(open_=False):
    n = int((0.22 if open_ else 0.06) * SR); t = np.arange(n) / SR
    x = hp(rng.standard_normal(n), 8000, 4) * np.exp(-t * (18 if open_ else 70))
    return x * 0.5


def clap():
    n = int(0.35 * SR); t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 900, 3200)
    e = np.zeros(n)
    for d in (0, 0.011, 0.022):
        i = int(d * SR); e[i:] += np.exp(-(t[: n - i]) * 60) * 0.6
    e += np.exp(-t * 14) * 0.35
    return x * e


def pluck(freq, length=0.5, bright=1.0):
    n = int(length * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 14):
        if freq * k > 16000:
            break
        x += (1 / k) * np.sin(2 * np.pi * freq * k * t + k) * np.exp(-t * (4 + k * 3.2 / bright))
    return x * 0.35 * np.minimum(1, t * 400)


def pad_chord(notes, length, bright=2400):
    n = int(length * SR)
    xl = np.zeros(n); xr = np.zeros(n)
    for m in notes:
        f = mtof(m)
        for d, pan in ((-0.11, -1), (-0.04, -0.4), (0.0, 0), (0.05, 0.4), (0.12, 1)):
            s = saw(f * 2 ** (d / 12), n, rng.random())
            xl += s * (1 - pan) / 2; xr += s * (1 + pan) / 2
    xl = hp(lp(xl, bright, 2), 160); xr = hp(lp(xr, bright, 2), 160)
    e = env_adsr(n, 0.35, 0.3, 0.85, 0.6, length - 0.6)
    g = 0.035 / np.sqrt(len(notes))
    return xl * e * g, xr * e * g


def bass_note(m, length):
    n = int(length * SR); t = np.arange(n) / SR
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.tanh(3 * np.sin(2 * np.pi * f * t)) + 0.15 * lp(saw(f, n), 600)
    e = np.minimum(1, t * 200) * np.exp(-t * 7.0)
    return x * e * 0.26


def whoosh(length=0.7, f0=300, f1=5000, level=0.5, peak=0.6, rev=0.35, pan_sweep=True, t0=0.0):
    n = int(length * SR); tt = np.linspace(0, 1, n)
    curve = f0 * (f1 / f0) ** (np.sin(np.pi * np.clip(tt / (2 * peak), 0, 0.5)) if peak < 1 else tt)
    x = svf_sweep(rng.standard_normal(n) * 0.5, curve, q=1.4)
    e = np.where(tt < peak, (tt / peak) ** 2, np.exp(-(tt - peak) / (1 - peak) * 4))
    x = x * e * level
    if pan_sweep:
        pan = np.linspace(-0.7, 0.7, n)
        gl = np.cos((pan + 1) * np.pi / 4); gr = np.sin((pan + 1) * np.pi / 4)
        add(L, x * gl, t0); add(Rr, x * gr, t0); add(revL, x * gl * rev, t0); add(revR, x * gr * rev, t0)
    else:
        put(x, t0, 1, 0, rev)


def blip(freq=2400, length=0.05, level=0.18, t0=0.0, pan=0.0, rev=0.2, sweep=1.0):
    n = int(length * SR); t = np.arange(n) / SR
    f = freq * sweep ** (t / length)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (6 / length)) * np.minimum(1, t * 3000)
    put(x, t0, level, pan, rev)


def click(t0, level=0.35, pan=0.0):
    n = int(0.03 * SR); t = np.arange(n) / SR
    x = hp(rng.standard_normal(n), 2500) * np.exp(-t * 350) + np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 250) * 0.6
    put(x, t0, level, pan, 0.15)


def pop(t0, freq=900, level=0.28, pan=0.0):
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = freq * (1 + 1.2 * np.exp(-t * 60))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    put(x, t0, level, pan, 0.3)


def digital(t0, level=0.12, pan=0.0, count=6, base=2600):
    for i in range(count):
        blip(base * (1 + 0.25 * ((i * 7) % 5)), 0.028, level, t0 + i * 0.035, pan + (0.3 if i % 2 else -0.3), 0.25)


def impact(t0, level=1.0):
    n = int(2.2 * SR); t = np.arange(n) / SR
    f = 30 + 70 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    crash = hp(rng.standard_normal(n), 3500) * np.exp(-t * 3.2) * 0.22
    put(np.tanh(sub * 1.4) * 0.75 * level, t0, 1, 0, 0.1)
    put(crash * level, t0, 1, -0.2, 0.6)
    put(hp(rng.standard_normal(n), 3500) * np.exp(-t * 3.0) * 0.2 * level, t0, 1, 0.2, 0.6)


def shimmer(t0, length=1.2, level=0.07, base=76):
    for i, m in enumerate([base, base + 7, base + 12, base + 16, base + 19, base + 24]):
        blip(mtof(m), 0.5, level, t0 + i * length / 8, pan=(-0.6 + i * 0.25), rev=0.8)


def riser(t0, length, level=0.35):
    n = int(length * SR); tt = np.linspace(0, 1, n)
    x = svf_sweep(rng.standard_normal(n) * 0.5, 400 * (9000 / 400) ** (tt ** 1.6), q=2.0)
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (tt * 2)) / SR) * 0.25
    put((x + tone) * tt ** 2.2 * level, t0, 1, 0, 0.5)


# ------------------------------------------------------------------ arrangement
CHORDS = [  # (start, end, pad notes, bass root)
    (0.0, 4.0, [53, 57, 60, 64], 41),        # Fmaj7
    (4.0, 8.0, [57, 60, 64, 67], 45),        # Am7
    (8.0, 12.0, [50, 53, 57, 60, 64], 38),   # Dm9
    (12.0, 15.3, [46, 50, 53, 57], 34),      # Bbmaj7
    (15.3, 16.12, [48, 52, 55, 62], 36),     # Cadd9 (build)
    (16.22, 20.0, [53, 57, 60, 64, 67], 41), # Fmaj9 (resolve on logo)
]
for (a, b, notes, root) in CHORDS:
    bright = 1400 if a < 3 else (3200 if a >= 16 else 2400)
    pl, pr = pad_chord([n for n in notes], b - a + 0.6, bright)
    add(L, pl, a); add(Rr, pr, a); add(revL, pl * 0.5, a); add(revR, pr * 0.5, a)

# drums
for i in range(int(DUR / BEAT * 4)):             # 16th grid
    t = i * BEAT / 4
    beat_pos = i % 4; beat = i // 4
    if 16.12 <= t < 16.22 or t >= 19.5:
        continue
    if t < 1.0:
        continue
    in_final = t >= 16.22
    # kick
    if beat_pos == 0 and (t < 3.0 and beat % 2 == 0 or 3.0 <= t < 16.12 or in_final and t < 19.0 and beat % 2 == 0):
        k = kick(0.95)
        put(k, t, 1.0, 0, 0.02)
        add(duck_src, np.exp(-np.arange(int(0.3 * SR)) / SR * 12), t)
    # hats
    if t >= 3.0 and not in_final:
        if beat_pos == 2:
            put(hat(True), t, 0.35, 0.25, 0.1)
        elif t >= 14.0 or beat_pos in (1, 3):
            put(hat(), t, 0.22 if beat_pos else 0.12, -0.3, 0.05)
    # clap on 2 & 4
    if t >= 3.0 and not in_final and beat_pos == 0 and beat % 2 == 1:
        put(clap(), t, 0.5, 0.05, 0.45)
# snare roll build 15.3 -> 16.12
for i in range(18):
    t = 15.3 + i * (0.82 / 18)
    put(clap(), t, 0.12 + 0.3 * i / 18, 0.0, 0.3)

# bass: 8th-note pulses from 3 s
for (a, b, notes, root) in CHORDS:
    t = max(a, 3.0)
    while t < b - 1e-6:
        if 16.12 <= t < 16.22 or t >= 19.0:
            break
        if t >= 3.0:
            put(bass_note(root + (12 if int(round(t / (BEAT / 2))) % 2 else 0) * 0, BEAT / 2), t + BEAT / 4, 0.9, 0, 0)
        t += BEAT / 2

# arp (16ths) from 1.0 (sparse) then full from 6.0
arp_pattern = [0, 2, 1, 3, 2, 1, 3, 4]
for (a, b, notes, root) in CHORDS:
    tones = sorted(notes) + [notes[0] + 12, notes[1] + 12]
    t = a
    i = 0
    while t < b - 1e-6:
        if (t >= 1.0 and (t >= 6.0 or i % 2 == 0)) and not (16.12 <= t < 16.22) and t < 19.2:
            m = tones[arp_pattern[i % 8] % len(tones)] + 12
            put(pluck(mtof(m), 0.35, 1.2 if t >= 6 else 0.8), t, 0.16 if t >= 6 else 0.11, (-0.5 if i % 2 else 0.5), 0.35)
        t += BEAT / 4; i += 1

# ------------------------------------------------------------------ sound design (synced to picture)
# scene 1: seed shape -> wireframe -> website
pop(0.05, 1200, 0.22, 0)                            # geometric seed appears
whoosh(0.6, 250, 3500, 0.22, 0.6, t0=0.3)           # shape stretches into a window
whoosh(0.4, 500, 5000, 0.12, 0.5, t0=0.18, pan_sweep=False)   # headline in
for i in range(8):                                   # wireframe blocks ticking in
    click(0.74 + i * 0.035, 0.08, -0.4 + i * 0.1)
digital(1.3, 0.06, 0.0, 8, 2800)                     # content fills
impact(1.6, 0.35)                                    # "WUJUDKAN JADI WEBSITE."
whoosh(0.4, 500, 5000, 0.14, 0.5, t0=1.5, pan_sweep=False)
# scene 2: exploded layers, selections, reassemble, dock
whoosh(1.0, 150, 3000, 0.32, 0.55, t0=2.95)
impact(3.2, 0.25)
for t, pn in ((3.95, -0.3), (4.35, 0.2), (4.7, 0.4)):
    click(t, 0.3, pn); blip(2600, 0.04, 0.08, t + 0.02, pn, 0.3)
pop(4.5, 700, 0.18, 0.2)
whoosh(0.8, 3000, 250, 0.26, 0.5, t0=5.0)           # collapse back
pop(5.9, 420, 0.3, 0)                                # docks into the laptop
# scene 3: service carousel
for t in (6.66, 7.5, 8.35, 9.2, 10.0, 10.82):
    whoosh(0.5, 300, 4500, 0.3, 0.5, t0=t - 0.05)
    blip(mtof(88), 0.08, 0.06, t + 0.2, 0.2, 0.4)
whoosh(0.5, 900, 2500, 0.08, 0.5, t0=6.3, pan_sweep=False)   # site scroll
click(7.28, 0.35, 0.3); pop(7.33, 1000, 0.2, 0.3); pop(7.4, 1300, 0.15, 0.3)   # add to cart
digital(7.65, 0.05, -0.2, 6, 3000)                   # charts draw
pop(8.08, 900, 0.2, 0.5); blip(1800, 0.1, 0.08, 8.1, 0.5, 0.3)   # notification
for k in range(4):                                   # typing "Dewi"
    click(8.72 + k * 0.09, 0.14, -0.2)
blip(2200, 0.06, 0.06, 9.14, 0, 0.3)
click(9.64, 0.28, -0.2); pop(10.13, 600, 0.26, 0.3)  # drag and drop
click(10.74, 0.3, 0)                                 # CTA press
# scene 4: responsive
for t in (11.12, 11.8, 12.46, 13.13):
    whoosh(0.3, 600, 5000, 0.14, 0.5, t0=t - 0.12, pan_sweep=False)
for k, t in enumerate((11.14, 11.82, 12.48, 13.15, 13.82)):
    blip(mtof(84 + [0, 2, 4, 7, 12][k]), 0.14, 0.09, t + 0.06, (-0.3, 0.3)[k % 2], 0.4)
click(11.45, 0.2, 0.5)
whoosh(0.7, 1200, 2200, 0.08, 0.5, t0=11.5, pan_sweep=False)  # dragging the window edge
whoosh(0.6, 1200, 2200, 0.08, 0.5, t0=12.3, pan_sweep=False)
pop(12.98, 500, 0.24, 0.3)                           # becomes a phone
whoosh(0.8, 200, 3000, 0.25, 0.5, t0=13.1)           # pull back to three devices
whoosh(0.35, 1500, 4500, 0.1, 0.5, t0=13.93, pan_sweep=False)  # mobile menu
click(14.2, 0.18, -0.4); click(14.5, 0.22, 0.2)
# scene 5: screens assemble -> logo
whoosh(0.9, 180, 4000, 0.4, 0.55, t0=14.9)
for i in range(6):
    pop(15.05 + i * 0.06, 700 + i * 90, 0.12, (-0.5, 0.5)[i % 2])
riser(15.35, 0.85, 0.3)
whoosh(0.4, 4000, 200, 0.3, 0.5, t0=15.9, pan_sweep=False)
impact(16.22, 0.9); shimmer(16.3, 1.2, 0.05, 81)
whoosh(0.5, 400, 4000, 0.12, 0.5, t0=16.36, pan_sweep=False)
# scene 6: CTA
whoosh(0.6, 300, 3500, 0.2, 0.5, t0=17.3)
pop(17.55, 700, 0.18, 0); pop(17.9, 900, 0.14, -0.2)
pop(18.05, 600, 0.28, 0); click(18.05, 0.15, 0)
shimmer(18.45, 0.8, 0.045, 88); blip(mtof(96), 0.4, 0.05, 18.9, 0.4, 0.7)

# ------------------------------------------------------------------ mix
# side-chain duck on the music bus (approximation: duck everything except the kick itself is fine at this level)
duck = 1 - 0.45 * np.clip(signal.lfilter([1], [1, -0.0], duck_src), 0, 1)
# short pre-drop gap before the final impact
gap = np.ones(N); g0, g1 = int(16.12 * SR), int(16.22 * SR)
gap[g0:g1] = 0.08; gap[g0 - 480:g0] = np.linspace(1, 0.08, 480)
L *= duck * gap; Rr *= duck * gap
revL *= gap; revR *= gap

# reverb: stereo decorrelated exponentially decaying noise IR
irn = int(2.2 * SR); ti = np.arange(irn) / SR
irL = rng.standard_normal(irn) * np.exp(-ti * 3.0); irR = rng.standard_normal(irn) * np.exp(-ti * 3.0)
irL = lp(irL, 7000); irR = lp(irR, 7000)
irL /= np.sqrt(np.sum(irL ** 2)); irR /= np.sqrt(np.sum(irR ** 2))
wetL = signal.fftconvolve(hp(revL, 200), irL)[:N]
wetR = signal.fftconvolve(hp(revR, 200), irR)[:N]
L += wetL * 0.55; Rr += wetR * 0.55

# ping-pong delay on the whole wet-ish bus at dotted 8th (subtle)
d = int(BEAT * 0.75 * SR)
dl = np.zeros(N); dr = np.zeros(N)
dl[d:] += Rr[:-d] * 0.12; dr[d:] += L[:-d] * 0.12
L += lp(dl, 4000); Rr += lp(dr, 4000)

mix = np.stack([L, Rr], 1)
mix = hp(mix.T, 28).T
# gentle master fade at the very end
fade = np.ones(N); fn = int(0.5 * SR); fade[-fn:] = np.linspace(1, 0, fn) ** 1.5
mix *= fade[:, None]
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix /= np.max(np.abs(mix)) / 0.89

out = sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav'
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out)
