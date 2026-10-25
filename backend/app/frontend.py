from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, directory: Path | None) -> None:
    """Mount the compiled client after API routes; Vite remains optional in dev."""
    if directory is None:
        return
    if not (directory / "index.html").is_file():
        raise RuntimeError(f"FRONTEND_DIST não contém index.html: {directory}")
    # Navigation uses URL fragments, so unknown server/API paths stay 404.
    app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
