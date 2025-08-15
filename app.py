# Standard library imports
import logging
import os
import shlex
import subprocess
import time
import tempfile

# Third-party imports
import gradio as gr

# Verzeichnis für generierte Audiodateien, falls es nicht existiert
output_dir = "/workspace/trainings_output"
os.makedirs(output_dir, exist_ok=True)

# Konfiguriere grundlegendes Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Konstanten auf Modulebene definieren
# Sprachen-Mapping für den language_idx Parameter des xtts_v2 Modells.
# Unterstützte Sprachen: en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko
LANG_MAP = {
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

def synthesize_speech(text, speaker_wav, language):
    logging.info(f"Synthesize speech called with text: '{text}', language: '{language}'")
    if speaker_wav:
        logging.info(f"Speaker wav path: {speaker_wav.name}")
    else:
        logging.info("No speaker wav provided.")

    """
    Nimmt Text, eine Referenz-WAV und eine Sprache entgegen,
    ruft Coqui TTS auf und gibt den Pfad zur Audiodatei sowie den Status zurück.
    """
    if not text or not text.strip():
        return None, "Fehler: Der Eingabetext darf nicht leer sein."
    if speaker_wav is None:
        return None, "Fehler: Bitte laden Sie eine Referenz-Audiodatei hoch."

    speaker_wav_path = speaker_wav.name
    converted_wav_path = None

    try:
        # Schritt 1: Audio-Konvertierung (falls notwendig)
        tts_speaker_path = speaker_wav_path
        if not speaker_wav_path.lower().endswith('.wav'):
            logging.info(f"'{os.path.basename(speaker_wav_path)}' ist keine WAV-Datei. Konvertiere zu WAV.")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                converted_wav_path = temp_wav.name

            ffmpeg_command = [
                "ffmpeg", "-i", speaker_wav_path,
                "-ar", "22050", "-ac", "1", "-y", converted_wav_path
            ]
            logging.info(f"Führe Konvertierung aus: {' '.join(shlex.quote(c) for c in ffmpeg_command)}")
            subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
            tts_speaker_path = converted_wav_path

        # Schritt 2: Sprachsynthese
        timestamp = int(time.time())
        output_filename = f"output_{timestamp}.wav"
        output_path = os.path.join(output_dir, output_filename)
        lang_idx = LANG_MAP.get(language, "de")

        command = [
            "tts", "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", text, "--speaker_wav", tts_speaker_path,
            "--language_idx", lang_idx, "--out_path", output_path
        ]
        logging.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")
        process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', timeout=120, input='y')
        
        # Schritt 3: Erfolgreiche Rückgabe
        status_message = f"Synthese erfolgreich abgeschlossen!\n\nLog:\n{process.stdout}\n{process.stderr}"
        logging.info(f"Synthesis successful. Output path: {output_path}")
        return output_path, status_message

    except subprocess.TimeoutExpired as e:
        context = "Synthese" if "tts" in str(e.cmd) else "Audiokonvertierung (ffmpeg)"
        error_message = f"FEHLER: Der Prozess '{context}' hat das Zeitlimit von {e.timeout} Sekunden überschritten und wurde abgebrochen. Dies kann bei sehr langen Texten oder hoher Systemlast passieren."
        logging.error(error_message)
        return None, error_message
    except subprocess.CalledProcessError as e:
        context = "Synthese" if "tts" in str(e.cmd) else "Audiokonvertierung (ffmpeg)"
        error_message = f"FEHLER bei der {context}:\n\nExit-Code: {e.returncode}\n\n--- STDOUT ---\n{e.stdout}\n\n--- STDERR ---\n{e.stderr}"
        logging.error(error_message)
        return None, error_message
    except FileNotFoundError as e:
        error_message = f"FEHLER: Das Programm '{e.filename}' wurde nicht gefunden. Ist es korrekt installiert und im Systempfad?"
        logging.error(error_message)
        return None, error_message
    except Exception as e:
        logging.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}", exc_info=True)
        return None, f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}"
    finally:
        # Schritt 4: Aufräumen
        if converted_wav_path and os.path.exists(converted_wav_path):
            logging.info(f"Entferne temporäre Datei: {converted_wav_path}")
            os.remove(converted_wav_path)

