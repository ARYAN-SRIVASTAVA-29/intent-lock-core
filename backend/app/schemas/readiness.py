from pydantic import BaseModel


class ReadinessCheck(BaseModel):
    name: str
    status: str


class ReadinessResponse(BaseModel):
    merchant_id: str
    overall: str
    checks: list[ReadinessCheck]
