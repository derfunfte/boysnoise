FROM gitpod/workspace-full

# TTS v0.22.0 benötigt Python >=3.9, <3.12.
# Das Standard-Image hat eine neuere Version. Wir installieren daher Python 3.11.
RUN pyenv install 3.11.9 && pyenv global 3.11.9

# Sicherstellen, dass die pyenv-Version von Python im PATH für nachfolgende Befehle ist.
ENV PATH="/home/gitpod/.pyenv/shims:/home/gitpod/.pyenv/bin:$PATH"

# Systemabhängigkeiten für TTS installieren (Audioverarbeitung, etc.)
# sudo ist notwendig, da der gitpod-Benutzer keine root-Rechte hat.
RUN sudo apt-get update && sudo apt-get install -y \
    libsndfile1 \
    ffmpeg \
    espeak-ng && \
    sudo rm -rf /var/lib/apt/lists/*

# Die TTS-Bibliothek via pip installieren, um DockerHub-Pull-Probleme zu umgehen.
RUN pip install --no-cache-dir TTS==0.22.0

# Wir setzen das Arbeitsverzeichnis
WORKDIR /workspace/boysnoise