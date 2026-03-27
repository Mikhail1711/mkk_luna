import pytest
import os


HEADERS = {"API-KEY": os.getenv("STATIC_API_KEY")}


@pytest.mark.asyncio(loop_scope="session")
async def test_create_organization_full(client):
    payload = {
        "name": "Тестовая Фирма",
        "address": {
            "raw_address": "Улица Тестов, 1",
            "latitude": 10.0,
            "longitude": 20.0,
        },
        "phones": [{"number": "123-456"}],
        "category_ids": [],
    }
    response = await client.post("/organizations/", json=payload, headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Тестовая Фирма"
    assert data["address"] == "Улица Тестов, 1"


@pytest.mark.asyncio(loop_scope="session")
async def test_category_depth_limit(client):
    response = await client.post("/categories/", json={"name": "L1"}, headers=HEADERS)
    assert response.status_code == 200
    level_1 = response.json()["id"]
    response = await client.post("/categories/", json={"name": "L1"}, headers=HEADERS)
    assert response.status_code == 400
    assert "уже" in response.json()["detail"]

    response = await client.post(
        "/categories/", json={"name": "L2", "parent_id": level_1}, headers=HEADERS
    )
    level_2 = response.json()["id"]

    response = await client.post(
        "/categories/", json={"name": "L3", "parent_id": level_2}, headers=HEADERS
    )
    level_3 = response.json()["id"]

    response = await client.post(
        "/categories/", json={"name": "L4", "parent_id": level_3}, headers=HEADERS
    )
    assert response.status_code == 400
    assert "Превышен" in response.json()["detail"]

    response = await client.get("/categories/", headers=HEADERS)
    assert len(response.json()) == 3


@pytest.mark.asyncio(loop_scope="session")
async def test_geo_radius_search(client):
    await client.post(
        "/organizations/",
        json={
            "name": "Центр",
            "address": {"raw_address": "Центр", "latitude": 55.75, "longitude": 37.61},
            "phones": [],
            "category_ids": [],
        },
        headers=HEADERS,
    )

    res_near = await client.get(
        "/search/radius?lat=55.75&lon=37.61&radius_km=5", headers=HEADERS
    )
    assert len(res_near.json()) == 1

    res_far = await client.get(
        "/search/radius?lat=59.93&lon=30.33&radius_km=5", headers=HEADERS
    )
    assert len(res_far.json()) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_search_by_address(client):
    addr_data = {"raw_address": "ул. Мира, 10", "latitude": 10.0, "longitude": 10.0}

    await client.post(
        "/organizations/",
        json={"name": "Кафе 1", "address": addr_data, "phones": [], "category_ids": []},
        headers=HEADERS,
    )
    await client.post(
        "/organizations/",
        json={
            "name": "Магазин 2",
            "address": addr_data,
            "phones": [],
            "category_ids": [],
        },
        headers=HEADERS,
    )
    response = await client.get(
        f"/search/address?address_str={addr_data['raw_address']}", headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert any(obj["name"] == "Кафе 1" for obj in data)
