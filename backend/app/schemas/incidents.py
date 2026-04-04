from datetime import datetime

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: str
    tenant_id: str
    severity: str
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
