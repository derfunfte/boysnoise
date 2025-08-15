import gradio as gr
import subprocess
import os

def dummy_synth():
    dummy_wav_path = "/workspace/boysnoise/dummy.wav"
    # Create a dummy wav file if it doesn't exist
    if not os.path.exists(dummy_wav_path):
        command = [
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
            "-t", "2", "-y", dummy_wav_path
        ]
        subprocess.run(command)
    return dummy_wav_path

with gr.Blocks() as demo:
    btn = gr.Button("Generate")
    audio = gr.Audio()
    btn.click(dummy_synth, outputs=audio)

demo.launch(server_name="0.0.0.0", server_port=7860)