"""Auto settings and the reasons for them.

- Sensitivity: the threshold whose notes best fit the spectrum (analysis.fit), in [-1, 0.5].
- Rhythm: quantise only when note starts sit on a 1/8, 1/16 or 1/32 grid.
- Hands: split only when low and high notes form two separate groups.
"""

from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any

import numpy as np

from pianotomidi import tempo
from pianotomidi.analysis import fit, noise_floor_db
from pianotomidi.options import Options, choose_split
from pianotomidi.transcription import Note, Transcription

THRESHOLDS = (-1.0, -0.5, 0.0, 0.5)
CLEAR_GAIN = 0.0002  # fit gain needed to move sensitivity away from 0
GRIDS = (("1/8", 2), ("1/16", 4), ("1/32", 8))
ON_GRID = 0.12  # median distance of onsets to the grid, as a fraction of a grid step
MIN_NOTES_FOR_RHYTHM = 24
HANDS_SEPARATION = 2.5
HANDS_MIN_DISTANCE = 12  # semitones between the groups' average pitches: at least an octave
MIN_HAND_SHARE = 0.15
NOISY_DB = -35.0  # quietest moments within 35 dB of the loudest: a noisy room or phone


@dataclass(frozen=True)
class Reason:
    code: str
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Suggestion:
    options: Options
    reasons: list[Reason]


def suggest(heard: np.ndarray, noise_db: float, transcription: Transcription) -> Suggestion:
    """Settings for this recording. `heard` is its semitone spectrogram (analysis module)."""
    reasons: list[Reason] = []
    changes: dict[str, Any] = {}

    if noise_db > NOISY_DB:
        reasons.append(Reason("noisy_recording", {"noise_db": round(noise_db, 1)}))
    threshold, fits = choose_sensitivity(heard, transcription.notes)
    kept = sum(1 for n in transcription.notes if n.confidence >= threshold)
    default_kept = sum(1 for n in transcription.notes if n.confidence >= 0)
    if threshold == 0.0:
        reasons.append(Reason("sensitivity_default", {"fit": round(fits[0.0], 4)}))
    else:
        changes["min_confidence"] = threshold
        reasons.append(
            Reason(
                "sensitivity_raised" if threshold > 0 else "sensitivity_lowered",
                {
                    "threshold": threshold,
                    "notes_changed": abs(kept - default_kept),
                    "fit_gain": round(fits[threshold] - fits[0.0], 4),
                },
            )
        )

    notes = [n for n in transcription.notes if n.confidence >= threshold]
    grid = choose_grid(notes)
    if grid is not None:
        name, bpm, error = grid
        changes |= {"tempo": "detected", "grid": name, "quantize_strength": 75}
        reasons.append(Reason("steady_rhythm", {"bpm": bpm, "grid": name, "error": round(error, 3)}))
    else:
        beat = tempo.detect([n.start for n in notes], [n.velocity / 127 for n in notes])
        reasons.append(Reason("free_rhythm", {"bpm": beat.bpm if beat else None}))

    split = choose_hands(notes)
    if split is not None:
        changes |= {"hands": "split", "split_key": split}
        reasons.append(Reason("hands_split", {"split_key": split}))
    else:
        reasons.append(Reason("hands_together", {}))

    return Suggestion(Options.model_validate(changes), reasons)


def choose_sensitivity(heard: np.ndarray, notes: list[Note]) -> tuple[float, dict[float, float]]:
    fits = {t: fit(heard, [n for n in notes if n.confidence >= t]) for t in THRESHOLDS}
    best = max(fits, key=lambda t: fits[t])
    if fits[best] - fits[0.0] < CLEAR_GAIN:
        best = 0.0
    return best, fits


def choose_grid(notes: list[Note]) -> tuple[str, float, float] | None:
    """(grid, bpm, error) for the coarsest grid the note starts sit on, or None for free timing."""
    if len(notes) < MIN_NOTES_FOR_RHYTHM:
        return None
    starts = [n.start for n in notes]
    beat = tempo.detect(starts, [n.velocity / 127 for n in notes])
    if beat is None:
        return None
    for name, division in GRIDS:
        step = beat.seconds / division
        offsets = (np.asarray(starts) - beat.first) / step
        error = float(np.median(np.abs(offsets - np.round(offsets))))
        if error < ON_GRID:
            return name, beat.bpm, error
    return None


def choose_hands(notes: list[Note]) -> int | None:
    """A split key if low and high notes form two clearly separate groups, else None."""
    if len(notes) < 20:
        return None
    split = choose_split(notes)
    low = [n.pitch for n in notes if n.pitch < split]
    high = [n.pitch for n in notes if n.pitch >= split]
    if min(len(low), len(high)) < MIN_HAND_SHARE * len(notes):
        return None
    distance = mean(high) - mean(low)
    spread = ((pstdev(low) ** 2 + pstdev(high) ** 2) / 2) ** 0.5 or 1.0
    # A single register split in two always looks separated, so require an absolute gap too.
    if distance < HANDS_MIN_DISTANCE or distance / spread < HANDS_SEPARATION:
        return None
    return split


__all__ = [
    "Reason",
    "Suggestion",
    "choose_grid",
    "choose_hands",
    "choose_sensitivity",
    "noise_floor_db",
    "suggest",
]
