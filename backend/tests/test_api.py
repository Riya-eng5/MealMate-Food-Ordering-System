import os

# Tests use an isolated SQLite database instead of the developer's local database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_food_ordering.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only")

from fastapi.testclient import TestClient
from app.main import app


def login(client: TestClient, email: str):
    response = client.post("/auth/login", json={"email": email, "password": "demo12345"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_customer_can_browse_restaurants(client):
    response = client.get("/restaurants")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_customer_can_place_and_pay_for_order(client):
    token = login(client, "customer@example.com")
    restaurants = client.get("/restaurants").json()
    restaurant = restaurants[0]
    menu = client.get(f"/restaurants/{restaurant['id']}/menu").json()
    assert menu

    order_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_id": restaurant["id"],
            "delivery_address": "Sector 45, Gurugram",
            "items": [{"menu_item_id": menu[0]["id"], "quantity": 2}],
        },
    )
    assert order_response.status_code == 201, order_response.text
    order = order_response.json()
    assert order["status"] == "pending"
    assert order["total_amount"] > 0

    payment = client.post(f"/orders/{order['id']}/pay", headers={"Authorization": f"Bearer {token}"})
    assert payment.status_code == 200, payment.text
    assert payment.json()["payment_status"] == "paid"


def test_customer_cannot_open_admin_dashboard(client):
    token = login(client, "customer@example.com")
    response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_owner_can_read_own_restaurant(client):
    token = login(client, "owner@example.com")
    response = client.get("/owner/restaurant", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "Campus Kitchen"


# The client fixture keeps one seeded test database for the module.
import pytest


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_complete_order_lifecycle_across_roles(client):
    customer_token = login(client, "customer@example.com")
    owner_token = login(client, "owner@example.com")
    admin_token = login(client, "admin@example.com")
    delivery_token = login(client, "delivery@example.com")

    restaurant = client.get("/restaurants").json()[0]
    menu_item = client.get(f"/restaurants/{restaurant['id']}/menu").json()[0]
    created = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "restaurant_id": restaurant["id"],
            "delivery_address": "Sector 45, Gurugram",
            "items": [{"menu_item_id": menu_item["id"], "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    for next_status in ("confirmed", "preparing"):
        updated = client.patch(f"/owner/orders/{order_id}/status", headers=owner_headers, json={"status": next_status})
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == next_status

    delivery_users = client.get("/admin/users?role=delivery", headers={"Authorization": f"Bearer {admin_token}"}).json()
    delivery_id = delivery_users[0]["id"]
    assigned = client.patch(
        f"/admin/orders/{order_id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"delivery_partner_id": delivery_id},
    )
    assert assigned.status_code == 200, assigned.text

    delivery_headers = {"Authorization": f"Bearer {delivery_token}"}
    for next_status in ("out_for_delivery", "delivered"):
        updated = client.patch(f"/delivery/orders/{order_id}/status", headers=delivery_headers, json={"status": next_status})
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == next_status

    review = client.post(
        f"/orders/{order_id}/reviews",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"rating": 5, "comment": "Fresh and tasty."},
    )
    assert review.status_code == 201, review.text
