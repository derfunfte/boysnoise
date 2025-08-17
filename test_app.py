import unittest
import os
import time
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

# Import the function and variables we need to test from app.py
import gradio as gr
from app import generate_tts, output_dir, LANG_MAP, get_generated_files, delete_file

class TestGenerateTTS(unittest.TestCase):

    def setUp(self):
        """Set up a temporary file to act as the speaker_wav input."""
        self.temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
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
        audio_path, _, status = generate_tts("", self.temp_wav_path, "Deutsch")
        self.assertIsNone(audio_path)
        self.assertIn("Der Eingabetext ist leer", status)

    def test_input_validation_no_speaker_file(self):
        """Should return an error if the speaker_wav file is None."""
        audio_path, _, status = generate_tts("Hallo Welt", None, "Deutsch")
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

        audio_path, _, status = generate_tts("Dies ist ein Test", self.temp_wav_path, "Deutsch")

        # Assert that subprocess.run was called once
        mock_subprocess_run.assert_called_once()
        
        # Assert that a valid path within the output directory is returned
        self.assertIsNotNone(audio_path)
        self.assertTrue(audio_path.startswith(str(output_dir)))
        self.assertTrue(audio_path.endswith(".wav"))
        
        # Assert that the status message indicates success
        self.assertIn("Sprache erfolgreich generiert", status)
        self.assertIn("TTS process finished successfully.", status)

    @patch('app.subprocess.run')
    def test_failed_synthesis_with_called_process_error(self, mock_subprocess_run):
        """Should return None and a detailed error message if TTS process fails."""
        # Configure the mock to raise a CalledProcessError
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd="tts",
            output="Model file not found.",
            stderr="A critical error occurred in the model loader."
        )
        mock_subprocess_run.side_effect = error

        audio_path, _, status = generate_tts("Dieser Test wird fehlschlagen", self.temp_wav_path, "Deutsch")

        # Assert that no audio path is returned
        self.assertIsNone(audio_path)
        
        # Assert that the status message contains the detailed error information
        self.assertIn("Ein Fehler ist aufgetreten", status)
        self.assertIn(str(error), status)

    @patch('app.subprocess.run')
    def test_synthesis_with_timeout_error(self, mock_subprocess_run):
        """Should return a specific timeout error message if the TTS process times out."""
        # Configure the mock to raise a TimeoutExpired exception
        error = subprocess.TimeoutExpired(
            cmd="tts --text 'Dieser Text ist sehr lang'",
            timeout=300
        )
        mock_subprocess_run.side_effect = error

        audio_path, _, status = generate_tts("Dieser Text ist sehr, sehr lang.", self.temp_wav_path, "Deutsch")

        # Assert that no audio path is returned
        self.assertIsNone(audio_path)

        # Assert that the status message indicates a timeout
        self.assertIn(str(error), status)

    @patch('app.subprocess.run')
    def test_file_not_found_error_for_tts(self, mock_subprocess_run):
        """Should return a specific error if the tts executable is not found."""
        error = FileNotFoundError("FEHLER: 'tts' wurde nicht gefunden. Bitte stellen Sie sicher, dass es installiert ist.")
        mock_subprocess_run.side_effect = error

        audio_path, _, status = generate_tts("Test", self.temp_wav_path, "Deutsch")

        self.assertIsNone(audio_path)
        self.assertIn(str(error), status)

    @patch('app.convert_audio')
    def test_file_not_found_error_for_ffmpeg(self, mock_convert_audio):
        """Should return a specific error if the ffmpeg executable is not found during conversion."""
        # Use a non-wav file to trigger the conversion path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name
        
        error = FileNotFoundError("FEHLER: 'ffmpeg' wurde nicht gefunden. Bitte stellen Sie sicher, dass es installiert ist.")
        mock_convert_audio.side_effect = error

        try:
            audio_path, _, status = generate_tts("Test", mp3_path, "Deutsch")
            self.assertIsNone(audio_path)
            self.assertIn(str(error), status)
        finally:
            os.remove(mp3_path)

    @patch('app.convert_audio')
    def test_ffmpeg_conversion_fails_with_called_process_error(self, mock_convert_audio):
        """Should return a specific error if ffmpeg fails during conversion."""
        # Use a non-wav file to trigger the conversion path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name

        error = RuntimeError("FEHLER bei der Audiokonvertierung (ffmpeg):\nExit-Code: 1\nFehler: Invalid data found when processing input")
        mock_convert_audio.side_effect = error

        try:
            audio_path, _, status = generate_tts("Test", mp3_path, "Deutsch")
            self.assertIsNone(audio_path)
            self.assertIn(str(error), status)
        finally:
            os.remove(mp3_path)

    @patch('app.subprocess.run')
    def test_unexpected_exception_is_handled(self, mock_subprocess_run):
        """Should handle generic exceptions gracefully."""
        error = Exception("A very unexpected error")
        mock_subprocess_run.side_effect = error

        audio_path, _, status = generate_tts("Test", self.temp_wav_path, "Deutsch")

        self.assertIsNone(audio_path)
        self.assertIn(str(error), status)

    @patch('app.convert_audio')
    def test_conversion_with_timeout_error(self, mock_convert_audio):
        """Should return a specific timeout error message if the ffmpeg process times out."""
        # Create a dummy mp3 file to trigger the conversion path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name
        
        error = TimeoutError("FEHLER: 'Audiokonvertierung (ffmpeg)' hat das Zeitlimit überschritten.")
        mock_convert_audio.side_effect = error

        try:
            audio_path, _, status = generate_tts("Test", mp3_path, "Deutsch")
            self.assertIsNone(audio_path)
            self.assertIn(str(error), status)
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

        generate_tts(test_text, self.temp_wav_path, test_language)

        # Check that subprocess.run was called with the correctly constructed command
        expected_command_parts = [
            "tts",
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", test_text,
            "--speaker_wav", self.temp_wav_path,
            "--language_idx", expected_lang_idx,
            "--out_path", ANY # The exact path is dynamic, so we check for its presence
        ]
        mock_subprocess_run.assert_called_with(expected_command_parts, check=True, capture_output=True, text=True, encoding='utf-8', timeout=300)

