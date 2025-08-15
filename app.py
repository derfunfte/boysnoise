# ...
      # Starte die GUI im Hintergrund, damit der Terminal frei bleibt
      python /workspace/boysnoise/app.py &
# ...
import gradio as gr
import subprocess
import os
import time
import shlex

# Verzeichnis für generierte Audiodateien, falls es nicht existiert
output_dir = "/workspace/trainings_output"
os.makedirs(output_dir, exist_ok=True)

def synthesize_speech(text, speaker_wav, language):
    """
    Nimmt Text, eine Referenz-WAV und eine Sprache entgegen,
    ruft Coqui TTS auf und gibt den Pfad zur Audiodatei sowie den Status zurück.
    """
    if not text or not text.strip():
        return None, "Fehler: Der Eingabetext darf nicht leer sein."
    if speaker_wav is None:
        return None, "Fehler: Bitte laden Sie eine Referenz-WAV-Datei hoch."

    # Generiere einen einzigartigen Dateinamen, um Überschreibungen zu vermeiden
    timestamp = int(time.time())
    output_filename = f"output_{timestamp}.wav"
    output_path = os.path.join(output_dir, output_filename)
    
    # Sprachen-Mapping für den language_idx Parameter
    # Das xtts_v2 Modell unterstützt: en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko
    lang_map = {
        "Deutsch": "de",
        "Englisch": "en",
        "Spanisch": "es",
        "Französisch": "fr",
        "Italienisch": "it",
        "Portugiesisch": "pt",
        "Polnisch": "pl",
        "Russisch": "ru",
        "Türkisch": "tr",
        "Japanisch": "ja",
        "Chinesisch": "zh-cn"
    }
    lang_idx = lang_map.get(language, "de") # Standard ist Deutsch, falls etwas schiefgeht

    # Baue den Befehl sicher zusammen
    command = [
        "tts",
        "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
        "--text", text,
        "--speaker_wav", speaker_wav.name, # .name gibt den temporären Pfad der hochgeladenen Datei an
        "--language_idx", lang_idx,
        "--out_path", output_path
    ]

    try:
        # Führe den Befehl aus
        print(f"Führe Kommando aus: {' '.join(shlex.quote(c) for c in command)}")
        process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        status_message = f"Synthese erfolgreich abgeschlossen!\n\nLog:\n{process.stdout}\n{process.stderr}"
        return output_path, status_message
    except subprocess.CalledProcessError as e:
        error_message = f"FEHLER bei der Synthese:\n\nExit-Code: {e.returncode}\n\n--- STDOUT ---\n{e.stdout}\n\n--- STDERR ---\n{e.stderr}"
        return None, error_message
    except Exception as e:
        return None, f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}"

# Nevo-Techno CSS für das Design
# Wir importieren eine futuristische Schriftart und definieren ein dunkles Farbschema mit Neon-Akzenten.
css = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=IBM+Plex+Mono&display=swap');
:root { --primary-hue: 160; --neutral-hue: 220; --font-family: 'IBM Plex Mono', monospace; }
body, .gradio-container { background: #0a0a14; }
#title { color: hsl(var(--primary-hue), 100%, 70%); text-shadow: 0 0 5px, 0 0 10px, 0 0 20px; text-align: center; font-family: 'Orbitron', sans-serif; }
.gr-button { background: transparent !important; color: hsl(var(--primary-hue), 100%, 70%) !important; border: 1px solid hsl(var(--primary-hue), 100%, 50%) !important; box-shadow: inset 0 0 8px, 0 0 8px; transition: all 0.3s ease; }
.gr-button:hover { background: hsl(var(--primary-hue), 100%, 10%) !important; box-shadow: inset 0 0 10px, 0 0 10px; }
.gr-input, .gr-textarea, .gr-dropdown, .gr-file, .gr-panel { background-color: rgba(10, 20, 30, 0.8) !important; border: 1px solid hsl(var(--neutral-hue), 50%, 30%) !important; color: #e0e0e0 !important; }
.gr-label { color: hsl(var(--primary-hue), 80%, 80%) !important; }
"""

with gr.Blocks(css=css, theme=gr.themes.Base()) as demo:
    gr.Markdown("# STIMMKLON SOUVERÄN", elem_id="title")
    gr.Markdown("### Nevo-Techno TTS Interface")

    with gr.Row():
        with gr.Column(scale=2):
            text_input = gr.Textbox(label="Zu synthetisierender Text", lines=4, placeholder="Schreiben Sie hier den Text...")
            speaker_wav_input = gr.File(label="Referenz-Stimme (WAV-Datei)", file_types=['.wav'])
            language_input = gr.Dropdown(label="Sprache", choices=list(lang_map.keys()), value="Deutsch")
            generate_button = gr.Button("Stimme generieren")
        with gr.Column(scale=3):
            audio_output = gr.Audio(label="Generierte Sprachausgabe")
            status_output = gr.Textbox(label="Status / Log", lines=10, interactive=False)

    generate_button.click(
        fn=synthesize_speech,
        inputs=[text_input, speaker_wav_input, language_input],
        outputs=[audio_output, status_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)