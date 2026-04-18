from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_ok(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["env"] == "local"


async def test_metrics_prometheus_format(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    # Prometheus default counters always include python_info
    assert "python_info" in resp.text


async def test_root_returns_service_name(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "grad-backend"
