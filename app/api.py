from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
import app.schemas as schemas
import app.services as services


router = APIRouter()  # prefix="/organizations", tags=["Organizations"])


@router.get("/organizations/{id}", response_model=schemas.OrganizationRead)
async def read_organization(id: int, db: AsyncSession = Depends(get_db)):
    return await services.get_organization_by_id(db, id)


@router.get("/organizations/{name}", response_model=schemas.OrganizationRead)
async def read_organizations_by_name(name: str, db: AsyncSession = Depends(get_db)):
    return await services.get_organizations_by_name(db, name)


@router.get(
    "/categories/{root_category_id}/organizations",
    response_model=schemas.List[schemas.OrganizationShort],
)
async def search_list_by_category(
    root_category_id: int, db: AsyncSession = Depends(get_db)
):
    return await services.get_list_by_category(db, root_category_id)


@router.get("/search/address", response_model=List[schemas.OrganizationShort])
async def search_by_address_name(address_str: str, db: AsyncSession = Depends(get_db)):
    return await services.get_list_by_raw_address(db, address_str)


@router.get("/search/radius", response_model=List[schemas.AddressList])
async def search_in_radius(
    lat: float, lon: float, radius_km: float, db: AsyncSession = Depends(get_db)
):
    return await services.get_list_in_radius(db, lat, lon, radius_km)


@router.get("/search/box", response_model=List[schemas.AddressList])
async def search_in_box(
    sw_lat: float,
    sw_lon: float,
    ne_lat: float,
    ne_lon: float,
    db: AsyncSession = Depends(get_db),
):
    return await services.get_list_in_box(db, sw_lat, sw_lon, ne_lat, ne_lon)


@router.get("/categories/")
async def get_all_categories(db: AsyncSession = Depends(get_db)):
    return await services.get_list_categories(db)


@router.post("/categories/", response_model=schemas.CategoryRead)
async def create_category(
    data: schemas.CategoryCreate, db: AsyncSession = Depends(get_db)
):
    return await services.create_category(db, data)


@router.post("/organizations/", response_model=schemas.OrganizationRead)
async def create_organization(
    data: schemas.OrganizationCreate, db: AsyncSession = Depends(get_db)
):
    return await services.create_organization(db, data)
