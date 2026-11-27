from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import HTTPException, Request, Response
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthAccount, User, UserPreference, UserSession


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_google_credential(credential: str) -> dict:
    if not settings.google_client_id:
        raise HTTPException(503, "Google sign-in is not configured")
    try:
        claims = id_token.verify_oauth2_token(
            credential,
            GoogleRequest(),
            settings.google_client_id,
        )
    except Exception as exc:
        raise HTTPException(401, "Google credential is invalid or expired") from exc
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(401, "Google credential issuer is invalid")
    if claims.get("aud") != settings.google_client_id:
        raise HTTPException(401, "Google credential was issued for a different application")
    if claims.get("azp") and claims.get("azp") != settings.google_client_id:
        raise HTTPException(401, "Google credential authorized party is invalid")
    if claims.get("exp") and int(claims["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(401, "Google credential is expired")
    if not claims.get("sub") or not claims.get("email") or not claims.get("email_verified"):
        raise HTTPException(401, "Google account must have a verified email address")
    return claims


def issue_session(db: Session, user: User, response: Response) -> None:
    raw_session = secrets.token_urlsafe(48)
    raw_csrf = secrets.token_urlsafe(32)
    ttl = timedelta(hours=settings.session_ttl_hours)
    session = UserSession(
        user_id=user.id,
        session_token_hash=hash_secret(raw_session),
        csrf_token_hash=hash_secret(raw_csrf),
        expires_at=datetime.now(timezone.utc) + ttl,
    )
    db.add(session)
    db.commit()
    cookie_options = {
        "max_age": int(ttl.total_seconds()),
        "secure": settings.session_cookie_secure,
        "samesite": settings.normalized_cookie_samesite,
        "path": "/api",
    }
    response.set_cookie(
        settings.session_cookie_name,
        raw_session,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        raw_csrf,
        httponly=False,
        **cookie_options,
    )


def clear_session_cookies(response: Response) -> None:
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            name,
            path="/api",
            secure=settings.session_cookie_secure,
            samesite=settings.normalized_cookie_samesite,
        )


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "profile_picture": user.profile_picture,
        "country": user.country,
        "bio": user.bio,
    }


def authenticate_request(
    request: Request,
    authorization: str | None,
    db: Session,
) -> User:
    raw_session = request.cookies.get(settings.session_cookie_name)
    if raw_session:
        session = db.scalar(
            select(UserSession).where(
                UserSession.session_token_hash == hash_secret(raw_session),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if session:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                csrf_cookie = request.cookies.get(settings.csrf_cookie_name, "")
                csrf_header = request.headers.get("x-csrf-token", "")
                if (
                    not csrf_cookie
                    or not secrets.compare_digest(csrf_cookie, csrf_header)
                    or not secrets.compare_digest(hash_secret(csrf_cookie), session.csrf_token_hash)
                ):
                    raise HTTPException(403, "CSRF validation failed")
            user = db.get(User, session.user_id)
            if not user or not user.is_active:
                raise HTTPException(401, "Account is unavailable")
            return user
        raise HTTPException(401, "Session is invalid, expired, or revoked")
    # Accept short-lived legacy JWTs during the migration window. New sessions
    # are always opaque, server-revocable cookies.
    if authorization and authorization.startswith("Bearer "):
        import jwt

        try:
            subject = jwt.decode(
                authorization[7:],
                settings.jwt_secret,
                algorithms=["HS256"],
            )["sub"]
        except Exception as exc:
            raise HTTPException(401, "Invalid or expired session") from exc
        user = db.get(User, subject)
        if user and user.is_active:
            return user
    raise HTTPException(401, "Authentication required")


def find_google_account(db: Session, subject: str) -> AuthAccount | None:
    return db.scalar(
        select(AuthAccount).where(
            AuthAccount.provider == "google",
            AuthAccount.provider_user_id == subject,
        )
    )
