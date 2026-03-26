from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlalchemy import func, text, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Phone, Address, Category, Organization
from schemas import CategoryCreate, OrganizationCreate


async def create_category(db: AsyncSession, data: CategoryCreate):
    depth_limit = 3
    depth = 0
    current_parent = data.parent_id

    while current_parent is not None:
        depth += 1
        if depth >= depth_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Превышена максимальная вложенность в {depth_limit} уровня",
            )
        result = await db.execute(select(Category).where(Category.id == current_parent))
        parent = result.scalars().first()
        if not parent:
            break
        current_parent = parent.parent_id

    new_cat = Category(name=data.name, parent_id=data.parent_id)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat


async def create_organization(db: AsyncSession, data: OrganizationCreate):
    query = select(Address).where(Address.raw_address == data.address.raw_address)
    result = await db.execute(query)
    db_address = result.scalars().first()

    if not db_address:
        db_address = Address(**data.address.model_dump())
        db.add(db_address)
        await db.flush()

    db_org = Organization(name=data.name, address_id=db_address.id)
    for phone in data.phones:
        db_org.phones.append(Phone(number=phone.number))

    if data.category_ids:
        query = select(Category).where(Category.id.in_(data.category_ids))
        cat_result = await db.execute(query)
        db_org.categories = list(cat_result.scalars().all())

    db.add(db_org)
    await db.commit()
    await db.refresh(db_org)
    return db_org


async def get_list_by_category(db: AsyncSession, root_category_id: int):
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
    result = await db.execute(query, {"root_id": root_category_id})
    category_ids = [row[0] for row in result.fetchall()]

    query = (
        select(Organization)
        .join(Organization.categories)
        .filter(Category.id.in_(category_ids))
        .distinct()
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_organization_by_id(db: AsyncSession, id: int):
    query = (
        select(Organization)
        .options(
            selectinload(Organization.address),
            selectinload(Organization.phones),
            selectinload(Organization.categories),
        )
        .where(Organization.id == id)
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_organizations_by_name(db: AsyncSession, name: str):
    query = (
        select(Organization)
        .options(
            selectinload(Organization.address),
            selectinload(Organization.phones),
            selectinload(Organization.categories),
        )
        .filter(Organization.name == name)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_list_by_raw_address(db: AsyncSession, address_str: str):
    query = (
        select(Organization)
        .join(Address)
        .filter(Address.raw_address.ilike(f"%{address_str}%"))
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_list_in_box(
    db: AsyncSession, sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float
):
    lat_filter = Address.latitude.between(sw_lat, ne_lat)
    if sw_lon > ne_lon:
        lon_filter = or_(Address.longitude >= sw_lon, Address.longitude <= ne_lon)
    else:
        lon_filter = Address.longitude.between(sw_lon, ne_lon)

    query = (
        select(Address)
        .filter(lat_filter, lon_filter)
        .options(selectinload(Address.organizations))
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_list_in_radius(
    db: AsyncSession, lat: float, lon: float, radius_km: float = 5.0
):
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * func.cos(func.radians(lat)))

    distance_formula = (
        func.acos(
            func.sin(func.radians(Address.latitude)) * func.sin(func.radians(lat))
            + func.cos(func.radians(Address.latitude))
            * func.cos(func.radians(lat))
            * func.cos(func.radians(Address.longitude) - func.radians(lon))
        )
        * 6371
    )
    query = (
        select(Address)
        .options(selectinload(Address.organizations))
        .filter(Address.latitude.between(lat - lat_delta, lat + lat_delta))
        .filter(Address.longitude.between(lon - lon_delta, lon + lon_delta))
        .filter(distance_formula <= radius_km)
    )
    result = await db.execute(query)
    return result.scalars().all()
