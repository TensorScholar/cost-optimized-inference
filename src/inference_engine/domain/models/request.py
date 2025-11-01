from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class RequestPriority(str, Enum):
    """Request priority levels affecting batching strategy"""

    EXPRESS = "express"  # <50ms target, minimal batching
    STANDARD = "standard"  # <200ms target, moderate batching
    BATCH = "batch"  # Best effort, maximum batching


class SamplingStrategy(str, Enum):
    """Sampling strategies for text generation"""

    GREEDY = "greedy"
    NUCLEUS = "nucleus"
    TOP_K = "top_k"
    TEMPERATURE = "temperature"


@dataclass(frozen=True)
class RequestMetadata:
    """Metadata for request tracking and attribution"""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    feature_name: Optional[str] = None
    experiment_id: Optional[str] = None
    application: str = "default"
    environment: str = "production"
    custom_tags: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelParameters:
    """Model generation parameters"""

    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 0.9
    top_k: int = 50
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be between 0 and 1")


@dataclass(frozen=True)
class InferenceRequest:
    """Complete inference request"""

    id: UUID = field(default_factory=uuid4)
    prompt: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)
    parameters: ModelParameters = field(default_factory=ModelParameters)
    priority: RequestPriority = RequestPriority.STANDARD
    metadata: RequestMetadata = field(default_factory=RequestMetadata)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Optional cache control
    use_cache: bool = True
    cache_ttl_seconds: Optional[int] = None

    # Optional model preference
    preferred_model: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.prompt and not self.messages:
            raise ValueError("Either prompt or messages must be provided")

    @property
    def estimated_input_tokens(self) -> int:
        """Estimate input token count"""
        text = self.prompt or " ".join(m.get("content", "") for m in self.messages)
        return len(text) // 4  # Rough estimation

    @property
    def cache_key(self) -> str:
        """Generate cache key for this request"""
        import hashlib

        # Combine prompt/messages + relevant parameters
        content = self.prompt or str(self.messages)
        param_str = f"{self.parameters.temperature}_{self.parameters.max_tokens}"

        key_input = f"{content}_{param_str}".encode()
        return hashlib.sha256(key_input).hexdigest()


