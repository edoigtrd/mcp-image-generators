# Étape 1: Image de base
FROM python:3.13-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Exposer le port (ajuster si nécessaire)
EXPOSE 7001

# Variable d'environnement
ENV PYTHONUNBUFFERED=1

# Commande de démarrage
CMD ["python", "main.py"]
