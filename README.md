# Piano to MIDI

Turns a piano recording into a MIDI file with notes, dynamics and pedal, ready to edit in a DAW.

```bash
cd backend && uv sync && uv run uvicorn pianotomidi.main:app --port 8100
cd frontend && pnpm install && pnpm dev   # second terminal, http://localhost:3300
```
