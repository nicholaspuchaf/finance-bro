import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.config import Settings
from app.frontend import mount_frontend
from app.main import LocalOnlyMiddleware


def test_native_defaults_keep_loopback_guard_and_vite_separate(monkeypatch):
    monkeypatch.delenv("LOCAL_ONLY", raising=False)
    monkeypatch.delenv("FRONTEND_DIST", raising=False)
    settings = Settings(_env_file=None)
    assert settings.local_only is True
    assert settings.frontend_dist is None


@pytest.mark.parametrize("local_only,expected", [(True, 403), (False, 200)])
def test_bridge_access_requires_explicit_opt_in(local_only, expected):
    app = FastAPI()
    app.add_middleware(LocalOnlyMiddleware, local_only=local_only)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    async def exercise():
        transport = httpx.ASGITransport(app=app, client=("172.20.0.1", 1234))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            response = await client.get("/api/health", headers={"X-Forwarded-For": "127.0.0.1"})
            assert response.status_code == expected
            if expected == 200:
                assert response.headers["cache-control"] == "no-store"

    asyncio.run(exercise())


def test_compiled_frontend_and_api_share_origin_without_exposing_other_files(tmp_path):
    frontend = tmp_path / "dist"
    (frontend / "assets").mkdir(parents=True)
    (frontend / "index.html").write_text('<html><script src="/assets/app.js"></script></html>')
    (frontend / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / ".env").write_text("PRIVATE=test")
    app = FastAPI()
    app.add_middleware(LocalOnlyMiddleware, local_only=False)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    mount_frontend(app, frontend)

    async def exercise():
        transport = httpx.ASGITransport(app=app, client=("172.20.0.1", 1234))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            index = await client.get("/")
            assert index.status_code == 200
            assert index.headers["content-type"].startswith("text/html")
            asset = await client.get("/assets/app.js")
            assert asset.status_code == 200 and asset.text == "console.log('app')"
            health = await client.get("/api/health")
            assert health.json() == {"status": "ok"}
            assert health.headers["cache-control"] == "no-store"
            for path in ("/api/missing", "/assets/missing.js", "/.env", "/%2e%2e/.env", "/backend/app/config.py"):
                assert (await client.get(path)).status_code == 404

    asyncio.run(exercise())


def test_frontend_mount_is_optional_and_fails_fast_for_missing_build(tmp_path):
    app = FastAPI()
    original_routes = len(app.routes)
    mount_frontend(app, None)
    assert len(app.routes) == original_routes
    with pytest.raises(RuntimeError, match="index.html"):
        mount_frontend(app, tmp_path)
