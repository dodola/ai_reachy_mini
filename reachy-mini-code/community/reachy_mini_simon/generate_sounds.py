"""Generate sound files for Simon game."""
import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 44100
ASSETS_DIR = "reachy_mini_simon/assets"


def generate_tone(frequency, duration, fade_ms=50):
    """Generate a pure tone with fade in/out."""
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)

    # Generate sine wave
    tone = np.sin(2 * np.pi * frequency * t)

    # Apply fade in/out to avoid clicks
    fade_samples = int(SAMPLE_RATE * fade_ms / 1000)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)

    tone[:fade_samples] *= fade_in
    tone[-fade_samples:] *= fade_out

    # Convert to 16-bit PCM
    tone = (tone * 32767).astype(np.int16)
    return tone


def generate_chord(frequencies, duration, fade_ms=50):
    """Generate multiple tones combined."""
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)

    # Combine multiple frequencies
    chord = np.zeros(samples)
    for freq in frequencies:
        chord += np.sin(2 * np.pi * freq * t)

    # Normalize
    chord = chord / len(frequencies)

    # Apply fade
    fade_samples = int(SAMPLE_RATE * fade_ms / 1000)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)

    chord[:fade_samples] *= fade_in
    chord[-fade_samples:] *= fade_out

    # Convert to 16-bit PCM
    chord = (chord * 32767).astype(np.int16)
    return chord


def generate_ascending_chime():
    """Generate success sound - ascending notes."""
    notes = [523, 659, 784]  # C5, E5, G5
    duration_per_note = 0.15

    result = []
    for freq in notes:
        tone = generate_tone(freq, duration_per_note, fade_ms=20)
        result.append(tone)

    return np.concatenate(result)


def generate_descending_tone():
    """Generate game over sound - descending tone."""
    duration = 0.6
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)

    # Frequency sweep from 600 Hz to 200 Hz
    freq = 600 - 400 * t / duration
    tone = np.sin(2 * np.pi * freq * t)

    # Fade out
    fade_out = np.linspace(1, 0, samples)
    tone *= fade_out

    # Convert to 16-bit PCM
    tone = (tone * 32767).astype(np.int16)
    return tone


def generate_cheerful_beep():
    """Generate start game sound - two quick beeps."""
    beep1 = generate_tone(784, 0.1, fade_ms=10)  # G5
    silence = np.zeros(int(SAMPLE_RATE * 0.05), dtype=np.int16)
    beep2 = generate_tone(988, 0.1, fade_ms=10)  # B5

    return np.concatenate([beep1, silence, beep2])


def main():
    """Generate all sound files."""
    print("Generating sound files...")

    # Head direction tones (simple pure tones)
    print("  up.wav (E5 - 659 Hz)")
    tone = generate_tone(659, 0.3)
    wavfile.write(f"{ASSETS_DIR}/up.wav", SAMPLE_RATE, tone)

    print("  down.wav (C5 - 523 Hz)")
    tone = generate_tone(523, 0.3)
    wavfile.write(f"{ASSETS_DIR}/down.wav", SAMPLE_RATE, tone)

    print("  left.wav (A4 - 440 Hz)")
    tone = generate_tone(440, 0.3)
    wavfile.write(f"{ASSETS_DIR}/left.wav", SAMPLE_RATE, tone)

    print("  right.wav (G5 - 784 Hz)")
    tone = generate_tone(784, 0.3)
    wavfile.write(f"{ASSETS_DIR}/right.wav", SAMPLE_RATE, tone)

    # Body yaw tones (Difficulty 2)
    print("  body_left.wav (F4 - 349 Hz)")
    tone = generate_tone(349, 0.3)
    wavfile.write(f"{ASSETS_DIR}/body_left.wav", SAMPLE_RATE, tone)

    print("  body_right.wav (B4 - 494 Hz)")
    tone = generate_tone(494, 0.3)
    wavfile.write(f"{ASSETS_DIR}/body_right.wav", SAMPLE_RATE, tone)

    # Antenna tones (Difficulty 3)
    print("  left_antenna_left.wav (D4 - 294 Hz)")
    tone = generate_tone(294, 0.3)
    wavfile.write(f"{ASSETS_DIR}/left_antenna_left.wav", SAMPLE_RATE, tone)

    print("  left_antenna_right.wav (E4 - 330 Hz)")
    tone = generate_tone(330, 0.3)
    wavfile.write(f"{ASSETS_DIR}/left_antenna_right.wav", SAMPLE_RATE, tone)

    print("  right_antenna_left.wav (F#4 - 370 Hz)")
    tone = generate_tone(370, 0.3)
    wavfile.write(f"{ASSETS_DIR}/right_antenna_left.wav", SAMPLE_RATE, tone)

    print("  right_antenna_right.wav (G#4 - 415 Hz)")
    tone = generate_tone(415, 0.3)
    wavfile.write(f"{ASSETS_DIR}/right_antenna_right.wav", SAMPLE_RATE, tone)

    # Difficulty selection sounds
    print("  difficulty1.wav (single beep - C major chord)")
    tone = generate_chord([523, 659, 784], 0.3)
    wavfile.write(f"{ASSETS_DIR}/difficulty1.wav", SAMPLE_RATE, tone)

    print("  difficulty2.wav (double beep)")
    beep1 = generate_tone(659, 0.15)
    silence = np.zeros(int(SAMPLE_RATE * 0.1), dtype=np.int16)
    beep2 = generate_tone(784, 0.15)
    tone = np.concatenate([beep1, silence, beep2])
    wavfile.write(f"{ASSETS_DIR}/difficulty2.wav", SAMPLE_RATE, tone)

    print("  difficulty3.wav (triple beep)")
    beep1 = generate_tone(523, 0.12)
    silence = np.zeros(int(SAMPLE_RATE * 0.08), dtype=np.int16)
    beep2 = generate_tone(659, 0.12)
    beep3 = generate_tone(784, 0.12)
    tone = np.concatenate([beep1, silence, beep2, silence, beep3])
    wavfile.write(f"{ASSETS_DIR}/difficulty3.wav", SAMPLE_RATE, tone)

    # Feedback sounds
    print("  success.wav (ascending chime)")
    tone = generate_ascending_chime()
    wavfile.write(f"{ASSETS_DIR}/success.wav", SAMPLE_RATE, tone)

    print("  game_over.wav (descending tone)")
    tone = generate_descending_tone()
    wavfile.write(f"{ASSETS_DIR}/game_over.wav", SAMPLE_RATE, tone)

    print("  start_game.wav (cheerful beep)")
    tone = generate_cheerful_beep()
    wavfile.write(f"{ASSETS_DIR}/start_game.wav", SAMPLE_RATE, tone)

    print("\nAll sound files generated successfully!")


if __name__ == "__main__":
    main()
