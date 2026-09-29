from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from app.security import auth
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Employee


def test_signed_jwt_claims_and_live_permissions(client, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        auth.jwks,
        "get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key=key.public_key()),
    )
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "00000000-0000-4000-8000-000000000003",
        "iss": settings.keycloak_issuer,
        "aud": settings.keycloak_audience,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }

    def headers(**changes):
        return {
            "Authorization": "Bearer "
            + jwt.encode({**claims, **changes}, key, algorithm="RS256")
        }

    assert client.get("/api/v1/auth/me", headers=headers()).json()["role"] == "user"
    assert client.get("/api/v1/audit", headers=headers()).status_code == 403
    for changes in [
        {"aud": "another-client"},
        {"iss": "https://attacker.invalid"},
        {"exp": now - timedelta(seconds=1)},
    ]:
        assert (
            client.get("/api/v1/auth/me", headers=headers(**changes)).status_code == 401
        )
    with SessionLocal() as db:
        employee = db.get(Employee, 3)
        employee.active = False
        db.commit()
    try:
        assert client.get("/api/v1/auth/me", headers=headers()).status_code == 403
    finally:
        with SessionLocal() as db:
            db.get(Employee, 3).active = True
            db.commit()
