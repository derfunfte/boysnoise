import unittest
import os
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, ANY

# Import the function and variables we need to test from app.py
from app import synthesize_speech, output_dir, LANG_MAP

class TestSynthesizeSpeech(unittest.TestCase):

    def setUp(self):
        """Set up a temporary file to act as the speaker_wav input."""
        # The Gradio File component provides an object with a .name attribute holding the file path.
        # We simulate this with a MagicMock instance.
        self.mock_speaker_wav = MagicMock()
        # We need a real file path, so we create a temporary file.
        self.temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.mock_speaker_wav.name = self.temp_wav_file.name
        self.temp_wav_file.close()

    def tearDown(self):
        """Clean up the temporary file after each test."""
        os.remove(self.mock_speaker_wav.name)
        # Clean up any output files created during tests
        for f in os.listdir(output_dir):
            if f.startswith("output_"):
                os.remove(os.path.join(output_dir, f))

    def test_input_validation_empty_text(self):
        """Should return an error if the input text is empty."""
        audio_path, status = synthesize_speech("", self.mock_speaker_wav, "Deutsch")
        self.assertIsNone(audio_path)
        self.assertIn("Der Eingabetext darf nicht leer sein", status)

    def test_input_validation_no_speaker_file(self):
        """Should return an error if the speaker_wav file is None."""
        audio_path, status = synthesize_speech("Hallo Welt", None, "Deutsch")
        self.assertIsNone(audio_path)
        self.assertIn("Bitte laden Sie eine Referenz-Audiodatei hoch", status)

    @patch('app.subprocess.run')
    def test_successful_synthesis(self, mock_subprocess_run):
        """Should return the audio path and a success message on successful TTS execution."""
        # Configure the mock to simulate a successful process run
        mock_process = MagicMock()
        mock_process.stdout = "TTS process finished successfully."
        mock_process.stderr = ""
        mock_subprocess_run.return_value = mock_process

        audio_path, status = synthesize_speech("Dies ist ein Test", self.mock_speaker_wav, "Deutsch")

        # Assert that subprocess.run was called once
        mock_subprocess_run.assert_called_once()
        
        # Assert that a valid path within the output directory is returned
        self.assertIsNotNone(audio_path)
        self.assertTrue(audio_path.startswith(output_dir))
        self.assertTrue(audio_path.endswith(".wav"))
        
        # Assert that the status message indicates success
        self.assertIn("Synthese erfolgreich abgeschlossen!", status)
        self.assertIn("TTS process finished successfully.", status)

    @patch('app.subprocess.run')
    def test_failed_synthesis_with_called_process_error(self, mock_subprocess_run):
        """Should return None and a detailed error message if TTS process fails."""
        # Configure the mock to raise a CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="tts",
            output="Model file not found.",
            stderr="A critical error occurred in the model loader."
        )

        audio_path, status = synthesize_speech("Dieser Test wird fehlschlagen", self.mock_speaker_wav, "Deutsch")

        # Assert that no audio path is returned
        self.assertIsNone(audio_path)
        
        # Assert that the status message contains the detailed error information
        self.assertIn("FEHLER bei der Synthese", status)
        self.assertIn("Exit-Code: 1", status)
        self.assertIn("Model file not found.", status) # stdout
        self.assertIn("A critical error occurred in the model loader.", status) # stderr

    @patch('app.subprocess.run')
    def test_synthesis_with_timeout_error(self, mock_subprocess_run):
        """Should return a specific timeout error message if the TTS process times out."""
        # Configure the mock to raise a TimeoutExpired exception
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd="tts --text 'Dieser Text ist sehr lang'",
            timeout=120
        )

        audio_path, status = synthesize_speech("Dieser Text ist sehr, sehr lang.", self.mock_speaker_wav, "Deutsch")

        # Assert that no audio path is returned
        self.assertIsNone(audio_path)

        # Assert that the status message indicates a timeout
        self.assertIn("FEHLER: Der Prozess 'Synthese' hat das Zeitlimit von 120 Sekunden überschritten", status)

    @patch('app.subprocess.run')
    def test_conversion_with_timeout_error(self, mock_subprocess_run):
        """Should return a specific timeout error message if the ffmpeg process times out."""
        # Create a dummy mp3 file to trigger the conversion path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name
        
        mock_mp3_input = MagicMock()
        mock_mp3_input.name = mp3_path

        # Configure the mock to raise a TimeoutExpired exception
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd="ffmpeg -i input.mp3 output.wav",
            timeout=30
        )

        try:
            audio_path, status = synthesize_speech("Test", mock_mp3_input, "Deutsch")
            self.assertIsNone(audio_path)
            self.assertIn("FEHLER: Der Prozess 'Audiokonvertierung (ffmpeg)' hat das Zeitlimit von 30 Sekunden überschritten", status)
        finally:
            os.remove(mp3_path)

    @patch('app.subprocess.run')
    def test_command_construction_and_language_mapping(self, mock_subprocess_run):
        """Should construct the tts command with the correct arguments and language index."""
        mock_subprocess_run.return_value = MagicMock() # Simulate success

        # Test with a specific language
        test_text = "This is a test in Japanese"
        test_language = "Japanisch"
        expected_lang_idx = LANG_MAP[test_language] # "ja"

        synthesize_speech(test_text, self.mock_speaker_wav, test_language)

        # Check that subprocess.run was called with the correctly constructed command
        expected_command_parts = [
            "tts",
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", test_text,
            "--speaker_wav", self.mock_speaker_wav.name,
            "--language_idx", expected_lang_idx,
            "--out_path", ANY # The exact path is dynamic, so we check for its presence
        ]
        mock_subprocess_run.assert_called_with(expected_command_part, check=True, capture_output=True, text=True, encoding='utf-8', timeout=120)

if __name__ == '__main__':
    unittest.main(verbosity=2)