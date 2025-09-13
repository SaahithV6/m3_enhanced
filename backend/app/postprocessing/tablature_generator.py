import numpy as np
import pretty_midi
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json
from dataclasses import dataclass
import music21
from music21 import stream, note, pitch, duration, meter, key, tempo
import warnings
warnings.filterwarnings('ignore')

from ..core.config import config
from ..utils.midi_utils import MidiUtils

@dataclass
class GuitarNote:
    """Represents a guitar note with fret/string information"""
    midi_note: int
    start_time: float
    end_time: float
    velocity: int
    string: int
    fret: int
    technique: str = "normal"  # normal, bend, slide, hammer, pull, vibrato

@dataclass
class TablatureSettings:
    """Configuration for tablature generation"""
    tuning: List[int]  # MIDI note numbers for each string
    num_frets: int
    capo_position: int
    technique_detection: bool
    fingering_optimization: bool
    alternate_fingerings: bool

class TablatureGenerator:
    """
    Advanced guitar tablature generation with fingering optimization.
    Supports multiple tunings, playing techniques, and ergonomic fingering.
    """

    def __init__(self):
        self.midi_utils = MidiUtils()

        # Standard guitar tunings (MIDI note numbers, low to high)
        self.tunings = {
            "standard": [40, 45, 50, 55, 59, 64],  # E A D G B E
            "drop_d": [38, 45, 50, 55, 59, 64],    # D A D G B E
            "open_g": [38, 43, 50, 55, 59, 62],    # D G D G B D
            "dadgad": [38, 45, 50, 55, 57, 62],    # D A D G A D
            "open_e": [40, 47, 52, 56, 59, 64],    # E B E G# B E
            "drop_c": [36, 43, 48, 53, 57, 62],    # C G C F A D
            "7_string": [35, 40, 45, 50, 55, 59, 64],  # B E A D G B E
            "bass_4": [28, 33, 38, 43],            # E A D G (bass)
            "bass_5": [23, 28, 33, 38, 43],        # B E A D G (5-string bass)
        }

        # Fretboard constraints
        self.max_frets = {
            "guitar": 24,
            "bass": 24,
            "ukulele": 15,
            "mandolin": 20
        }

        # Technique detection parameters
        self.technique_thresholds = {
            "bend_cents": 50,      # Minimum pitch bend in cents
            "slide_semitones": 2,   # Minimum slide distance
            "vibrato_hz": 4,        # Vibrato frequency range
            "hammer_time_ms": 50,   # Max time for hammer-on
            "pull_time_ms": 50      # Max time for pull-off
        }

    def generate_tablature(self,
                          midi_path: Path,
                          instrument_type: str,
                          tuning: str = "auto") -> Path:
        """
        Generate optimized guitar tablature from MIDI file.

        Args:
            midi_path: Input MIDI file path
            instrument_type: Type of stringed instrument
            tuning: Tuning name or "auto" for detection

        Returns:
            Path to generated tablature file
        """
        try:
            # Load MIDI file
            midi_data = pretty_midi.PrettyMIDI(str(midi_path))

            # Determine instrument and tuning
            detected_tuning = self._detect_optimal_tuning(midi_data, instrument_type, tuning)
            print(f"Using tuning: {detected_tuning}")

            # Extract notes from MIDI
            notes = self._extract_notes_from_midi(midi_data)

            if not notes:
                raise ValueError("No notes found in MIDI file")

            # Create tablature settings
            settings = TablatureSettings(
                tuning=self.tunings[detected_tuning],
                num_frets=self.max_frets.get(instrument_type, 24),
                capo_position=0,
                technique_detection=True,
                fingering_optimization=True,
                alternate_fingerings=True
            )

            # Convert to guitar notes with fret positions
            guitar_notes = self._convert_to_guitar_notes(notes, settings)

            # Optimize fingerings
            optimized_notes = self._optimize_fingerings(guitar_notes, settings)

            # Detect playing techniques
            technique_notes = self._detect_techniques(optimized_notes, midi_data)

            # Generate tablature formats
            output_dir = midi_path.parent / "tablature"
            output_dir.mkdir(exist_ok=True)

            # Generate multiple formats
            formats_generated = []

            # 1. ASCII tablature
            ascii_path = self._generate_ascii_tablature(
                technique_notes, settings, output_dir / f"{midi_path.stem}_tab.txt"
            )
            formats_generated.append(ascii_path)

            # 2. Guitar Pro format (simplified)
            gp_path = self._generate_guitar_pro_format(
                technique_notes, settings, output_dir / f"{midi_path.stem}_tab.gp"
            )
            formats_generated.append(gp_path)

            # 3. TuxGuitar format
            tux_path = self._generate_tuxguitar_format(
                technique_notes, settings, output_dir / f"{midi_path.stem}_tab.tg"
            )
            formats_generated.append(tux_path)

            # 4. Music21 tablature notation
            music21_path = self._generate_music21_tablature(
                technique_notes, settings, output_dir / f"{midi_path.stem}_notation.xml"
            )
            formats_generated.append(music21_path)

            # Return primary format (ASCII)
            return ascii_path

        except Exception as e:
            print(f"Tablature generation failed: {e}")
            # Create placeholder tablature
            return self._create_placeholder_tablature(midi_path)

    def _detect_optimal_tuning(self,
                             midi_data: pretty_midi.PrettyMIDI,
                             instrument_type: str,
                             tuning_hint: str) -> str:
        """Detect optimal tuning based on MIDI content"""
        try:
            if tuning_hint != "auto" and tuning_hint in self.tunings:
                return tuning_hint

            # Extract all note pitches
            all_pitches = []
            for instrument in midi_data.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        all_pitches.append(note.pitch)

            if not all_pitches:
                return self._get_default_tuning(instrument_type)

            # Analyze pitch range and common notes
            min_pitch = min(all_pitches)
            max_pitch = max(all_pitches)
            pitch_range = max_pitch - min_pitch

            # Score each tuning
            tuning_scores = {}

            for tuning_name, tuning_notes in self.tunings.items():
                if not self._is_compatible_tuning(tuning_name, instrument_type):
                    continue

                score = self._score_tuning_fit(all_pitches, tuning_notes, 24)
                tuning_scores[tuning_name] = score

            # Return best scoring tuning
            if tuning_scores:
                best_tuning = max(tuning_scores, key=tuning_scores.get)
                print(f"Tuning scores: {tuning_scores}")
                return best_tuning
            else:
                return self._get_default_tuning(instrument_type)

        except Exception as e:
            print(f"Tuning detection failed: {e}")
            return self._get_default_tuning(instrument_type)

    def _is_compatible_tuning(self, tuning_name: str, instrument_type: str) -> bool:
        """Check if tuning is compatible with instrument type"""
        if "bass" in instrument_type:
            return "bass" in tuning_name
        elif "guitar" in instrument_type:
            return "bass" not in tuning_name and "7_string" not in tuning_name
        else:
            return tuning_name == "standard"

    def _get_default_tuning(self, instrument_type: str) -> str:
        """Get default tuning for instrument type"""
        if "bass" in instrument_type:
            return "bass_4"
        else:
            return "standard"

    def _score_tuning_fit(self, pitches: List[int], tuning: List[int], max_frets: int) -> float:
        """Score how well a tuning fits the given pitches"""
        try:
            playable_notes = 0
            total_notes = len(pitches)

            # Generate all possible notes for this tuning
            possible_notes = set()
            for string_note in tuning:
                for fret in range(max_frets + 1):
                    possible_notes.add(string_note + fret)

            # Count how many pitches are playable
            for pitch in pitches:
                if pitch in possible_notes:
                    playable_notes += 1

            # Calculate fitness score
            fitness = playable_notes / total_notes if total_notes > 0 else 0

            # Bonus for using open strings
            open_string_bonus = 0
            for pitch in pitches:
                if pitch in tuning:
                    open_string_bonus += 0.1

            return fitness + open_string_bonus

        except Exception:
            return 0.0

    def _extract_notes_from_midi(self, midi_data: pretty_midi.PrettyMIDI) -> List[Dict]:
        """Extract note events from MIDI data"""
        try:
            notes = []

            for instrument in midi_data.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        notes.append({
                            'pitch': note.pitch,
                            'start': note.start,
                            'end': note.end,
                            'velocity': note.velocity
                        })

            # Sort by start time
            notes.sort(key=lambda x: x['start'])

            return notes

        except Exception as e:
            print(f"Note extraction failed: {e}")
            return []

    def _convert_to_guitar_notes(self,
                               notes: List[Dict],
                               settings: TablatureSettings) -> List[GuitarNote]:
        """Convert MIDI notes to guitar notes with string/fret positions"""
        try:
            guitar_notes = []

            for note_data in notes:
                pitch = note_data['pitch']

                # Find best string/fret combination
                string, fret = self._find_best_fingering(pitch, settings)

                if string >= 0 and fret >= 0:
                    guitar_note = GuitarNote(
                        midi_note=pitch,
                        start_time=note_data['start'],
                        end_time=note_data['end'],
                        velocity=note_data['velocity'],
                        string=string,
                        fret=fret
                    )
                    guitar_notes.append(guitar_note)

            return guitar_notes

        except Exception as e:
            print(f"Guitar note conversion failed: {e}")
            return []

    def _find_best_fingering(self, pitch: int, settings: TablatureSettings) -> Tuple[int, int]:
        """Find optimal string and fret for a given pitch"""
        try:
            possible_positions = []

            # Check each string
            for string_idx, string_pitch in enumerate(settings.tuning):
                fret = pitch - string_pitch - settings.capo_position

                # Check if fret is playable
                if 0 <= fret <= settings.num_frets:
                    # Score this position
                    score = self._score_fingering_position(string_idx, fret, settings)
                    possible_positions.append((string_idx, fret, score))

            if not possible_positions:
                return -1, -1  # Unplayable

            # Return best scoring position
            best_position = max(possible_positions, key=lambda x: x[2])
            return best_position[0], best_position[1]

        except Exception:
            return -1, -1

    def _score_fingering_position(self, string: int, fret: int, settings: TablatureSettings) -> float:
        """Score a fingering position for ergonomics"""
        try:
            score = 1.0

            # Prefer lower frets (easier to play)
            if fret <= 5:
                score += 0.3
            elif fret <= 12:
                score += 0.1
            else:
                score -= 0.2  # High frets are harder

            # Prefer middle strings (easier to mute adjacent strings)
            num_strings = len(settings.tuning)
            middle_strings = range(1, num_strings - 1)
            if string in middle_strings:
                score += 0.1

            # Open strings get bonus
            if fret == 0:
                score += 0.2

            return score

        except Exception:
            return 0.0

    def _optimize_fingerings(self,
                           guitar_notes: List[GuitarNote],
                           settings: TablatureSettings) -> List[GuitarNote]:
        """Optimize fingerings for playability and flow"""
        try:
            if not guitar_notes:
                return guitar_notes

            optimized_notes = guitar_notes.copy()

            # Group notes by time windows for chord detection
            time_windows = self._group_notes_by_time(optimized_notes)

            for window_notes in time_windows:
                if len(window_notes) > 1:
                    # Optimize chord fingering
                    self._optimize_chord_fingering(window_notes, settings)
                else:
                    # Optimize single note in context
                    self._optimize_single_note_context(window_notes[0], optimized_notes, settings)

            return optimized_notes

        except Exception as e:
            print(f"Fingering optimization failed: {e}")
            return guitar_notes

    def _group_notes_by_time(self, notes: List[GuitarNote], tolerance: float = 0.05) -> List[List[GuitarNote]]:
        """Group notes that start within tolerance time of each other"""
        try:
            if not notes:
                return []

            groups = []
            current_group = [notes[0]]
            current_time = notes[0].start_time

            for note in notes[1:]:
                if abs(note.start_time - current_time) <= tolerance:
                    current_group.append(note)
                else:
                    groups.append(current_group)
                    current_group = [note]
                    current_time = note.start_time

            groups.append(current_group)
            return groups

        except Exception:
            return [[note] for note in notes]

    def _optimize_chord_fingering(self, chord_notes: List[GuitarNote], settings: TablatureSettings):
        """Optimize fingering for a chord"""
        try:
            if len(chord_notes) <= 1:
                return

            # Get all possible fingering combinations
            fingering_combinations = []

            for note in chord_notes:
                note_positions = []

                # Find alternative fingerings for this note
                for string_idx, string_pitch in enumerate(settings.tuning):
                    fret = note.midi_note - string_pitch - settings.capo_position
                    if 0 <= fret <= settings.num_frets:
                        note_positions.append((string_idx, fret))

                fingering_combinations.append(note_positions)

            # Find best combination that avoids conflicts
            best_fingering = self._find_best_chord_fingering(fingering_combinations, settings)

            # Apply best fingering
            for i, note in enumerate(chord_notes):
                if i < len(best_fingering):
                    note.string, note.fret = best_fingering[i]

        except Exception as e:
            print(f"Chord fingering optimization failed: {e}")

    def _find_best_chord_fingering(self, combinations: List[List[Tuple[int, int]]], settings: TablatureSettings) -> List[Tuple[int, int]]:
        """Find best chord fingering from combinations"""
        try:
            import itertools

            # Generate all possible combinations
            all_combinations = list(itertools.product(*combinations))

            best_combination = None
            best_score = -1

            for combination in all_combinations:
                # Check for string conflicts
                strings_used = [pos[0] for pos in combination]
                if len(set(strings_used)) != len(strings_used):
                    continue  # String conflict

                # Score this combination
                score = self._score_chord_fingering(combination, settings)

                if score > best_score:
                    best_score = score
                    best_combination = combination

            return best_combination or combinations[0][0:1] * len(combinations)

        except Exception:
            return [(0, 0)] * len(combinations)

    def _score_chord_fingering(self, fingering: Tuple, settings: TablatureSettings) -> float:
        """Score a chord fingering for playability"""
        try:
            score = 0.0
            frets = [pos[1] for pos in fingering]

            # Prefer compact fingerings
            fret_span = max(frets) - min(frets)
            if fret_span <= 4:  # Playable with one hand position
                score += 1.0
            else:
                score -= 0.5 * (fret_span - 4)

            # Prefer lower fret positions
            avg_fret = sum(frets) / len(frets)
            if avg_fret <= 5:
                score += 0.5
            elif avg_fret <= 12:
                score += 0.2

            # Bonus for open strings
            open_strings = sum(1 for fret in frets if fret == 0)
            score += open_strings * 0.3

            return score

        except Exception:
            return 0.0

    def _optimize_single_note_context(self, note: GuitarNote, all_notes: List[GuitarNote], settings: TablatureSettings):
        """Optimize single note fingering based on context"""
        try:
            # Find previous and next notes
            note_idx = all_notes.index(note)

            prev_note = all_notes[note_idx - 1] if note_idx > 0 else None
            next_note = all_notes[note_idx + 1] if note_idx < len(all_notes) - 1 else None

            # Get alternative fingerings
            alternatives = []
            for string_idx, string_pitch in enumerate(settings.tuning):
                fret = note.midi_note - string_pitch - settings.capo_position
                if 0 <= fret <= settings.num_frets:
                    alternatives.append((string_idx, fret))

            if len(alternatives) <= 1:
                return  # No alternatives

            # Score each alternative based on context
            best_fingering = None
            best_score = -1

            for string, fret in alternatives:
                score = 0.0

                # Score based on hand position continuity
                if prev_note:
                    fret_distance = abs(fret - prev_note.fret)
                    if fret_distance <= 4:
                        score += 0.5
                    else:
                        score -= 0.2 * (fret_distance - 4)

                if next_note:
                    fret_distance = abs(fret - next_note.fret)
                    if fret_distance <= 4:
                        score += 0.5
                    else:
                        score -= 0.2 * (fret_distance - 4)

                # Prefer same string as context if possible
                if prev_note and string == prev_note.string:
                    score += 0.3
                if next_note and string == next_note.string:
                    score += 0.3

                if score > best_score:
                    best_score = score
                    best_fingering = (string, fret)

            # Apply best fingering
            if best_fingering:
                note.string, note.fret = best_fingering

        except Exception as e:
            print(f"Single note context optimization failed: {e}")

    def _detect_techniques(self,
                         guitar_notes: List[GuitarNote],
                         midi_data: pretty_midi.PrettyMIDI) -> List[GuitarNote]:
        """Detect and annotate playing techniques"""
        try:
            technique_notes = guitar_notes.copy()

            # Detect techniques between consecutive notes
            for i in range(len(technique_notes) - 1):
                current_note = technique_notes[i]
                next_note = technique_notes[i + 1]

                # Detect slides
                if self._is_slide(current_note, next_note):
                    current_note.technique = "slide"

                # Detect hammer-ons
                elif self._is_hammer_on(current_note, next_note):
                    next_note.technique = "hammer"

                # Detect pull-offs
                elif self._is_pull_off(current_note, next_note):
                    next_note.technique = "pull"

            # Detect bends and vibrato from pitch bend data
            self._detect_pitch_techniques(technique_notes, midi_data)

            return technique_notes

        except Exception as e:
            print(f"Technique detection failed: {e}")
            return guitar_notes

    def _is_slide(self, note1: GuitarNote, note2: GuitarNote) -> bool:
        """Detect slide between two notes"""
        try:
            # Same string, different frets, overlapping or very close timing
            return (note1.string == note2.string and
                    abs(note1.fret - note2.fret) >= 2 and
                    note2.start_time - note1.end_time < 0.1)
        except Exception:
            return False

    def _is_hammer_on(self, note1: GuitarNote, note2: GuitarNote) -> bool:
        """Detect hammer-on"""
        try:
            # Same string, ascending frets, very close timing
            return (note1.string == note2.string and
                    note2.fret > note1.fret and
                    note2.start_time - note1.start_time < 0.05 and
                    note2.velocity < note1.velocity * 0.8)  # Hammer-ons are typically quieter
        except Exception:
            return False

    def _is_pull_off(self, note1: GuitarNote, note2: GuitarNote) -> bool:
        """Detect pull-off"""
        try:
            # Same string, descending frets, very close timing
            return (note1.string == note2.string and
                    note2.fret < note1.fret and
                    note2.start_time - note1.start_time < 0.05 and
                    note2.velocity < note1.velocity * 0.8)  # Pull-offs are typically quieter
        except Exception:
            return False

    def _detect_pitch_techniques(self, guitar_notes: List[GuitarNote], midi_data: pretty_midi.PrettyMIDI):
        """Detect pitch bends and vibrato from MIDI data"""
        try:
            for instrument in midi_data.instruments:
                if instrument.is_drum:
                    continue

                # Analyze pitch bend data
                pitch_bends = instrument.pitch_bends

                for note in guitar_notes:
                    # Find pitch bends during this note
                    note_bends = [pb for pb in pitch_bends
                                 if note.start_time <= pb.time <= note.end_time]

                    if note_bends:
                        # Analyze bend pattern
                        bend_values = [pb.pitch for pb in note_bends]

                        # Detect string bends (significant pitch change)
                        max_bend = max(bend_values) if bend_values else 0
                        if max_bend > self.technique_thresholds["bend_cents"]:
                            note.technique = "bend"

                        # Detect vibrato (oscillating pitch)
                        elif self._detect_vibrato_pattern(bend_values):
                            note.technique = "vibrato"

        except Exception as e:
            print(f"Pitch technique detection failed: {e}")

    def _detect_vibrato_pattern(self, bend_values: List[float]) -> bool:
        """Detect vibrato in pitch bend data"""
        try:
            if len(bend_values) < 10:
                return False

            # Look for oscillating pattern
            bend_array = np.array(bend_values)

            # Remove trend
            detrended = bend_array - np.linspace(bend_array[0], bend_array[-1], len(bend_array))

            # Check for oscillation
            zero_crossings = np.where(np.diff(np.signbit(detrended)))[0]

            # Vibrato should have multiple zero crossings
            return len(zero_crossings) >= 4

        except Exception:
            return False

    def _generate_ascii_tablature(self,
                                guitar_notes: List[GuitarNote],
                                settings: TablatureSettings,
                                output_path: Path) -> Path:
        """Generate ASCII tablature format"""
        try:
            # Create tablature lines
            num_strings = len(settings.tuning)
            tab_lines = [[] for _ in range(num_strings)]

            # Add tuning labels
            tuning_names = ["E", "B", "G", "D", "A", "E"]  # Standard tuning names
            if len(tuning_names) >= num_strings:
                string_labels = tuning_names[-num_strings:][::-1]  # Reverse for high to low
            else:
                string_labels = [f"S{i}" for i in range(num_strings)]

            # Determine time grid
            if not guitar_notes:
                # Create empty tablature
                for i in range(num_strings):
                    tab_lines[i] = ["-" * 50]
            else:
                # Create time-based grid
                start_time = min(note.start_time for note in guitar_notes)
                end_time = max(note.end_time for note in guitar_notes)
                duration = end_time - start_time

                # Grid resolution (16th notes at 120 BPM = 0.125 seconds)
                grid_resolution = 0.125
                grid_size = int(duration / grid_resolution) + 1

                # Initialize grid
                for i in range(num_strings):
                    tab_lines[i] = ["-"] * grid_size

                # Place notes on grid
                for note in guitar_notes:
                    if 0 <= note.string < num_strings:
                        time_pos = int((note.start_time - start_time) / grid_resolution)
                        if 0 <= time_pos < grid_size:
                            fret_str = str(note.fret)

                            # Add technique symbols
                            if note.technique == "hammer":
                                fret_str = f"h{fret_str}"
                            elif note.technique == "pull":
                                fret_str = f"p{fret_str}"
                            elif note.technique == "bend":
                                fret_str = f"{fret_str}b"
                            elif note.technique == "slide":
                                fret_str = f"{fret_str}/"
                            elif note.technique == "vibrato":
                                fret_str = f"{fret_str}~"

                            # Pad to ensure alignment
                            if len(fret_str) > 1:
                                # Extend following positions if needed
                                for j in range(1, len(fret_str)):
                                    if time_pos + j < grid_size:
                                        tab_lines[note.string][time_pos + j] = "-"

                            tab_lines[note.string][time_pos] = fret_str

            # Format tablature
            tab_content = []
            tab_content.append("Guitar Tablature")
            tab_content.append("=" * 50)
            tab_content.append("")

            # Add tuning information
            tuning_info = "Tuning: " + " ".join(string_labels)
            tab_content.append(tuning_info)
            tab_content.append("")

            # Add legend
            tab_content.append("Legend:")
            tab_content.append("h = hammer-on, p = pull-off, b = bend")
            tab_content.append("/ = slide up, \\ = slide down, ~ = vibrato")
            tab_content.append("")

            # Split into measures for readability
            chars_per_line = 80

            for start_pos in range(0, len(tab_lines[0]), chars_per_line):
                end_pos = min(start_pos + chars_per_line, len(tab_lines[0]))

                # Add measure lines
                for i, line in enumerate(tab_lines):
                    line_content = "".join(line[start_pos:end_pos])
                    tab_content.append(f"{string_labels[i]}|{line_content}|")

                tab_content.append("")

            # Write to file
            with open(output_path, 'w') as f:
                f.write("\n".join(tab_content))

            return output_path

        except Exception as e:
            print(f"ASCII tablature generation failed: {e}")
            return self._create_placeholder_tablature(output_path.parent / "placeholder.txt")

    def _generate_guitar_pro_format(self,
                                   guitar_notes: List[GuitarNote],
                                   settings: TablatureSettings,
                                   output_path: Path) -> Path:
        """Generate Guitar Pro compatible format"""
        try:
            # Create simplified Guitar Pro format (text-based)
            gp_content = []

            gp_content.append("{title: Guitar Tablature}")
            gp_content.append("{subtitle: Generated by M3 Enhanced}")
            gp_content.append("")

            # Track definition
            gp_content.append(f"{{track: Guitar - {len(settings.tuning)} strings}}")

            # Tuning
            tuning_str = " ".join(str(note) for note in settings.tuning)
            gp_content.append(f"{{tuning: {tuning_str}}}")
            gp_content.append("")

            # Notes in Guitar Pro format
            gp_content.append("# Tablature Data")

            for note in guitar_notes:
                # Guitar Pro format: string.fret duration
                duration_code = "4"  # Quarter note default

                technique_code = ""
                if note.technique == "hammer":
                    technique_code = " h"
                elif note.technique == "pull":
                    technique_code = " p"
                elif note.technique == "bend":
                    technique_code = " b"
                elif note.technique == "slide":
                    technique_code = " s"
                elif note.technique == "vibrato":
                    technique_code = " v"

                note_line = f"{note.string + 1}.{note.fret} {duration_code}{technique_code}"
                gp_content.append(note_line)

            # Write to file
            with open(output_path, 'w') as f:
                f.write("\n".join(gp_content))

            return output_path

        except Exception as e:
            print(f"Guitar Pro format generation failed: {e}")
            return output_path

    def _generate_tuxguitar_format(self,
                                  guitar_notes: List[GuitarNote],
                                  settings: TablatureSettings,
                                  output_path: Path) -> Path:
        """Generate TuxGuitar compatible format"""
        try:
            # TuxGuitar uses a proprietary format, so we'll create a text representation
            tux_content = []

            tux_content.append("TuxGuitar Tablature Format")
            tux_content.append("Generated by M3 Enhanced")
            tux_content.append("")

            # Track info
            tux_content.append(f"Strings: {len(settings.tuning)}")
            tux_content.append(f"Frets: {settings.num_frets}")
            tux_content.append("")

            # Note data
            tux_content.append("Note Data:")
            tux_content.append("Time(s) | String | Fret | Technique")
            tux_content.append("-" * 40)

            for note in guitar_notes:
                note_line = f"{note.start_time:.3f} | {note.string + 1} | {note.fret} | {note.technique}"
                tux_content.append(note_line)

            # Write to file
            with open(output_path, 'w') as f:
                f.write("\n".join(tux_content))

            return output_path

        except Exception as e:
            print(f"TuxGuitar format generation failed: {e}")
            return output_path

    def _generate_music21_tablature(self,
                                   guitar_notes: List[GuitarNote],
                                   settings: TablatureSettings,
                                   output_path: Path) -> Path:
        """Generate music notation with tablature using music21"""
        try:
            # Create music21 stream
            score = stream.Score()

            # Add metadata
            score.append(meter.TimeSignature('4/4'))
            score.append(key.KeySignature(0))  # C major
            score.append(tempo.TempoIndication(number=120))

            # Create part for guitar
            guitar_part = stream.Part()

            # Convert guitar notes to music21 notes
            for guitar_note in guitar_notes:
                # Create note
                m21_note = note.Note(guitar_note.midi_note)
                m21_note.quarterLength = guitar_note.end_time - guitar_note.start_time

                # Add tablature annotation
                m21_note.addLyric(f"{guitar_note.string + 1}:{guitar_note.fret}")

                # Add technique annotation
                if guitar_note.technique != "normal":
                    m21_note.addLyric(guitar_note.technique)

                guitar_part.append(m21_note)

            score.append(guitar_part)

            # Write to MusicXML
            score.write('musicxml', fp=str(output_path))

            return output_path

        except Exception as e:
            print(f"Music21 tablature generation failed: {e}")
            return output_path

    def _create_placeholder_tablature(self, output_path: Path) -> Path:
        """Create placeholder tablature file"""
        try:
            placeholder_content = """
Guitar Tablature - Placeholder

No tablature could be generated for this file.
This may be due to:
- No guitar content detected
- MIDI file parsing errors
- Unsupported note ranges

Please check the original audio file and try again.
            """

            with open(output_path, 'w') as f:
                f.write(placeholder_content.strip())

            return output_path

        except Exception:
            return output_path

# Global tablature generator instance
tablature_generator = TablatureGenerator()
