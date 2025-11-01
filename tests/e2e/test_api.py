import pytest


@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_inference(client):
    payload = {"prompt": "hello world", "max_tokens": 16}
    res = await client.post("/v1/inference", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert "Echo:" in body["text"]
    assert body["model_used"] == "economy-dummy"
