FROM python:3.12-slim

WORKDIR /app

# Installer dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    git graphviz build-essential && \
    rm -rf /var/lib/apt/lists/*

# Cloner le dépôt Meshview avec les protobufs (submodules)
RUN git clone --recurse-submodules https://github.com/pablorevilla-meshtastic/meshview.git .

# Créer un environnement virtuel Python
RUN python -m venv env

# Installer les dépendances
RUN /app/env/bin/pip install --upgrade pip setuptools wheel && \
    /app/env/bin/pip install -r requirements.txt

EXPOSE 8081

# Lancement de meshview avec config personnalisée
CMD ["/app/env/bin/python3", "mvrun.py", "--config", "config.ini"]
