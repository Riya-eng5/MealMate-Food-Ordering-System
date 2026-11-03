# MealMate — Online Food Ordering & Restaurant Management System

A full-stack educational MVP built to demonstrate a complete food-order workflow across four roles: Customer, Restaurant Owner, Delivery Partner and Admin.

## 1. Features

### Customer
- Register and log in securely.
- Browse restaurants and search by restaurant name, cuisine or description.
- Browse available menu items and search/filter menu results through the API.
- Add items to a basket, adjust quantities and place an order.
- Complete a **mock payment** (no real payment gateway or money transfer).
- View order history and current order status.
- Submit one rating/review after an order is delivered.

### Restaurant Owner
- View the restaurant profile linked to the owner account.
- Add menu items and show/hide existing items.
- View incoming orders and accept, prepare or cancel orders.

### Delivery Partner
- View orders assigned by the admin.
- Move an eligible order to `out_for_delivery`, then `delivered`.
- View previous deliveries in the same list.

### Admin
- View platform metrics, registered users and all orders.
- Assign an available delivery-partner account to an order.

### Technical features
- React responsive frontend.
- FastAPI REST backend with automatically generated Swagger/OpenAPI docs.
- SQLite relational database using SQLAlchemy ORM.
- JWT bearer authentication and role-based authorization.
- Input validation, API error responses and request logging.
- Pagination and search parameters on list endpoints.
- Unit/API tests with pytest.
- Dockerfiles and Docker Compose configuration.
- Postman API collection and ER/database schema documentation.

## 2. Demo accounts

The backend creates these accounts and a sample restaurant/menu on first start. All demo accounts use the password `demo12345`.

| Role | Email | Password |
|---|---|---|
| Customer | `customer@example.com` | `demo12345` |
| Restaurant Owner | `owner@example.com` | `demo12345` |
| Delivery Partner | `delivery@example.com` | `demo12345` |
| Admin | `admin@example.com` | `demo12345` |

A new account registered from the UI receives the `customer` role. Demo role accounts are only for local evaluation.

## 3. Run locally (Windows + VS Code)

You need Python 3.11 or newer and Node.js 20 or newer.

### Backend

Open a terminal in the project folder:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

- Interactive API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

The SQLite database file `food_ordering.db` is created in the backend folder automatically. The sample restaurant and demo users are seeded on first run.

### Frontend

Open a **second** VS Code terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The frontend calls `http://localhost:8000` by default. To use a different backend URL, create `frontend/.env` with:

```env
VITE_API_URL=http://localhost:8000
```

Restart the Vite server after changing `.env`.

## 4. Run tests

From the `backend` folder, activate the virtual environment and run:

```powershell
python -m pytest -q
```

The tests cover the health endpoint, restaurant browsing, customer checkout/mock payment, role authorization and owner restaurant access.

## 5. Run with Docker

From the project root:

```powershell
docker compose up --build
```

- Frontend: `http://localhost:8080`
- Backend docs: `http://localhost:8000/docs`

The database is kept in the named Docker volume `food_data`.

## 6. Order lifecycle

1. Customer places an order → `pending`.
2. Restaurant owner accepts it → `confirmed`.
3. Restaurant owner starts preparation → `preparing`.
4. Admin assigns a delivery partner.
5. Delivery partner starts the trip → `out_for_delivery`.
6. Delivery partner completes the drop → `delivered`.
7. Customer can then submit a review.

The mock payment endpoint changes `payment_status` to `paid`; it does not connect to a payment provider.

## 7. Main API routes

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a customer |
| POST | `/auth/login` | Public | Login and receive JWT |
| GET | `/auth/me` | Authenticated | Current account |
| GET | `/restaurants` | Public | Search and browse restaurants |
| GET | `/restaurants/{id}/menu` | Public | Browse restaurant menu |
| POST | `/orders` | Customer | Place an order |
| GET | `/orders` | Customer | View order history |
| GET | `/orders/{id}` | Related user/admin | View order tracking/details |
| POST | `/orders/{id}/pay` | Customer | Mock payment |
| POST | `/orders/{id}/reviews` | Customer | Review a delivered order |
| GET/POST | `/owner/restaurant` | Owner | Read/create restaurant profile |
| GET/POST | `/owner/menu` | Owner | List/add menu items |
| PATCH/DELETE | `/owner/menu/{id}` | Owner | Update/hide a menu item |
| GET | `/owner/orders` | Owner | View incoming orders |
| PATCH | `/owner/orders/{id}/status` | Owner | Confirm, prepare or cancel |
| GET | `/delivery/orders` | Delivery partner | View assigned deliveries |
| PATCH | `/delivery/orders/{id}/status` | Delivery partner | Update delivery status |
| GET | `/admin/dashboard` | Admin | Platform metrics |
| GET | `/admin/users` | Admin | User directory and role filter |
| GET | `/admin/orders` | Admin | All orders |
| PATCH | `/admin/orders/{id}/assign` | Admin | Assign delivery partner |

For request/response examples, use Swagger at `/docs` or import `Postman_Collection.json` into Postman.

## 8. Database and design documents

- `PROJECT_REPORT.md` — project overview, modules, architecture, workflow, testing and conclusion.
- `docs/ER_DIAGRAM.md` — Mermaid ER diagram and relationships.
- `docs/DATABASE_SCHEMA.md` — tables, keys and normalization notes.
- `Postman_Collection.json` — API requests grouped by role.

## 9. Important limitations and production checklist

This is a working MVP for an internship assignment, not a production food-delivery service. Before a public production launch:

- Replace the development JWT secret with a long random secret and keep it out of source control.
- Restrict CORS to the actual frontend domain.
- Use PostgreSQL or another managed database, backups and migrations.
- Integrate a real payment gateway only with server-side verification and webhook handling.
- Add email/phone verification, password reset, rate limiting and stronger abuse protection.
- Add address/geolocation and real-time delivery updates if required.
- Add more tests for all edge cases and deploy over HTTPS.

## 10. Personal verification before submission

Run the app locally and test each demo role. Replace this section with your own short notes after you have tested it:

- What I tested:
- One issue I fixed:
- What I would improve next:

Do not submit a deployment URL until the application is actually deployed and tested.

## Personal Verification

### What I tested
- Customer ordering
- Mock payment
- Order tracking
- Restaurant owner order management
- Admin delivery assignment
- Delivery partner status updates
- Customer reviews

### One issue I fixed
Fixed the "React is not defined" error in App.jsx by adding the React import.

### What I would improve next
- Integrate a real payment gateway.
- Migrate to PostgreSQL.
- Add real-time delivery tracking.
