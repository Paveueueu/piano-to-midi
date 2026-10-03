"""Writing an arrangement as a standard MIDI file.

One piano track: notes with their velocities, the sustain pedal as controller 64 and the soft
pedal as controller 67. The tempo is the arrangement's: 120 BPM for real-time output, or the
piece's own so a DAW's bar lines match its beats.
"""

import io

import pretty_midi

from pianotomidi.options import Arrangement

_CONTROLLER = {"sustain": 64, "soft": 67}


def to_midi(arrangement: Arrangement, name: str = "Piano") -> bytes:
    midi = pretty_midi.PrettyMIDI(resolution=960, initial_tempo=arrangement.bpm)
    piano = pretty_midi.Instrument(program=0, name=name)
    piano.notes = [pretty_midi.Note(n.velocity, n.pitch, n.start, n.end) for n in arrangement.notes]
    for p in arrangement.pedals:
        number = _CONTROLLER[p.kind]
        piano.control_changes.append(pretty_midi.ControlChange(number, p.value, p.start))
        piano.control_changes.append(pretty_midi.ControlChange(number, 0, p.end))
    piano.control_changes.sort(key=lambda c: (c.time, c.value))  # a release before a press at the same tick
    midi.instruments.append(piano)
    buffer = io.BytesIO()
    midi.write(buffer)
    return buffer.getvalue()
