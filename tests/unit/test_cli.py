from __future__ import annotations

import argparse

import pytest

from inference_engine.cli import _run_smoke


@pytest.mark.asyncio
async def test_smoke_cli_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    args = argparse.Namespace(
        provider="openai",
        model="gpt-4o-mini",
        prompt="hello",
        base_url=None,
        timeout_seconds=30.0,
        max_tokens=16,
        temperature=0.0,
        log_path="unused.jsonl",
    )

    exit_code = await _run_smoke(args)

    assert exit_code == 2
