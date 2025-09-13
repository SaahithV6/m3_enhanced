import numpy as np
import pretty_midi
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import music21
from music21 import stream, note, pitch, duration, meter, key, tempo, interval, chord, bar, clef, instrument
from music21 import metadata, layout, spanner, expressions, articulations
import subprocess
import json
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from ..core.config import config
from ..utils.midi_utils import MidiUtils

@dataclass
class NotationSettings:
    """Configuration for sheet music rendering"""
    clef_type: str  # treble, bass, alto, percussion
    key_signature: str  # "C", "G", "F", "Bb", etc.
    time_signature: str  # "4/4", "3/4", "6/8", etc.
    tempo_bpm: int
    instrument_name: str
    transposition: int  # semitones
    show_chord_symbols: bool
    show_lyrics: bool
    show_fingerings: bool
    multi_voice: bool

class SheetMusicRenderer:
    """
    Professional sheet music rendering system.
    Generates publication-quality notation in multiple formats.
    """

    def __init__(self):
        self.midi_utils = MidiUtils()

        # Instrument-specific notation settings
        self.instrument_settings = {
            "piano": NotationSettings(
                clef_type="treble_bass",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Piano",
                transposition=0,
                show_chord_symbols=True,
                show_lyrics=False,
                show_fingerings=True,
                multi_voice=True
            ),
            "lead_guitar": NotationSettings(
                clef_type="treble",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Electric Guitar",
                transposition=-12,  # Guitar sounds octave lower
                show_chord_symbols=False,
                show_lyrics=False,
                show_fingerings=False,
                multi_voice=False
            ),
            "rhythm_guitar": NotationSettings(
                clef_type="treble",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Electric Guitar",
                transposition=-12,
                show_chord_symbols=True,
                show_lyrics=False,
                show_fingerings=False,
                multi_voice=False
            ),
            "acoustic_guitar": NotationSettings(
                clef_type="treble",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Acoustic Guitar",
                transposition=-12,
                show_chord_symbols=True,
                show_lyrics=False,
                show_fingerings=True,
                multi_voice=False
            ),
            "bass": NotationSettings(
                clef_type="bass",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Electric Bass",
                transposition=-12,
                show_chord_symbols=False,
                show_lyrics=False,
                show_fingerings=True,
                multi_voice=False
            ),
            "vocals": NotationSettings(
                clef_type="treble",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Voice",
                transposition=0,
                show_chord_symbols=True,
                show_lyrics=True,
                show_fingerings=False,
                multi_voice=False
            ),
            "drums": NotationSettings(
                clef_type="percussion",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Drum Set",
                transposition=0,
                show_chord_symbols=False,
                show_lyrics=False,
                show_fingerings=False,
                multi_voice=True
            ),
            "synthesizer": NotationSettings(
                clef_type="treble",
                key_signature="C",
                time_signature="4/4",
                tempo_bpm=120,
                instrument_name="Synthesizer",
                transposition=0,
                show_chord_symbols=True,
                show_lyrics=False,
                show_fingerings=False,
                multi_voice=True
            )
        }

        # Output formats and their renderers
        self.output_formats = {
            "pdf": self._render_pdf,
            "svg": self._render_svg,
            "png": self._render_png,
            "musicxml": self._render_musicxml,
            "midi": self._render_midi,
            "abc": self._render_abc_notation,
            "lilypond": self._render_lilypond
        }

        # Check for external rendering tools
        self.available_renderers = self._detect_rendering_tools()

    def _detect_rendering_tools(self) -> Dict[str, bool]:
        """Detect available external rendering tools"""
        tools = {
            "lilypond": False,
            "mscore": False,  # MuseScore
            "timidity": False,
            "fluidsynth": False
        }

        for tool in tools:
            try:
                result = subprocess.run([tool, "--version"],
                                      capture_output=True,
                                      text=True,
                                      timeout=5)
                tools[tool] = result.returncode == 0
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                tools[tool] = False

        print(f"Available rendering tools: {tools}")
        return tools

    def render_sheet_music(self,
                          midi_path: Path,
                          instrument_type: str,
                          output_formats: List[str] = None) -> Path:
        """
        Render professional sheet music from MIDI file.

        Args:
            midi_path: Input MIDI file path
            instrument_type: Type of instrument for notation settings
            output_formats: List of output formats to generate

        Returns:
            Path to primary output file (PDF if available)
        """
        try:
            if output_formats is None:
                output_formats = ["pdf", "musicxml", "svg"]

            # Create sheet music directory
            sheet_dir = midi_path.parent / "sheet_music"
            sheet_dir.mkdir(exist_ok=True)

            # Load and analyze MIDI
            midi_data = pretty_midi.PrettyMIDI(str(midi_path))
            analysis = self._analyze_midi_for_notation(midi_data, instrument_type)

            # Get notation settings
            settings = self._get_notation_settings(instrument_type, analysis)

            # Create music21 score
            score = self._create_music21_score(midi_data, settings, analysis)

            # Enhance score with musical intelligence
            enhanced_score = self._enhance_score_musicality(score, settings, analysis)

            # Generate multiple formats
            output_files = []
            primary_output = None

            for format_name in output_formats:
                if format_name in self.output_formats:
                    output_path = sheet_dir / f"{midi_path.stem}_sheet.{format_name}"

                    try:
                        generated_path = self.output_formats[format_name](
                            enhanced_score, output_path, settings
                        )
                        output_files.append(generated_path)

                        # PDF is preferred primary output
                        if format_name == "pdf" or (primary_output is None and generated_path.exists()):
                            primary_output = generated_path

                    except Exception as e:
                        print(f"Failed to generate {format_name}: {e}")

            # Generate analysis report
            self._save_notation_analysis(analysis, settings, sheet_dir / "notation_analysis.json")

            return primary_output or (output_files[0] if output_files else midi_path)

        except Exception as e:
            print(f"Sheet music rendering failed: {e}")
            return self._create_placeholder_sheet_music(midi_path)

    def _analyze_midi_for_notation(self, midi_data: pretty_midi.PrettyMIDI, instrument_type: str) -> Dict:
        """Analyze MIDI data for intelligent notation decisions"""
        try:
            analysis = {
                "total_duration": midi_data.get_end_time(),
                "tempo_changes": [],
                "key_signature": "C",
                "time_signature": "4/4",
                "note_range": {"min": 127, "max": 0},
                "chord_progressions": [],
                "rhythmic_patterns": [],
                "dynamic_range": {"min": 127, "max": 0},
                "polyphony_level": 0,
                "articulations": [],
                "phrase_structure": []
            }

            all_notes = []

            # Collect all notes
            for instrument in midi_data.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        all_notes.append({
                            'pitch': note.pitch,
                            'start': note.start,
                            'end': note.end,
                            'velocity': note.velocity
                        })

            if not all_notes:
                return analysis

            # Analyze note range
            pitches = [n['pitch'] for n in all_notes]
            analysis["note_range"]["min"] = min(pitches)
            analysis["note_range"]["max"] = max(pitches)

            # Analyze dynamic range
            velocities = [n['velocity'] for n in all_notes]
            analysis["dynamic_range"]["min"] = min(velocities)
            analysis["dynamic_range"]["max"] = max(velocities)

            # Estimate key signature
            analysis["key_signature"] = self._estimate_key_signature(all_notes)

            # Estimate time signature
            analysis["time_signature"] = self._estimate_time_signature(all_notes)

            # Analyze polyphony
            analysis["polyphony_level"] = self._analyze_polyphony(all_notes)

            # Detect chord progressions (for harmonic instruments)
            if instrument_type in ["piano", "rhythm_guitar", "acoustic_guitar"]:
                analysis["chord_progressions"] = self._detect_chord_progressions(all_notes)

            # Analyze rhythmic patterns
            analysis["rhythmic_patterns"] = self._analyze_rhythmic_patterns(all_notes)

            # Detect phrase structure
            analysis["phrase_structure"] = self._detect_phrase_structure(all_notes)

            # Analyze tempo
            analysis["tempo_changes"] = self._analyze_tempo_changes(midi_data)

            return analysis

        except Exception as e:
            print(f"MIDI analysis failed: {e}")
            return {"error": str(e)}

    def _estimate_key_signature(self, notes: List[Dict]) -> str:
        """Estimate key signature using Krumhansl-Schmuckler algorithm"""
        try:
            # Count pitch classes
            pitch_class_counts = [0] * 12

            for note in notes:
                pc = note['pitch'] % 12
                duration = note['end'] - note['start']
                pitch_class_counts[pc] += duration

            # Normalize
            total_duration = sum(pitch_class_counts)
            if total_duration == 0:
                return "C"

            pitch_class_weights = [count / total_duration for count in pitch_class_counts]

            # Krumhansl-Schmuckler key profiles
            major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
            minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

            # Calculate correlations for all keys
            key_correlations = {}
            key_names = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'Db', 'Ab', 'Eb', 'Bb', 'F']

            for i in range(12):
                # Major key correlation
                major_corr = np.corrcoef(
                    pitch_class_weights,
                    [major_profile[(j - i) % 12] for j in range(12)]
                )[0, 1]

                # Minor key correlation
                minor_corr = np.corrcoef(
                    pitch_class_weights,
                    [minor_profile[(j - i) % 12] for j in range(12)]
                )[0, 1]

                if not np.isnan(major_corr):
                    key_correlations[key_names[i]] = major_corr
                if not np.isnan(minor_corr):
                    key_correlations[key_names[i] + 'm'] = minor_corr

            # Return most likely key
            if key_correlations:
                best_key = max(key_correlations, key=key_correlations.get)
                return best_key
            else:
                return "C"

        except Exception as e:
            print(f"Key estimation failed: {e}")
            return "C"

    def _estimate_time_signature(self, notes: List[Dict]) -> str:
        """Estimate time signature from rhythmic patterns"""
        try:
            if not notes:
                return "4/4"

            # Analyze note onset times
            onset_times = [note['start'] for note in notes]
            onset_times.sort()

            # Calculate inter-onset intervals
            intervals = []
            for i in range(1, len(onset_times)):
                interval = onset_times[i] - onset_times[i-1]
                if interval > 0.01:  # Ignore very small intervals
                    intervals.append(interval)

            if not intervals:
                return "4/4"

            # Find most common interval (beat estimate)
            interval_counts = {}
            for interval in intervals:
                rounded_interval = round(interval * 8) / 8  # Round to 8th note precision
                interval_counts[rounded_interval] = interval_counts.get(rounded_interval, 0) + 1

            most_common_interval = max(interval_counts, key=interval_counts.get)

            # Estimate time signature based on patterns
            if most_common_interval < 0.2:
                return "4/4"  # Fast notes, likely 4/4
            elif most_common_interval < 0.4:
                return "4/4"
            elif most_common_interval < 0.8:
                return "3/4"  # Could be 3/4 waltz
            else:
                return "4/4"  # Default

        except Exception:
            return "4/4"

    def _analyze_polyphony(self, notes: List[Dict]) -> int:
        """Analyze maximum polyphony level"""
        try:
            if not notes:
                return 0

            # Create time grid
            start_time = min(note['start'] for note in notes)
            end_time = max(note['end'] for note in notes)

            time_resolution = 0.01  # 10ms resolution
            num_steps = int((end_time - start_time) / time_resolution) + 1

            polyphony_levels = []

            for step in range(num_steps):
                current_time = start_time + step * time_resolution

                # Count simultaneous notes
                simultaneous_notes = 0
                for note in notes:
                    if note['start'] <= current_time <= note['end']:
                        simultaneous_notes += 1

                polyphony_levels.append(simultaneous_notes)

            return max(polyphony_levels) if polyphony_levels else 0

        except Exception:
            return 1

    def _detect_chord_progressions(self, notes: List[Dict]) -> List[Dict]:
        """Detect chord progressions in harmonic content"""
        try:
            # Group notes by time windows
            time_windows = self._group_notes_by_time_windows(notes, window_size=0.5)

            chord_progressions = []

            for window_start, window_notes in time_windows:
                if len(window_notes) >= 3:  # Minimum for a chord
                    # Extract pitches
                    pitches = [note['pitch'] % 12 for note in window_notes]
                    unique_pitches = sorted(set(pitches))

                    # Identify chord
                    chord_name = self._identify_chord(unique_pitches)

                    chord_progressions.append({
                        'time': window_start,
                        'pitches': unique_pitches,
                        'chord': chord_name,
                        'duration': 0.5
                    })

            return chord_progressions

        except Exception:
            return []

    def _identify_chord(self, pitch_classes: List[int]) -> str:
        """Identify chord from pitch classes"""
        try:
            if len(pitch_classes) < 3:
                return "unknown"

            # Common chord patterns (intervals from root)
            chord_patterns = {
                (0, 4, 7): "major",
                (0, 3, 7): "minor",
                (0, 4, 7, 11): "major7",
                (0, 3, 7, 10): "minor7",
                (0, 4, 7, 10): "dominant7",
                (0, 3, 6): "diminished",
                (0, 4, 8): "augmented",
                (0, 5, 7): "sus4",
                (0, 2, 7): "sus2"
            }

            # Try each pitch class as root
            for root in pitch_classes:
                # Normalize to root
                normalized = tuple(sorted([(pc - root) % 12 for pc in pitch_classes]))

                if normalized in chord_patterns:
                    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    root_name = note_names[root]
                    chord_type = chord_patterns[normalized]
                    return f"{root_name}{chord_type}"

            return "unknown"

        except Exception:
            return "unknown"

    def _analyze_rhythmic_patterns(self, notes: List[Dict]) -> List[Dict]:
        """Analyze rhythmic patterns and note durations"""
        try:
            if not notes:
                return []

            # Calculate note durations
            durations = []
            for note in notes:
                duration = note['end'] - note['start']
                durations.append(duration)

            # Quantize durations to common note values
            quantized_durations = []
            note_values = [2.0, 1.0, 0.5, 0.25, 0.125, 0.0625]  # Whole, half, quarter, eighth, sixteenth

            for duration in durations:
                # Find closest note value
                closest_value = min(note_values, key=lambda x: abs(x - duration))
                quantized_durations.append(closest_value)

            # Count patterns
            duration_counts = {}
            for duration in quantized_durations:
                duration_counts[duration] = duration_counts.get(duration, 0) + 1

            # Create pattern analysis
            patterns = []
            for duration, count in duration_counts.items():
                note_name = {
                    2.0: "whole",
                    1.0: "half",
                    0.5: "quarter",
                    0.25: "eighth",
                    0.125: "sixteenth",
                    0.0625: "thirty-second"
                }.get(duration, "irregular")

                patterns.append({
                    'duration': duration,
                    'note_type': note_name,
                    'count': count,
                    'percentage': count / len(durations) * 100
                })

            return patterns

        except Exception:
            return []

    def _detect_phrase_structure(self, notes: List[Dict]) -> List[Dict]:
        """Detect musical phrase structure"""
        try:
            if not notes:
                return []

            # Sort notes by time
            sorted_notes = sorted(notes, key=lambda x: x['start'])

            # Detect phrase boundaries based on gaps
            phrases = []
            current_phrase_start = sorted_notes[0]['start']
            current_phrase_notes = []

            gap_threshold = 1.0  # 1 second gap indicates phrase boundary

            for i, note in enumerate(sorted_notes):
                if i > 0:
                    gap = note['start'] - sorted_notes[i-1]['end']

                    if gap > gap_threshold:
                        # End current phrase
                        if current_phrase_notes:
                            phrases.append({
                                'start': current_phrase_start,
                                'end': current_phrase_notes[-1]['end'],
                                'note_count': len(current_phrase_notes),
                                'average_pitch': np.mean([n['pitch'] for n in current_phrase_notes]),
                                'dynamic_range': max(n['velocity'] for n in current_phrase_notes) -
                                               min(n['velocity'] for n in current_phrase_notes)
                            })

                        # Start new phrase
                        current_phrase_start = note['start']
                        current_phrase_notes = []

                current_phrase_notes.append(note)

            # Add final phrase
            if current_phrase_notes:
                phrases.append({
                    'start': current_phrase_start,
                    'end': current_phrase_notes[-1]['end'],
                    'note_count': len(current_phrase_notes),
                    'average_pitch': np.mean([n['pitch'] for n in current_phrase_notes]),
                    'dynamic_range': max(n['velocity'] for n in current_phrase_notes) -
                                   min(n['velocity'] for n in current_phrase_notes)
                })

            return phrases

        except Exception:
            return []

    def _analyze_tempo_changes(self, midi_data: pretty_midi.PrettyMIDI) -> List[Dict]:
        """Analyze tempo changes in MIDI data"""
        try:
            tempo_changes = []

            # Get tempo changes from MIDI
            for tempo_change in midi_data.tempo_changes:
                tempo_changes.append({
                    'time': tempo_change.time,
                    'tempo': tempo_change.tempo
                })

            # If no tempo changes, estimate from note timing
            if not tempo_changes:
                estimated_tempo = self._estimate_tempo_from_notes(midi_data)
                tempo_changes.append({
                    'time': 0.0,
                    'tempo': estimated_tempo
                })

            return tempo_changes

        except Exception:
            return [{'time': 0.0, 'tempo': 120}]

    def _estimate_tempo_from_notes(self, midi_data: pretty_midi.PrettyMIDI) -> float:
        """Estimate tempo from note timing patterns"""
        try:
            all_onsets = []

            for instrument in midi_data.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        all_onsets.append(note.start)

            if len(all_onsets) < 4:
                return 120.0  # Default tempo

            all_onsets.sort()

            # Calculate inter-onset intervals
            intervals = []
            for i in range(1, len(all_onsets)):
                interval = all_onsets[i] - all_onsets[i-1]
                if 0.1 < interval < 2.0:  # Reasonable interval range
                    intervals.append(interval)

            if not intervals:
                return 120.0

            # Find most common interval (beat estimate)
            median_interval = np.median(intervals)

            # Convert to BPM (assuming quarter note beat)
            estimated_bpm = 60.0 / median_interval

            # Clamp to reasonable range
            estimated_bpm = max(60, min(200, estimated_bpm))

            return float(estimated_bpm)

        except Exception:
            return 120.0

    def _get_notation_settings(self, instrument_type: str, analysis: Dict) -> NotationSettings:
        """Get notation settings based on instrument type and analysis"""
        try:
            # Start with default settings for instrument
            settings = self.instrument_settings.get(
                instrument_type,
                self.instrument_settings["piano"]
            ).copy()  # Make a copy to avoid modifying original

            # Override with analysis results
            if "key_signature" in analysis:
                settings.key_signature = analysis["key_signature"]

            if "time_signature" in analysis:
                settings.time_signature = analysis["time_signature"]

            if analysis.get("tempo_changes"):
                settings.tempo_bpm = int(analysis["tempo_changes"][0]["tempo"])

            # Adjust clef based on note range
            note_range = analysis.get("note_range", {})
            if note_range.get("max", 60) < 60:  # Below middle C
                if settings.clef_type == "treble":
                    settings.clef_type = "bass"

            return settings

        except Exception as e:
            print(f"Settings determination failed: {e}")
            return self.instrument_settings["piano"]

    def _create_music21_score(self,
                            midi_data: pretty_midi.PrettyMIDI,
                            settings: NotationSettings,
                            analysis: Dict) -> stream.Score:
        """Create music21 score from MIDI data"""
        try:
            # Create score
            score = stream.Score()

            # Add metadata
            score.append(metadata.Metadata())
            score.metadata.title = f"{settings.instrument_name} - M3 Enhanced Transcription"
            score.metadata.composer = "M3 Enhanced AI"

            # Add time signature
            time_sig = meter.TimeSignature(settings.time_signature)
            score.append(time_sig)

            # Add key signature
            key_sig = key.KeySignature(self._parse_key_signature(settings.key_signature))
            score.append(key_sig)

            # Add tempo
            tempo_mark = tempo.TempoIndication(number=settings.tempo_bpm)
            score.append(tempo_mark)

            # Create parts based on instrument type
            if settings.clef_type == "treble_bass":
                # Piano: create treble and bass parts
                treble_part = self._create_piano_treble_part(midi_data, settings, analysis)
                bass_part = self._create_piano_bass_part(midi_data, settings, analysis)
                score.append(treble_part)
                score.append(bass_part)

            elif settings.clef_type == "percussion":
                # Drums: create percussion part
                drum_part = self._create_drum_part(midi_data, settings, analysis)
                score.append(drum_part)

            else:
                # Single staff instrument
                single_part = self._create_single_staff_part(midi_data, settings, analysis)
                score.append(single_part)

            return score

        except Exception as e:
            print(f"Score creation failed: {e}")
            return stream.Score()

    def _parse_key_signature(self, key_str: str) -> int:
        """Parse key signature string to sharps/flats count"""
        try:
            key_map = {
                'C': 0, 'Am': 0,
                'G': 1, 'Em': 1,
                'D': 2, 'Bm': 2,
                'A': 3, 'F#m': 3,
                'E': 4, 'C#m': 4,
                'B': 5, 'G#m': 5,
                'F#': 6, 'D#m': 6,
                'F': -1, 'Dm': -1,
                'Bb': -2, 'Gm': -2,
                'Eb': -3, 'Cm': -3,
                'Ab': -4, 'Fm': -4,
                'Db': -5, 'Bbm': -5,
                'Gb': -6, 'Ebm': -6
            }

            return key_map.get(key_str, 0)

        except Exception:
            return 0

    def _create_single_staff_part(self,
                                midi_data: pretty_midi.PrettyMIDI,
                                settings: NotationSettings,
                                analysis: Dict) -> stream.Part:
        """Create single staff part for most instruments"""
        try:
            part = stream.Part()

            # Add instrument
            if settings.clef_type == "treble":
                part.append(clef.TrebleClef())
            elif settings.clef_type == "bass":
                part.append(clef.BassClef())
            elif settings.clef_type == "alto":
                part.append(clef.AltoClef())

            # Add instrument name
            part.append(instrument.Instrument(instrumentName=settings.instrument_name))

            # Convert MIDI notes to music21 notes
            all_notes = []
            for midi_instrument in midi_data.instruments:
                if not midi_instrument.is_drum:
                    for midi_note in midi_instrument.notes:
                        # Apply transposition
                        transposed_pitch = midi_note.pitch + settings.transposition

                        # Create music21 note
                        m21_note = note.Note(transposed_pitch)
                        m21_note.offset = midi_note.start
                        m21_note.quarterLength = midi_note.end - midi_note.start

                        # Add dynamics based on velocity
                        dynamic_marking = self._velocity_to_dynamic(midi_note.velocity)
                        if dynamic_marking:
                            m21_note.volume = dynamic_marking

                        all_notes.append(m21_note)

            # Sort notes by offset
            all_notes.sort(key=lambda x: x.offset)

            # Add notes to part with proper measures
            current_offset = 0
            measure_length = 4.0  # Assume 4/4 time for now

            for note_obj in all_notes:
                # Check if we need a new measure
                while note_obj.offset >= current_offset + measure_length:
                    current_offset += measure_length

                part.append(note_obj)

            # Add chord symbols if requested
            if settings.show_chord_symbols and analysis.get("chord_progressions"):
                for chord_info in analysis["chord_progressions"]:
                    if chord_info["chord"] != "unknown":
                        chord_symbol = chord.ChordSymbol(chord_info["chord"])
                        chord_symbol.offset = chord_info["time"]
                        part.append(chord_symbol)

            return part

        except Exception as e:
            print(f"Single staff part creation failed: {e}")
            return stream.Part()

    def _create_piano_treble_part(self,
                                midi_data: pretty_midi.PrettyMIDI,
                                settings: NotationSettings,
                                analysis: Dict) -> stream.Part:
        """Create treble clef part for piano"""
        try:
            part = stream.Part()
            part.append(clef.TrebleClef())
            part.append(instrument.Piano())

            # Filter notes for treble clef (typically above middle C)
            treble_notes = []
            for midi_instrument in midi_data.instruments:
                if not midi_instrument.is_drum:
                    for midi_note in midi_instrument.notes:
                        if midi_note.pitch >= 60:  # Middle C and above
                            m21_note = note.Note(midi_note.pitch)
                            m21_note.offset = midi_note.start
                            m21_note.quarterLength = midi_note.end - midi_note.start

                            dynamic_marking = self._velocity_to_dynamic(midi_note.velocity)
                            if dynamic_marking:
                                m21_note.volume = dynamic_marking

                            treble_notes.append(m21_note)

            # Sort and add notes
            treble_notes.sort(key=lambda x: x.offset)
            for note_obj in treble_notes:
                part.append(note_obj)

            return part

        except Exception as e:
            print(f"Piano treble part creation failed: {e}")
            return stream.Part()

    def _create_piano_bass_part(self,
                              midi_data: pretty_midi.PrettyMIDI,
                              settings: NotationSettings,
                              analysis: Dict) -> stream.Part:
        """Create bass clef part for piano"""
        try:
            part = stream.Part()
            part.append(clef.BassClef())
            part.append(instrument.Piano())

            # Filter notes for bass clef (typically below middle C)
            bass_notes = []
            for midi_instrument in midi_data.instruments:
                if not midi_instrument.is_drum:
                    for midi_note in midi_instrument.notes:
                        if midi_note.pitch < 60:  # Below middle C
                            m21_note = note.Note(midi_note.pitch)
                            m21_note.offset = midi_note.start
                            m21_note.quarterLength = midi_note.end - midi_note.start

                            dynamic_marking = self._velocity_to_dynamic(midi_note.velocity)
                            if dynamic_marking:
                                m21_note.volume = dynamic_marking

                            bass_notes.append(m21_note)

            # Sort and add notes
            bass_notes.sort(key=lambda x: x.offset)
            for note_obj in bass_notes:
                part.append(note_obj)

            return part

        except Exception as e:
            print(f"Piano bass part creation failed: {e}")
            return stream.Part()

    def _create_drum_part(self,
                        midi_data: pretty_midi.PrettyMIDI,
                        settings: NotationSettings,
                        analysis: Dict) -> stream.Part:
        """Create percussion part for drums"""
        try:
            part = stream.Part()
            part.append(clef.PercussionClef())
            part.append(instrument.Percussion())

            # Standard drum mapping
            drum_map = {
                36: 'C4',  # Kick drum
                38: 'D4',  # Snare
                42: 'F#4', # Hi-hat closed
                46: 'A#4', # Hi-hat open
                49: 'C#5', # Crash cymbal
                51: 'D#5', # Ride cymbal
            }

            # Convert drum notes
            drum_notes = []
            for midi_instrument in midi_data.instruments:
                if midi_instrument.is_drum:
                    for midi_note in midi_instrument.notes:
                        if midi_note.pitch in drum_map:
                            drum_pitch = drum_map[midi_note.pitch]
                            m21_note = note.Note(drum_pitch)
                            m21_note.offset = midi_note.start
                            m21_note.quarterLength = midi_note.end - midi_note.start

                            # Add drum-specific notehead
                            if midi_note.pitch == 36:  # Kick
                                m21_note.notehead = 'diamond'
                            elif midi_note.pitch == 38:  # Snare
                                m21_note.notehead = 'normal'
                            elif midi_note.pitch in [42, 46]:  # Hi-hats
                                m21_note.notehead = 'x'

                            drum_notes.append(m21_note)

            # Sort and add notes
            drum_notes.sort(key=lambda x: x.offset)
            for note_obj in drum_notes:
                part.append(note_obj)

            return part

        except Exception as e:
            print(f"Drum part creation failed: {e}")
            return stream.Part()

    def _velocity_to_dynamic(self, velocity: int) -> Optional[str]:
        """Convert MIDI velocity to dynamic marking"""
        try:
            if velocity < 32:
                return "pp"
            elif velocity < 48:
                return "p"
            elif velocity < 64:
                return "mp"
            elif velocity < 80:
                return "mf"
            elif velocity < 96:
                return "f"
            elif velocity < 112:
                return "ff"
            else:
                return "fff"
        except Exception:
            return None

    def _enhance_score_musicality(self,
                                score: stream.Score,
                                settings: NotationSettings,
                                analysis: Dict) -> stream.Score:
        """Enhance score with musical intelligence and proper formatting"""
        try:
            enhanced_score = score

            # Add phrase markings
            self._add_phrase_markings(enhanced_score, analysis)

            # Add articulations based on analysis
            self._add_articulations(enhanced_score, analysis)

            # Add breath marks and slurs
            self._add_expression_markings(enhanced_score, analysis)

            # Optimize note spelling (enharmonic equivalents)
            self._optimize_note_spelling(enhanced_score, settings)

            # Add measure numbers
            self._add_measure_numbers(enhanced_score)

            # Format layout
            self._format_score_layout(enhanced_score, settings)

            return enhanced_score

        except Exception as e:
            print(f"Score enhancement failed: {e}")
            return score

    def _add_phrase_markings(self, score: stream.Score, analysis: Dict):
        """Add phrase markings based on analysis"""
        try:
            phrases = analysis.get("phrase_structure", [])

            for part in score.parts:
                for phrase in phrases:
                    # Find notes in phrase time range
                    phrase_notes = []
                    for element in part.flat.notes:
                        if phrase["start"] <= element.offset <= phrase["end"]:
                            phrase_notes.append(element)

                    # Add slur over phrase
                    if len(phrase_notes) >= 2:
                        phrase_slur = spanner.Slur(phrase_notes[0], phrase_notes[-1])
                        part.append(phrase_slur)

        except Exception as e:
            print(f"Phrase marking failed: {e}")

    def _add_articulations(self, score: stream.Score, analysis: Dict):
        """Add articulations based on rhythmic analysis"""
        try:
            rhythmic_patterns = analysis.get("rhythmic_patterns", [])

            # Determine if music is staccato or legato based on note durations
            short_note_percentage = 0
            for pattern in rhythmic_patterns:
                if pattern["duration"] <= 0.25:  # Eighth notes or shorter
                    short_note_percentage += pattern["percentage"]

            # Add staccato to short notes if music is predominantly short
            if short_note_percentage > 60:
                for part in score.parts:
                    for note_obj in part.flat.notes:
                        if note_obj.quarterLength <= 0.25:
                            note_obj.articulations.append(articulations.Staccato())

        except Exception as e:
            print(f"Articulation addition failed: {e}")

    def _add_expression_markings(self, score: stream.Score, analysis: Dict):
        """Add expression markings and dynamics"""
        try:
            # Add dynamic markings based on velocity analysis
            dynamic_range = analysis.get("dynamic_range", {})

            if dynamic_range.get("max", 0) - dynamic_range.get("min", 127) > 40:
                # High dynamic range - add expression markings
                for part in score.parts:
                    # Add crescendo and diminuendo markings
                    notes = list(part.flat.notes)
                    if len(notes) > 4:
                        # Add crescendo in middle section
                        mid_point = len(notes) // 2
                        crescendo = expressions.Crescendo()
                        crescendo.offset = notes[mid_point - 2].offset
                        part.append(crescendo)

        except Exception as e:
            print(f"Expression marking failed: {e}")

    def _optimize_note_spelling(self, score: stream.Score, settings: NotationSettings):
        """Optimize enharmonic note spelling based on key signature"""
        try:
            key_obj = key.Key(settings.key_signature)

            for part in score.parts:
                for note_obj in part.flat.notes:
                    if hasattr(note_obj, 'pitch'):
                        # Get the pitch in the context of the key
                        corrected_pitch = key_obj.getEnharmonic(note_obj.pitch)
                        note_obj.pitch = corrected_pitch

        except Exception as e:
            print(f"Note spelling optimization failed: {e}")

    def _add_measure_numbers(self, score: stream.Score):
        """Add measure numbers to score"""
        try:
            for part in score.parts:
                measures = part.getElementsByClass(bar.Measure)
                for i, measure in enumerate(measures):
                    if i % 4 == 0:  # Every 4 measures
                        measure.number = i + 1

        except Exception as e:
            print(f"Measure numbering failed: {e}")

    def _format_score_layout(self, score: stream.Score, settings: NotationSettings):
        """Format score layout and spacing"""
        try:
            # Add title and composer
            title_text = layout.TextBox(f"{settings.instrument_name} Transcription")
            title_text.style.fontSize = 16
            title_text.style.fontWeight = 'bold'
            score.insert(0, title_text)

            # Set page layout
            page_layout = layout.PageLayout(
                pageHeight=11*72,  # 11 inches in points
                pageWidth=8.5*72,  # 8.5 inches in points
                leftMargin=72,     # 1 inch margins
                rightMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            score.insert(0, page_layout)

        except Exception as e:
            print(f"Score layout formatting failed: {e}")

    # Output format renderers
    def _render_pdf(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to PDF"""
        try:
            if self.available_renderers["lilypond"]:
                return self._render_pdf_lilypond(score, output_path, settings)
            elif self.available_renderers["mscore"]:
                return self._render_pdf_musescore(score, output_path, settings)
            else:
                # Fallback to music21's built-in PDF generation
                score.write('pdf', fp=str(output_path))
                return output_path

        except Exception as e:
            print(f"PDF rendering failed: {e}")
            return output_path

    def _render_pdf_lilypond(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render PDF using LilyPond"""
        try:
            # Convert to LilyPond format first
            ly_path = output_path.with_suffix('.ly')
            score.write('lilypond', fp=str(ly_path))

            # Render with LilyPond
            subprocess.run([
                'lilypond',
                '--pdf',
                '--output=' + str(output_path.parent),
                str(ly_path)
            ], check=True, capture_output=True)

            # Clean up intermediate file
            ly_path.unlink()

            return output_path

        except Exception as e:
            print(f"LilyPond PDF rendering failed: {e}")
            return output_path

    def _render_svg(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to SVG"""
        try:
            score.write('svg', fp=str(output_path))
            return output_path
        except Exception as e:
            print(f"SVG rendering failed: {e}")
            return output_path

    def _render_png(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to PNG"""
        try:
            score.write('png', fp=str(output_path))
            return output_path
        except Exception as e:
            print(f"PNG rendering failed: {e}")
            return output_path

    def _render_musicxml(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to MusicXML"""
        try:
            score.write('musicxml', fp=str(output_path))
            return output_path
        except Exception as e:
            print(f"MusicXML rendering failed: {e}")
            return output_path

    def _render_midi(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to MIDI"""
        try:
            score.write('midi', fp=str(output_path))
            return output_path
        except Exception as e:
            print(f"MIDI rendering failed: {e}")
            return output_path

    def _render_abc_notation(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to ABC notation"""
        try:
            # Convert to ABC format
            abc_content = []
            abc_content.append("X:1")
            abc_content.append(f"T:{settings.instrument_name} Transcription")
            abc_content.append("C:M3 Enhanced AI")
            abc_content.append(f"M:{settings.time_signature}")
            abc_content.append(f"Q:1/4={settings.tempo_bpm}")
            abc_content.append(f"K:{settings.key_signature}")
            abc_content.append("")

            # Simple note conversion (basic implementation)
            for part in score.parts:
                for note_obj in part.flat.notes:
                    if hasattr(note_obj, 'pitch'):
                        # Convert to ABC notation
                        abc_note = self._midi_to_abc_note(note_obj.pitch.midi)
                        abc_content.append(abc_note)

            # Write to file
            with open(output_path, 'w') as f:
                f.write('\n'.join(abc_content))

            return output_path

        except Exception as e:
            print(f"ABC notation rendering failed: {e}")
            return output_path

    def _render_lilypond(self, score: stream.Score, output_path: Path, settings: NotationSettings) -> Path:
        """Render score to LilyPond format"""
        try:
            score.write('lilypond', fp=str(output_path))
            return output_path
        except Exception as e:
            print(f"LilyPond rendering failed: {e}")
            return output_path

    def _midi_to_abc_note(self, midi_pitch: int) -> str:
        """Convert MIDI pitch to ABC notation"""
        try:
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = midi_pitch // 12 - 1
            note_name = note_names[midi_pitch % 12]

            # ABC notation octave handling
            if octave < 4:
                note_name = note_name.lower()
                if octave < 3:
                    note_name += ',' * (3 - octave)
            else:
                if octave > 4:
                    note_name += "'" * (octave - 4)

            return note_name

        except Exception:
            return "C"

    def _group_notes_by_time_windows(self, notes: List[Dict], window_size: float) -> List[Tuple[float, List[Dict]]]:
        """Group notes by time windows"""
        try:
            if not notes:
                return []

            sorted_notes = sorted(notes, key=lambda x: x['start'])
            windows = []

            current_window_start = sorted_notes[0]['start']
            current_window_notes = []

            for note in sorted_notes:
                if note['start'] < current_window_start + window_size:
                    current_window_notes.append(note)
                else:
                    if current_window_notes:
                        windows.append((current_window_start, current_window_notes))

                    current_window_start = note['start']
                    current_window_notes = [note]

            # Add final window
            if current_window_notes:
                windows.append((current_window_start, current_window_notes))

            return windows

        except Exception:
            return []

    def _save_notation_analysis(self, analysis: Dict, settings: NotationSettings, report_path: Path):
        """Save notation analysis report"""
        try:
            from datetime import datetime

            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "analysis": analysis,
                "notation_settings": {
                    "clef_type": settings.clef_type,
                    "key_signature": settings.key_signature,
                    "time_signature": settings.time_signature,
                    "tempo_bpm": settings.tempo_bpm,
                    "instrument_name": settings.instrument_name,
                    "transposition": settings.transposition
                },
                "rendering_tools": self.available_renderers
            }

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

        except Exception as e:
            print(f"Failed to save notation analysis: {e}")

    def _create_placeholder_sheet_music(self, midi_path: Path) -> Path:
        """Create placeholder sheet music file"""
        try:
            placeholder_path = midi_path.parent / f"{midi_path.stem}_sheet_placeholder.txt"

            placeholder_content = """
Sheet Music Generation Failed

No sheet music could be generated for this file.
This may be due to:
- MIDI file parsing errors
- Missing music notation dependencies
- Unsupported note ranges or instruments

Please install LilyPond or MuseScore for better sheet music generation.

To install LilyPond:
- Ubuntu/Debian: sudo apt-get install lilypond
- macOS: brew install lilypond
- Windows: Download from lilypond.org
            """

            with open(placeholder_path, 'w') as f:
                f.write(placeholder_content.strip())

            return placeholder_path

        except Exception:
            return midi_path

# Global sheet music renderer instance
sheet_music_renderer = SheetMusicRenderer()
