import pytest
from httpx import AsyncClient
from inference_engine.adapters.api.app import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
