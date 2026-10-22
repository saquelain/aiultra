"""Synthesized soundtrack: a melodic note on every bounce, a chime on every break."""
import random
import wave

import numpy as np

SR = 44100
# C major pentatonic over three octaves
SCALE = [261.63, 293.66, 329.63, 392.00, 440.00]
NOTES = [f * m for m in (1, 2, 4) for f in SCALE]
# a few melodic walks; the bounce index steps through one of them
MELODIES = [
    [0, 2, 4, 5, 4, 2, 3, 5, 7, 5, 4, 2],
    [4, 3, 2, 0, 2, 4, 5, 7, 9, 7, 5, 4],
    [0, 4, 2, 5, 3, 7, 5, 9, 7, 5, 4, 2],
]


def _tone(freq, dur, vol, bright=0.3):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 7) * np.minimum(1, t * 400)
    w = np.sin(2 * np.pi * freq * t) + bright * np.sin(4 * np.pi * freq * t) + 0.1 * np.sin(6 * np.pi * freq * t)
    return vol * env * w


def _chime(freq, dur=1.2, vol=0.5):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 3.5) * np.minimum(1, t * 600)
    w = sum(np.sin(2 * np.pi * freq * m * t) / (j + 1) for j, m in enumerate((1, 2.0, 3.01, 4.2)))
    noise = np.random.default_rng(int(freq)).normal(0, 1, len(t)) * np.exp(-t * 30) * 0.3
    return vol * (env * w + noise)


def _add(buf, start, clip):
    i = int(start * SR)
    j = min(len(buf), i + len(clip))
    if i < len(buf):
        buf[i:j] += clip[: j - i]


def write(events, duration, path, seed=0):
    rng = random.Random(seed)
    melody = rng.choice(MELODIES)
    buf = np.zeros(int(SR * (duration + 1.5)))
    nb = 0
    last_bounce = -1
    for t, kind, ring in events:
        if kind == "bounce":
            if t - last_bounce < 0.05:
                continue
            last_bounce = t
            note = NOTES[(melody[nb % len(melody)] + ring // 6) % len(NOTES)]
            _add(buf, t, _tone(note, 0.5, 0.35))
            nb += 1
        else:
            note = NOTES[min(len(NOTES) - 1, 5 + ring % 10)]
            _add(buf, t, _chime(note))
    # final fanfare
    breaks = [t for t, k, _ in events if k == "break"]
    if breaks:
        for j, n in enumerate((10, 12, 14)):
            _add(buf, breaks[-1] + 0.12 * (j + 1), _chime(NOTES[n], 1.5, 0.45))
    peak = np.max(np.abs(buf)) or 1
    buf = np.tanh(buf / peak * 1.6) * 0.85
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
