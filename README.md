# MCP Image Generators

[MCP](https://modelcontextprotocol.io/) server exposing several image generators (Flux, RunPod Nano Banana Pro) as tools, with automatic upload of the results to an S3-compatible bucket.

## How it works

The server auto-discovers the generators declared in `imagen/` (via the `@register_generator` decorator) and exposes a set of MCP tools for each one:

- `image-{name}-generate` / `image-{name}-generate_schema` — if the generator implements `generate_image`
- `image-{name}-edit` / `image-{name}-edit_schema` — if the generator implements `edit_image`
- `image-{name}-readme` — generator-specific prompting guide
- `image-list` — lists all available generators and their capabilities

Every generated image is downloaded and copied to S3; the tool returns the final public URL.

### Included generators

| Name | Capabilities | Required API key |
|---|---|---|
| `flux` | generation | `BFL_API_KEY` |
| `nanobanana` | editing | `RUNPOD_API_KEY` |

## Installation

```bash
pip install -r requirements.txt
```

Python 3.11+ is required (uses `tomllib`).

## Configuration

All API keys and S3 settings are read from environment variables (a `.env` file is loaded via `python-dotenv`).

```bash
# Generators
BFL_API_KEY=...
RUNPOD_API_KEY=...

# S3-compatible storage (upload of generated images)
S3_ENDPOINT_URL=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=...
S3_CDN_URL=...
S3_BUCKET=...

# MCP server (optional)
MCP_TRANSPORT=http   # or "stdio"
MCP_HOST=0.0.0.0
MCP_PORT=7001
IMAGESMCP_CONFIG=config.toml
```

An optional `config.toml` file can override each generator's config, under a section named after its `Config` class (e.g. `[FluxImageGeneratorConfig]`).

## Running

```bash
python main.py
```

The server starts over HTTP on port 7001 by default. For stdio transport (local usage with an MCP client):

```bash
MCP_TRANSPORT=stdio python main.py
```

### With Docker

```bash
docker build -t mcp-image-generators .
docker run --env-file .env -p 7001:7001 mcp-image-generators
```

## Adding a generator

Create a file in `imagen/`, define a class inheriting from `ImageGenerator` (see `imagen/abstract.py`), register it with `@register_generator("name")`, and implement `generate_image` and/or `edit_image`. The module is imported automatically at startup and the matching MCP tools are created with no extra configuration.

```python
@register_generator("mygen")
class MyGenerator(ImageGenerator):
    Config = MyGeneratorConfig

    def generate_image(self, options: MyGeneratorOptions) -> ImageGenerationResponse:
        ...
```
