import pytest
import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from models import Base


load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url:
    admin_url = db_url.rsplit('/', 1)[0] + "/postgres"
    test_db_name = f"{os.getenv('POSTGRES_DB')}_test"
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        try:
            conn.execute(text(f"CREATE DATABASE {os.getenv('POSTGRES_DB')}_test"))
        except ProgrammingError:
            pass
    engine.dispose()

raw_url = os.getenv("DATABASE_URL")
if not raw_url:
    TEST_DB_URL = "postgresql://user:pass@db:5432/organizations_db_test"
else:
    TEST_DB_URL = raw_url + "_test"

engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

HEADERS = {"API-KEY": os.getenv("STATIC_API_KEY")}


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]


def test_create_organization_full(client):
    payload = {
        "name": "Тестовая Фирма",
        "address": {
            "raw_address": "Улица Тестов, 1",
            "latitude": 10.0,
            "longitude": 20.0
        },
        "phones": [{"number": "123-456"}],
        "category_ids": []
    }
    response = client.post(
        "/organizations/", 
        json=payload, 
        headers=HEADERS
    )
 
    assert response.status_code == 200
    data = response.json()
    #print(f"DEBUG: {response.json()}")
    assert data["name"] == "Тестовая Фирма"
    assert data["address"] == "Улица Тестов, 1"


def test_category_depth_limit(client):
    response = client.post(
        "/categories/", 
        json={"name": "L1"}, 
        headers=HEADERS
    )
    assert response.status_code == 200
    level_1 = response.json()["id"]

    level_2 = client.post(
        "/categories/", 
        json={"name": "L2", "parent_id": level_1}, 
        headers=HEADERS
    ).json()["id"]

    level_3 = client.post(
        "/categories/", 
        json={"name": "L3", "parent_id": level_2},
        headers=HEADERS
    ).json()["id"]
    
    response = client.post(
        "/categories/", json={"name": "L4", "parent_id": level_3}, 
        headers=HEADERS
    )
    assert response.status_code == 400
    assert "Превышена" in response.json()["detail"]


def test_geo_radius_search(client):
    client.post("/organizations/", json={
        "name": "Центр",
        "address": {"raw_address": "Центр", "latitude": 55.75, "longitude": 37.61},
        "phones": [], "category_ids": []
    }, headers=HEADERS)

    res_near = client.get("/search/radius?lat=55.75&lon=37.61&radius_km=5", 
    headers=HEADERS)
    assert len(res_near.json()) == 1
    print(res_near.json())

    res_far = client.get("/search/radius?lat=59.93&lon=30.33&radius_km=5", 
    headers=HEADERS)
    assert len(res_far.json()) == 0


def test_search_by_address(client):
    addr_data = {"raw_address": "ул. Мира, 10", "latitude": 10.0, "longitude": 10.0}
    
    client.post("/organizations/", json={
        "name": "Кафе 1", 
        "address": addr_data, 
        "phones": [], 
        "category_ids": []
    }, headers=HEADERS
    )
    client.post("/organizations/", json={
        "name": "Магазин 2", 
        "address": addr_data, 
        "phones": [], 
        "category_ids": []
    }, headers=HEADERS
    )
    response = client.get(
        f"/search/address?address_str={addr_data['raw_address']}", 
        headers=HEADERS
    )
    
    print(f"DEBUG: Status {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert any(obj["name"] == "Кафе 1" for obj in data)
