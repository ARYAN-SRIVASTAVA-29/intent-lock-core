from pydantic import BaseModel, ConfigDict, Field, model_validator


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: str
    version: str
    status: str
    max_transaction_minor: int
    step_up_above_minor: int
    daily_spend_minor: int
    max_discount_pct: float
    max_recovery_attempts: int
    alternative_skus_allowed: bool
    merchant_switching_allowed: bool
    unknown_agent_action: str


class PolicyUpdateRequest(BaseModel):
    max_transaction_minor: int = Field(gt=0)
    step_up_above_minor: int = Field(gt=0)
    daily_spend_minor: int = Field(gt=0)
    max_discount_pct: float = Field(ge=0, le=100)
    max_recovery_attempts: int = Field(ge=0, le=10)
    alternative_skus_allowed: bool = True
    merchant_switching_allowed: bool = False
    unknown_agent_action: str = "STEP_UP"

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.step_up_above_minor > self.max_transaction_minor:
            raise ValueError("Step-up threshold cannot exceed maximum transaction amount")
        if self.daily_spend_minor < self.max_transaction_minor:
            raise ValueError("Daily spend limit cannot be lower than maximum transaction amount")
        return self
