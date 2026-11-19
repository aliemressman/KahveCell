import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import UserRole


class PhoneNumberInput(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if digits.startswith("00"):
            digits = digits[2:]
        if len(digits) == 11 and digits.startswith("0"):
            digits = "90" + digits[1:]
        elif len(digits) == 10 and digits.startswith("5"):
            digits = "90" + digits
        if len(digits) != 12 or not digits.startswith("905"):
            raise ValueError("Geçerli bir Türkiye GSM numarası girin.")
        return f"+{digits}"


class RegisterInput(PhoneNumberInput):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Ad soyad boş olamaz.")
        return normalized

    @model_validator(mode="after")
    def validate_registration_credentials(self) -> "RegisterInput":
        if (self.full_name is None) != (self.password is None):
            raise ValueError("Ad soyad ve şifre birlikte gönderilmelidir.")
        return self


class PasswordLoginInput(PhoneNumberInput):
    password: str = Field(min_length=8, max_length=128)


class OTPVerifyInput(PhoneNumberInput):
    code: str = Field(pattern=r"^[0-9]{4}$")


class OTPChallengeResponse(BaseModel):
    message: str
    otp_code: str = Field(description="SMS simülasyon kodu; sabit olarak 1234.")
    expires_in_seconds: int


class UserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: str | None
    email: str | None
    role: UserRole
    profile_completed: bool


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool
    user: UserResponse


class RefreshInput(BaseModel):
    refresh_token: str


class ProfileUpdateInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    preferences: dict[str, Any] | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Geçerli bir e-posta adresi girin.")
        return normalized or None
