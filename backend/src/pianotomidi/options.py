"""Transcription settings, applied to finished notes so the model never runs again."""

from dataclasses import dataclass, replace
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field

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


@dataclass(frozen=True)
class Arrangement:
    """The result of applying options: what goes into the MIDI file and onto the piano roll."""

    notes: list[Note]
    pedals: list[Pedal]
    seconds: float


def arrange(transcription: Transcription, options: Options) -> Arrangement:
    notes = filter_notes(transcription.notes, options)
    notes = set_velocity(notes, options)
    pedals = list(transcription.pedals)
    if options.pedal == "held_notes":
        notes = hold_with_pedal(notes, [p for p in pedals if p.kind == "sustain"])
    if options.pedal != "controller":
        pedals = []
    return Arrangement(notes=notes, pedals=pedals, seconds=transcription.seconds)


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
