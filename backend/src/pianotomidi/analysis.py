"""Analysis by synthesis: how well a set of notes explains a recording's semitone spectrogram."""

from collections.abc import Sequence

import numpy as np

from pianotomidi.audio import Audio
from pianotomidi.transcription import Note

HOP_SECONDS = 0.05
WINDOW = 4096
LOWEST, HIGHEST = 21, 108
KEYS = HIGHEST - LOWEST + 1
HARMONICS = 6


def semitone_spectrogram(audio: Audio) -> np.ndarray:
    """Power per piano key (rows: A0..C8) per 50 ms frame."""
    mono = audio.samples.mean(axis=1) if audio.samples.ndim == 2 else audio.samples
    hop = round(audio.rate * HOP_SECONDS)
    padded = np.pad(mono, (WINDOW // 2, WINDOW // 2))
    n_frames = max(1, 1 + (padded.size - WINDOW) // hop)
    window = np.hanning(WINDOW).astype(np.float32)

    freqs = np.fft.rfftfreq(WINDOW, 1 / audio.rate)
    safe = np.maximum(freqs, 1.0)  # 0 Hz has no key; it's filtered out below anyway
    keys = np.round(12 * np.log2(safe / 440.0) + 69).astype(int)
    usable = (freqs >= 25) & (keys >= LOWEST) & (keys <= HIGHEST)
    rows = keys[usable] - LOWEST

    spec = np.zeros((KEYS, n_frames), dtype=np.float32)
    for start in range(0, n_frames, 512):  # in blocks, to keep memory flat on long pieces
        idx = np.arange(start, min(start + 512, n_frames))
        frames = np.stack([padded[i * hop : i * hop + WINDOW] for i in idx]) * window
        power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
        block = np.zeros((KEYS, idx.size), dtype=np.float32)
        np.add.at(block, rows, power[:, usable].T)
        spec[:, idx] = block
    return spec


def imagined_spectrogram(notes: Sequence[Note], n_frames: int) -> np.ndarray:
    """What the notes would roughly look like in a semitone spectrogram."""
    spec = np.zeros((KEYS, n_frames), dtype=np.float32)
    t = np.arange(n_frames) * HOP_SECONDS
    for n in notes:
        first = int(n.start / HOP_SECONDS)
        last = min(n_frames, int((n.end + 0.3) / HOP_SECONDS) + 1)
        if first >= n_frames or last <= first:
            continue
        span = t[first:last] - n.start
        # Low strings ring for seconds, high ones fade fast; after release, ~0.1 s.
        ring = 0.4 + 2.5 * (HIGHEST - n.pitch) / KEYS
        envelope = np.exp(-np.maximum(span, 0) / ring)
        released = t[first:last] > n.end
        envelope[released] *= np.exp(-(t[first:last][released] - n.end) / 0.1)
        loud = (n.velocity / 127) ** 2
        for k in range(1, HARMONICS + 1):
            row = round(n.pitch + 12 * np.log2(k)) - LOWEST
            if 0 <= row < KEYS:
                spec[row, first:last] += loud * envelope / k
    return spec


def fit(heard: np.ndarray, notes: Sequence[Note]) -> float:
    """Cosine similarity (0-1) of log spectra, averaged over frames with sound."""
    imagined = imagined_spectrogram(notes, heard.shape[1])
    a = np.log1p(heard / (np.median(heard[heard > 0]) if np.any(heard > 0) else 1.0))
    b = np.log1p(imagined / (np.median(imagined[imagined > 0]) if np.any(imagined > 0) else 1.0))
    energy = a.sum(axis=0)
    active = energy > np.percentile(energy, 20)
    if not np.any(active):
        return 0.0
    num = (a * b).sum(axis=0)
    den = np.linalg.norm(a, axis=0) * np.linalg.norm(b, axis=0)
    cos = np.divide(num, den, out=np.zeros_like(num), where=den > 0)
    return float(np.average(cos[active], weights=energy[active]))


def noise_floor_db(audio: Audio) -> float:
    """How loud the quietest moments are against the loudest (dB, negative; near 0 = noisy)."""
    mono = audio.samples.mean(axis=1) if audio.samples.ndim == 2 else audio.samples
    hop = round(audio.rate * HOP_SECONDS)
    frames = mono[: mono.size // hop * hop].reshape(-1, hop)
    rms = np.sqrt(np.mean(frames**2, axis=1)) + 1e-9
    return float(20 * np.log10(np.percentile(rms, 5) / np.percentile(rms, 95)))