class TestGetGeneratedFiles(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory and patch app.output_dir for test isolation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        # Patch the output_dir in the 'app' module to use our temporary directory
        self.output_dir_patcher = patch('app.output_dir', Path(self.temp_dir.name))
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

    @patch('app.gr.update')
    def test_returns_gradio_update_object(self, mock_gr_update):
        """Should call gr.update with correct choices when for_update is True."""
        # Create a dummy file to be found
        path = os.path.join(self.temp_dir.name, "a.wav")
        open(path, 'a').close()
        
        expected_choices = [("a.wav", path)]

        get_generated_files(for_update=True)
        mock_gr_update.assert_called_once_with(choices=expected_choices, value=None)

    def test_handles_non_existent_output_dir(self):
        """Should return an empty list if the output directory does not exist."""
        # Stop the patcher and clean up the temp dir to make the path invalid
        self.output_dir_patcher.stop()
        self.temp_dir.cleanup()
        
        # Now self.temp_dir.name points to a non-existent path.
        # We re-patch it just for this test to trigger the FileNotFoundError.
        with patch('app.output_dir', Path(self.temp_dir.name)):
            self.assertEqual(get_generated_files(for_update=False), [])
            
            # Also test the for_update=True path
            with patch('app.gr.update') as mock_gr_update:
                get_generated_files(for_update=True)
                mock_gr_update.assert_called_once_with(choices=[], value=None)

    @patch('app.os.remove')
    @patch('app.convert_audio')
    def test_temp_file_is_cleaned_up_on_failure(self, mock_convert_audio, mock_os_remove):
        """Should clean up the temporary converted file even if TTS synthesis fails."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            mp3_path = temp_mp3_file.name

        mock_convert_audio.return_value = "converted.wav"
        with patch('app.subprocess.run') as mock_subprocess_run:
            mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "tts")
            generate_tts("Test", mp3_path, "Deutsch")
        
        mock_os_remove.assert_called_once_with("converted.wav")
        os.remove(mp3_path)  # Clean up the test input file

class TestDeleteFile(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory and patch app.output_dir for test isolation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir_patcher = patch('app.output_dir', Path(self.temp_dir.name))
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
            mock_get_files.return_value = gr.update(choices=[])  # Simulate an empty list after deletion
            updated_files, audio_output, status = delete_file(file_to_delete_path)

        self.assertFalse(os.path.exists(file_to_delete_path))
        self.assertEqual(updated_files.choices, [])
        self.assertIsNone(audio_output)
        self.assertIn("erfolgreich gelöscht", status)

    def test_delete_no_file_selected(self):
        """Should return an error message if no file is provided."""
        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = gr.update(choices=[])
            updated_files, audio_output, status = delete_file(None)
        self.assertEqual(updated_files.choices, [])
        self.assertIsNone(audio_output)
        self.assertIn("Keine Datei zum Löschen ausgewählt", status)

    def test_delete_path_traversal_attack_is_blocked(self):
        """Should prevent deletion of files outside the designated output directory."""
        # Create a file outside the patched output_dir
        with tempfile.NamedTemporaryFile(delete=False) as outside_file:
            outside_file_path = outside_file.name
        
        self.assertTrue(os.path.exists(outside_file_path))
        
        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = gr.update(choices=[])
            _, _, status = delete_file(outside_file_path)

        # Assert the file was NOT deleted and a security warning was issued
        self.assertTrue(os.path.exists(outside_file_path))
        self.assertIn("Löschen außerhalb des erlaubten Verzeichnisses verweigert", status)
        
        os.remove(outside_file_path) # Clean up the external file

    def test_delete_file_not_found(self):
        """Should handle cases where the file to be deleted does not exist."""
        non_existent_path = os.path.join(self.temp_dir.name, "ghost.wav")
        _, _, status = delete_file(non_existent_path)
        self.assertIn("Fehler", status)

    @patch('app.Path.unlink')
    def test_delete_unexpected_exception(self, mock_unlink):
        """Should handle generic exceptions during file deletion gracefully."""
        file_to_delete_path = os.path.join(self.temp_dir.name, "test_file.wav")
        open(file_to_delete_path, 'w').close()

        # Simulate an OS-level error during deletion
        mock_unlink.side_effect = OSError("Permission denied")

        with patch('app.get_generated_files') as mock_get_files:
            mock_get_files.return_value = gr.update(choices=[])
            _, _, status = delete_file(file_to_delete_path)

        # Assert that the generic exception was caught and a proper message is returned
        self.assertIn("Ein unerwarteter Fehler ist beim Löschen aufgetreten: Permission denied", status)

if __name__ == '__main__':
    unittest.main(verbosity=2)
