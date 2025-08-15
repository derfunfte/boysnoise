import unittest
import os
import time
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, ANY

# Import the function and variables we need to test from app.py
import gradio as gr
from app import synthesize_speech, output_dir, LANG_MAP, get_generated_files, delete_file

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
    def test_file_not_found_error_for_tts(self, mock_subprocess_run):
        """Should return a specific error if the tts executable is not found."""
        mock_subprocess_run.side_effect = FileNotFoundError(2, "No such file or directory", "tts")

        audio_path, status = synthesize_speech("Test", self.mock_speaker_wav, "Deutsch")

        self.assertIsNone(audio_path)
        self.assertIn("FEHLER: Das Programm 'tts' wurde nicht gefunden.", status)

    @patch('app.subprocess.run')
    def test_file_not_found_error_for_ffmpeg(self, mock_subprocess_run):
        """Should return a specific error if the ffmpeg executable is not found during conversion."""
        # Use a non-wav file to trigger the conversion path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name
        mock_mp3_input = MagicMock()
        mock_mp3_input.name = mp3_path
        
        mock_subprocess_run.side_effect = FileNotFoundError(2, "No such file or directory", "ffmpeg")

        try:
            audio_path, status = synthesize_speech("Test", mock_mp3_input, "Deutsch")
            self.assertIsNone(audio_path)
            self.assertIn("FEHLER: Das Programm 'ffmpeg' wurde nicht gefunden.", status)
        finally:
            os.remove(mp3_path)

    @patch('app.subprocess.run')
    def test_ffmpeg_conversion_fails_with_called_process_error(self, mock_subprocess_run):
        """Should return a specific error if ffmpeg fails during conversion."""
        # Use a non-wav file to trigger the conversion path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name
        mock_mp3_input = MagicMock()
        mock_mp3_input.name = mp3_path

        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="ffmpeg",
            stderr="Invalid data found when processing input"
        )

        try:
            audio_path, status = synthesize_speech("Test", mock_mp3_input, "Deutsch")
            self.assertIsNone(audio_path)
            self.assertIn("FEHLER bei der Audiokonvertierung (ffmpeg)", status)
            self.assertIn("Invalid data found when processing input", status)
        finally:
            os.remove(mp3_path)

    @patch('app.subprocess.run')
    def test_unexpected_exception_is_handled(self, mock_subprocess_run):
        """Should handle generic exceptions gracefully."""
        mock_subprocess_run.side_effect = Exception("A very unexpected error")

        audio_path, status = synthesize_speech("Test", self.mock_speaker_wav, "Deutsch")

        self.assertIsNone(audio_path)
        self.assertIn("Ein unerwarteter Fehler ist aufgetreten: A very unexpected error", status)

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
        mock_subprocess_run.assert_called_with(expected_command_parts, check=True, capture_output=True, text=True, encoding='utf-8', timeout=120)

