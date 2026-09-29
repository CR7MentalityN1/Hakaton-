import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.errors import fail
from app.db.session import get_db
from app.models import Employee

bearer = HTTPBearer(auto_error=False)
jwks = jwt.PyJWKClient(
    settings.keycloak_jwks_url
    or settings.keycloak_issuer + "/protocol/openid-connect/certs",
    cache_keys=True,
    timeout=5,
)


def verify_token(token: str):
    try:
        key = jwks.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer,
            audience=settings.keycloak_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except (jwt.PyJWTError, OSError):
        fail(401, "TOKEN_INVALID", "Сессия истекла или токен недействителен")


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Employee:
    if not credentials:
        fail(401, "AUTH_REQUIRED", "Войдите через Keycloak")
    claims = verify_token(credentials.credentials)
    user = db.scalar(select(Employee).where(Employee.keycloak_user_id == claims["sub"]))
    if not user:
        roles = claims.get("realm_access", {}).get("roles", [])
        role = next((r for r in ["admin", "manager", "user"] if r in roles), None)
        if not role:
            fail(403, "ROLE_REQUIRED", "Назначьте роль CRM в Keycloak")
        user = Employee(
            keycloak_user_id=claims["sub"],
            full_name=claims.get(
                "name", claims.get("preferred_username", "Пользователь")
            ),
            email=claims.get("email", claims["sub"] + "@unconfigured.local"),
            role=role,
        )
        db.add(user)
        db.commit()
    # Local role and active flag are deliberately read from PostgreSQL on every request.
    if not user.active:
        fail(403, "ACCOUNT_DISABLED", "Учётная запись отключена")
    return user


def require_roles(*roles):
    def dependency(user: Employee = Depends(current_user)):
        if user.role not in roles:
            fail(403, "ROLE_FORBIDDEN", "Недостаточно прав для этого действия")
        return user

    return dependency


admin_user = require_roles("admin")
manager_user = require_roles("manager", "admin")
