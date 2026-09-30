"""Transkun (https://github.com/Yujia-Yan/Transkun, MIT) with progress per window.

The window loop follows Transkun's own `transcribe`, which reports no progress.
"""

import math
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from typing import Any, Literal, Protocol

import torch
import torch.nn.functional as F  # noqa: N812

from pianotomidi.audio import Audio

# Transkun's track numbers for the two pedals it hears.
_PEDALS: dict[int, Literal["sustain", "soft"]] = {-64: "sustain", -67: "soft"}

Progress = Callable[[float], None]


@dataclass(frozen=True)
class Note:
    start: float  # seconds
    end: float
    pitch: int  # MIDI, 21 (A0) to 108 (C8)
    velocity: int  # 1-127
    # CRF score margin over silence, before bias; around 0 the model was undecided.
    confidence: float = 0.0


@dataclass(frozen=True)
class Pedal:
    start: float
    end: float
    kind: Literal["sustain", "soft"]
    value: int  # MIDI controller value while down, 1-127


@dataclass(frozen=True)
class Transcription:
    notes: list[Note]
    pedals: list[Pedal]
    seconds: float


class Transcriber(Protocol):
    sample_rate: int

    def transcribe(self, audio: Audio, progress: Progress) -> Transcription: ...


class TranskunTranscriber:
    """Loads the model once; one transcription at a time.

    `bias` is added to note scores before decoding (pedals unbiased), so the confidence
    filter can choose the sensitivity later without running the network again.
    """

    def __init__(self, threads: int | None = None, bias: float = 0.0) -> None:
        import moduleconf

        pretrained = resources.files("transkun") / "pretrained"
        conf = moduleconf.parseFromFile(str(pretrained / "2.0.conf"))["Model"]
        self._model: Any = conf.module.TransKun(conf=conf.config)
        checkpoint = torch.load(str(pretrained / "2.0.pt"), map_location="cpu", weights_only=False)
        state = checkpoint.get("best_state_dict", checkpoint.get("state_dict"))
        self._model.load_state_dict(state, strict=False)
        self._model.eval()
        if threads:
            torch.set_num_threads(threads)
        self.sample_rate: int = int(self._model.fs)
        self.bias = bias
        self._lock = threading.Lock()
        self._windows: list[_Window] = []
        original = self._model.processFramesBatch

        def scored(frames: torch.Tensor) -> tuple[Any, Any]:
            crf, ctx = original(frames)
            if self.bias:
                crf.score[..., _N_PEDAL_TRACKS:] += self.bias
            window = _Window(crf)
            self._windows.append(window)
            decode = crf.decode

            def remembering_decode(*args: Any, **kwargs: Any) -> Any:
                window.path = decode(*args, **kwargs)
                return window.path

            crf.decode = remembering_decode
            return crf, ctx

        self._model.processFramesBatch = scored

    def transcribe(self, audio: Audio, progress: Progress) -> Transcription:
        if audio.rate != self.sample_rate:
            raise ValueError(f"audio must be at {self.sample_rate} Hz")
        with self._lock, torch.inference_mode():
            events = self._run(torch.from_numpy(audio.samples), progress)
        return _to_transcription(events, audio.seconds)

    def _run(self, x: torch.Tensor, progress: Progress) -> list[Any]:
        from transkun.Data import resolveOverlapping
        from transkun.Util import makeFrame

        m = self._model
        step_s, segment_s = m.segmentHopSizeInSecond, m.segmentSizeInSecond
        x = x.transpose(-1, -2)  # (channels, samples)
        pad_begin = segment_s - step_s
        x = F.pad(x, (math.ceil(pad_begin * m.fs), math.ceil(pad_begin * m.fs)))
        n_sample = x.shape[-1]

        start_frame = math.floor(pad_begin * m.fs / m.hopSize)
        start_pos = [start_frame] * len(m.targetMIDIPitch)
        step = math.ceil(step_s * m.fs / m.hopSize) * m.hopSize
        segment = math.ceil(segment_s * m.fs)
        by_pitch: dict[int, list[Any]] = defaultdict(list)

        windows = range(0, n_sample, step)
        for done, i in enumerate(windows, start=1):
            j = min(i + segment, n_sample)
            begin_time = i / m.fs - pad_begin
            piece = x[:, i:j]
            if piece.shape[-1] < segment:
                piece = F.pad(piece, (0, segment - piece.shape[-1]))
            frames = makeFrame(piece, m.hopSize, m.windowSize)
            self._windows.clear()
            events, last = m.transcribeFrames(
                frames.unsqueeze(0),
                forcedStartPos=start_pos,
                velocityCriteron="hamming",
                onsetBound=None,
                lastFrameIdx=round(segment / m.hopSize),
            )
            start_pos = [max(k - int(step / m.hopSize), 0) for k in last]
            self._attach_confidence(events[0])

            for e in events[0]:
                e.start = max(e.start + begin_time, 0)
                e.end = max(e.end + begin_time, e.start)
                track = by_pitch[e.pitch]
                if track and e.start < track[-1].end:
                    # The overlap of two windows saw the same note twice: keep one.
                    if e.hasOnset:
                        track[-1] = e
                    else:
                        track[-1].hasOffset = e.hasOffset
                        track[-1].end = max(e.end, track[-1].end)
                    continue
                if e.hasOnset:
                    track.append(e)
            progress(done / len(windows))

        for track in by_pitch.values():
            if track:
                track[-1].hasOffset = True
        finished = [e for track in by_pitch.values() for e in track if e.hasOffset]
        return list(resolveOverlapping(finished))

    def _attach_confidence(self, events: list[Any]) -> None:
        """Match each note to the decoded interval of the same pitch with the nearest start."""
        if not self._windows or self._windows[-1].path is None:
            return
        window = self._windows[-1]
        frame = self._model.hopSize / self._model.fs
        tracks = self._model.targetMIDIPitch
        for e in events:
            if e.pitch <= 0:
                continue
            k = tracks.index(e.pitch)
            intervals = window.path[k]
            if not intervals:
                continue
            begin, end = min(intervals, key=lambda iv: abs(iv[0] - e.start / frame))
            e.confidence = window.margin(begin, end, k) - self.bias


# Transkun's first two tracks are the pedals; the 88 keys follow.
_N_PEDAL_TRACKS = 2


class _Window:
    """One window's CRF scores and, once decoded, its intervals per track."""

    def __init__(self, crf: Any) -> None:
        self.score = crf.score  # [end, begin, track]
        self.noise = crf.noiseScore  # [t, track]: staying silent from frame t to t + 1
        self.path: Any = None

    def margin(self, begin: int, end: int, track: int) -> float:
        note = float(self.score[end, begin, track])
        silence = float(self.noise[begin:end, track].sum())
        return note - silence


def _to_transcription(events: list[Any], seconds: float) -> Transcription:
    notes, pedals = [], []
    for e in events:
        start, end = float(e.start), min(float(e.end), seconds)
        if end <= start:
            continue
        if e.pitch > 0:
            confidence = float(getattr(e, "confidence", 0.0))
            notes.append(Note(start, end, int(e.pitch), max(1, min(127, int(e.velocity))), confidence))
        elif e.pitch in _PEDALS:
            pedals.append(Pedal(start, end, _PEDALS[e.pitch], max(1, min(127, int(e.velocity)))))
    notes.sort(key=lambda n: (n.start, n.pitch))
    pedals.sort(key=lambda p: (p.kind, p.start))
    return Transcription(notes=notes, pedals=pedals, seconds=seconds)
