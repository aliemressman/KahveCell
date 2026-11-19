import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.core.tokens import (
    ACCESS_TOKEN_MINUTES,
    REFRESH_TOKEN_DAYS,
    create_token,
    decode_token,
)
from app.db.session import get_db
from app.models import OTPChallenge, RefreshSession, User, UserRole
from app.schemas.auth import (
    OTPChallengeResponse,
    OTPVerifyInput,
    PasswordLoginInput,
    PhoneNumberInput,
    ProfileUpdateInput,
    RegisterInput,
    RefreshInput,
    TokenPairResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Kullanıcı Yönetimi"])

OTP_CODE = "1234"
OTP_TTL_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


def _user_response(user: User) -> UserResponse:
    full_name = user.full_name.strip() or None
    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        full_name=full_name,
        email=user.email,
        role=UserRole(user.role),
        profile_completed=full_name is not None,
    )


def _issue_tokens(session: Session, user: User, is_new_user: bool) -> TokenPairResponse:
    refresh_jti = secrets.token_urlsafe(32)
    access_token, _ = create_token(
        str(user.id),
        "access",
        timedelta(minutes=ACCESS_TOKEN_MINUTES),
    )
    refresh_token, refresh_expires_at = create_token(
        str(user.id),
        "refresh",
        timedelta(days=REFRESH_TOKEN_DAYS),
        token_id=refresh_jti,
    )
    session.add(
        RefreshSession(
            token_jti=refresh_jti,
            user_id=user.id,
            expires_at=refresh_expires_at,
        )
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_MINUTES * 60,
        is_new_user=is_new_user,
        user=_user_response(user),
    )


def _create_otp_challenge(
    session: Session,
    phone_number: str,
    purpose: str,
    *,
    full_name: str | None = None,
    password_hash: str | None = None,
) -> OTPChallengeResponse:
    now = datetime.now(timezone.utc)
    challenge = session.get(OTPChallenge, phone_number)
    if challenge is None:
        challenge = OTPChallenge(
            phone_number=phone_number,
            purpose=purpose,
            code_hash=hashlib.sha256(OTP_CODE.encode("ascii")).hexdigest(),
            created_at=now,
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
            attempts=0,
            full_name=full_name,
            password_hash=password_hash,
        )
        session.add(challenge)
    else:
        challenge.purpose = purpose
        challenge.code_hash = hashlib.sha256(OTP_CODE.encode("ascii")).hexdigest()
        challenge.created_at = now
        challenge.expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
        challenge.attempts = 0
        challenge.full_name = full_name
        challenge.password_hash = password_hash
    session.commit()
    return OTPChallengeResponse(
        message="SMS simülasyonu: doğrulama kodu oluşturuldu.",
        otp_code=OTP_CODE,
        expires_in_seconds=OTP_TTL_MINUTES * 60,
    )


def _unauthorized_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz, süresi dolmuş veya iptal edilmiş yenileme tokenı.",
    )


@router.post(
    "/register",
    response_model=OTPChallengeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="GSM numarasıyla kayıt başlat",
)
def register(
    payload: RegisterInput,
    session: Session = Depends(get_db),
) -> OTPChallengeResponse:
    existing_user = session.scalar(
        select(User).where(User.phone_number == payload.phone_number)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu numara zaten kayıtlı. Giriş akışını kullanın.",
        )
    password_hash = (
        hash_password(payload.password)
        if payload.password is not None
        else None
    )
    return _create_otp_challenge(
        session,
        payload.phone_number,
        "REGISTER",
        full_name=payload.full_name,
        password_hash=password_hash,
    )


@router.post(
    "/login",
    response_model=OTPChallengeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="GSM numarasıyla giriş kodu iste",
)
def login(
    payload: PhoneNumberInput,
    session: Session = Depends(get_db),
) -> OTPChallengeResponse:
    existing_user = session.scalar(
        select(User).where(User.phone_number == payload.phone_number)
    )
    if existing_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu numarayla kayıt bulunamadı. Önce kayıt olun.",
        )
    return _create_otp_challenge(session, payload.phone_number, "LOGIN")


@router.post(
    "/login/password",
    response_model=TokenPairResponse,
    summary="GSM numarası ve şifreyle giriş yap",
)
def password_login(
    payload: PasswordLoginInput,
    session: Session = Depends(get_db),
) -> TokenPairResponse:
    user = session.scalar(
        select(User).where(User.phone_number == payload.phone_number)
    )
    if user is None or user.password_hash is None or not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon numarası veya şifre hatalı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_pair = _issue_tokens(session, user, is_new_user=False)
    session.commit()
    return token_pair


