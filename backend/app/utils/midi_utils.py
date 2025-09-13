"""
MIDI Utilities for M3 Enhanced
Comprehensive MIDI handling, processing, and conversion utilities
"""

import numpy as np
import pretty_midi
import mido
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class MidiNote:
    """Container for MIDI note information"""
    pitch: int
    velocity: int
    start: float
    end: float
    channel: int = 0

@dataclass
class MidiTrack:
    """Container for MIDI track information"""
    name: str
    instrument: int
    channel: int
    notes: List[MidiNote]
    is_drum: bool = False

@dataclass
class MidiInfo:
    """Container for MIDI file information"""
    filename: str
    duration: float
    tempo: float
    time_signature: Tuple[int, int]
    key_signature: str
    tracks: List[MidiTrack]
    total_notes: int

class MidiUtils:
    """Comprehensive MIDI processing utilities"""

    # Standard MIDI configurations
    DEFAULT_TEMPO = 120.0
    DEFAULT_TIME_SIGNATURE = (4, 4)
    DEFAULT_VELOCITY = 64
    DRUM_CHANNEL = 9  # Channel 10 in 1-indexed (9 in 0-indexed)

    # Instrument mappings for common instruments in M3
    INSTRUMENT_MAP = {
        'piano': 0,
        'electric_piano': 4,
        'guitar': 24,
        'electric_guitar': 27,
        'clean_guitar': 27,
        'distortion_guitar': 30,
        'overdrive_guitar': 29,
        'bass': 32,
        'electric_bass': 33,
        'synth_bass': 38,
        'violin': 40,
        'viola': 41,
        'cello': 42,
        'strings': 48,
        'trumpet': 56,
        'saxophone': 64,
        'flute': 73,
        'lead_synth': 80,
        'pad_synth': 88,
        'drums': 128  # Special case for percussion
    }

    @staticmethod
    def create_midi_from_notes(
        notes: List[MidiNote],
        tempo: float = DEFAULT_TEMPO,
        time_signature: Tuple[int, int] = DEFAULT_TIME_SIGNATURE,
        instrument: int = 0,
        track_name: str = "Generated Track"
    ) -> pretty_midi.PrettyMIDI:
        """
        Create MIDI file from note list

        Args:
            notes: List of MidiNote objects
            tempo: Tempo in BPM
            time_signature: Time signature tuple (numerator, denominator)
            instrument: MIDI instrument number
            track_name: Name for the track

        Returns:
            PrettyMIDI object
        """
        try:
            # Create new MIDI object
            midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)

            # Create instrument track
            if instrument == 128:  # Drums
                midi_instrument = pretty_midi.Instrument(
                    program=0,
                    is_drum=True,
                    name=track_name
                )
            else:
                midi_instrument = pretty_midi.Instrument(
                    program=instrument,
                    is_drum=False,
                    name=track_name
                )

            # Add notes to instrument
            for note in notes:
                midi_note = pretty_midi.Note(
                    velocity=note.velocity,
                    pitch=note.pitch,
                    start=note.start,
                    end=note.end
                )
                midi_instrument.notes.append(midi_note)

            # Add instrument to MIDI
            midi.instruments.append(midi_instrument)

            # Add time signature
            time_sig = pretty_midi.TimeSignature(
                numerator=time_signature[0],
                denominator=time_signature[1],
                time=0
            )
            midi.time_signature_changes.append(time_sig)

            logger.debug(f"Created MIDI with {len(notes)} notes, tempo {tempo} BPM")
            return midi

        except Exception as e:
            logger.error(f"Failed to create MIDI from notes: {str(e)}")
            raise

    @staticmethod
    def save_midi(
        midi: pretty_midi.PrettyMIDI,
        file_path: Union[str, Path],
        validate: bool = True
    ) -> Path:
        """
        Save MIDI to file with validation

        Args:
            midi: PrettyMIDI object to save
            file_path: Output file path
            validate: Validate MIDI before saving

        Returns:
            Path to saved file
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate MIDI if requested
            if validate and not MidiUtils.validate_midi(midi):
                raise ValueError("MIDI validation failed")

            # Save MIDI file
            midi.write(str(file_path))

            if not file_path.exists():
                raise RuntimeError(f"Failed to create MIDI file: {file_path}")

            logger.debug(f"Saved MIDI: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save MIDI to {file_path}: {str(e)}")
            raise

    @staticmethod
    def load_midi(file_path: Union[str, Path]) -> pretty_midi.PrettyMIDI:
        """
        Load MIDI file with error handling

        Args:
            file_path: Path to MIDI file

        Returns:
            PrettyMIDI object
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"MIDI file not found: {file_path}")

            midi = pretty_midi.PrettyMIDI(str(file_path))

            logger.debug(f"Loaded MIDI: {file_path} ({midi.get_end_time():.2f}s)")
            return midi

        except Exception as e:
            logger.error(f"Failed to load MIDI {file_path}: {str(e)}")
            raise

    @staticmethod
    def get_midi_info(midi: pretty_midi.PrettyMIDI, filename: str = "") -> MidiInfo:
        """Get comprehensive MIDI file information"""
        try:
            tracks = []
            total_notes = 0

            for i, instrument in enumerate(midi.instruments):
                notes = [
                    MidiNote(
                        pitch=note.pitch,
                        velocity=note.velocity,
                        start=note.start,
                        end=note.end,
                        channel=instrument.channel if hasattr(instrument, 'channel') else 0
                    )
                    for note in instrument.notes
                ]

                track = MidiTrack(
                    name=instrument.name or f"Track {i+1}",
                    instrument=instrument.program,
                    channel=instrument.channel if hasattr(instrument, 'channel') else 0,
                    notes=notes,
                    is_drum=instrument.is_drum
                )

                tracks.append(track)
                total_notes += len(notes)

            # Get tempo (use first tempo change or default)
            tempo = midi.estimate_tempo() if hasattr(midi, 'estimate_tempo') else MidiUtils.DEFAULT_TEMPO
            if len(midi.tempo_changes) > 0:
                tempo = mido.tempo2bpm(midi.tempo_changes[0].tempo)

            # Get time signature
            time_sig = MidiUtils.DEFAULT_TIME_SIGNATURE
            if len(midi.time_signature_changes) > 0:
                ts = midi.time_signature_changes[0]
                time_sig = (ts.numerator, ts.denominator)

            # Get key signature
            key_sig = "C major"  # Default
            if len(midi.key_signature_changes) > 0:
                ks = midi.key_signature_changes[0]
                key_sig = MidiUtils._format_key_signature(ks.key_number)

            return MidiInfo(
                filename=filename,
                duration=midi.get_end_time(),
                tempo=tempo,
                time_signature=time_sig,
                key_signature=key_sig,
                tracks=tracks,
                total_notes=total_notes
            )

        except Exception as e:
            logger.error(f"Failed to get MIDI info: {str(e)}")
            raise

    @staticmethod
    def validate_midi(midi: pretty_midi.PrettyMIDI) -> bool:
        """Validate MIDI file for common issues"""
        try:
            # Check if MIDI has any content
            if len(midi.instruments) == 0:
                logger.warning("MIDI has no instruments")
                return False

            # Check if any instrument has notes
            has_notes = any(len(inst.notes) > 0 for inst in midi.instruments)
            if not has_notes:
                logger.warning("MIDI has no notes")
                return False

            # Check for reasonable duration
            duration = midi.get_end_time()
            if duration <= 0 or duration > 3600:  # 0 seconds or more than 1 hour
                logger.warning(f"MIDI has unreasonable duration: {duration}")
                return False

            # Check for valid note properties
            for instrument in midi.instruments:
                for note in instrument.notes:
                    # Check pitch range
                    if not (0 <= note.pitch <= 127):
                        logger.warning(f"Invalid pitch: {note.pitch}")
                        return False

                    # Check velocity range
                    if not (0 <= note.velocity <= 127):
                        logger.warning(f"Invalid velocity: {note.velocity}")
                        return False

                    # Check timing
                    if note.start < 0 or note.end <= note.start:
                        logger.warning(f"Invalid note timing: start={note.start}, end={note.end}")
                        return False

            return True

        except Exception as e:
            logger.error(f"MIDI validation error: {str(e)}")
            return False

    @staticmethod
    def quantize_notes(
        notes: List[MidiNote],
        quantization: float = 0.25,
        tempo: float = DEFAULT_TEMPO
    ) -> List[MidiNote]:
        """
        Quantize note timings to musical grid

        Args:
            notes: List of notes to quantize
            quantization: Quantization value (0.25 = 16th notes, 0.5 = 8th notes, etc.)
            tempo: Tempo for quantization grid

        Returns:
            List of quantized notes
        """
        try:
            if not notes:
                return notes

            # Calculate quantization step in seconds
            beat_duration = 60.0 / tempo
            step_duration = beat_duration * quantization

            quantized_notes = []

            for note in notes:
                # Quantize start time
                quantized_start = round(note.start / step_duration) * step_duration

                # Quantize end time (ensure minimum duration)
                note_duration = max(note.end - note.start, step_duration)
                quantized_end = quantized_start + note_duration
                quantized_end = round(quantized_end / step_duration) * step_duration

                quantized_note = MidiNote(
                    pitch=note.pitch,
                    velocity=note.velocity,
                    start=max(0, quantized_start),  # Ensure non-negative
                    end=quantized_end,
                    channel=note.channel
                )

                quantized_notes.append(quantized_note)

            logger.debug(f"Quantized {len(notes)} notes with {quantization} step")
            return quantized_notes

        except Exception as e:
            logger.error(f"Failed to quantize notes: {str(e)}")
            return notes  # Return original on error

    @staticmethod
    def split_by_instrument(midi: pretty_midi.PrettyMIDI) -> Dict[str, pretty_midi.PrettyMIDI]:
        """
        Split MIDI into separate files by instrument

        Returns:
            Dictionary mapping instrument names to MIDI objects
        """
        try:
            result = {}

            for i, instrument in enumerate(midi.instruments):
                # Create new MIDI for this instrument
                new_midi = pretty_midi.PrettyMIDI(initial_tempo=midi.estimate_tempo())

                # Copy instrument
                new_instrument = pretty_midi.Instrument(
                    program=instrument.program,
                    is_drum=instrument.is_drum,
                    name=instrument.name or f"Instrument_{i+1}"
                )

                # Copy notes
                new_instrument.notes = instrument.notes.copy()
                new_midi.instruments.append(new_instrument)

                # Copy time signatures and key signatures
                new_midi.time_signature_changes = midi.time_signature_changes.copy()
                new_midi.key_signature_changes = midi.key_signature_changes.copy()

                instrument_name = instrument.name or f"instrument_{i+1}"
                result[instrument_name] = new_midi

            logger.debug(f"Split MIDI into {len(result)} instrument tracks")
            return result

        except Exception as e:
            logger.error(f"Failed to split MIDI by instrument: {str(e)}")
            raise

    @staticmethod
    def merge_midis(midis: List[pretty_midi.PrettyMIDI]) -> pretty_midi.PrettyMIDI:
        """
        Merge multiple MIDI files into one

        Args:
            midis: List of PrettyMIDI objects to merge

        Returns:
            Merged PrettyMIDI object
        """
        try:
            if not midis:
                raise ValueError("No MIDI files to merge")

            if len(midis) == 1:
                return midis[0]

            # Use first MIDI as base
            merged = pretty_midi.PrettyMIDI(initial_tempo=midis[0].estimate_tempo())

            # Merge all instruments
            for midi in midis:
                for instrument in midi.instruments:
                    merged.instruments.append(instrument)

            # Use time signature from first MIDI
            if midis[0].time_signature_changes:
                merged.time_signature_changes = midis[0].time_signature_changes.copy()

            # Use key signature from first MIDI
            if midis[0].key_signature_changes:
                merged.key_signature_changes = midis[0].key_signature_changes.copy()

            logger.debug(f"Merged {len(midis)} MIDI files")
            return merged

        except Exception as e:
            logger.error(f"Failed to merge MIDI files: {str(e)}")
            raise

    @staticmethod
    def extract_melody(midi: pretty_midi.PrettyMIDI) -> List[MidiNote]:
        """
        Extract main melody from MIDI (highest notes per time slice)

        Returns:
            List of melody notes
        """
        try:
            all_notes = []

            # Collect all notes from non-drum instruments
            for instrument in midi.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        all_notes.append(MidiNote(
                            pitch=note.pitch,
                            velocity=note.velocity,
                            start=note.start,
                            end=note.end,
                            channel=0
                        ))

            if not all_notes:
                return []

            # Sort notes by start time
            all_notes.sort(key=lambda n: n.start)

            # Extract melody using highest pitch at each time
            melody_notes = []
            time_resolution = 0.1  # 100ms resolution
            current_time = 0
            end_time = max(note.end for note in all_notes)

            while current_time < end_time:
                # Find notes active at current time
                active_notes = [
                    note for note in all_notes
                    if note.start <= current_time < note.end
                ]

                if active_notes:
                    # Select highest pitch
                    melody_note = max(active_notes, key=lambda n: n.pitch)

                    # Avoid duplicates
                    if not melody_notes or melody_notes[-1].pitch != melody_note.pitch:
                        melody_notes.append(MidiNote(
                            pitch=melody_note.pitch,
                            velocity=melody_note.velocity,
                            start=current_time,
                            end=min(current_time + time_resolution, melody_note.end),
                            channel=0
                        ))

                current_time += time_resolution

            logger.debug(f"Extracted melody with {len(melody_notes)} notes")
            return melody_notes

        except Exception as e:
            logger.error(f"Failed to extract melody: {str(e)}")
            return []

    @staticmethod
    def get_instrument_from_name(instrument_name: str) -> int:
        """Get MIDI instrument number from instrument name"""
        name_lower = instrument_name.lower().replace(' ', '_')

        # Try exact match first
        if name_lower in MidiUtils.INSTRUMENT_MAP:
            return MidiUtils.INSTRUMENT_MAP[name_lower]

        # Try partial matches
        for key, value in MidiUtils.INSTRUMENT_MAP.items():
            if key in name_lower or name_lower in key:
                return value

        # Default to piano
        return 0

    @staticmethod
    def create_chord_progression(
        chord_sequence: List[List[int]],
        durations: List[float],
        velocity: int = DEFAULT_VELOCITY
    ) -> List[MidiNote]:
        """
        Create MIDI notes from chord progression

        Args:
            chord_sequence: List of chords (each chord is list of MIDI note numbers)
            durations: Duration for each chord
            velocity: Note velocity

        Returns:
            List of MIDI notes
        """
        try:
            notes = []
            current_time = 0.0

            for chord, duration in zip(chord_sequence, durations):
                for pitch in chord:
                    if 0 <= pitch <= 127:  # Valid MIDI range
                        note = MidiNote(
                            pitch=pitch,
                            velocity=velocity,
                            start=current_time,
                            end=current_time + duration,
                            channel=0
                        )
                        notes.append(note)

                current_time += duration

            logger.debug(f"Created chord progression with {len(notes)} notes")
            return notes

        except Exception as e:
            logger.error(f"Failed to create chord progression: {str(e)}")
            return []

    @staticmethod
    def export_to_json(midi: pretty_midi.PrettyMIDI, file_path: Union[str, Path]) -> Path:
        """Export MIDI data to JSON format"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            midi_data = {
                "tempo": midi.estimate_tempo(),
                "duration": midi.get_end_time(),
                "time_signatures": [
                    {
                        "time": ts.time,
                        "numerator": ts.numerator,
                        "denominator": ts.denominator
                    }
                    for ts in midi.time_signature_changes
                ],
                "instruments": []
            }

            for i, instrument in enumerate(midi.instruments):
                inst_data = {
                    "name": instrument.name or f"Instrument {i+1}",
                    "program": instrument.program,
                    "is_drum": instrument.is_drum,
                    "notes": [
                        {
                            "pitch": note.pitch,
                            "velocity": note.velocity,
                            "start": note.start,
                            "end": note.end
                        }
                        for note in instrument.notes
                    ]
                }
                midi_data["instruments"].append(inst_data)

            with open(file_path, 'w') as f:
                json.dump(midi_data, f, indent=2)

            logger.debug(f"Exported MIDI to JSON: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to export MIDI to JSON: {str(e)}")
            raise

    @staticmethod
    def _format_key_signature(key_number: int) -> str:
        """Format key signature from MIDI key number"""
        key_map = {
            -7: "Cb major", -6: "Gb major", -5: "Db major", -4: "Ab major",
            -3: "Eb major", -2: "Bb major", -1: "F major", 0: "C major",
            1: "G major", 2: "D major", 3: "A major", 4: "E major",
            5: "B major", 6: "F# major", 7: "C# major"
        }

        return key_map.get(key_number, "C major")
