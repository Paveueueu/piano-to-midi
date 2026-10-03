"""MIDI export: one piano track (or one per hand), sustain as CC64 and soft pedal as CC67."""

import io

import pretty_midi

from pianotomidi.options import Arrangement

_CONTROLLER = {"sustain": 64, "soft": 67}


def to_midi(arrangement: Arrangement, name: str = "Piano") -> bytes:
    midi = pretty_midi.PrettyMIDI(resolution=960, initial_tempo=arrangement.bpm)
    if arrangement.split_key is None:
        tracks = [(name, arrangement.notes)]
    else:
        tracks = [("Right hand", arrangement.notes), ("Left hand", arrangement.left)]
    for track_name, notes in tracks:
        piano = pretty_midi.Instrument(program=0, name=track_name)
        piano.notes = [pretty_midi.Note(n.velocity, n.pitch, n.start, n.end) for n in notes]
        for p in arrangement.pedals:
            number = _CONTROLLER[p.kind]
            piano.control_changes.append(pretty_midi.ControlChange(number, p.value, p.start))
            piano.control_changes.append(pretty_midi.ControlChange(number, 0, p.end))
        piano.control_changes.sort(key=lambda c: (c.time, c.value))  # a release before a press at one tick
        midi.instruments.append(piano)
    buffer = io.BytesIO()
    midi.write(buffer)
    return buffer.getvalue()
