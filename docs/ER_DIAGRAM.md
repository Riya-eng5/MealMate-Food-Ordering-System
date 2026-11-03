# Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o| RESTAURANTS : owns
    USERS ||--o{ ORDERS : places
    USERS ||--o{ ORDERS : delivers
    RESTAURANTS ||--o{ MENU_ITEMS : offers
    RESTAURANTS ||--o{ ORDERS : receives
    ORDERS ||--|{ ORDER_ITEMS : contains
    MENU_ITEMS ||--o{ ORDER_ITEMS : appears_in
    USERS ||--o{ REVIEWS : writes
    RESTAURANTS ||--o{ REVIEWS : receives
    ORDERS ||--o| REVIEWS : reviewed_by

    USERS {
      int id PK
      string name
      string email UK
      string password_hash
      string role
      string address
    }
    RESTAURANTS {
      int id PK
      string name
      string description
      string cuisine
      string address
      int owner_id FK
      boolean is_active
    }
    MENU_ITEMS {
      int id PK
      int restaurant_id FK
      string name
      string description
      string category
      decimal price
      boolean is_available
    }
    ORDERS {
      int id PK
      int customer_id FK
      int restaurant_id FK
      int delivery_partner_id FK
      string status
      decimal total_amount
      string payment_status
      string delivery_address
      datetime created_at
    }
    ORDER_ITEMS {
      int id PK
      int order_id FK
      int menu_item_id FK
      string item_name
      decimal unit_price
      int quantity
    }
    REVIEWS {
      int id PK
      int restaurant_id FK
      int customer_id FK
      int order_id FK
      int rating
      string comment
      datetime created_at
    }
```

## Relationship notes

- One owner manages one restaurant in this MVP; one restaurant has many menu items.
- A customer can place many orders. Each order belongs to one restaurant and can be assigned to one delivery partner.
- An order contains one or more order-item rows. `item_name` and `unit_price` are snapshots so an old order remains readable if the restaurant later edits its menu.
- A customer can submit at most one review for a delivered order.
- The `role` column distinguishes customer, owner, delivery and admin accounts.
