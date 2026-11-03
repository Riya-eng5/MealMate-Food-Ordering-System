# Database Schema

| Table | Main columns | Purpose |
|---|---|---|
| `users` | `id` (PK), `name`, `email` (unique), `password_hash`, `role`, `address`, `created_at` | Stores all platform accounts. Passwords are never stored as plain text. |
| `restaurants` | `id` (PK), `name`, `description`, `cuisine`, `address`, `owner_id` (FK, unique), `is_active`, `created_at` | Restaurant profile owned by a restaurant-owner account. |
| `menu_items` | `id` (PK), `restaurant_id` (FK), `name`, `description`, `category`, `price`, `is_available` | Individual dishes offered by a restaurant. |
| `orders` | `id` (PK), `customer_id` (FK), `restaurant_id` (FK), `delivery_partner_id` (FK, nullable), `status`, `total_amount`, `payment_status`, `delivery_address`, timestamps | Main order record and delivery/payment state. |
| `order_items` | `id` (PK), `order_id` (FK), `menu_item_id` (FK), `item_name`, `unit_price`, `quantity` | Line items in an order, including price/name snapshots. |
| `reviews` | `id` (PK), `restaurant_id` (FK), `customer_id` (FK), `order_id` (FK, unique), `rating`, `comment`, `created_at` | Customer rating and feedback after delivery. |

## Normalization notes

- **1NF:** each column stores a single value; ordered dishes are separate rows in `order_items` rather than comma-separated text.
- **2NF:** order-line details depend on the order-item row, while restaurant/menu data is stored in its own tables.
- **3NF:** user, restaurant, menu, order and review facts are separated to reduce update anomalies. Foreign keys connect related records.
- `order_items.item_name` and `order_items.unit_price` intentionally keep purchase-time snapshots. These are transaction facts, not duplicate live menu data.
