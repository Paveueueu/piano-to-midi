"""Ready-made settings."""

from dataclasses import dataclass
from typing import Any

from pianotomidi.options import Options


@dataclass(frozen=True)
class Preset:
    id: str
    changes: dict[str, Any]

    def options(self) -> Options:
        return Options.model_validate(self.changes)


PRESETS: tuple[Preset, ...] = (
    Preset("as_played", {}),
    # Fewer stray notes.
    Preset("clean", {"min_confidence": 1.0}),
    # More quiet notes, some of them wrong.
    Preset("more_notes", {"min_confidence": -1.0}),
    # For editing on a DAW grid: detected tempo, notes pulled towards 1/16, hands split.
    Preset("on_grid", {"tempo": "detected", "grid": "1/16", "quantize_strength": 75, "hands": "split"}),
    # For instruments that ignore CC64.
    Preset("no_pedal_support", {"pedal": "held_notes"}),
)


def preset(preset_id: str) -> Preset | None:
    return next((p for p in PRESETS if p.id == preset_id), None)