class TestGetGeneratedFiles(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory and patch app.output_dir for test isolation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        # Patch the output_dir in the 'app' module to use our temporary directory
        self.output_dir_patcher = patch('app.output_dir', self.temp_dir.name)
        self.output_dir_patcher.start()

    def tearDown(self):
        """Clean up the patch and the temporary directory."""
        self.output_dir_patcher.stop()
        self.temp_dir.cleanup()

    def test_empty_directory(self):
        """Should return an empty list when the directory contains no .wav files."""
        open(os.path.join(self.temp_dir.name, "a.txt"), 'w').close()
        self.assertEqual(get_generated_files(for_update=False), [])

    def test_files_are_found_and_sorted_correctly(self):
        """Should find .wav files and sort them by modification time (newest first)."""
        # Create dummy files with controlled modification times to test sorting
        path1_oldest = os.path.join(self.temp_dir.name, "oldest.wav")
        open(path1_oldest, 'a').close()
        time.sleep(0.02)  # Ensure different mtime on all systems

        path2_not_wav = os.path.join(self.temp_dir.name, "ignored_file.txt")
        open(path2_not_wav, 'a').close()
        time.sleep(0.02)

        path3_newest = os.path.join(self.temp_dir.name, "newest.wav")
        open(path3_newest, 'a').close()

        result = get_generated_files(for_update=False)

        # Assert only .wav files are returned and they are sorted correctly
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("newest.wav", path3_newest))
        self.assertEqual(result[1], ("oldest.wav", path1_oldest))

    @patch('app.gr.Dropdown')
    def test_returns_gradio_update_object(self, mock_dropdown):
        """Should call gr.Dropdown.update with correct choices when for_update is True."""
        # Create a dummy file to be found
        path = os.path.join(self.temp_dir.name, "a.wav")
        open(path, 'a').close()
        
        expected_choices = [("a.wav", path)]

        get_generated_files(for_update=True)
        mock_dropdown.update.assert_called_once_with(choices=expected_choices)

    def test_handles_non_existent_output_dir(self):
        """Should return an empty list if the output directory does not exist."""
        # Stop the patcher and clean up the temp dir to make the path invalid
        self.output_dir_patcher.stop()
        self.temp_dir.cleanup()
        
        # Now self.temp_dir.name points to a non-existent path.
        # We re-patch it just for this test to trigger the FileNotFoundError.
        with patch('app.output_dir', self.temp_dir.name):
            self.assertEqual(get_generated_files(for_update=False), [])
            
            # Also test the for_update=True path
            with patch('app.gr.Dropdown') as mock_dropdown:
                get_generated_files(for_update=True)
                mock_dropdown.update.assert_called_once_with(choices=[])

    @patch('app.os.remove')
    @patch('app.subprocess.run')
    def test_temp_file_is_cleaned_up_on_failure(self, mock_subprocess_run, mock_os_remove):
        """Should clean up the temporary converted file even if TTS synthesis fails."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name
        mock_mp3_input = MagicMock()
        mock_mp3_input.name = mp3_path

        mock_subprocess_run.side_effect = [MagicMock(), subprocess.CalledProcessError(1, "tts")]
        synthesize_speech("Test", mock_mp3_input, "Deutsch")
        mock_os_remove.assert_called_once()
        os.remove(mp3_path)  # Clean up the test input file

class TestDeleteFile(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory and patch app.output_dir for test isolation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir_patcher = patch('app.output_dir', self.temp_dir.name)
        self.output_dir_patcher.start()

    def tearDown(self):
        """Clean up the patch and the temporary directory."""
        self.output_dir_patcher.stop()
        self.temp_dir.cleanup()

    def test_successful_deletion(self):
        """Should delete the specified file and return an updated file list."""
        file_to_delete_path = os.path.join(self.temp_dir.name, "test_file.wav")
        open(file_to_delete_path, 'w').close()
        self.assertTrue(os.path.exists(file_to_delete_path))

        # We need to mock get_generated_files as it's called inside delete_file
        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = []  # Simulate an empty list after deletion
            updated_files, audio_output, status = delete_file(file_to_delete_path)

        self.assertFalse(os.path.exists(file_to_delete_path))
        self.assertEqual(updated_files, [])
        self.assertIsNone(audio_output)
        self.assertIn("erfolgreich gelöscht", status)

    def test_delete_no_file_selected(self):
        """Should return an error message if no file is provided."""
        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = []
            updated_files, audio_output, status = delete_file(None)
        self.assertEqual(updated_files, [])
        self.assertIsNone(audio_output)
        self.assertIn("Keine Datei zum Löschen ausgewählt", status)

    def test_delete_path_traversal_attack_is_blocked(self):
        """Should prevent deletion of files outside the designated output directory."""
        # Create a file outside the patched output_dir
        with tempfile.NamedTemporaryFile(delete=False) as outside_file:
            outside_file_path = outside_file.name
        
        self.assertTrue(os.path.exists(outside_file_path))
        
        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = []
            _, _, status = delete_file(outside_file_path)

        # Assert the file was NOT deleted and a security warning was issued
        self.assertTrue(os.path.exists(outside_file_path))
        self.assertIn("Löschen außerhalb des erlaubten Verzeichnisses verweigert", status)
        
        os.remove(outside_file_path) # Clean up the external file

    def test_delete_file_not_found(self):
        """Should handle cases where the file to be deleted does not exist."""
        non_existent_path = os.path.join(self.temp_dir.name, "ghost.wav")
        _, _, status = delete_file(non_existent_path)
        self.assertIn("nicht gefunden", status)

    @patch('app.os.remove')
    def test_delete_unexpected_exception(self, mock_os_remove):
        """Should handle generic exceptions during file deletion gracefully."""
        file_to_delete_path = os.path.join(self.temp_dir.name, "test_file.wav")
        open(file_to_delete_path, 'w').close()

        # Simulate an OS-level error during deletion
        mock_os_remove.side_effect = OSError("Permission denied")

        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = []
            _, _, status = delete_file(file_to_delete_path)

        # Assert that the generic exception was caught and a proper message is returned
        self.assertIn("Ein unerwarteter Fehler ist beim Löschen aufgetreten: Permission denied", status)

if __name__ == '__main__':
    unittest.main(verbosity=2)