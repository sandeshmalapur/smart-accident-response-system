import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayloadError, decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.services.auth_service import get_user_by_id

# tokenUrl is documentation-only here (login isn't form-encoded per API_SPEC.md,
# but this still gives FastAPI's OpenAPI UI a working "Authorize" flow).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise unauthorized
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (TokenPayloadError, ValueError):
        raise unauthorized

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
