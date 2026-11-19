from pydantic import BaseModel, ConfigDict, Field


class AddressCreate(BaseModel):
    line1: str = Field(min_length=3, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=80)
    pincode: str = Field(min_length=4, max_length=20)
    is_default: bool = False


class AddressOut(AddressCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AddressUpdate(BaseModel):
    line1: str | None = Field(default=None, min_length=3, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=80)
    pincode: str | None = Field(default=None, min_length=4, max_length=20)
    is_default: bool | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=20)


class CustomerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    phone: str
