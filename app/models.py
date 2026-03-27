from sqlalchemy import Column, Integer, ForeignKey, Table, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base


Base = declarative_base()

org_category_association = Table(
    "org_category_association",
    Base.metadata,
    Column(
        "organization_id", Integer, ForeignKey("organizations.id"), primary_key=True
    ),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
)


class Phone(Base):
    __tablename__ = "phones"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(nullable=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="phones")


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    raw_address: Mapped[str] = mapped_column(nullable=False)
    latitude: Mapped[float] = mapped_column(index=True)
    longitude: Mapped[float] = mapped_column(index=True)

    organizations: Mapped[list["Organization"]] = relationship(
        back_populates="address", lazy="selectin"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )

    subcategories: Mapped[list["Category"]] = relationship(
        backref="parent", remote_side=[id], lazy="selectin"
    )
    organizations: Mapped[list["Organization"]] = relationship(
        secondary=org_category_association, back_populates="categories", lazy="selectin"
    )
    __table_args__ = (
        UniqueConstraint("name", "parent_id", name="unique_category_name_parent"),
        Index(
            "unique_root_category_name",
            "name",
            unique=True,
            postgresql_where=(parent_id is None),
        ),
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True, nullable=False)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id"), index=True)

    phones: Mapped[list["Phone"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )
    address: Mapped["Address"] = relationship(
        back_populates="organizations", lazy="selectin"
    )
    categories: Mapped[list["Category"]] = relationship(
        secondary=org_category_association,
        back_populates="organizations",
        lazy="selectin",
    )
