"""Transcription settings, applied to finished notes so the model never runs again."""

from dataclasses import dataclass

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


@dataclass(frozen=True)
class Arrangement:
    """The result of applying options: what goes into the MIDI file and onto the piano roll."""

    notes: list[Note]
    pedals: list[Pedal]
    seconds: float


def arrange(transcription: Transcription, options: Options) -> Arrangement:
    notes = filter_notes(transcription.notes, options)
    return Arrangement(notes=notes, pedals=list(transcription.pedals), seconds=transcription.seconds)


def filter_notes(notes: list[Note], options: Options) -> list[Note]:
    low, high = sorted((options.lowest_key, options.highest_key))
    shortest = options.min_note_ms / 1000
    return [
        n
        for n in notes
        if n.confidence >= options.min_confidence and low <= n.pitch <= high and n.end - n.start >= shortest
    ]
