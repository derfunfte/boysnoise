FROM gitpod/workspace-full

# Python 3.11.9 installieren (nur, falls nicht vorhanden)
RUN pyenv install -s 3.11.9 && pyenv global 3.11.9

# Pfad setzen, damit pyenv-Python sofort genutzt wird
ENV PATH="/home/gitpod/.pyenv/shims:/home/gitpod/.pyenv/bin:$PATH"

# Systemabhängigkeiten installieren
RUN sudo apt-get update && sudo apt-get install -y \
    libsndfile1 \
    ffmpeg \
    espeak-ng && \
    sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/*

# pip aktualisieren und Coqui TTS installieren
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir TTS==0.22.0

# Arbeitsverzeichnis setzen
WORKDIR /workspace/boysnoise
