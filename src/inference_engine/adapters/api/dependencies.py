"""Dependency injection for API endpoints."""
from ...application.services.inference.inference_service import InferenceService
from ...application.services.inference.batch_service import BatchService
from ...application.services.cache.cache_service import CacheService
from ...application.services.routing.routing_service import RoutingService


# Singleton service instances
_inference_service: InferenceService | None = None
_batch_service: BatchService | None = None
_cache_service: CacheService | None = None
_routing_service: RoutingService | None = None


def get_inference_service() -> InferenceService:
    """Get or create inference service singleton."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service


def get_batch_service() -> BatchService:
    """Get or create batch service singleton."""
    global _batch_service
    if _batch_service is None:
        _batch_service = BatchService(get_inference_service())
    return _batch_service


def get_cache_service() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_service
    if _cache_service is None:
        from ...domain.caching.exact import ExactCache
        exact_cache = ExactCache()
        _cache_service = CacheService(exact_cache)
    return _cache_service


def get_routing_service() -> RoutingService:
    """Get or create routing service singleton."""
    global _routing_service
    if _routing_service is None:
        from ...domain.routing.cost_aware import CostAwareRouter
        from ...domain.routing.complexity import ComplexityEstimator
        from ...domain.routing.load_balanced import LoadBalancedRouter
        from ...domain.models.routing import ModelConfig, ModelTier
        
        # Create mock models for now
        models = [
            ModelConfig(
                id="gpt-4",
                name="GPT-4",
                tier=ModelTier.PREMIUM,
                max_context_length=8192,
                cost_per_1k_input_tokens=0.03,
                cost_per_1k_output_tokens=0.06,
            ),
            ModelConfig(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                tier=ModelTier.ECONOMY,
                max_context_length=4096,
                cost_per_1k_input_tokens=0.0015,
                cost_per_1k_output_tokens=0.002,
            ),
        ]
        
        complexity_estimator = ComplexityEstimator()
        cost_router = CostAwareRouter(models, complexity_estimator)
        load_router = LoadBalancedRouter(models)
        
        routers = {
            "cost_optimal": cost_router,
            "round_robin": load_router,
        }
        
        _routing_service = RoutingService(routers)
    return _routing_service

