import os
from typing import List

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import schemas
import services
from models import Base, Category
from database import get_db, engine


STATIC_KEY = os.getenv("STATIC_API_KEY")
api_key_header = APIKeyHeader(name="API-KEY", auto_error=True)


def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == STATIC_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Неверный ключ")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    dependencies=[Depends(get_api_key)],
    title="MKK Luna API",
    description="API справочника организаций",
)


@app.get("/organizations/{id}", response_model=schemas.OrganizationRead)
async def read_organization(id: int, db: AsyncSession = Depends(get_db)):
    return await services.get_organization_by_id(db, id)


@app.get("/organizations/{name}", response_model=schemas.OrganizationRead)
async def read_organizations_by_name(name: str, db: AsyncSession = Depends(get_db)):
    return await services.get_organizations_by_name(db, name)


@app.get(
    "/categories/{root_category_id}/organizations",
    response_model=schemas.List[schemas.OrganizationShort],
)
async def search_list_by_category(
    root_category_id: int, db: AsyncSession = Depends(get_db)
):
    return await services.get_list_by_category(db, root_category_id)


@app.get("/search/address", response_model=List[schemas.OrganizationShort])
async def search_by_address_name(address_str: str, db: AsyncSession = Depends(get_db)):
    return await services.get_list_by_raw_address(db, address_str)


@app.get("/search/radius", response_model=List[schemas.AddressList])
async def search_in_radius(
    lat: float, lon: float, radius_km: float, db: AsyncSession = Depends(get_db)
):
    return await services.get_list_in_radius(db, lat, lon, radius_km)


@app.get("/search/box", response_model=List[schemas.AddressList])
async def search_in_box(
    sw_lat: float,
    sw_lon: float,
    ne_lat: float,
    ne_lon: float,
    db: AsyncSession = Depends(get_db),
):
    return await services.get_list_in_box(db, sw_lat, sw_lon, ne_lat, ne_lon)


@app.get("/categories/")
async def get_all_categories(db: AsyncSession = Depends(get_db)):
    query = select(Category)
    result = await db.execute(query)
    return result.scalars().all()


@app.post("/categories/", response_model=schemas.CategoryRead)
async def create_category(
    data: schemas.CategoryCreate, db: AsyncSession = Depends(get_db)
):
    return await services.create_category(db, data)


@app.post("/organizations/", response_model=schemas.OrganizationRead)
async def create_organization(
    data: schemas.OrganizationCreate, db: AsyncSession = Depends(get_db)
):
    return await services.create_organization(db, data)
