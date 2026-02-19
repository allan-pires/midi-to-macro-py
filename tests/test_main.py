import os
from pathlib import Path

import main
from main import build_mcr_lines, export_mcr


def test_parse_midi_returns_events():
    path = Path('sample') / 'sample.mid'
    assert path.exists(), 'sample MIDI must exist for tests'
    events = main.parse_midi(str(path))
    assert isinstance(events, list)
    assert len(events) > 0
    # first event should occur at 0 ms
    first_time = events[0][0]
    assert first_time == 0


def test_build_mcr_lines_groups_and_modifiers(tmp_path):
    # create synthetic events: two simultaneous notes at t=0 and one at t=214
    events = [
        (0, [], 'B'),
        (0, ['CTRL'], 'N'),
        (214, [], 'X'),
    ]
    lines = build_mcr_lines(events)
    # Expect a leading DELAY : 0
    assert any(l.startswith('DELAY : 0') for l in lines)
    # CTRL modifier should produce ControlLeft KeyDown and KeyUp
    assert any('ControlLeft : KeyDown' in l for l in lines)
    assert any('ControlLeft : KeyUp' in l for l in lines)
    # There should be a DELAY : 214 somewhere
    assert any('DELAY : 214' in l or 'DELAY : 215' in l for l in lines)


def test_export_mcr_writes_file(tmp_path):
    events = [
        (0, [], 'Z'),
        (100, ['SHIFT'], 'Z'),
    ]
    out = tmp_path / 'out.mcr'
    export_mcr(str(out), events)
    assert out.exists()
    content = out.read_text(encoding='utf-8')
    assert 'Keyboard : Z : KeyDown' in content
    assert 'Keyboard : ShiftLeft : KeyDown' in content
