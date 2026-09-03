from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    store_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("store_name")
    @classmethod
    def normalize_store_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Store name is required")
        return normalized


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MerchantSession(BaseModel):
    merchant_id: str
    merchant_name: str
    status: str
    onboarding_completed: bool
    environment: str
    discovery_enabled: bool


class AuthMeResponse(BaseModel):
    user_id: str
    email: str
    merchant: MerchantSession


class LogoutResponse(BaseModel):
    ok: bool
