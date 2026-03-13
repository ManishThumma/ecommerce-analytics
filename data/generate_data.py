"""
Synthetic E-Commerce Data Generator
Generates realistic datasets mimicking Amazon-scale transactional data.
Produces: customers, products, orders, order_items, events (clickstream)
"""

import random
import json
import csv
import os
from datetime import datetime, timedelta

random.seed(42)

# ── Config ──────────────────────────────────────────────────────────────────
NUM_CUSTOMERS   = 5_000
NUM_PRODUCTS    = 500
NUM_ORDERS      = 40_000
START_DATE      = datetime(2022, 1, 1)
END_DATE        = datetime(2024, 12, 31)

CATEGORIES = {
    "Electronics":      (50,  2000, 0.12),
    "Books":            (5,   60,   0.25),
    "Home & Kitchen":   (10,  300,  0.18),
    "Clothing":         (8,   200,  0.22),
    "Sports & Fitness": (15,  400,  0.14),
    "Beauty":           (8,   150,  0.16),
    "Toys & Games":     (10,  180,  0.20),
    "Grocery":          (2,   80,   0.30),
}

REGIONS = ["US-West", "US-East", "US-Central", "US-South", "International"]
CHANNELS = ["organic_search", "paid_search", "email", "direct", "social", "affiliate"]
STATUSES = ["delivered", "delivered", "delivered", "delivered", "returned", "cancelled"]


# ── Helpers ──────────────────────────────────────────────────────────────────
def rand_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def weighted_rand_date(start: datetime, end: datetime) -> datetime:
    """Skew orders toward Q4 (holiday effect)."""
    d = rand_date(start, end)
    # 30% chance to push into Oct-Dec
    if random.random() < 0.30:
        year = random.randint(start.year, end.year)
        d = datetime(year, random.randint(10, 12), random.randint(1, 28),
                     random.randint(0, 23), random.randint(0, 59))
    return min(d, end)


# ── Generators ───────────────────────────────────────────────────────────────
def generate_customers(n: int) -> list[dict]:
    customers = []
    for i in range(1, n + 1):
        signup = rand_date(START_DATE, END_DATE - timedelta(days=30))
        customers.append({
            "customer_id":   f"C{i:05d}",
            "signup_date":   signup.strftime("%Y-%m-%d"),
            "region":        random.choice(REGIONS),
            "channel":       random.choice(CHANNELS),
            "is_prime":      random.random() < 0.55,        # 55% Prime penetration
            "age_group":     random.choice(["18-24","25-34","35-44","45-54","55+"]),
        })
    return customers


def generate_products(n: int) -> list[dict]:
    products = []
    for i in range(1, n + 1):
        cat = random.choice(list(CATEGORIES.keys()))
        lo, hi, _ = CATEGORIES[cat]
        price = round(random.uniform(lo, hi), 2)
        cost  = round(price * random.uniform(0.35, 0.65), 2)
        products.append({
            "product_id":   f"P{i:04d}",
            "category":     cat,
            "price":        price,
            "cost":         cost,
            "rating":       round(random.uniform(3.0, 5.0), 1),
            "review_count": random.randint(0, 15000),
            "is_fba":       random.random() < 0.70,         # Fulfilled by Amazon
        })
    return products


def generate_orders(customers, products, n: int):
    orders, items = [], []
    order_id = 1

    # Pre-index products by category for cross-sell realism
    prod_by_cat: dict[str, list] = {}
    for p in products:
        prod_by_cat.setdefault(p["category"], []).append(p)

    customer_order_count: dict[str, int] = {}

    for _ in range(n):
        cust    = random.choice(customers)
        cid     = cust["customer_id"]
        odate   = weighted_rand_date(
            datetime.strptime(cust["signup_date"], "%Y-%m-%d"), END_DATE
        )
        status  = random.choice(STATUSES)
        oid     = f"O{order_id:07d}"
        order_id += 1

        # Items in this order (1–4, Prime members order slightly more)
        n_items = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
        if cust["is_prime"]:
            n_items = min(n_items + random.randint(0, 1), 4)

        chosen_prods = random.sample(products, min(n_items, len(products)))
        total = 0.0

        for prod in chosen_prods:
            qty       = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
            discount  = round(random.uniform(0, 0.25), 2)  # 0-25% discount
            unit_rev  = round(prod["price"] * (1 - discount), 2)
            line_rev  = round(unit_rev * qty, 2)
            total    += line_rev
            items.append({
                "order_id":    oid,
                "product_id":  prod["product_id"],
                "category":    prod["category"],
                "quantity":    qty,
                "unit_price":  prod["price"],
                "discount":    discount,
                "revenue":     line_rev,
                "order_date":  odate.strftime("%Y-%m-%d"),
            })

        customer_order_count[cid] = customer_order_count.get(cid, 0) + 1
        orders.append({
            "order_id":       oid,
            "customer_id":    cid,
            "order_date":     odate.strftime("%Y-%m-%d"),
            "status":         status,
            "total_amount":   round(total, 2),
            "is_prime_order": cust["is_prime"],
            "region":         cust["region"],
            "channel":        cust["channel"],
        })

    return orders, items


def generate_events(customers, products, n_events: int = 200_000) -> list[dict]:
    """Simplified clickstream: browse → add_to_cart → purchase funnel."""
    events = []
    event_types = ["view", "view", "view", "add_to_cart", "add_to_cart", "purchase"]
    for _ in range(n_events):
        cust = random.choice(customers)
        prod = random.choice(products)
        events.append({
            "customer_id": cust["customer_id"],
            "product_id":  prod["product_id"],
            "category":    prod["category"],
            "event_type":  random.choice(event_types),
            "event_date":  rand_date(START_DATE, END_DATE).strftime("%Y-%m-%d"),
            "device":      random.choice(["mobile", "desktop", "tablet"]),
        })
    return events


# ── Writers ──────────────────────────────────────────────────────────────────
def write_csv(rows: list[dict], path: str):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):>8,} rows → {path}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__))
    print("Generating synthetic e-commerce data...\n")

    customers = generate_customers(NUM_CUSTOMERS)
    products  = generate_products(NUM_PRODUCTS)
    orders, items = generate_orders(customers, products, NUM_ORDERS)
    events    = generate_events(customers, products)

    write_csv(customers, f"{out}/customers.csv")
    write_csv(products,  f"{out}/products.csv")
    write_csv(orders,    f"{out}/orders.csv")
    write_csv(items,     f"{out}/order_items.csv")
    write_csv(events,    f"{out}/events.csv")

    print(f"\nDone. Total revenue: ${sum(o['total_amount'] for o in orders):,.2f}")
