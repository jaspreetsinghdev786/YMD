# YMD — YouTube Media Downloader

A Django project for YouTube media downloads, with account pages, download history, URL analysis, and media processing through yt-dlp and FFmpeg.

## Project map

| Path | Purpose |
| --- | --- |
| [requirements.txt](requirements.txt) | Python dependency versions |
| [core/manage.py](core/manage.py) | Django management entry point |
| [core/core/settings.py](core/core/settings.py) | Database, cache, email, and integration configuration |
| [core/core/urls.py](core/core/urls.py) | Page routes and API entry points |
| [core/accounts](core/accounts) | Account functionality |
| [core/youtube](core/youtube) | YouTube integration |
| [core/downloader](core/downloader) | Download services, tasks, and models |
| [core/templates](core/templates) | Page templates |
| [core/package.json](core/package.json) | Tailwind stylesheet commands |

## Local development

These steps describe the configuration in the repository. They are a local development guide, not a production deployment recipe.

### Prerequisites

- Python 3.11 and pip. The pinned Django 5.0.1 release supports Python 3.10–3.12; see the [Django release notes](https://docs.djangoproject.com/en/5.2/releases/5.0/#python-compatibility).
- FFmpeg available on your PATH for audio extraction and media conversion. Confirm with `ffmpeg -version`.
- Node.js and npm if you need to rebuild the Tailwind stylesheet.

### Install Python dependencies

From the repository root:

```sh
python -m venv .venv
```

Activate the environment with the command for your shell:

| Shell | Command |
| --- | --- |
| macOS / Linux | `source .venv/bin/activate` |
| Windows Command Prompt | `.venv\Scripts\activate.bat` |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |

Then install the repository's dependencies:

```sh
python -m pip install -r requirements.txt
cd core
```

### Configure and start Django

Create a local `.env` file inside `core/`. Set `DJANGO_SECRET_KEY` to your own random value and `DEBUG=True` for local development. Keep credentials out of commits.

The default configuration uses SQLite at `core/db.sqlite3` and an in-memory cache. Leave `DB_ENGINE` and `REDIS_URL` unset to use those defaults; no separate PostgreSQL or Redis service is needed for this mode.

Run from `core/` with the virtual environment active:

```sh
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Page routes include `/register/`, `/login/`, `/downloads/`, `/history/`, and `/urlsanalyzer/`. Some operations require an authenticated account or configured integrations.

### Rebuild styles

From `core/`:

```sh
npm ci
npm run build:css
```

For ongoing style work, use `npm run watch:css`. Both scripts read `static/css/input.css` and write `static/css/output.css`. The existing `npm test` script is a placeholder that exits with an error; it is not an application test suite.

## Optional services and integrations

| Configuration | Behavior |
| --- | --- |
| `DB_ENGINE=django.db.backends.postgresql` | Uses PostgreSQL with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` |
| `REDIS_URL` | Enables Redis caching and configures the Celery broker |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google integration settings |
| `YOUTUBE_API_KEY` | YouTube API configuration |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Email credentials used by the configured email backend |

With no Redis URL, Celery is configured to execute tasks eagerly in the calling process. With Redis configured and reachable, run a separate worker from `core/` in an activated environment:

```sh
celery -A core worker --loglevel=INFO
```

See [Celery's worker guide](https://docs.celeryq.dev/en/stable/userguide/workers.html) for worker operation. Both Django and the worker must use the same environment configuration.

## Files and troubleshooting

- Downloads are stored under `core/media/downloads/`.
- Application logging is configured at `core/logs/downloader.log`. Review logs locally; redact URLs, account data, and credentials before sharing.
- If `manage.py` cannot be found, run management commands from the `core/` directory.
- If media conversion fails, check FFmpeg availability and the download error log.
- If jobs do not run with Redis configured, check the Redis connection and worker process.
- If a Google, YouTube API, or email operation fails, check the corresponding integration configuration.

Before deploying publicly, review the actual development defaults in `settings.py`, including debug mode, wildcard hosts, permissive CORS, and cookie security, and update dependencies to supported releases. Download only media you have permission to save.
