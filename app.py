import unittest
import os
import time
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

# Import the function and variables we need to test from app.py
import gradio as gr
from app import generate_tts, output_dir, LANG_MAP, get_generated_files, delete_file, convert_audio

class TestGenerateTTS(unittest.TestCase):

    def setUp(self):
        """Set up a temporary file to act as the speaker_wav input."""
        self.temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_wav_path = self.temp_wav_file.name
        self.temp_wav_file.close()
self.temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_wav_path = self.temp_wav_file.name
        self.temp_wav_file.close()
    @patch('app.convert_audio')
    @patch('app.subprocess.run')
    def test_successful_synthesis_with_conversion(self, mock_subprocess_run, mock_convert_audio):
        """Should convert non-wav speaker file and then synthesize."""
        # Create a dummy non-wav file
        temp_mp3_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_mp3_path = temp_mp3_file.name
        temp_mp3_file.close()

        mock_convert_audio.return_value = self.temp_wav_path # Simulate successful conversion
        mock_subprocess_run.return_value = MagicMock(stdout="TTS success", stderr="")

        audio_path, _, status = generate_tts("Test text", "Deutsch", temp_mp3_path)

        mock_convert_audio.assert_called_once_with(temp_mp3_path, "Audiokonvertierung (ffmpeg)")
        mock_subprocess_run.assert_called_once()
        self.assertIsNotNone(audio_path)
        self.assertIn("Sprache erfolgreich generiert", status)

        os.remove(temp_mp3_path) # Clean up dummy mp3

    def tearDown(self):
        """Clean up the temporary file after each test."""
        os.remove(self.temp_wav_path)
        # Clean up any output files created during tests
        for f in output_dir.glob("output_*.wav"):
            f.unlink()

    def test_input_validation_empty_text(self):
        """Should return an error if the input text is empty."""
        audio_path, _, status = generate_tts("", "Deutsch", self.temp_wav_path)
        self.assertIsNone(audio_path)
        self.assertIn("Der Eingabetext ist leer", status)

    def test_input_validation_no_speaker_file(self):
        """Should return an error if the speaker_wav file is None."""
        audio_path, _, status = generate_tts("Hallo Welt", "Deutsch", None)
        self.assertIsNone(audio_path)
        self.assertIn("Es wurde keine Referenz-Audiodatei hochgeladen", status)

    @patch('app.subprocess.run')
    def test_successful_synthesis(self, mock_subprocess_run):
        """Should return the audio path and a success message on successful TTS execution."""
        # Configure the mock to simulate a successful process run
        mock_process = MagicMock()
        mock_process.stdout = "TTS process finished successfully."
        mock_process.stderr = ""
        mock_subprocess_run.return_value = mock_process

        audio_path, _, status = generate_tts("Dies ist ein Test", "Deutsch", self.temp_wav_path)

        # Assert that subprocess.run was called once
        mock_subprocess_run.assert_called_once()
        
        # Assert that a valid path within the output directory is returned
        self.assertIsNotNone(audio_path)
        self.assertTrue(audio_path.startswith(str(output_dir)))
        self.assertTrue(audio_path.endswith(".wavself.temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_wav_path = self.temp_wav_file.name
        self.temp_wav_file.close()

    def tearDown(self):
        """Clean up the temporary file after each test."""
        os.remove(self.temp_wav_path)
        # Clean up any output files created during tests
        for f in output_dir.glob("output_*.wav"):
            f.unlink()

    def test_input_validation_empty_text(self):
        """Should return an error if the input text is empty."""
        audio_path, _, status = generate_tts("", "Deutsch", self.temp_wav_path)
        self.assertIsNone(audio_path)
        self.assertIn("Der Eingabetext ist leer", status)

    def test_input_validation_no_speaker_file(self):
        """Should return an error if the speaker_wav file is None."""
        audio_path, _, status = generate_tts("Hallo Welt", "Deutsch", None)
        self.assertIsNone(audio_path)
        self.assertIn("Es wurde keine Referenz-Audiodatei hochgeladen", status)

    @patch('app.subprocess.run')
    def test_successful_synthesis(self, mock_subprocess_run):
        """Should return the audio path and a success message on successful TTS execution."""
        # Configure the mock to simulate a successful process run
        mock_process = MagicMock()
        mock_process.stdout = "TTS process finished successfully."
        mock_process.stderr = ""
        mock_subprocess_run.return_value =import gradio as gr
import subprocess
import os
import tempfile
import time
import sys
from pathlib import Path

# --- Konfiguration ---
output_dir = Path("generierte_stimmen")
output_dir.mkdir(exist_ok=True)

LANG_MAP = {
    "Deutsch": "de", "Englisch": "en", "Spanisch": "es", "Französisch": "fr",
    "Italienisch": "it", "Portugiesisch": "pt", "Polnisch": "pl", "Türkisch": "tr",
    "Russisch": "ru", "Niederländisch": "nl", "Tschechisch": "cs", "Arabisch": "ar",
    "Chinesisch": "zh-cn", "Japanisch": "ja", "Ungarisch": "hu", "Koreanisch": "ko"
}
LANG_CHOICES = list(LANG_MAP.keys())



# --- Hilfsfunktionen ---

def get_generated_files(for_update: bool = False):
    """
    Listet die generierten WAV-Dateien auf, sortiert nach Änderungsdatum.
    """
    try:
        files = [f for f in output_dir.glob("*.wav")]
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        choices = [(f.name, str(f)) for f in files]
    except FileNotFoundError:
        choices = []
    
    if for_update:
        return gr.update(choices=choices, value=None)
    return choices

def convert_audio(input_path: str, process_name: str, timeout: int = 30) -> str:
    """
    Konvertiert eine Audio-Datei in 22.05 kHz Mono WAV mit ffmpeg.
    """
    converted_path = Path(tempfile.gettempdir()) / f"{Path(input_path).stem}_converted.wav"
    
    command = [
        "ffmpeg", "-i", str(input_path), 
        "-ar", "22050", "-ac", "1", 
        str(converted_path), "-y"
    ]
    
    try:
        subprocess.run(
            command, check=True, capture_output=True, 
            text=True, encoding='utf-8', timeout=timeout
        )
        return str(converted_path)
    except FileNotFoundError:
        raise FileNotFoundError("FEHLER: 'ffmpeg' wurde nicht gefunden. Bitte stellen Sie sicher, dass es installiert ist.")
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"FEHLER: '{process_name}' hat das Zeitlimit überschritten.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FEHLER bei der Audiokonvertierung (ffmpeg):\nExit-Code: {e.returncode}\nFehler: {e.stderr}")

class SecurityException(Exception):
    pass

def delete_file(file_to_delete_path: str):
    """
    Löscht eine ausgewählte generierte Datei sicher.
    """
    if not file_to_delete_path:
        return get_generated_files(for_update=True), None, "⚠️ Keine Datei zum Löschen ausgewählt."
    try:
        safe_path = Path(file_to_delete_path).resolve()
        if output_dir.resolve() not in safe_path.parents:
            raise SecurityException(f"Sicherheitswarnung: Löschen außerhalb des erlaubten Verzeichnisses '{output_dir}' verweigert.")
        safe_path.unlink(missing_ok=False)
        status_message = f"🗑️ Datei '{safe_path.name}' erfolgreich gelöscht."
        return get_generated_files(for_update=True), None, status_message
    except (FileNotFoundError, SecurityException) as e:
        return get_generated_files(for_update=True), None, f"❌ Fehler: {e}"
    except Exception as e:
        return get_generated_files(for_update=True), None, f"❌ Ein unerwarteter Fehler ist beim Löschen aufgetreten: {e}"

# --- Hauptlogik ---

def generate_tts(text: str, language: str, speaker_file):
    """
    Erzeugt TTS-Ausgabe, verarbeitet Fehler und gibt detailliertes Feedback.
    """
    temp_files_to_clean = []
    
    # Der erste Rückgabewert muss der Audio-Pfad sein, die anderen Status-Updates.
    audio_output = None
    status_message = ""

    try:
        status_message += "Starte TTS-Generierung...\n"
        # 1. Eingabe validieren
        if not text or not text.strip():
            status_message += "⚠️ Der Eingabetext ist leer.\n"
            return None, get_generated_files(for_update=True), status_message
        
        if speaker_file is None:
            status_message += "⚠️ Es wurde keine Referenz-Audiodatei hochgeladen.\n"
            return None, get_generated_files(for_update=True), status_message

        speaker_path = speaker_file
        status_message += f"Referenzdatei: {speaker_path}\n"
        
        # 2. Audio bei Bedarf konvertieren
        if not speaker_path.lower().endswith(".wav"):
            status_message += "Konvertiere Audio in das WAV-Format...\n"
            converted_speaker_path = convert_audio(speaker_path, "Audiokonvertierung (ffmpeg)")
            temp_files_to_clean.append(converted_speaker_path)
            speaker_path = converted_speaker_path
            status_message += f"Konvertierung abgeschlossen: {speaker_path}\n"

        # 3. TTS-Befehl ausführen
        lang_idx = LANG_MAP.get(language, "de")
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_filename = f"output_{timestamp}.wav"
        output_path = output_dir / output_filename
        
        command = [
            "tts",
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", text,
            "--speaker_wav", speaker_path,
            "--language_idx", lang_idx,
            "--out_path", str(output_path)
        ]
        
        status_message += f"Führe TTS-Befehl aus: {' '.join(command)}\n"
        process = subprocess.run(
            command, check=True, capture_output=True, 
            text=True, encoding='utf-8', timeout=300 # Erhöhtes Zeitlimit für große Modelle
        )
        status_message += "TTS-Prozess erfolgreich abgeschlossen.\n"
        status_message += f"stdout: {process.stdout}\n"
        status_message += f"stderr: {process.stderr}\n"
        
        audio_output = str(output_path)
        status_message += f"✅ Sprache erfolgreich generiert: {output_filename}\n"
        
    except subprocess.CalledProcessError as e:
        status_message += f"❌ Fehler bei der TTS-Generierung:\n"
        status_message += f"Exit-Code: {e.returncode}\n"
        status_message += f"stdout: {e.stdout}\n"
        status_message += f"stderr: {e.stderr}\n"
        audio_output = None
    except Exception as e:
        status_message += f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}\n"
        audio_output = None
        
    finally:
        # Temporäre Dateien bereinigen
        for temp_file in temp_files_to_clean:
            try:
                os.remove(temp_file)
                status_message += f"Temporäre Datei gelöscht: {temp_file}\n"
            except OSError as e:
                status_message += f"Fehler beim Löschen der temporären Datei {temp_file}: {e}\n"
    
    # Rückgabe in der richtigen Reihenfolge
    return audio_output, get_generated_files(for_update=True), status_message

