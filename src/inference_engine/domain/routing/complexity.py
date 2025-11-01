from ..models.request import InferenceRequest
from ..models.routing import ComplexityEstimate


class ComplexityEstimator:
    """
    Estimates request complexity to guide model selection.
    """

    def __init__(self) -> None:
        self.reasoning_keywords = {
            "analyze",
            "explain",
            "compare",
            "evaluate",
            "argue",
            "reason",
            "deduce",
            "infer",
            "conclude",
            "synthesize",
            "step by step",
            "think through",
            "let me break down",
        }
        self.technical_domains = {
            "code",
            "programming",
            "algorithm",
            "mathematics",
            "science",
            "physics",
            "chemistry",
            "biology",
            "legal",
            "medical",
            "financial",
            "engineering",
        }

    async def estimate(self, request: InferenceRequest) -> ComplexityEstimate:
        text = (request.prompt or " ".join(m.get("content", "") for m in request.messages)).lower()
        factors: dict[str, float] = {}
        input_length = len(text)
        length_score = min(1.0, input_length / 2000)
        factors["length"] = length_score
        reasoning_count = sum(1 for kw in self.reasoning_keywords if kw in text)
        reasoning_score = min(1.0, reasoning_count / 3)
        factors["reasoning"] = reasoning_score
        domain_count = sum(1 for domain in self.technical_domains if domain in text)
        domain_score = min(1.0, domain_count / 2)
        factors["domain"] = domain_score
        has_context = len(request.messages) > 2
        context_score = 0.5 if has_context else 0.0
        factors["context"] = context_score
        max_tokens = request.parameters.max_tokens
        output_score = min(1.0, max_tokens / 2000)
        factors["output_length"] = output_score
        weights = {
            "length": 0.2,
            "reasoning": 0.3,
            "domain": 0.2,
            "context": 0.15,
            "output_length": 0.15,
        }
        overall_score = sum(factors[k] * weights[k] for k in factors)
        return ComplexityEstimate(
            score=overall_score,
            factors=factors,
            input_length=input_length,
            estimated_reasoning_steps=reasoning_count,
            requires_context=has_context,
            domain_specific=domain_count > 0,
        )
