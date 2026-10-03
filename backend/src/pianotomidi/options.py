"""Transcription settings, applied to finished notes so the model never runs again."""

from dataclasses import dataclass, field, replace
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field

from pianotomidi import tempo
from pianotomidi.transcription import Note, Pedal, Transcription

LOWEST_KEY, HIGHEST_KEY = 21, 108  # A0, C8


class Options(BaseModel):
    min_confidence: float = Field(
        0.0,
        ge=-2.0,
        le=3.0,
        description="Sensitivity: lower keeps doubtful notes too, higher keeps only sure ones",
    )
    min_note_ms: int = Field(0, ge=0, le=500, description="Drop notes shorter than this")
    lowest_key: int = Field(LOWEST_KEY, ge=LOWEST_KEY, le=HIGHEST_KEY, description="MIDI number, 21 = A0")
    highest_key: int = Field(HIGHEST_KEY, ge=LOWEST_KEY, le=HIGHEST_KEY, description="MIDI number, 108 = C8")

    velocity: Literal["as_played", "compressed", "fixed"] = Field(
        "as_played",
        description="How hard notes are: as heard, evened out halfway to the median, or all the same",
    )
    fixed_velocity: int = Field(80, ge=1, le=127, description="Velocity of every note when velocity is fixed")

    pedal: Literal["controller", "held_notes", "none"] = Field(
        "controller",
        description="Pedals as MIDI controllers 64/67, folded into longer notes (for instruments that ignore "
        "the pedal), or left out",
    )

    tempo: Literal["real_time", "detected"] = Field(
        "real_time",
        description="real_time: 120 BPM with timing untouched, so the MIDI lines up with the recording; "
        "detected: the piece's own tempo, shifted so its beats fall on the DAW's bar lines",
    )
    bpm: float | None = Field(None, ge=30, le=260, description="Tempo to use instead of the detected one")
    grid: Literal["off", "1/8", "1/16", "1/32"] = Field(
        "off", description="Snap notes to this grid (uses the piece's tempo, as with tempo=detected)"
    )
    quantize_strength: int = Field(100, ge=0, le=100, description="How far notes move toward the grid, in %")

    hands: Literal["one_track", "split"] = Field(
        "one_track", description="One piano track, or left and right hand on separate tracks"
    )
    split_key: int | None = Field(
        None,
        ge=LOWEST_KEY,
        le=HIGHEST_KEY,
        description="Lowest key of the right hand; empty to choose it from the notes",
    )


REAL_TIME_BPM = 120.0
_DIVISIONS = {"1/8": 2, "1/16": 4, "1/32": 8}


@dataclass(frozen=True)
class Arrangement:
    """The result of applying options: what goes into the MIDI file and onto the piano roll."""

    notes: list[Note]
    pedals: list[Pedal]
    seconds: float
    bpm: float  # tempo written into the MIDI file
    shift: float = 0.0  # seconds added to every event so beats land on bar lines
    detected_bpm: float | None = None  # what the notes suggest, shown to the user
    left: list[Note] = field(default_factory=list)  # left hand, when hands are split (`notes` is the right)
    split_key: int | None = None  # where the hands were split


def arrange(transcription: Transcription, options: Options) -> Arrangement:
    arrangement = _arrange_time(transcription, options)
    if options.hands == "one_track":
        return arrangement
    split = options.split_key or choose_split(arrangement.notes)
    return replace(
        arrangement,
        notes=[n for n in arrangement.notes if n.pitch >= split],
        left=[n for n in arrangement.notes if n.pitch < split],
        split_key=split,
    )


