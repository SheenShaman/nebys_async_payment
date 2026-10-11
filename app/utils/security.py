from fastapi import Header, HTTPException, status

from app.database.config import get_settings


async def require_api_key(api_key: str | None = Header(default=None)) -> None:
    if api_key != get_settings().API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API KEY")
