from sqlalchemy import Column, Integer, String, ForeignKey, Float, Table
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()

org_category_association = Table(
    "org_category_association",
    Base.metadata,
    Column("organization_id", Integer, ForeignKey("organizations.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
)


class Phone(Base):
    __tablename__ = "phones"

    id = Column(Integer, primary_key=True)
    number = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)

    organization = relationship("Organization", back_populates="phones")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    raw_address = Column(String, nullable=False)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)

    organizations = relationship("Organization", back_populates="address")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)

    subcategories = relationship("Category", backref="parent", remote_side=[id])
    organizations = relationship(
        "Organization", secondary=org_category_association, back_populates="categories"
    )


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address_id = Column(Integer, ForeignKey('addresses.id'), index=True)

    phones = relationship("Phone", back_populates="organization", cascade="all, delete-orphan")
    address = relationship("Address", back_populates="organizations")
    categories = relationship(
        "Category", secondary=org_category_association, 
        back_populates="organizations"
    )
