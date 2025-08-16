import gradio as gr
import subprocess
import os
import tempfile
import uuid

# Hilfsfunktion: Beliebige Audiodateien in WAV konvertieren
def convert_audio_to_wav(input_path: str) -> str:
    """
    Konvertiert eine Audio-Datei in 22.05 kHz Mono WAV mit ffmpeg.
    Gibt den Pfad zur konvertierten Datei zurück.
    """
    wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", input_path, "-ar", "22050", "-ac", "1", wav_path, "-y"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return wav_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Audio-Konvertierung fehlgeschlagen: {e.stderr.decode()}")

# Hauptfunktion: TTS-Ausgabe erzeugen
def generate_tts(text: str, language: str, speaker_file: str):
    """
    Erzeugt TTS-Ausgabe mit Coqui XTTSv2, unter Verwendung einer Referenzstimme.
    """
    try:
        if not text.strip():
            return None, None, "⚠️ Kein Text eingegeben."
        if not speaker_file:
            return None, None, "⚠️ Keine Referenz-Stimme hochgeladen."

        # Falls nötig, Audio in WAV konvertieren
        speaker_path = speaker_file
        if not speaker_path.lower().endswith(".wav"):
            speaker_path = convert_audio_to_wav(speaker_path)

        # Ziel-Datei im temporären Verzeichnis
        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")

        # TTS-Befehl zusammenstellen
        cmd = [
            "tts",
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", text,
            "--speaker_wav", speaker_path,
            "--language_idx", language,
            "--out_path", output_path
        ]

        # TTS ausführen
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            return None, None, f"❌ TTS-Fehler:\n{result.stderr}"

        return output_path, output_path, "✅ Sprache erfolgreich generiert."
    except Exception as e:
        return None, None, f"❌ Unerwarteter Fehler: {str(e)}"

# Gradio UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎤 Stimmklon Souverän – Nevo-Techno Voice Cloning")
    gr.Markdown("Laden Sie eine Referenzstimme hoch und erzeugen Sie synthetische Sprache mit Coqui TTS.")

    with gr.Row():
        text_input = gr.Textbox(label="Text", value="Willkommen! Laden Sie eine Referenzstimme hoch und erzeugen Sie synthetische Sprache mit Coqui TTS.")
        lang_input = gr.Textbox(label="Sprache (z. B. de, en, fr)", value="de")

    speaker_wav_input = gr.File(label="Referenz-Stimme (beliebige Audiodatei)", file_types=["audio"], type="filepath")

    with gr.Row():
        audio_output = gr.Audio(label="TTS-Ausgabe")
        file_output = gr.File(label="Download generierte Datei")
    status_output = gr.Textbox(label="Status / Log")

    btn = gr.Button("🎯 Sprache generieren")
    btn.click(generate_tts, inputs=[text_input, lang_input, speaker_wav_input], outputs=[audio_output, file_output, status_output])

demo.launch(server_name="0.0.0.0", server_port=7860)
