#!/usr/bin/env python3
"""
Professional Stem Creator & Mixer - Powered by Demucs AI
Separates audio into vocals, drums, bass, and other instruments
Uses state-of-the-art AI models for studio-quality separation
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import threading
import json
import tempfile

# Try to import required libraries
try:
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import save_audio, convert_audio
except ImportError as e:
    print(f"Installing required packages... ({e})")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                          "demucs", "torch", "soundfile", "numpy"])
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import save_audio, convert_audio

try:
    from pydub import AudioSegment
    from pydub.playback import play
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydub"])
    from pydub import AudioSegment
    from pydub.playback import play


class ProfessionalStemMixer:
    """
    Professional stem separation and mixing tool using Demucs AI
    """

    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Professional Stem Mixer - Powered by Demucs AI")
        self.root.geometry("900x750")
        self.root.configure(bg='#0a0a0a')

        self.input_file = None
        self.output_dir = None
        self.stems = {}  # Will store: vocals, drums, bass, other
        self.is_playing = False
        self.playback_thread = None
        self.model = None
        self.sample_rate = 44100

        # Volume levels (0.0 to 1.0) for each stem
        self.volumes = {
            'vocals': 1.0,
            'drums': 1.0,
            'bass': 1.0,
            'other': 1.0
        }

        # Solo/mute states
        self.solo_states = {
            'vocals': False,
            'drums': False,
            'bass': False,
            'other': False
        }

        self.mute_states = {
            'vocals': False,
            'drums': False,
            'bass': False,
            'other': False
        }

        self.setup_ui()
        self.load_model_async()

    def setup_ui(self):
        """Setup the professional GUI"""

        # Header
        header = tk.Frame(self.root, bg='#1a1a2e', height=100)
        header.pack(fill=tk.X)

        title = tk.Label(header, text="🎵 PROFESSIONAL STEM MIXER",
                        font=('Arial', 26, 'bold'),
                        bg='#1a1a2e', fg='#00d9ff')
        title.pack(pady=10)

        subtitle = tk.Label(header, text="Powered by Demucs AI - Studio Quality Separation",
                           font=('Arial', 11),
                           bg='#1a1a2e', fg='#888888')
        subtitle.pack()

        # Main container with scrolling
        canvas = tk.Canvas(self.root, bg='#0a0a0a', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0a0a0a')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # File selection
        file_frame = tk.LabelFrame(scrollable_frame, text="📁 Audio File",
                                   bg='#0a0a0a', fg='#00d9ff',
                                   font=('Arial', 12, 'bold'),
                                   padx=10, pady=10)
        file_frame.pack(fill=tk.X, padx=20, pady=10)

        self.file_label = tk.Label(file_frame, text="No file selected",
                                   bg='#0a0a0a', fg='#ffffff',
                                   font=('Arial', 10))
        self.file_label.pack(side=tk.LEFT, padx=10)

        tk.Button(file_frame, text="Select Audio File",
                 command=self.select_file,
                 bg='#00d9ff', fg='#000000',
                 font=('Arial', 10, 'bold'),
                 cursor='hand2').pack(side=tk.RIGHT, padx=10)

        # Model status
        status_frame = tk.Frame(scrollable_frame, bg='#0a0a0a')
        status_frame.pack(fill=tk.X, padx=20)

        self.model_status = tk.Label(status_frame,
                                     text="⏳ Loading Demucs AI model...",
                                     bg='#0a0a0a', fg='#ffaa00',
                                     font=('Arial', 9, 'italic'))
        self.model_status.pack()

        # Separation controls
        sep_frame = tk.LabelFrame(scrollable_frame, text="🤖 AI Stem Separation",
                                 bg='#0a0a0a', fg='#00d9ff',
                                 font=('Arial', 12, 'bold'),
                                 padx=10, pady=10)
        sep_frame.pack(fill=tk.X, padx=20, pady=10)

        model_info = tk.Label(sep_frame,
                             text="Separates into 4 stems: Vocals, Drums, Bass, Other (guitar, piano, etc.)",
                             bg='#0a0a0a', fg='#888888',
                             font=('Arial', 9))
        model_info.pack(pady=5)

        tk.Button(sep_frame, text="🔀 Separate Stems with AI",
                 command=self.separate_stems,
                 bg='#ff0066', fg='#ffffff',
                 font=('Arial', 13, 'bold'),
                 height=2,
                 cursor='hand2').pack(pady=10)

        self.progress_label = tk.Label(sep_frame, text="Ready to separate",
                                      bg='#0a0a0a', fg='#ffffff',
                                      font=('Arial', 10))
        self.progress_label.pack(pady=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(sep_frame, mode='indeterminate', length=400)
        self.progress_bar.pack(pady=5)

        # Mixer section
        mixer_frame = tk.LabelFrame(scrollable_frame, text="🎚️ Professional Mixer",
                                   bg='#0a0a0a', fg='#00d9ff',
                                   font=('Arial', 12, 'bold'),
                                   padx=10, pady=10)
        mixer_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create mixer channels
        channels_frame = tk.Frame(mixer_frame, bg='#0a0a0a')
        channels_frame.pack(fill=tk.BOTH, expand=True)

        self.sliders = {}
        self.solo_buttons = {}
        self.mute_buttons = {}

        stems_config = [
            ('vocals', '🎤 Vocals', '#ff0066'),
            ('drums', '🥁 Drums', '#00ff88'),
            ('bass', '🎸 Bass', '#ffaa00'),
            ('other', '🎹 Other', '#00d9ff')
        ]

        for i, (stem, label, color) in enumerate(stems_config):
            self.create_mixer_channel(channels_frame, stem, label, color, i)

        # Master controls
        master_frame = tk.Frame(scrollable_frame, bg='#0a0a0a')
        master_frame.pack(fill=tk.X, padx=20, pady=10)

        # Playback controls
        playback_frame = tk.LabelFrame(master_frame, text="⏯️ Playback",
                                       bg='#0a0a0a', fg='#00d9ff',
                                       font=('Arial', 11, 'bold'))
        playback_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(playback_frame, bg='#0a0a0a')
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="▶ Play Mix",
                 command=self.play_mixed,
                 bg='#00ff88', fg='#000000',
                 font=('Arial', 11, 'bold'),
                 width=12,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="⏹ Stop",
                 command=self.stop_playback,
                 bg='#ff0066', fg='#ffffff',
                 font=('Arial', 11, 'bold'),
                 width=12,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)

        # Export controls
        export_frame = tk.LabelFrame(master_frame, text="💾 Export",
                                     bg='#0a0a0a', fg='#00d9ff',
                                     font=('Arial', 11, 'bold'))
        export_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.BOTH, expand=True)

        exp_btn_frame = tk.Frame(export_frame, bg='#0a0a0a')
        exp_btn_frame.pack(pady=10)

        tk.Button(exp_btn_frame, text="💾 Export All Stems",
                 command=self.export_all_stems,
                 bg='#0066ff', fg='#ffffff',
                 font=('Arial', 10, 'bold'),
                 width=15,
                 cursor='hand2').pack(pady=3)

        tk.Button(exp_btn_frame, text="💾 Export Custom Mix",
                 command=self.export_custom_mix,
                 bg='#0066ff', fg='#ffffff',
                 font=('Arial', 10, 'bold'),
                 width=15,
                 cursor='hand2').pack(pady=3)

        tk.Button(exp_btn_frame, text="💾 Export Individual",
                 command=self.export_individual,
                 bg='#0066ff', fg='#ffffff',
                 font=('Arial', 10, 'bold'),
                 width=15,
                 cursor='hand2').pack(pady=3)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_mixer_channel(self, parent, stem_name, label, color, column):
        """Create a mixer channel strip"""
        channel = tk.Frame(parent, bg='#1a1a2e', relief=tk.RAISED, borderwidth=2)
        channel.grid(row=0, column=column, padx=5, pady=10, sticky='nsew')
        parent.columnconfigure(column, weight=1)

        # Channel label
        tk.Label(channel, text=label, bg='#1a1a2e', fg=color,
                font=('Arial', 12, 'bold')).pack(pady=10)

        # Solo button
        solo_btn = tk.Button(channel, text="S", width=3,
                            command=lambda: self.toggle_solo(stem_name),
                            bg='#333333', fg='#ffffff',
                            font=('Arial', 9, 'bold'),
                            cursor='hand2')
        solo_btn.pack(pady=2)
        self.solo_buttons[stem_name] = solo_btn

        # Mute button
        mute_btn = tk.Button(channel, text="M", width=3,
                            command=lambda: self.toggle_mute(stem_name),
                            bg='#333333', fg='#ffffff',
                            font=('Arial', 9, 'bold'),
                            cursor='hand2')
        mute_btn.pack(pady=2)
        self.mute_buttons[stem_name] = mute_btn

        # Volume slider
        slider = tk.Scale(channel, from_=100, to=0,
                         orient=tk.VERTICAL,
                         bg='#1a1a2e', fg='#ffffff',
                         troughcolor=color,
                         length=200,
                         command=lambda v, s=stem_name: self.update_volume(s, v))
        slider.set(100)
        slider.pack(pady=10)
        self.sliders[stem_name] = slider

        # Volume label
        vol_label = tk.Label(channel, text="100%", bg='#1a1a2e', fg='#ffffff',
                            font=('Arial', 9))
        vol_label.pack()

        # Store label reference for updates
        slider.vol_label = vol_label

    def load_model_async(self):
        """Load Demucs model asynchronously"""
        def load():
            try:
                self.model_status.config(text="⏳ Loading Demucs AI model (this may take a minute)...",
                                        fg='#ffaa00')
                self.root.update()

                # Load the hybrid transformer model (best quality)
                self.model = get_model('htdemucs')
                self.model.cpu()
                self.model.eval()

                self.model_status.config(text="✅ Demucs AI model ready! (htdemucs - studio quality)",
                                        fg='#00ff88')

            except Exception as e:
                self.model_status.config(text=f"❌ Model load error: {str(e)}",
                                        fg='#ff0066')
                messagebox.showerror("Model Error",
                                   f"Failed to load AI model:\n{str(e)}\n\n"
                                   f"Try: pip install demucs torch")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def select_file(self):
        """Select audio file"""
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.flac *.m4a *.ogg *.aac"),
                ("All Files", "*.*")
            ]
        )

        if filename:
            self.input_file = filename
            self.file_label.config(text=os.path.basename(filename))

    def separate_stems(self):
        """Separate audio into stems using Demucs AI"""
        if not self.input_file:
            messagebox.showerror("Error", "Please select an audio file first!")
            return

        if self.model is None:
            messagebox.showerror("Error", "AI model is still loading. Please wait...")
            return

        self.progress_label.config(text="🤖 AI is separating stems... This may take a few minutes...")
        self.progress_bar.start(10)
        self.root.update()

        def separate():
            try:
                # Load audio
                self.progress_label.config(text="📂 Loading audio file...")
                self.root.update()

                wav, sr = sf.read(self.input_file)

                # Convert to torch tensor
                if len(wav.shape) == 1:
                    wav = np.stack([wav, wav], axis=1)

                wav_tensor = torch.from_numpy(wav.T).float()

                # Convert to model sample rate if needed
                if sr != self.model.samplerate:
                    self.progress_label.config(text="🔄 Resampling audio...")
                    self.root.update()
                    wav_tensor = convert_audio(wav_tensor, sr, self.model.samplerate, self.model.audio_channels)

                self.sample_rate = self.model.samplerate

                # Apply model
                self.progress_label.config(text="🤖 AI is analyzing and separating (this takes time)...")
                self.root.update()

                with torch.no_grad():
                    sources = apply_model(self.model, wav_tensor.unsqueeze(0), device='cpu')[0]

                # Extract stems (htdemucs order: drums, bass, other, vocals)
                sources_np = sources.cpu().numpy()

                self.stems = {
                    'drums': sources_np[0],
                    'bass': sources_np[1],
                    'other': sources_np[2],
                    'vocals': sources_np[3],
                    'sample_rate': self.sample_rate
                }

                # Create output directory
                base_name = Path(self.input_file).stem
                self.output_dir = Path(self.input_file).parent / f"{base_name}_stems_demucs"
                self.output_dir.mkdir(exist_ok=True)

                # Save stems
                self.progress_label.config(text="💾 Saving separated stems...")
                self.root.update()

                for stem_name in ['vocals', 'drums', 'bass', 'other']:
                    stem_path = self.output_dir / f"{stem_name}.wav"
                    save_audio(torch.from_numpy(self.stems[stem_name]),
                             str(stem_path), self.sample_rate)

                self.progress_bar.stop()
                self.progress_label.config(
                    text=f"✅ Stems separated successfully! Saved to: {self.output_dir.name}/"
                )

                messagebox.showinfo("Success",
                                  f"AI separation complete!\n\n"
                                  f"Location: {self.output_dir}\n\n"
                                  f"Stems created:\n"
                                  f"• vocals.wav - Singing voice\n"
                                  f"• drums.wav - Percussion\n"
                                  f"• bass.wav - Bass line\n"
                                  f"• other.wav - Instruments (guitar, piano, etc.)")

            except Exception as e:
                self.progress_bar.stop()
                self.progress_label.config(text=f"❌ Error: {str(e)}")
                messagebox.showerror("Separation Error",
                                   f"Failed to separate stems:\n{str(e)}\n\n"
                                   f"Make sure you have enough RAM and disk space.")

        thread = threading.Thread(target=separate, daemon=True)
        thread.start()

    def update_volume(self, stem, value):
        """Update volume for a stem"""
        self.volumes[stem] = float(value) / 100.0

        # Update label
        if stem in self.sliders:
            self.sliders[stem].vol_label.config(text=f"{int(value)}%")

    def toggle_solo(self, stem):
        """Toggle solo for a stem"""
        self.solo_states[stem] = not self.solo_states[stem]

        # Update button color
        if self.solo_states[stem]:
            self.solo_buttons[stem].config(bg='#ffff00', fg='#000000')
        else:
            self.solo_buttons[stem].config(bg='#333333', fg='#ffffff')

    def toggle_mute(self, stem):
        """Toggle mute for a stem"""
        self.mute_states[stem] = not self.mute_states[stem]

        # Update button color
        if self.mute_states[stem]:
            self.mute_buttons[stem].config(bg='#ff0066', fg='#ffffff')
        else:
            self.mute_buttons[stem].config(bg='#333333', fg='#ffffff')

    def get_effective_volume(self, stem):
        """Get effective volume considering solo and mute states"""
        # Check if any stem is soloed
        any_solo = any(self.solo_states.values())

        if any_solo:
            # If this stem is not soloed, return 0
            if not self.solo_states[stem]:
                return 0.0

        # Check mute
        if self.mute_states[stem]:
            return 0.0

        return self.volumes[stem]

    def play_mixed(self):
        """Play mixed audio with current settings"""
        if not self.stems:
            messagebox.showerror("Error", "Please separate stems first!")
            return

        if self.is_playing:
            messagebox.showinfo("Info", "Already playing!")
            return

        def play_audio():
            try:
                self.is_playing = True

                # Mix all stems with volumes
                mixed = np.zeros_like(self.stems['vocals'])

                for stem_name in ['vocals', 'drums', 'bass', 'other']:
                    volume = self.get_effective_volume(stem_name)
                    mixed += self.stems[stem_name] * volume

                # Normalize to prevent clipping
                max_val = np.abs(mixed).max()
                if max_val > 0:
                    mixed = mixed / max_val * 0.95

                # Save temporary file
                if not self.output_dir:
                    temp_dir = Path(tempfile.gettempdir())
                else:
                    temp_dir = self.output_dir

                temp_file = temp_dir / "temp_preview.wav"
                save_audio(torch.from_numpy(mixed), str(temp_file), self.sample_rate)

                # Play
                audio = AudioSegment.from_wav(str(temp_file))
                play(audio)

                self.is_playing = False

            except Exception as e:
                self.is_playing = False
                messagebox.showerror("Playback Error", f"Failed to play:\n{str(e)}")

        self.playback_thread = threading.Thread(target=play_audio, daemon=True)
        self.playback_thread.start()

    def stop_playback(self):
        """Stop playback"""
        self.is_playing = False

    def export_all_stems(self):
        """Export all stems separately"""
        if not self.stems:
            messagebox.showerror("Error", "Please separate stems first!")
            return

        if not self.output_dir:
            messagebox.showerror("Error", "No output directory available!")
            return

        messagebox.showinfo("Stems Saved",
                          f"All stems are already saved in:\n{self.output_dir}\n\n"
                          f"Files:\n"
                          f"• vocals.wav\n"
                          f"• drums.wav\n"
                          f"• bass.wav\n"
                          f"• other.wav")

    def export_individual(self):
        """Export individual stem with current volume"""
        if not self.stems:
            messagebox.showerror("Error", "Please separate stems first!")
            return

        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Stem to Export")
        dialog.geometry("300x250")
        dialog.configure(bg='#1a1a2e')

        tk.Label(dialog, text="Select stem to export:",
                bg='#1a1a2e', fg='#ffffff',
                font=('Arial', 12)).pack(pady=20)

        selected_stem = tk.StringVar(value='vocals')

        for stem in ['vocals', 'drums', 'bass', 'other']:
            tk.Radiobutton(dialog, text=stem.capitalize(),
                          variable=selected_stem, value=stem,
                          bg='#1a1a2e', fg='#ffffff',
                          selectcolor='#0a0a0a',
                          font=('Arial', 11)).pack(pady=5)

        def do_export():
            stem = selected_stem.get()
            dialog.destroy()

            output_file = filedialog.asksaveasfilename(
                title=f"Save {stem.capitalize()}",
                defaultextension=".wav",
                initialfile=f"{stem}.wav",
                filetypes=[("WAV", "*.wav"), ("MP3", "*.mp3")]
            )

            if output_file:
                try:
                    stem_audio = self.stems[stem] * self.volumes[stem]

                    # Normalize
                    max_val = np.abs(stem_audio).max()
                    if max_val > 0:
                        stem_audio = stem_audio / max_val * 0.95

                    save_audio(torch.from_numpy(stem_audio), output_file, self.sample_rate)

                    messagebox.showinfo("Success",
                                      f"{stem.capitalize()} exported to:\n{output_file}")
                except Exception as e:
                    messagebox.showerror("Export Error", str(e))

        tk.Button(dialog, text="Export", command=do_export,
                 bg='#00d9ff', fg='#000000',
                 font=('Arial', 11, 'bold')).pack(pady=20)

    def export_custom_mix(self):
        """Export custom mix with current mixer settings"""
        if not self.stems:
            messagebox.showerror("Error", "Please separate stems first!")
            return

        output_file = filedialog.asksaveasfilename(
            title="Save Custom Mix",
            defaultextension=".wav",
            initialfile="custom_mix.wav",
            filetypes=[("WAV", "*.wav"), ("MP3", "*.mp3")]
        )

        if output_file:
            try:
                # Mix with current settings
                mixed = np.zeros_like(self.stems['vocals'])

                settings_text = "Mix settings:\n"
                for stem_name in ['vocals', 'drums', 'bass', 'other']:
                    volume = self.get_effective_volume(stem_name)
                    mixed += self.stems[stem_name] * volume

                    # Build settings text
                    status = ""
                    if self.mute_states[stem_name]:
                        status = " (MUTED)"
                    elif self.solo_states[stem_name]:
                        status = " (SOLO)"
                    settings_text += f"• {stem_name.capitalize()}: {int(volume * 100)}%{status}\n"

                # Normalize
                max_val = np.abs(mixed).max()
                if max_val > 0:
                    mixed = mixed / max_val * 0.95

                # Save
                save_audio(torch.from_numpy(mixed), output_file, self.sample_rate)

                messagebox.showinfo("Success",
                                  f"Custom mix exported to:\n{output_file}\n\n{settings_text}")

            except Exception as e:
                messagebox.showerror("Export Error", str(e))


def main():
    """Main entry point"""
    root = tk.Tk()
    app = ProfessionalStemMixer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
