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
    (12.0, 16.0, [46, 50, 53, 57], 34),      # Bbmaj7
    (16.0, 16.9, [48, 52, 55, 62], 36),      # Cadd9 (build)
    (17.0, 20.0, [53, 57, 60, 64, 67], 41),  # Fmaj9 (resolve)
]
for (a, b, notes, root) in CHORDS:
    bright = 1400 if a < 3 else (3200 if a >= 17 else 2400)
    pl, pr = pad_chord([n for n in notes], b - a + 0.6, bright)
    add(L, pl, a); add(Rr, pr, a); add(revL, pl * 0.5, a); add(revR, pr * 0.5, a)

# drums
for i in range(int(DUR / BEAT * 4)):             # 16th grid
    t = i * BEAT / 4
    beat_pos = i % 4; beat = i // 4
    if 16.9 <= t < 17.0 or t >= 19.5:
        continue
    if t < 1.0:
        continue
    in_final = t >= 17.0
    # kick
    if beat_pos == 0 and (t < 3.0 and beat % 2 == 0 or 3.0 <= t < 16.9 or in_final and t < 19.0 and beat % 2 == 0):
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
# snare roll build 16.0 -> 16.9
for i in range(18):
    t = 16.0 + i * (0.9 / 18)
    put(clap(), t, 0.12 + 0.3 * i / 18, 0.0, 0.3)

# bass: 8th-note pulses from 3 s
for (a, b, notes, root) in CHORDS:
    t = max(a, 3.0)
    while t < b - 1e-6:
        if 16.9 <= t < 17.0 or t >= 19.0:
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
        if (t >= 1.0 and (t >= 6.0 or i % 2 == 0)) and not (16.9 <= t < 17.0) and t < 19.2:
            m = tones[arp_pattern[i % 8] % len(tones)] + 12
            put(pluck(mtof(m), 0.35, 1.2 if t >= 6 else 0.8), t, 0.16 if t >= 6 else 0.11, (-0.5 if i % 2 else 0.5), 0.35)
        t += BEAT / 4; i += 1

# ------------------------------------------------------------------ sound design (synced to picture)
whoosh(0.35, 200, 3000, 0.25, 0.9, t0=-0.05)      # into logo
impact(0.28, 0.55); shimmer(0.3, 1.0, 0.05)
whoosh(0.9, 180, 2500, 0.28, 0.5, t0=1.0)         # laptop rises
whoosh(0.8, 300, 4000, 0.22, 0.5, t0=1.3)         # phone slides in
for t in (1.62, 1.75, 1.9, 2.02):
    click(t, 0.16, 0.2)
whoosh(0.7, 250, 6000, 0.45, 0.55, t0=2.62)       # scene 1 -> 2 streak
blip(1400, 0.08, 0.12, 3.02, 0, 0.3, 1.5)
for t, pn in ((3.45, -0.5), (3.55, 0.5), (3.6, -0.4), (3.75, -0.5), (3.9, 0.5)):
    pop(t, 700 + 200 * (pn > 0), 0.24, pn)
click(4.6, 0.5, -0.2)                               # mouse click
blip(3200, 0.04, 0.1, 4.62, -0.2, 0.3)
whoosh(0.7, 800, 3000, 0.12, 0.5, t0=4.8, pan_sweep=False)  # scroll
whoosh(0.75, 150, 7000, 0.6, 0.75, t0=5.3)        # dive into the screen
impact(5.9, 0.35)
for i, t in enumerate(np.arange(5.95, 6.7, 0.1)):
    click(t, 0.1, -0.4 + 0.1 * i)
for t, pn in ((7.2, -0.6), (7.4, 0.6), (7.6, 0.5)):
    pop(t, 820, 0.24, pn)
digital(7.8, 0.09, 0.0, 8)
click(8.3, 0.3, 0.5); click(8.6, 0.3, 0.5)
digital(8.9, 0.05, 0.3, 4, 3400)
whoosh(0.8, 300, 5000, 0.45, 0.6, t0=9.25)        # scene 3 -> 4
impact(9.9, 0.3)
for t, pn in ((10.35, 0), (10.5, -0.6), (10.62, 0.6)):
    whoosh(0.45, 300, 3500, 0.16, 0.4, t0=t - 0.1, pan_sweep=False)
pop(10.8, 420, 0.35, 0)                            # hub
digital(11.0, 0.08, 0.0, 10, 2200)
for i in range(3):
    pop(11.0 + i * 0.12, 1100 + i * 150, 0.14, (-0.5, 0.5, 0)[i])
digital(12.4, 0.04, -0.3, 5, 3000); digital(13.1, 0.04, 0.3, 5, 3000)
whoosh(0.7, 300, 6500, 0.45, 0.6, t0=13.45)       # scene 4 -> 5
for k in range(6):                                  # kinetic words
    t = 14.05 + k * 0.47
    whoosh(0.3, 600, 5000, 0.14, 0.5, t0=t - 0.12, pan_sweep=False)
    blip(mtof(84 + [0, 2, 4, 7, 9, 12][k]), 0.12, 0.10, t + 0.08, (-0.3, 0.3)[k % 2], 0.4)
riser(15.6, 1.3, 0.35)
whoosh(0.5, 200, 8000, 0.4, 0.8, t0=16.55)
impact(17.0, 1.0); shimmer(17.05, 1.4, 0.06, 81)
pop(17.75, 600, 0.3, 0); pop(18.05, 900, 0.22, -0.3); pop(18.3, 700, 0.3, 0.2)
click(18.3, 0.2, 0.2)
shimmer(18.55, 0.8, 0.05, 88); blip(mtof(96), 0.4, 0.05, 18.95, 0.4, 0.7)

# ------------------------------------------------------------------ mix
# side-chain duck on the music bus (approximation: duck everything except the kick itself is fine at this level)
duck = 1 - 0.45 * np.clip(signal.lfilter([1], [1, -0.0], duck_src), 0, 1)
# short pre-drop gap before the final impact
gap = np.ones(N); g0, g1 = int(16.9 * SR), int(17.0 * SR)
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