def get_generated_files(for_update=True):
    """
    Sucht im output_dir nach .wav-Dateien und gibt sie sortiert zurück (neueste zuerst).
    Kann entweder eine Liste für die initiale Befüllung oder ein Gradio-Update-Objekt zurückgeben.
    """
    try:
        files = [f for f in os.listdir(output_dir) if f.endswith('.wav')]
        # Sortiere nach Änderungsdatum, neueste zuerst
        files.sort(key=lambda name: os.path.getmtime(os.path.join(output_dir, name)), reverse=True)
        # Erstelle (Label, Wert) Paare für das Dropdown
        choices = [(f, os.path.join(output_dir, f)) for f in files]
        
        if for_update:
            # Gib ein Update-Objekt für die dynamische Aktualisierung zurück
            return gr.update(choices=choices)
        else:
            # Gib nur die Liste für die initiale Befüllung zurück
            return choices
    except FileNotFoundError:
        return [] if not for_update else gr.update(choices=[])

def delete_file(file_to_delete):
    """
    Löscht eine ausgewählte Datei aus dem Verlauf und dem Dateisystem.
    Enthält eine Sicherheitsprüfung, um das Löschen außerhalb des output_dir zu verhindern.
    """
    if not file_to_delete:
        return get_generated_files(), None, "Keine Datei zum Löschen ausgewählt."

    try:
        # SICHERHEITSPRÜFUNG: Verhindert Path-Traversal-Angriffe.
        # Stellt sicher, dass die zu löschende Datei sich innerhalb des erlaubten Verzeichnisses befindet.
        safe_dir = os.path.abspath(output_dir)
        file_path = os.path.abspath(file_to_delete)

        if not file_path.startswith(safe_dir):
            error_message = "FEHLER: Löschen außerhalb des erlaubten Verzeichnisses verweigert."
            logging.warning(f"Sicherheitsverletzungsversuch: Löschen von '{file_path}' wurde blockiert.")
            return get_generated_files(), None, error_message

        if os.path.exists(file_path):
            os.remove(file_path)
            filename = os.path.basename(file_path)
            success_message = f"Datei '{filename}' erfolgreich gelöscht."
            logging.info(success_message)
            # Aktualisiere Dropdown, leere den Audioplayer und zeige Erfolgsmeldung
            return get_generated_files(), None, success_message
        else:
            not_found_message = f"Datei '{os.path.basename(file_path)}' nicht gefunden. Wurde sie bereits gelöscht?"
            return get_generated_files(), None, not_found_message

    except Exception as e:
        error_message = f"Ein unerwarteter Fehler ist beim Löschen aufgetreten: {str(e)}"
        logging.error(error_message, exc_info=True)
        return get_generated_files(), None, error_message

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
            speaker_wav_input = gr.File(label="Referenz-Stimme (beliebige Audiodatei)", file_types=['audio'])
            language_input = gr.Dropdown(label="Sprache", choices=list(LANG_MAP.keys()), value="Deutsch")
            generate_button = gr.Button("Stimme generieren")
        with gr.Column(scale=3):
            audio_output = gr.Audio(label="Generierte Sprachausgabe")
            status_output = gr.Textbox(label="Status / Log", lines=10, interactive=False)

            with gr.Row():
                history_dropdown = gr.Dropdown(
                    label="Verlauf der generierten Dateien (neueste zuerst)",
                    choices=get_generated_files(for_update=False),
                    interactive=True,
                    scale=4)
                delete_button = gr.Button("🗑️ Löschen", scale=1)

    # Event-Handler für den "Stimme generieren"-Button
    synthesis_event = generate_button.click(
        fn=synthesize_speech,
        inputs=[text_input, speaker_wav_input, language_input],
        outputs=[audio_output, status_output]
    )

    # Nach der Synthese, aktualisiere die Verlaufsliste.
    # .then() stellt sicher, dass dies nach dem Haupt-Click-Event ausgeführt wird.
    synthesis_event.then(fn=get_generated_files, outputs=history_dropdown)

    # Event-Handler, um eine Datei aus dem Verlauf in den Player zu laden
    history_dropdown.change(fn=lambda x: x, inputs=history_dropdown, outputs=audio_output)

    # Event-Handler für den Löschen-Button
    delete_button.click(
        fn=delete_file,
        inputs=[history_dropdown],
        outputs=[history_dropdown, audio_output, status_output])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