@router.post(
    "/verify-otp",
    response_model=TokenPairResponse,
    summary="OTP doğrula ve tokenları al",
)
def verify_otp(
    payload: OTPVerifyInput,
    session: Session = Depends(get_db),
) -> TokenPairResponse:
    challenge = session.get(OTPChallenge, payload.phone_number)
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aktif doğrulama kodu bulunamadı. Yeni kod isteyin.",
        )

    now = datetime.now(timezone.utc)
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        session.delete(challenge)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doğrulama kodunun süresi doldu. Yeni kod isteyin.",
        )

    if challenge.attempts >= OTP_MAX_ATTEMPTS:
        session.delete(challenge)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla hatalı deneme yapıldı. Yeni kod isteyin.",
        )

    submitted_hash = hashlib.sha256(payload.code.encode("ascii")).hexdigest()
    if not hmac.compare_digest(challenge.code_hash, submitted_hash):
        challenge.attempts += 1
        attempts_exhausted = challenge.attempts >= OTP_MAX_ATTEMPTS
        if attempts_exhausted:
            session.delete(challenge)
        session.commit()
        raise HTTPException(
            status_code=(
                status.HTTP_429_TOO_MANY_REQUESTS
                if attempts_exhausted
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Deneme sınırı aşıldı. Yeni kod isteyin."
                if attempts_exhausted
                else "Doğrulama kodu hatalı."
            ),
        )

    if challenge.purpose == "REGISTER":
        user = session.scalar(
            select(User).where(User.phone_number == payload.phone_number)
        )
        if user is not None:
            session.delete(challenge)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu numara zaten kayıtlı. Giriş akışını kullanın.",
            )
        user = User(
            phone_number=payload.phone_number,
            full_name=challenge.full_name or "",
            password_hash=challenge.password_hash,
            role=UserRole.CUSTOMER,
        )
        session.add(user)
        session.flush()
        is_new_user = True
    elif challenge.purpose == "LOGIN":
        user = session.scalar(
            select(User).where(User.phone_number == payload.phone_number)
        )
        if user is None:
            session.delete(challenge)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bu numarayla kayıt bulunamadı. Önce kayıt olun.",
            )
        is_new_user = False
    else:
        session.delete(challenge)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doğrulama isteği geçersiz. Yeni kod isteyin.",
        )

    session.delete(challenge)
    token_pair = _issue_tokens(session, user, is_new_user)
    session.commit()
    return token_pair


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Tokenları yenile",
)
def refresh_tokens(
    payload: RefreshInput,
    session: Session = Depends(get_db),
) -> TokenPairResponse:
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise _unauthorized_refresh()
        user_id = int(claims["sub"])
        token_jti = str(claims["jti"])
    except InvalidTokenError:
        raise _unauthorized_refresh() from None
    except (KeyError, TypeError, ValueError):
        raise _unauthorized_refresh() from None

    refresh_session = session.get(RefreshSession, token_jti)
    if (
        refresh_session is None
        or refresh_session.revoked_at is not None
        or refresh_session.user_id != user_id
    ):
        raise _unauthorized_refresh()

    user = session.get(User, user_id)
    if user is None:
        raise _unauthorized_refresh()

    refresh_session.revoked_at = datetime.now(timezone.utc)
    token_pair = _issue_tokens(session, user, is_new_user=False)
    session.commit()
    return token_pair


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Oturumu kapat")
def logout(
    payload: RefreshInput,
    session: Session = Depends(get_db),
) -> Response:
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise _unauthorized_refresh()
        token_jti = str(claims["jti"])
    except InvalidTokenError:
        raise _unauthorized_refresh() from None
    except (KeyError, TypeError, ValueError):
        raise _unauthorized_refresh() from None

    refresh_session = session.get(RefreshSession, token_jti)
    if refresh_session is not None and refresh_session.revoked_at is None:
        refresh_session.revoked_at = datetime.now(timezone.utc)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse, summary="Oturumdaki kullanıcıyı gör")
def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="İlk profil bilgilerini tamamla",
)
def update_me(
    payload: ProfileUpdateInput,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> UserResponse:
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ad soyad boş olamaz.",
        )
    user.full_name = full_name

    if "email" in payload.model_fields_set:
        email = payload.email.strip() if payload.email else None
        if email is not None:
            existing_email = session.scalar(
                select(User.id).where(User.email == email, User.id != user.id)
            )
            if existing_email is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bu e-posta başka bir kullanıcı tarafından kullanılıyor.",
                )
        user.email = email

    if "preferences" in payload.model_fields_set:
        user.preferences = payload.preferences or {}

    session.commit()
    return _user_response(user)
