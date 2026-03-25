from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class AIInsightResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    type: str
    message: str
    created_at: datetime

class AIInsightsRequest(BaseModel):
    force_refresh: bool = False