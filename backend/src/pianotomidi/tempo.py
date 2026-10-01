"""One average tempo and beat phase from note onsets (autocorrelation), for lining up a DAW grid."""

from dataclasses import dataclass

import numpy as np

RATE = 100  # onset signal samples per second
MIN_BPM, MAX_BPM = 50.0, 200.0


@dataclass(frozen=True)
class Beat:
    bpm: float
    first: float  # seconds: where a beat falls, at or after 0

    @property
    def seconds(self) -> float:
        return 60.0 / self.bpm


def onset_signal(starts: list[float], weights: list[float], length: float) -> np.ndarray:
    signal = np.zeros(int(length * RATE) + RATE)
    for t, w in zip(starts, weights, strict=True):
        # Squared, so accented notes dominate and steady eighths aren't read as double tempo.
        signal[round(t * RATE)] += w * w
    # Smear each onset over ~20 ms, as played timing is never exact.
    kernel = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2)
    return np.convolve(signal, kernel, mode="same")


def detect(starts: list[float], weights: list[float] | None = None) -> Beat | None:
    """Average beat, or None with too few notes. `weights`: e.g. velocity / 127."""
    if len(starts) < 8:
        return None
    weights = weights or [1.0] * len(starts)
    signal = onset_signal(starts, weights, max(starts))
    signal = signal - signal.mean()
    ac = np.correlate(signal, signal, mode="full")[signal.size - 1 :]

    lags = np.arange(int(RATE * 60 / MAX_BPM), int(RATE * 60 / MIN_BPM) + 1)
    lags = lags[lags < ac.size]
    if lags.size == 0:
        return None
    bpms = 60.0 * RATE / lags
    prior = np.exp(-0.5 * (np.log2(bpms / 120.0) / 0.9) ** 2)
    strength = ac[lags] * prior
    lag = int(lags[int(np.argmax(strength))])

    # Refine the period to a fraction of a sample with a parabola through the peak.
    if 0 < lag < ac.size - 1:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        denom = a - 2 * b + c
        period = lag + (0.5 * (a - c) / denom if denom else 0.0)
    else:
        period = float(lag)
    bpm = 60.0 * RATE / period

    # Phase: the offset where onsets pile up most when folded onto the beat.
    beat = 60.0 / bpm
    angles = 2 * np.pi * (np.asarray(starts) % beat) / beat
    mean = np.sum(np.asarray(weights) * np.exp(1j * angles))
    first = (np.angle(mean) % (2 * np.pi)) / (2 * np.pi) * beat
    return Beat(bpm=round(float(bpm), 2), first=float(first))
