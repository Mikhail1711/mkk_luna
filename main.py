from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List
import os
from dotenv import load_dotenv

import schemas
import services
from models import Base, Category

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("ОШИБКА: Переменная DATABASE_URL в .env файле не найдена")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

STATIC_KEY = os.getenv("STATIC_API_KEY")
api_key_header = APIKeyHeader(name="API-KEY", auto_error=True)


def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == STATIC_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Неверный ключ")


app = FastAPI(
    dependencies=[Depends(get_api_key)],
    title="MKK Luna API",
    description="API справочника организаций"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/organizations/{id}", response_model=schemas.OrganizationRead)
def read_organization(id: int, db: Session = Depends(get_db)):
    return services.get_organization_by_id(db, id)


@app.get("/organizations/{name}", response_model=schemas.OrganizationRead)
def read_organizations_by_name(name: str, db: Session = Depends(get_db)):
    return services.get_organizations_by_name(db, name)


@app.get("/categories/{root_category_id}/organizations", 
    response_model=schemas.List[schemas.OrganizationShort])
def search_list_by_category(root_category_id: int, db: Session = Depends(get_db)):
    return services.get_list_by_category(db, root_category_id)


@app.get("/search/address", response_model=List[schemas.OrganizationShort])
def search_by_address_name(address_str: str, db: Session = Depends(get_db)):
    return services.get_list_by_raw_address(db, address_str)


@app.get("/search/radius", response_model=List[schemas.AddressList])
def search_in_radius(
    lat: float, lon: float, 
    radius_km: float, db: Session = Depends(get_db)
):
    return services.get_list_in_radius(db, lat, lon, radius_km)


@app.get("/search/box", response_model=List[schemas.AddressList])
def search_in_box(
    sw_lat: float, sw_lon: float, 
    ne_lat: float, ne_lon: float,
    db: Session = Depends(get_db)
):
    return services.get_list_in_box(db, sw_lat, sw_lon, ne_lat, ne_lon)


@app.get("/categories/")
def get_all_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@app.post("/categories/", response_model=schemas.CategoryRead)
def create_category(data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return services.create_category(db, data)


@app.post("/organizations/", response_model=schemas.OrganizationRead)
def create_organization(data: schemas.OrganizationCreate, db: Session = Depends(get_db)):
    return services.create_organization(db, data)
