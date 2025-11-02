"""End-to-end API tests."""
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health(client):
    """Test health endpoint."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_ready(client):
    """Test readiness probe."""
    res = await client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["ready"] is True


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_inference(client):
    """Test single inference endpoint."""
    payload = {"prompt": "hello world", "max_tokens": 16}
    res = await client.post("/v1/inference", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert "Echo:" in body["text"]
    assert body["model_used"] == "economy-dummy"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_batch_inference(client, sample_request_dict):
    """Test batch inference endpoint."""
    payload = [sample_request_dict, sample_request_dict]
    res = await client.post("/v1/batch", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_list_models(client):
    """Test models listing endpoint."""
    res = await client.get("/v1/models")
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 2
    assert models[0]["id"] in ["gpt-4", "gpt-3.5-turbo"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_metrics_summary(client):
    """Test metrics summary endpoint."""
    res = await client.get("/v1/metrics/summary")
    assert res.status_code == 200
    metrics = res.json()
    assert "total_requests" in metrics
    assert "cache_hit_rate" in metrics
