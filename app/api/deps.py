from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error in session: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def verify_admin_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Validate Admin API key."""
    if not api_key or api_key != settings.ADMIN_API_KEY:
        logger.warning(f"Unauthorized admin API access attempt with key: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Admin API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
