from typing import Optional
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class TimescaleClient:
    _engine: Optional[AsyncEngine] = None

    @classmethod
    def get_engine(cls, url: str) -> AsyncEngine:
        if cls._engine is None:
            cls._engine = create_async_engine(url, pool_pre_ping=True)
        return cls._engine