def _arrange_time(transcription: Transcription, options: Options) -> Arrangement:
    notes = filter_notes(transcription.notes, options)
    notes = set_velocity(notes, options)
    pedals = list(transcription.pedals)
    if options.pedal == "held_notes":
        notes = hold_with_pedal(notes, [p for p in pedals if p.kind == "sustain"])
    if options.pedal != "controller":
        pedals = []

    starts = [n.start for n in transcription.notes]
    weights = [n.velocity / 127 for n in transcription.notes]
    detected = tempo.detect(starts, weights)
    detected_bpm = detected.bpm if detected else None
    on_grid = options.tempo == "detected" or options.grid != "off"
    bpm = options.bpm or detected_bpm
    if not on_grid or bpm is None:
        return Arrangement(notes, pedals, transcription.seconds, REAL_TIME_BPM, 0.0, detected_bpm)

    beat = 60.0 / bpm
    first = detected.first if detected and not options.bpm else tempo.phase(starts, weights, bpm)
    shift = (-first) % beat
    notes = [replace(n, start=n.start + shift, end=n.end + shift) for n in notes]
    pedals = [replace(p, start=p.start + shift, end=p.end + shift) for p in pedals]
    if options.grid != "off":
        step = beat / _DIVISIONS[options.grid]
        strength = options.quantize_strength / 100
        notes = [_snap_note(n, step, strength) for n in notes]
        pedals = [_snap_pedal(p, step, strength) for p in pedals]
    return Arrangement(notes, pedals, transcription.seconds + shift, bpm, shift, detected_bpm)


def _snap(t: float, step: float, strength: float) -> float:
    return t + strength * (round(t / step) * step - t)


def _snap_note(n: Note, step: float, strength: float) -> Note:
    start, end = _snap(n.start, step, strength), _snap(n.end, step, strength)
    return replace(n, start=start, end=max(end, start + step * max(strength, 0.25)))


def _snap_pedal(p: Pedal, step: float, strength: float) -> Pedal:
    start, end = _snap(p.start, step, strength), _snap(p.end, step, strength)
    return replace(p, start=start, end=max(end, start + step))


def filter_notes(notes: list[Note], options: Options) -> list[Note]:
    low, high = sorted((options.lowest_key, options.highest_key))
    shortest = options.min_note_ms / 1000
    return [
        n
        for n in notes
        if n.confidence >= options.min_confidence and low <= n.pitch <= high and n.end - n.start >= shortest
    ]


def set_velocity(notes: list[Note], options: Options) -> list[Note]:
    if options.velocity == "fixed":
        return [replace(n, velocity=options.fixed_velocity) for n in notes]
    if options.velocity == "compressed" and notes:
        middle = median(n.velocity for n in notes)
        return [
            replace(n, velocity=max(1, min(127, round(middle + (n.velocity - middle) / 2)))) for n in notes
        ]
    return notes


def hold_with_pedal(notes: list[Note], sustain: list[Pedal]) -> list[Note]:
    """Extend notes held by the sustain pedal until it lifts or the key is struck again."""
    if not sustain:
        return notes
    next_strike: dict[int, list[float]] = {}
    for n in sorted(notes, key=lambda n: n.start):
        next_strike.setdefault(n.pitch, []).append(n.start)
    out = []
    for n in notes:
        pedal = next((p for p in sustain if p.start <= n.end < p.end), None)
        if pedal is None:
            out.append(n)
            continue
        later = [s for s in next_strike[n.pitch] if s > n.start]
        end = min(pedal.end, later[0]) if later else pedal.end
        out.append(replace(n, end=max(n.end, end)))
    return out


SPLIT_RANGE = (52, 67)  # E3 to G4: where pianists' hands usually meet


def choose_split(notes: list[Note]) -> int:
    """Split key between the hands (Otsu's method on the pitch histogram); middle C if unclear."""
    if len(notes) < 2:
        return 60
    counts = [0] * 128
    for n in notes:
        counts[n.pitch] += 1
    total = len(notes)
    best, best_score = 60, -1.0
    for split in range(SPLIT_RANGE[0], SPLIT_RANGE[1] + 1):
        low = [p for p in range(split) for _ in range(counts[p])]
        high = [p for p in range(split, 128) for _ in range(counts[p])]
        if not low or not high:
            continue
        w_low, w_high = len(low) / total, len(high) / total
        between = w_low * w_high * (sum(high) / len(high) - sum(low) / len(low)) ** 2
        if between > best_score:
            best, best_score = split, between
    return best
