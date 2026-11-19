from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.tokens import decode_token
from app.db.session import get_db
from app.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçerli bir erişim tokenı gerekli.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = decode_token(credentials.credentials)
    except InvalidTokenError:
        raise unauthorized from None
    if claims.get("type") != "access":
        raise unauthorized
    try:
        user_id = int(claims["sub"])
    except (ValueError, KeyError, TypeError):
        raise unauthorized from None

    user = session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_roles(*allowed_roles: UserRole):
    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için rolünüz yeterli değil.",
            )
        return user

    return check_role
