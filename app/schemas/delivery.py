from pydantic import BaseModel, Field
from app.models import OrderStatus


class AssignAgent(BaseModel):
    agent_id: int = Field(gt=0)


class DeliveryStatusUpdate(BaseModel):
    status: OrderStatus
    remark: str | None = Field(default=None, max_length=255)
