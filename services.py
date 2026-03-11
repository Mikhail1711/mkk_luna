from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_

from models import Phone, Address, Category, Organization
from schemas import CategoryCreate, OrganizationCreate


def create_category(db: Session, data: CategoryCreate):
    depth_limit = 3
    depth = 0
    
    if data.parent_id:
        current_parent = db.query(Category).filter(
            Category.id == data.parent_id
        ).first()
        depth += 1
        
        while current_parent and current_parent.parent_id is not None:
            current_parent = db.query(Category).filter(
                Category.id == current_parent.parent_id
            ).first()
            depth += 1

        if depth >= depth_limit:
            raise HTTPException(
                status_code=400, 
                detail=f"Превышена максимальная вложенность в {depth_limit} уровня"
            )
    new_cat = Category(name=data.name, parent_id=data.parent_id)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat



def create_organization(db: Session, data: OrganizationCreate):
    db_address = db.query(Address).filter(
        Address.raw_address == data.address.raw_address
    ).first()

    if not db_address:
        db_address = Address(**data.address.model_dump())
        db.add(db_address)
        db.flush()

    db_org = Organization(
        name=data.name,
        address_id=db_address.id
    )
    for phone in data.phones:
        db_org.phones.append(Phone(number=phone.number))

    if data.category_ids:
        categories = db.query(Category).filter(Category.id.in_(data.category_ids)).all()
        db_org.categories = categories

    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org



def get_list_by_category(db: Session, root_category_id: int):
    """
    Рекурсивно находит ID самой категории и всех её потомков (любой вложенности).
    Возвращает список организаций. 
    """
    query = text("""
        WITH RECURSIVE category_tree AS (
            SELECT id FROM categories WHERE id = :root_id
            UNION ALL
            SELECT c.id FROM categories c
            JOIN category_tree ct ON c.parent_id = ct.id
        )
        SELECT id FROM category_tree;
    """)
    result = db.execute(query, {"root_id": root_category_id}).fetchall()
    category_ids = [row[0] for row in result]
    
    return (
        db.query(Organization)
        .join(Organization.categories)
        .filter(Category.id.in_(category_ids))
        .distinct()
        .all()
    )


def get_organization_by_id(db: Session, id: int):
    return (
        db.query(Organization)
        .options(
            joinedload(Organization.address),
            joinedload(Organization.phones),
            joinedload(Organization.categories)
        )
        .filter(Organization.id == id)
        .first()
    )


def get_organizations_by_name(db: Session, name: str):
    return (
        db.query(Organization)
        .options(
            joinedload(Organization.address),
            joinedload(Organization.phones),
            joinedload(Organization.categories)
        )
        .filter(Organization.name == name)
        .all()
    )


def get_list_by_raw_address(db: Session, address_str: str):
    return (
        db.query(Organization)
        .join(Address)
        .filter(Address.raw_address.ilike(f"%{address_str}%"))
        .all()
    ) 


def get_list_in_box(
        db: Session, sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float
    ):
    lat_filter = Address.latitude.between(sw_lat, ne_lat)
    if sw_lon > ne_lon:
        lon_filter = or_(Address.longitude >= sw_lon, Address.longitude <= ne_lon)
    else:
        lon_filter = Address.longitude.between(sw_lon, ne_lon)

    return (
        db.query(Address)
        .filter(lat_filter, lon_filter)
        .options(joinedload(Address.organizations))
        .all()
    )


def get_list_in_radius(db: Session, lat: float, lon: float, radius_km: float = 5.0):
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * func.cos(func.radians(lat)))

    distance_formula = (
        func.acos(
            func.sin(func.radians(Address.latitude)) * func.sin(func.radians(lat)) +
            func.cos(func.radians(Address.latitude)) * func.cos(func.radians(lat)) *
            func.cos(func.radians(Address.longitude) - func.radians(lon))
        ) * 6371
    )
    return (
        db.query(Address)
        .options(joinedload(Address.organizations))
        .filter(Address.latitude.between(lat - lat_delta, lat + lat_delta))
        .filter(Address.longitude.between(lon - lon_delta, lon + lon_delta))
        .filter(distance_formula <= radius_km)
        .all()
    )
