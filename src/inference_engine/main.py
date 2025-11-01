from fastapi import FastAPI

from inference_engine.adapters.api.app import app  # re-export for uvicorn

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("inference_engine.main:app", host="0.0.0.0", port=8000, reload=True)


