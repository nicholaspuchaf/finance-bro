# Backend

Run the application from the repository root:

```sh
docker compose --env-file .env.conf up --build -d
```

FastAPI serves the compiled frontend and the API together. The host port is configured by `FINANCE_BRO_PORT` in `.env.conf` (default: 808). SQLite persists under `/data` in the named volume; credentials come from the optional root `.env` at runtime. See [Docker setup](../docs/DOCKER.md).

`FRONTEND_DIST` points to the frontend build inside the image. `LOCAL_ONLY` defaults to `true` for direct/native use; Compose explicitly disables the client-address guard for Docker bridge traffic and publishes only on host loopback.

Contributors can run backend checks locally with `uv sync` and `uv run pytest -q`. The old root `dev.py` launcher has been removed.
