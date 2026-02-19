import mido
import sys

path = sys.argv[1]
mid = mido.MidiFile(path)
ticks_per_beat = mid.ticks_per_beat
tempo = 500000
time_sec = 0.0

print('ticks_per_beat:', ticks_per_beat)
for msg in mido.merge_tracks(mid.tracks):
    # delta ticks -> seconds
    delta_sec = mido.tick2second(msg.time, ticks_per_beat, tempo)
    time_sec += delta_sec
    if msg.type == 'set_tempo':
        tempo = msg.tempo
    if msg.type == 'note_on' and getattr(msg, 'velocity', 0) > 0:
        print(f"time={time_sec:.3f}s delta_ms={int(delta_sec*1000)} note={msg.note} vel={msg.velocity}")
