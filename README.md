# MIDI → .mcr (Windows)

Convert MIDI files to macro (.mcr) command files and optionally play them directly with keyboard simulation.

## Features
- **Export to .mcr**: Convert MIDI files to macro format with proper timing and key mappings
- **Live Playback**: Play MIDI notes as keyboard input in real-time using pynput
- **Tempo Control**: Speed up or slow down playback independently
- **Transposition**: Shift notes up or down by semitones
- **Chord Support**: Handle simultaneous key presses naturally

## Installation

### From Source
```bash
pip install -r requirements.txt
python main.py
```

### Using the Executable
- Download `midi-to-mcr.exe` from the dist folder
- The app will automatically prompt for Administrator privileges (required for keyboard simulation with games)

## Requirements
- Python 3.8+ (if running from source)
- `mido` - MIDI file parsing
- `pynput` - Keyboard simulation

## Usage

### GUI Controls
1. **Open folder**: Select a folder containing .mid/.midi files, then pick one from the list
2. **Tempo ×**: Multiply note timing (>1.0 = slower, <1.0 = faster)
3. **Transpose**: Shift all notes by semitones
4. **Export .mcr**: Save as macro file
5. **Play (keyboard)**: Simulate the macro keys in real-time
6. **Stop**: Stop playback

### Key Mappings
The tool maps MIDI notes to game keys by **pitch class** (note % 12) and **row by range**:
- **Low row** (notes < 60): Z, X, C, V, B, N, M
- **Mid row** (60–71): A, S, D, F, G, H, J
- **High row** (72+): Q, W, E, R, T, Y, U

Notes below 0 or above 95 are clamped. So low melodies use the low row, middle register the mid row, and high notes the high row.

Black keys use Shift (or Ctrl for D# on the low row). Notes outside the range are clamped to the nearest mapped note. Use **Transpose** to shift octaves.

## Macro File Format
Exported .mcr files contain keyboard commands:
```
DELAY : 100
Keyboard : Q : KeyDown
Keyboard : Q : KeyUp
DELAY : 200
Keyboard : ShiftLeft : KeyDown
Keyboard : Q : KeyDown
Keyboard : Q : KeyUp
Keyboard : ShiftLeft : KeyUp
```

## Important Notes

### Admin Privileges Required
The executable requires Administrator privileges to send keyboard input to games. Windows will automatically prompt when launching.

### Game Compatibility
- Works with applications that accept standard Windows keyboard input (Notepad, Word, etc.)
- May not work with games that use anti-cheat systems or raw input filtering
- Tested with Where Winds Meet (requires admin mode)

### Performance
- Key holds are optimized for game responsiveness (~20ms per note)
- Timing is calculated from absolute MIDI positions to ensure accurate playback
- Chord notes (simultaneous key presses) are synchronized for proper sound

## Troubleshooting

**Keys not recognized by game?**
- Ensure the app is running as Administrator
- Focus the game window before clicking Run
- Some games may reject simulated input regardless

**Chord timing sounds off?**
- This is a limitation of simulated input - timing may not be pixel-perfect
- Real-time hardware macro devices may provide better results

**MIDI not loading?**
- Ensure the file is a valid standard MIDI file (.mid or .midi)
- Check that all tracks are properly formatted


