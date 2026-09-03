from pydantic import BaseModel


class OnboardingActionResponse(BaseModel):
    status: str
    merchant_id: str
    detail: str


class IdentityResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    algorithm: str
    fingerprint: str
    status: str


class CompleteOnboardingResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    status: str
    onboarding_completed: bool
