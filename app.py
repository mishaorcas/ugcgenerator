from __future__ import annotations

import logging
import os

from flask import Flask, render_template, request

try:
    from .config import Config
    from .html_processor import process_html
except ImportError:
    from config import Config
    from html_processor import process_html

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    _configure_logging(app)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.post("/process")
    def process() -> tuple[dict[str, object], int]:
        if not request.is_json:
            return {
                "success": False,
                "error": "Expected JSON payload with field 'text'.",
            }, 415

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid JSON body."}, 400

        source_text = data.get("text")
        if not isinstance(source_text, str):
            return {"success": False, "error": "Field 'text' must be a string."}, 400

        if not source_text.strip():
            return {"success": False, "error": "Input text is empty."}, 400

        try:
            processed_text = process_html(source_text)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}, 400
        except Exception:
            logger.exception("Unhandled exception while processing text.")
            return {"success": False, "error": "Internal server error."}, 500

        return {
            "success": True,
            "result": processed_text,
            "length": len(processed_text),
        }, 200

    @app.errorhandler(413)
    def payload_too_large(_: Exception) -> tuple[dict[str, object], int]:
        max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return {
            "success": False,
            "error": f"Payload too large. Max size is {max_mb} MB.",
        }, 413

    return app


def _configure_logging(app: Flask) -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app.logger.setLevel(level)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


app = create_app()


if __name__ == "__main__":
    # Cloud platforms (Render/Heroku-like) inject a single PORT variable.
    port = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5000")))
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=port,
        debug=_env_flag("FLASK_DEBUG", default=False),
    )
