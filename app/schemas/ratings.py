from pydantic import BaseModel, ConfigDict, Field


class RatingCreate(BaseModel):
    restaurant_rating: int = Field(ge=1, le=5)
    agent_rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class RatingOut(RatingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
