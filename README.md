# Improved Version (Safe Copy)

This directory contains an improved copy of the original project.
Original files in the repository root were not modified.

## What was improved

- App factory pattern for Flask (`create_app`), which is easier to test and deploy.
- Configuration via environment variables (`SECRET_KEY`, `FLASK_DEBUG`, limits, host/port).
- Safer API behavior:
  - strict JSON validation,
  - consistent HTTP status codes,
  - no internal exception leakage in responses.
- Better logging setup for debugging and operations.
- Refactored HTML processing into a dedicated module with clearer helper functions.
- Reduced false-positive paragraph conversions by validating probable author names.
- Frontend improvements:
  - request race protection (`AbortController`),
  - stronger fetch error handling,
  - modern clipboard API with fallback,
  - improved status feedback and accessibility basics.
- Added unit tests for core transformation logic.

## Run

```bash
pip install -r improved_version/requirements.txt
python improved_version/app.py
```

Open `http://127.0.0.1:5000`.

## Deploy

- The project is ready for Render-style deployment:
  - build command: `pip install -r requirements.txt`
  - start command: `gunicorn app:app`
- `render.yaml` and `Procfile` are included.

## Optional environment variables

- `SECRET_KEY`
- `FLASK_DEBUG` (`true/false`)
- `FLASK_HOST` (default `127.0.0.1`)
- `FLASK_PORT` (default `5000`)
- `MAX_CONTENT_LENGTH_MB` (default `16`)
- `LOG_LEVEL` (default `INFO`)
