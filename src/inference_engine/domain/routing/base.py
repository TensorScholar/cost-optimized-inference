import abc
from ..models.request import InferenceRequest
from ..models.routing import RoutingDecision


class AbstractRouter(abc.ABC):
    @abc.abstractmethod
    async def route(self, request: InferenceRequest) -> RoutingDecision:
        raise NotImplementedError

    async def update_model_health(self, model_id: str, healthy: bool, circuit_breaker_open: bool = False) -> None:
        return None

    async def update_model_load(self, model_id: str, load: float) -> None:
        return None
