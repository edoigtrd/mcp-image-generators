# MCP Image Generators

Serveur [MCP](https://modelcontextprotocol.io/) exposant plusieurs générateurs d'images (Flux, RunPod Nano Banana Pro) sous forme d'outils, avec upload automatique des résultats vers un bucket S3-compatible.

## Fonctionnement

Le serveur découvre automatiquement les générateurs déclarés dans `imagen/` (via le décorateur `@register_generator`) et expose pour chacun un jeu d'outils MCP :

- `image-{name}-generate` / `image-{name}-generate_schema` — si le générateur implémente `generate_image`
- `image-{name}-edit` / `image-{name}-edit_schema` — si le générateur implémente `edit_image`
- `image-{name}-readme` — guide de prompting spécifique au générateur
- `image-list` — liste tous les générateurs disponibles et leurs capacités

Chaque image générée est téléchargée puis recopiée vers S3 ; l'outil renvoie l'URL publique finale.

### Générateurs inclus

| Nom | Capacités | Variable d'API requise |
|---|---|---|
| `flux` | génération | `BFL_API_KEY` |
| `nanobanana` | édition | `RUNPOD_API_KEY` |

## Installation

```bash
pip install -r requirements.txt
```

Python 3.11+ est requis (utilisation de `tomllib`).

## Configuration

Toutes les clés d'API et paramètres S3 sont lus depuis les variables d'environnement (un fichier `.env` est chargé via `python-dotenv`).

```bash
# Générateurs
BFL_API_KEY=...
RUNPOD_API_KEY=...

# Stockage S3-compatible (upload des images générées)
S3_ENDPOINT_URL=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=...
S3_CDN_URL=...
S3_BUCKET=...

# Serveur MCP (optionnel)
MCP_TRANSPORT=http   # ou "stdio"
MCP_HOST=0.0.0.0
MCP_PORT=7001
IMAGESMCP_CONFIG=config.toml
```

Un fichier `config.toml` optionnel peut surcharger la config de chaque générateur, sous une section nommée d'après sa classe `Config` (ex. `[FluxImageGeneratorConfig]`).

## Lancement

```bash
python main.py
```

Le serveur démarre en HTTP sur le port 7001 par défaut. Pour du transport stdio (usage local avec un client MCP) :

```bash
MCP_TRANSPORT=stdio python main.py
```

### Avec Docker

```bash
docker build -t mcp-image-generators .
docker run --env-file .env -p 7001:7001 mcp-image-generators
```

## Ajouter un générateur

Créer un fichier dans `imagen/`, définir une classe héritant de `ImageGenerator` (voir `imagen/abstract.py`), l'enregistrer avec `@register_generator("nom")`, et implémenter `generate_image` et/ou `edit_image`. Le module est importé automatiquement au démarrage et les outils MCP correspondants sont créés sans configuration supplémentaire.

```python
@register_generator("mygen")
class MyGenerator(ImageGenerator):
    Config = MyGeneratorConfig

    def generate_image(self, options: MyGeneratorOptions) -> ImageGenerationResponse:
        ...
```
