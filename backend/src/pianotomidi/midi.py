"""Writing a transcription as a standard MIDI file.

One piano track: notes with their velocities, the sustain pedal as controller 64 and the soft
pedal as controller 67, at a fixed 120 BPM so DAWs place everything in real time.
"""

import io

import pretty_midi

from pianotomidi.transcription import Transcription

_CONTROLLER = {"sustain": 64, "soft": 67}
TEMPO = 120.0


def to_midi(transcription: Transcription, name: str = "Piano") -> bytes:
    midi = pretty_midi.PrettyMIDI(resolution=960, initial_tempo=TEMPO)
    piano = pretty_midi.Instrument(program=0, name=name)
    piano.notes = [pretty_midi.Note(n.velocity, n.pitch, n.start, n.end) for n in transcription.notes]
    for p in transcription.pedals:
        number = _CONTROLLER[p.kind]
        piano.control_changes.append(pretty_midi.ControlChange(number, p.value, p.start))
        piano.control_changes.append(pretty_midi.ControlChange(number, 0, p.end))
    piano.control_changes.sort(key=lambda c: (c.time, c.value))  # a release before a press at the same tick
    midi.instruments.append(piano)
    buffer = io.BytesIO()
    midi.write(buffer)
    return buffer.getvalue()
