"""Decoding uploads with PyAV (bundled FFmpeg), resampled to the model's rate."""

from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np
from av.audio.resampler import AudioResampler


class AudioError(Exception):
    """The file can't be used: not audio, unreadable, silent or too long."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class Audio:
    samples: np.ndarray  # (n, channels), float32 in [-1, 1]
    rate: int

    @property
    def seconds(self) -> float:
        return float(self.samples.shape[0] / self.rate)


def decode(path: Path, rate: int, max_seconds: float) -> Audio:
    """The recording at `path`, resampled to `rate`. AudioError if it isn't usable."""
    try:
        container = av.open(str(path))
    except (av.error.FFmpegError, OSError) as e:
        raise AudioError("not_audio", str(e)) from e
    with container:
        if not container.streams.audio:
            raise AudioError("not_audio", "no audio stream")
        stream = container.streams.audio[0]
        if stream.duration is not None and stream.time_base is not None:
            declared = float(stream.duration * stream.time_base)
            if declared > max_seconds + 1:
                raise AudioError("too_long", f"{declared:.0f} s")
        layout = "stereo" if (stream.channels or 1) >= 2 else "mono"
        resampler = AudioResampler(format="flt", layout=layout, rate=rate)
        chunks: list[np.ndarray] = []
        total = 0
        try:
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    chunk = out.to_ndarray().reshape(-1, out.layout.nb_channels)
                    chunks.append(chunk)
                    total += chunk.shape[0]
                    if total > (max_seconds + 1) * rate:
                        raise AudioError("too_long", f"over {max_seconds:.0f} s")
            for out in resampler.resample(None):
                chunks.append(out.to_ndarray().reshape(-1, out.layout.nb_channels))
        except av.error.FFmpegError as e:
            raise AudioError("not_audio", str(e)) from e

    if not chunks:
        raise AudioError("empty")
    samples = np.concatenate(chunks).astype(np.float32, copy=False)
    if samples.shape[0] < rate // 2:
        raise AudioError("empty", "shorter than half a second")
    if float(np.abs(samples).max()) < 1e-4:
        raise AudioError("silent")
    return Audio(samples=samples, rate=rate)
