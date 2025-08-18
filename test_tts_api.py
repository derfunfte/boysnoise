import os
import sys
from pathlib import Path
from TTS.api import TTS
import tempfile
import soundfile as sf
import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
import io # Hinzugefügt

# Dummy WAV-Datei erstellen, falls nicht vorhanden
dummy_wav_path = Path("/workspace/boysnoise/dummy.wav")
if not dummy_wav_path.exists():
    # Erstelle eine einfache Dummy-WAV-Datei (z.B. 1 Sekunde Stille)
    import numpy as np
    samplerate = 16000  # Beispiel-Samplerate
    duration = 1      # 1 Sekunde
    data = np.zeros(samplerate * duration).astype(np.float32)
    sf.write(str(dummy_wav_path), data, samplerate)


# Umleitung von stdout/stderr, um die Ausgabe zu erfassen
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = self._stringio_stdout = io.StringIO() # Geändert
        sys.stderr = self._stringio_stderr = io.StringIO() # Geändert
        return self
    def __exit__(self, *args):
        self.extend(self._stringio_stdout.getvalue().splitlines())
        self.extend(self._stringio_stderr.getvalue().splitlines())
        del self._stringio_stdout
        del self._stringio_stderr
        sys.stdout = self._stdout
        sys.stderr = self._stderr

print("Starte Testskript für TTS.api.TTS...")

try:
    # COQUI_TOS_AGREED Umgebungsvariable setzen
    os.environ["COQUI_TOS_AGREED"] = "1"

    # Füge XttsConfig, XttsAudioConfig, BaseDatasetConfig und XttsArgs zu den sicheren globalen Variablen hinzu
    torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs])

    # TTS-Modell initialisieren
    print("Initialisiere TTS-Modell...")
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    print("TTS-Modell erfolgreich initialisiert.")

    # Text-zu-Sprache-Generierung durchführen
    print("Starte TTS-Generierung...")
    text = "Das ist ein Test von der TTS API." # Verwende einen einfachen Text
    speaker_wav = str(dummy_wav_path) # Verwende die Dummy-WAV-Datei
    language = "de" # Deutsch

    # Erfasse die Ausgabe des tts.tts Aufrufs
    with Capturing() as output:
        wav = tts.tts(text=text, speaker_wav=speaker_wav, language=language)
    
    print("TTS-Generierung erfolgreich.")
    # Speichere die generierte WAV-Datei
    output_path = Path("/workspace/boysnoise/test_output.wav")
    sf.write(str(output_path), wav, 24000) # XTTS v2 verwendet 24kHz
    print(f"Generierte Audiodatei gespeichert unter: {output_path}")

except Exception as e:
    print(f"Fehler im Testskript: {e}")
    import traceback
    traceback.print_exc()

print("Testskript beendet.")