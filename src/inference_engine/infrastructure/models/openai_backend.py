from typing import List, AsyncIterator
import structlog

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore

from ...domain.models.request import InferenceRequest
from ...domain.models.response import InferenceResponse, UsageMetrics, CacheInfo
from ...utils.text_utils import estimate_tokens
from .base import AbstractModelBackend

logger = structlog.get_logger()


class OpenAIBackend(AbstractModelBackend):
    """OpenAI API model backend."""

    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        if AsyncOpenAI is None:
            raise ImportError("openai package not installed")

        self.client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        """Run inference via OpenAI API."""
        import time

        start = time.time()

        messages = request.messages or [{"role": "user", "content": request.prompt}]

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=request.parameters.max_tokens,
            temperature=request.parameters.temperature,
        )

        elapsed_ms = int((time.time() - start) * 1000)

        completion = response.choices[0].message.content
        usage = response.usage

        return InferenceResponse(
            request_id=request.id,
            text=completion or "",
            finish_reason=response.choices[0].finish_reason or "stop",
            model_used=self.model_name,
            usage=UsageMetrics(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                cost_usd=0.0,  # Will be calculated externally
            ),
            cache_info=CacheInfo(hit=False),
            latency_ms=elapsed_ms,
        )

    async def infer_batch(self, requests: List[InferenceRequest]) -> List[InferenceResponse]:
        """Process batch sequentially (OpenAI doesn't support batching)."""
        results = []
        for req in requests:
            results.append(await self.infer(req))
        return results

    async def stream(self, request: InferenceRequest) -> AsyncIterator[str]:
        """Stream tokens from OpenAI."""
        messages = request.messages or [{"role": "user", "content": request.prompt}]

        async for chunk in await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=request.parameters.max_tokens,
            temperature=request.parameters.temperature,
            stream=True,
        ):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.error("openai_health_check_failed", error=str(e))
            return False

