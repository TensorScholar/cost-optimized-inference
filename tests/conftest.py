"""Shared pytest fixtures."""
import pytest
from httpx import AsyncClient
from inference_engine.adapters.api.app import app


@pytest.fixture
async def client():
    """FastAPI test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_request_dict():
    """Sample request as dictionary."""
    return {
        "prompt": "What is the capital of France?",
        "max_tokens": 100,
        "temperature": 0.7,
        "priority": "standard",
        "use_cache": True,
    }
