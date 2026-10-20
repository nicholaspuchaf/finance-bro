# Backend

Install dependencies with `uv sync`. Copy the root `.env.example` to `.env`, fill in the credentials you want to use, then run `uv run uvicorn app.main:app --reload` from this directory.

The API listens on `127.0.0.1:8000`. SQLite data is stored in `backend/data/` by default. Pluggy and AI credentials are read only by the backend. Run `uv run python scripts/backup.py` to create a consistent copy.
