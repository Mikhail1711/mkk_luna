from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from typing import List, Any


class PhoneBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: str


class OrganizationShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    raw_address: str = Field(max_length=100)


class AddressList(AddressRead):
    id: int
    organizations: List[OrganizationShort]


class AddressCreate(AddressRead):
    latitude: float = Field(
        ge=-90, le=90, description="Отрицательные значения для южной широты"
    )
    longitude: float = Field(
        ge=-180, le=180, description="Отрицательные значения для западной долготы"
    )


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(max_length=50)


class CategoryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(max_length=50)
    parent_id: int | None = None


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(max_length=50)
    address: AddressCreate
    phones: List[PhoneBase]
    category_ids: List[int] = []


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phones: List[str]
    categories: List[str]
    
    @field_validator('address', mode='before')
    @classmethod
    def transform_address(cls, v: Any):
        return v.raw_address if hasattr(v, 'raw_address') else str(v)

    @field_validator('phones', mode='before')
    @classmethod
    def transform_phones(cls, v: Any):
        if isinstance(v, list):
            return [p.number if hasattr(p, 'number') else str(p) for p in v]
        return v

    @field_validator('categories', mode='before')
    @classmethod
    def serialize_categories(cls, v: Any):
        if isinstance(v, list):
            return [c.name if hasattr(c, 'name') else str(c) for c in v]
        return v
