-- Seed data for Restaurant Support & Operations Agent
-- Fixed UUIDs for demo users so AUTH_MODE=demo can map header names to IDs

-- Restaurants
INSERT INTO restaurants (id, name, address, phone) VALUES
  ('a0000000-0000-0000-0000-000000000001'::uuid, 'Spice Garden', '123 MG Road, Mumbai', '+91-22-1234-5678'),
  ('a0000000-0000-0000-0000-000000000002'::uuid, 'Pizza Paradise', '456 Brigade Road, Bangalore', '+91-80-9876-5432'),
  ('a0000000-0000-0000-0000-000000000003'::uuid, 'Dragon Bowl', '789 Park Street, Kolkata', '+91-33-5555-1234')
ON CONFLICT DO NOTHING;

-- Demo users with fixed UUIDs
INSERT INTO profiles (id, name, email, role) VALUES
  ('d0000000-0000-0000-0000-000000000001'::uuid, 'Alice Johnson', 'alice@example.com', 'CUSTOMER'),
  ('d0000000-0000-0000-0000-000000000002'::uuid, 'Bob Smith', 'bob@example.com', 'CUSTOMER'),
  ('d0000000-0000-0000-0000-000000000003'::uuid, 'Carol Davis', 'carol@example.com', 'CUSTOMER')
ON CONFLICT DO NOTHING;

-- Orders: 10 orders across 3 users, covering every status
-- Alice's orders
INSERT INTO orders (id, order_code, user_id, restaurant_id, status, payment_status, total_amount, currency, eta_minutes) VALUES
  ('e0000000-0000-0000-0000-000000000001'::uuid, 'ORD-1005', 'd0000000-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'OUT_FOR_DELIVERY', 'PAID', 450.00, 'INR', 18),
  ('e0000000-0000-0000-0000-000000000002'::uuid, 'ORD-1002', 'd0000000-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000002'::uuid, 'DELIVERED', 'PAID', 799.00, 'INR', NULL),
  ('e0000000-0000-0000-0000-000000000003'::uuid, 'ORD-1003', 'd0000000-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'PREPARING', 'PAID', 325.50, 'INR', 35),
  ('e0000000-0000-0000-0000-000000000004'::uuid, 'ORD-1010', 'd0000000-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000003'::uuid, 'FAILED', 'DEDUCTED_NOT_CONFIRMED', 550.00, 'INR', NULL)
ON CONFLICT DO NOTHING;

-- Bob's orders
INSERT INTO orders (id, order_code, user_id, restaurant_id, status, payment_status, total_amount, currency, eta_minutes) VALUES
  ('e0000000-0000-0000-0000-000000000005'::uuid, 'ORD-1001', 'd0000000-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'CONFIRMED', 'PAID', 299.00, 'INR', 25),
  ('e0000000-0000-0000-0000-000000000006'::uuid, 'ORD-1004', 'd0000000-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000002'::uuid, 'CANCELLED', 'REFUNDED', 425.00, 'INR', NULL),
  ('e0000000-0000-0000-0000-000000000007'::uuid, 'ORD-1006', 'd0000000-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000003'::uuid, 'PLACED', 'PENDING', 180.00, 'INR', 40)
ON CONFLICT DO NOTHING;

-- Carol's orders
INSERT INTO orders (id, order_code, user_id, restaurant_id, status, payment_status, total_amount, currency, eta_minutes) VALUES
  ('e0000000-0000-0000-0000-000000000008'::uuid, 'ORD-1007', 'd0000000-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'READY', 'PAID', 675.00, 'INR', 10),
  ('e0000000-0000-0000-0000-000000000009'::uuid, 'ORD-1008', 'd0000000-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000002'::uuid, 'DELIVERED', 'PAID', 520.00, 'INR', NULL),
  ('e0000000-0000-0000-0000-000000000010'::uuid, 'ORD-1009', 'd0000000-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000003'::uuid, 'OUT_FOR_DELIVERY', 'PAID', 390.00, 'INR', 12)
ON CONFLICT DO NOTHING;

-- Order items
INSERT INTO order_items (order_id, item_name, quantity, price) VALUES
  -- ORD-1005 (Alice, OUT_FOR_DELIVERY)
  ('e0000000-0000-0000-0000-000000000001'::uuid, 'Butter Chicken', 1, 280.00),
  ('e0000000-0000-0000-0000-000000000001'::uuid, 'Garlic Naan', 2, 60.00),
  ('e0000000-0000-0000-0000-000000000001'::uuid, 'Raita', 1, 50.00),
  -- ORD-1002 (Alice, DELIVERED)
  ('e0000000-0000-0000-0000-000000000002'::uuid, 'Margherita Pizza', 1, 399.00),
  ('e0000000-0000-0000-0000-000000000002'::uuid, 'Pepperoni Pizza', 1, 449.00),
  -- ORD-1003 (Alice, PREPARING)
  ('e0000000-0000-0000-0000-000000000003'::uuid, 'Paneer Tikka', 1, 225.50),
  ('e0000000-0000-0000-0000-000000000003'::uuid, 'Mango Lassi', 1, 100.00),
  -- ORD-1010 (Alice, FAILED - payment issue)
  ('e0000000-0000-0000-0000-000000000004'::uuid, 'Kung Pao Chicken', 1, 350.00),
  ('e0000000-0000-0000-0000-000000000004'::uuid, 'Fried Rice', 1, 200.00),
  -- ORD-1001 (Bob, CONFIRMED)
  ('e0000000-0000-0000-0000-000000000005'::uuid, 'Dal Makhani', 1, 199.00),
  ('e0000000-0000-0000-0000-000000000005'::uuid, 'Jeera Rice', 1, 100.00),
  -- ORD-1004 (Bob, CANCELLED)
  ('e0000000-0000-0000-0000-000000000006'::uuid, 'Hawaiian Pizza', 1, 425.00),
  -- ORD-1006 (Bob, PLACED)
  ('e0000000-0000-0000-0000-000000000007'::uuid, 'Spring Rolls', 2, 90.00),
  -- ORD-1007 (Carol, READY)
  ('e0000000-0000-0000-0000-000000000008'::uuid, 'Chicken Biryani', 2, 300.00),
  ('e0000000-0000-0000-0000-000000000008'::uuid, 'Gulab Jamun', 1, 75.00),
  -- ORD-1008 (Carol, DELIVERED)
  ('e0000000-0000-0000-0000-000000000009'::uuid, 'Farmhouse Pizza', 1, 520.00),
  -- ORD-1009 (Carol, OUT_FOR_DELIVERY)
  ('e0000000-0000-0000-0000-000000000010'::uuid, 'Hakka Noodles', 1, 220.00),
  ('e0000000-0000-0000-0000-000000000010'::uuid, 'Manchurian', 1, 170.00)
ON CONFLICT DO NOTHING;
