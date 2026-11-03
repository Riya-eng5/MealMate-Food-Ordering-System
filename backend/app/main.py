"""Food ordering and restaurant management API.

A compact educational MVP with role-based JWT authentication and SQLite storage.
"""
from __future__ import annotations

import base64
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, or_
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

# -----------------------------------------------------------------------------
# Configuration and database
# -----------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./food_ordering.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret-before-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("food_ordering")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Database tables (normalized: users, restaurants, menu, orders, order items,
# and reviews are stored separately).
# -----------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(300), nullable=False)
    role = Column(String(30), nullable=False, default="customer", index=True)
    address = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    restaurant = relationship("Restaurant", back_populates="owner", uselist=False)
    customer_orders = relationship("Order", back_populates="customer", foreign_keys="Order.customer_id")


class Restaurant(Base):
    __tablename__ = "restaurants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(140), nullable=False, index=True)
    description = Column(Text, default="")
    cuisine = Column(String(80), default="General", index=True)
    address = Column(String(300), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="restaurant")
    menu_items = relationship("MenuItem", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="restaurant")
    reviews = relationship("Review", back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    name = Column(String(140), nullable=False)
    description = Column(Text, default="")
    category = Column(String(80), default="Main Course", index=True)
    price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

    restaurant = relationship("Restaurant", back_populates="menu_items")
    order_items = relationship("OrderItem", back_populates="menu_item")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    delivery_partner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(40), default="pending", nullable=False, index=True)
    total_amount = Column(Numeric(12, 2), nullable=False)
    payment_status = Column(String(30), default="pending", nullable=False)
    delivery_address = Column(String(300), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    customer = relationship("User", back_populates="customer_orders", foreign_keys=[customer_id])
    delivery_partner = relationship("User", foreign_keys=[delivery_partner_id])
    restaurant = relationship("Restaurant", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    # Snapshot values preserve the price/name at the time the order was placed.
    item_name = Column(String(140), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    restaurant = relationship("Restaurant", back_populates="reviews")
    order = relationship("Order", back_populates="review")


# -----------------------------------------------------------------------------
# API schemas
# -----------------------------------------------------------------------------

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=6, max_length=100)
    address: Optional[str] = Field(default=None, max_length=300)


class LoginInput(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    address: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: str = ""
    cuisine: str = "General"
    address: str = Field(min_length=3, max_length=300)


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    cuisine: str
    address: str
    owner_id: int
    is_active: bool


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: str = ""
    category: str = "Main Course"
    price: float = Field(gt=0, le=100000)


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0, le=100000)
    is_available: Optional[bool] = None


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    restaurant_id: int
    name: str
    description: str
    category: str
    price: float
    is_available: bool


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(min_length=5, max_length=300)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    menu_item_id: int
    item_name: str
    unit_price: float
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    restaurant_id: int
    delivery_partner_id: Optional[int]
    status: str
    total_amount: float
    payment_status: str
    delivery_address: str
    created_at: datetime
    items: list[OrderItemOut]


class StatusUpdate(BaseModel):
    status: str


class AssignDeliveryInput(BaseModel):
    delivery_partner_id: int


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


# -----------------------------------------------------------------------------
# Password and JWT helpers
# -----------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = 240_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user: User) -> str:
    """Create a standards-compliant HS256 JWT using Python's standard library."""
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp())
    header = _b64url_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url_encode(json.dumps({"sub": str(user.id), "role": user.role, "exp": expires_at}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    signature = _b64url_encode(hmac.new(SECRET_KEY.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest())
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> dict:
    """Verify JWT signature and expiry before returning its payload."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token")
    header = json.loads(_b64url_decode(parts[0]))
    if header.get("alg") != ALGORITHM:
        raise ValueError("Unsupported token algorithm")
    signing_input = f"{parts[0]}.{parts[1]}"
    expected = _b64url_encode(hmac.new(SECRET_KEY.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, parts[2]):
        raise ValueError("Invalid token signature")
    payload = json.loads(_b64url_decode(parts[1]))
    if int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Expired token")
    return payload


bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub", "0"))
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account no longer exists")
    return user


def require_roles(*roles: str):
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return user
    return role_dependency


def get_owned_restaurant(db: Session, owner: User) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.owner_id == owner.id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Create your restaurant profile first")
    return restaurant


def get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# -----------------------------------------------------------------------------
# App, logging, and common error handling
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield


app = FastAPI(
    title="Food Ordering & Restaurant Management API",
    description="Role-based food ordering platform with customer, owner, delivery and admin workflows.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your deployed frontend URL before production.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error for %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred"})


# -----------------------------------------------------------------------------
# Demo records. These make it easy to evaluate each role after first startup.
# -----------------------------------------------------------------------------

def seed_demo_data():
    db = SessionLocal()
    try:
        demo_users = [
            ("Demo Customer", "customer@example.com", "customer"),
            ("Demo Restaurant Owner", "owner@example.com", "owner"),
            ("Demo Delivery Partner", "delivery@example.com", "delivery"),
            ("Demo Admin", "admin@example.com", "admin"),
        ]
        for name, email, role in demo_users:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(name=name, email=email, password_hash=hash_password("demo12345"), role=role, address="Sector 45, Gurugram"))
        db.commit()
        owner = db.query(User).filter(User.email == "owner@example.com").first()
        if owner and not db.query(Restaurant).filter(Restaurant.owner_id == owner.id).first():
            restaurant = Restaurant(
                name="Campus Kitchen", description="Fresh and tasty meals made to order.",
                cuisine="Indian", address="Sector 45, Gurugram", owner_id=owner.id,
            )
            db.add(restaurant)
            db.commit()
            db.refresh(restaurant)
            db.add_all([
                MenuItem(restaurant_id=restaurant.id, name="Paneer Butter Masala", description="Paneer in a creamy tomato gravy.", category="Main Course", price=220),
                MenuItem(restaurant_id=restaurant.id, name="Veg Biryani", description="Fragrant rice with seasonal vegetables.", category="Rice", price=160),
                MenuItem(restaurant_id=restaurant.id, name="Masala Fries", description="Crispy fries with house masala.", category="Sides", price=90),
            ])
            db.commit()
    finally:
        db.close()


# -----------------------------------------------------------------------------
# General and authentication endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "food-ordering-api"}


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="customer", address=payload.address)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user}


@app.get("/auth/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user


# -----------------------------------------------------------------------------
# Customer: restaurant discovery and menu browsing
# -----------------------------------------------------------------------------

@app.get("/restaurants", response_model=list[RestaurantOut])
def list_restaurants(
    q: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    sort: str = Query(default="name", pattern="^(name|newest)$"),
    db: Session = Depends(get_db),
):
    query = db.query(Restaurant).filter(Restaurant.is_active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Restaurant.name.ilike(term), Restaurant.cuisine.ilike(term), Restaurant.description.ilike(term)))
    query = query.order_by(Restaurant.created_at.desc() if sort == "newest" else Restaurant.name.asc())
    return query.offset((page - 1) * page_size).limit(page_size).all()


@app.get("/restaurants/{restaurant_id}/menu", response_model=list[MenuItemOut])
def restaurant_menu(
    restaurant_id: int,
    q: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id, Restaurant.is_active.is_(True)).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    query = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id, MenuItem.is_available.is_(True))
    if q:
        query = query.filter(or_(MenuItem.name.ilike(f"%{q}%"), MenuItem.category.ilike(f"%{q}%")))
    return query.order_by(MenuItem.category, MenuItem.name).offset((page - 1) * page_size).limit(page_size).all()


# -----------------------------------------------------------------------------
# Customer: cart checkout, orders, mock payment, tracking and reviews
# -----------------------------------------------------------------------------

@app.post("/orders", response_model=OrderOut, status_code=201)
def place_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles("customer")),
):
    restaurant = db.query(Restaurant).filter(Restaurant.id == payload.restaurant_id, Restaurant.is_active.is_(True)).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or inactive")

    menu_ids = [line.menu_item_id for line in payload.items]
    menu_items = db.query(MenuItem).filter(
        MenuItem.id.in_(menu_ids), MenuItem.restaurant_id == restaurant.id, MenuItem.is_available.is_(True)
    ).all()
    by_id = {item.id: item for item in menu_items}
    if len(by_id) != len(set(menu_ids)):
        raise HTTPException(status_code=400, detail="One or more menu items are unavailable or belong to another restaurant")

    total = sum(by_id[line.menu_item_id].price * line.quantity for line in payload.items)
    order = Order(
        customer_id=customer.id, restaurant_id=restaurant.id, status="pending",
        total_amount=round(total, 2), payment_status="pending", delivery_address=payload.delivery_address.strip(),
    )
    db.add(order)
    db.flush()
    for line in payload.items:
        item = by_id[line.menu_item_id]
        db.add(OrderItem(order_id=order.id, menu_item_id=item.id, item_name=item.name, unit_price=item.price, quantity=line.quantity))
    db.commit()
    return get_order_or_404(db, order.id)


@app.get("/orders", response_model=list[OrderOut])
def my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    customer: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    return db.query(Order).filter(Order.customer_id == customer.id).order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = get_order_or_404(db, order_id)
    allowed = (
        user.role == "admin"
        or (user.role == "customer" and order.customer_id == user.id)
        or (user.role == "delivery" and order.delivery_partner_id == user.id)
        or (user.role == "owner" and order.restaurant.owner_id == user.id)
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="You cannot view this order")
    return order


@app.post("/orders/{order_id}/pay", response_model=OrderOut)
def mock_payment(
    order_id: int,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles("customer")),
):
    order = get_order_or_404(db, order_id)
    if order.customer_id != customer.id:
        raise HTTPException(status_code=403, detail="You cannot pay for this order")
    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled orders cannot be paid")
    order.payment_status = "paid"  # Mock payment only; no real money is collected.
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return order


@app.post("/orders/{order_id}/reviews", status_code=201)
def add_review(
    order_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles("customer")),
):
    order = get_order_or_404(db, order_id)
    if order.customer_id != customer.id:
        raise HTTPException(status_code=403, detail="You can review only your own orders")
    if order.status != "delivered":
        raise HTTPException(status_code=400, detail="You can review after the order is delivered")
    if order.review:
        raise HTTPException(status_code=409, detail="A review has already been submitted for this order")
    review = Review(restaurant_id=order.restaurant_id, customer_id=customer.id, order_id=order.id, rating=payload.rating, comment=payload.comment.strip())
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"message": "Thank you for your review", "review_id": review.id, "rating": review.rating}


# -----------------------------------------------------------------------------
# Restaurant owner: profile, menu management and incoming orders
# -----------------------------------------------------------------------------

@app.get("/owner/restaurant", response_model=RestaurantOut)
def owner_restaurant(owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    return get_owned_restaurant(db, owner)


@app.post("/owner/restaurant", response_model=RestaurantOut, status_code=201)
def create_owner_restaurant(payload: RestaurantCreate, owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    if db.query(Restaurant).filter(Restaurant.owner_id == owner.id).first():
        raise HTTPException(status_code=409, detail="You already have a restaurant profile")
    restaurant = Restaurant(**payload.model_dump(), owner_id=owner.id)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@app.get("/owner/menu", response_model=list[MenuItemOut])
def owner_menu(owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    restaurant = get_owned_restaurant(db, owner)
    return db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).order_by(MenuItem.category, MenuItem.name).all()


@app.post("/owner/menu", response_model=MenuItemOut, status_code=201)
def add_menu_item(payload: MenuItemCreate, owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    restaurant = get_owned_restaurant(db, owner)
    item = MenuItem(restaurant_id=restaurant.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.patch("/owner/menu/{item_id}", response_model=MenuItemOut)
def update_menu_item(item_id: int, payload: MenuItemUpdate, owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    restaurant = get_owned_restaurant(db, owner)
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/owner/menu/{item_id}")
def remove_menu_item(item_id: int, owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    restaurant = get_owned_restaurant(db, owner)
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.is_available = False  # Soft remove keeps historical order records intact.
    db.commit()
    return {"message": "Menu item marked unavailable"}


@app.get("/owner/orders", response_model=list[OrderOut])
def owner_orders(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=30, ge=1, le=100),
    owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db),
):
    restaurant = get_owned_restaurant(db, owner)
    return db.query(Order).filter(Order.restaurant_id == restaurant.id).order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@app.patch("/owner/orders/{order_id}/status", response_model=OrderOut)
def owner_update_order(order_id: int, payload: StatusUpdate, owner: User = Depends(require_roles("owner")), db: Session = Depends(get_db)):
    restaurant = get_owned_restaurant(db, owner)
    order = get_order_or_404(db, order_id)
    if order.restaurant_id != restaurant.id:
        raise HTTPException(status_code=403, detail="This order does not belong to your restaurant")
    allowed_statuses = {"confirmed", "preparing", "cancelled"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Owner can set status to confirmed, preparing or cancelled")
    if order.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=400, detail="This order is already closed")
    order.status = payload.status
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return order


# -----------------------------------------------------------------------------
# Delivery partner: assigned work and delivery status
# -----------------------------------------------------------------------------

@app.get("/delivery/orders", response_model=list[OrderOut])
def delivery_orders(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=30, ge=1, le=100),
    partner: User = Depends(require_roles("delivery")), db: Session = Depends(get_db),
):
    return db.query(Order).filter(Order.delivery_partner_id == partner.id).order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@app.patch("/delivery/orders/{order_id}/status", response_model=OrderOut)
def delivery_update_status(order_id: int, payload: StatusUpdate, partner: User = Depends(require_roles("delivery")), db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_id)
    if order.delivery_partner_id != partner.id:
        raise HTTPException(status_code=403, detail="This order is not assigned to you")
    if payload.status not in {"out_for_delivery", "delivered"}:
        raise HTTPException(status_code=400, detail="Delivery partner can set status to out_for_delivery or delivered")
    if payload.status == "out_for_delivery" and order.status not in {"preparing", "confirmed", "out_for_delivery"}:
        raise HTTPException(status_code=400, detail="Restaurant must confirm the order before dispatch")
    if payload.status == "delivered" and order.status != "out_for_delivery":
        raise HTTPException(status_code=400, detail="Mark the order out for delivery first")
    order.status = payload.status
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return order


# -----------------------------------------------------------------------------
# Admin: overview, user/order lists and delivery assignment
# -----------------------------------------------------------------------------

@app.get("/admin/dashboard")
def admin_dashboard(admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return {
        "total_users": db.query(User).count(),
        "total_customers": db.query(User).filter(User.role == "customer").count(),
        "total_restaurants": db.query(Restaurant).count(),
        "total_orders": db.query(Order).count(),
        "pending_orders": db.query(Order).filter(Order.status == "pending").count(),
        "delivered_orders": db.query(Order).filter(Order.status == "delivered").count(),
    }


@app.get("/admin/users", response_model=list[UserOut])
def admin_users(
    role: Optional[str] = Query(default=None, pattern="^(customer|owner|delivery|admin)$"),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@app.get("/admin/orders", response_model=list[OrderOut])
def admin_orders(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db),
):
    return db.query(Order).order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@app.patch("/admin/orders/{order_id}/assign", response_model=OrderOut)
def assign_delivery_partner(
    order_id: int, payload: AssignDeliveryInput,
    admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db),
):
    order = get_order_or_404(db, order_id)
    partner = db.query(User).filter(User.id == payload.delivery_partner_id, User.role == "delivery").first()
    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")
    if order.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=400, detail="Closed orders cannot be assigned")
    order.delivery_partner_id = partner.id
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return order
