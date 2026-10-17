# techslop

Sistema de noticias internacionales en español con captación RSS, clasificación editorial,
deduplicación y enlaces de procedencia. Perfil predeterminado: BBC Mundo, DW y Noticias ONU.
Reuters, AP y AFP requieren endpoints oficiales autorizados configurados por el usuario.

**Publicación protegida:** `run` y `preview` solo generan archivos locales. Publicar exige
`publish <ID> --approve-publication` después de revisar el video. Tener credenciales
configuradas nunca constituye aprobación.

Consulta [la guía de noticias internacionales](docs/international-news.md) para conocer
fuentes, restricciones de red, pruebas gratuitas y el primer video sin APIs de pago.

## Setup

```bash
# Clone
git clone https://github.com/vanities/techslop.git
cd techslop

# Install dependencies
uv sync

# Configure
cp .env.example .env
# Edit .env with your API keys
```

### Required API Keys

- **OPENAI_API_KEY** - For script generation (required)
- **YouTube OAuth** - For publishing (optional, needed for `run` command)

### System Requirements

- Python 3.12+
- ffmpeg (for video assembly)
- uv (Python package manager)

## Usage

```bash
# Fetch and score stories from all sources
uv run python pipeline.py ingest

# Show stories and their statuses
uv run python pipeline.py list

# Generate a video preview (no upload)
uv run python pipeline.py preview

# Generate a local preview (may use paid generation APIs; never uploads)
uv run python pipeline.py run

# Process multiple stories
uv run python pipeline.py preview --count 3
```

## Sources

- **Hacker News** - Top stories via Firebase API
- **Reddit** - r/technology, r/programming RSS feeds
- **TechCrunch** - RSS feed

## TTS Providers

Set `TTS_PROVIDER` in `.env`:

| Provider | Key | Cost |
|----------|-----|------|
| `edge` | None needed | Free (default) |
| `openai` | `OPENAI_API_KEY` | Paid |
| `elevenlabs` | `ELEVENLABS_API_KEY` | Paid (stub) |

## Docker

```bash
# Build and run
docker compose build
docker compose run techslop ingest
docker compose run techslop preview

# The default compose command generates locally; it never publishes.
```

## Pipeline Steps

1. **Ingest** - Fetch stories from HN, Reddit, TechCrunch
2. **Score** - Normalize scores, apply source weights, recency boost, dedup
3. **Script** - Generate 30-45s YouTube Shorts script via OpenAI
4. **Voice** - Synthesize narration with edge-tts (or OpenAI/ElevenLabs)
5. **Timestamps** - Extract word-level timestamps with Whisper
6. **Captions** - Generate ASS subtitles with karaoke-style word highlighting
7. **Video** - Assemble with ffmpeg (background + audio + captions + branding)
8. **Publish** - Upload to YouTube Shorts

## Project Structure

```
techslop/
├── pipeline.py              # CLI entry point
├── techslop/
│   ├── models.py            # Dataclasses: Story, Script, VideoJob
│   ├── config.py            # Settings from .env
│   ├── db.py                # SQLite schema + CRUD
│   ├── ingest/              # News source fetchers + scoring
│   ├── scriptgen/           # OpenAI script generation
│   ├── voice/               # TTS providers + Whisper timestamps
│   ├── video/               # ffmpeg assembly + ASS captions
│   └── publish/             # YouTube upload + stubs
├── Dockerfile
├── docker-compose.yml
└── output/                  # Generated videos (gitignored)
```

## License

[GNU General Public License v3.0](LICENSE)
