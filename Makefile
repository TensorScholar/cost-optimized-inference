.PHONY: run dev test format lint

run:
	uvicorn inference_engine.adapters.api.app:app --host 0.0.0.0 --port 8000

dev:
	uvicorn inference_engine.adapters.api.app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q

format:
	black src tests
	ruff check --fix src tests

lint:
	ruff check src tests
	mypy src