# --- Gradio GUI erstellen ---

with gr.Blocks(title="Voice Cloning & TTS App") as demo:
    gr.Markdown("# 🗣️ Voice Cloning mit TTS")
    
    with gr.Tab("Sprache generieren"):
        with gr.Row():
            text_input = gr.Textbox(label="Text für die Sprachausgabe", lines=5, placeholder="Geben Sie hier den Text ein, den die KI sprechen soll...")
            lang_input = gr.Dropdown(
                label="Sprache",
                choices=LANG_CHOICES,
                value="Deutsch",
                interactive=True
            )
        
        with gr.Row():
            speaker_wav_input = gr.Audio(type="filepath", label="Referenz-Sprachdatei hochladen (.wav, .mp3, etc.)")
            audio_output = gr.Audio(label="Generierte Sprachausgabe", interactive=False)
        
        with gr.Row():
            generate_btn = gr.Button("🎯 Sprache generieren")

    with gr.Tab("Generierte Dateien verwalten"):
        gr.Markdown("### Generierte Dateien abspielen oder löschen")
        with gr.Row():
            file_output = gr.Dropdown(label="Verfügbare Dateien", choices=get_generated_files())
            delete_btn = gr.Button("🗑️ Datei löschen")
        
    gr.Markdown("---")
    status_output = gr.Textbox(label="Status & Logs", interactive=False, lines=10)

    delete_btn.click(
        fn=delete_file,
        inputs=[file_output],
        outputs=[file_output, audio_output, status_output]
    )

    gr.Markdown("---")
    status_output = gr.Textbox(label="Status & Logs", interactive=False, lines=10)

    

    # Aktionen zuordnen
    generate_btn.click(
        fn=generate_tts,
        inputs=[text_input, lang_input, speaker_wav_input],
        outputs=[audio_output, file_output, status_output]
    )

demo.launch(server_name="0.0.0.0", server_port=7861)