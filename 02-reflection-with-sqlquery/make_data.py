"""Generate a synthetic product-events dataset in SQLite.

Writes inventory.db with a single `events` table modeling everything that
happens to a product catalog: an initial `insert`, periodic `restock`s,
individual `sale`s, and occasional `price_update`s. This event-log shape
is deliberate - a naive query ("SELECT unit_price FROM events WHERE ...")
gets the wrong answer for current stock or current price, which is what
makes the reflection loop worth watching.

Deterministic: same seed -> same DB, every time.
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "inventory.db"
SEED = 11
random.seed(SEED)

# --- catalog ---------------------------------------------------------------

CATALOG = [
    # (product_name, brand, category, color, launch_price)
    ("Aero Runner",        "Velox",    "footwear",    "black",  129.00),
    ("Aero Runner",        "Velox",    "footwear",    "white",  129.00),
    ("Trail Ridge Boot",   "Velox",    "footwear",    "brown",  185.00),
    ("Court Classic",      "Baseline", "footwear",    "white",   89.00),
    ("Court Classic",      "Baseline", "footwear",    "green",   89.00),
    ("Cloud Hoodie",       "Northwind","apparel",     "grey",    74.00),
    ("Cloud Hoodie",       "Northwind","apparel",     "navy",    74.00),
    ("Cloud Hoodie",       "Northwind","apparel",     "black",   74.00),
    ("Storm Shell",        "Northwind","apparel",     "olive",  159.00),
    ("Merino Tee",         "Baseline", "apparel",     "white",   45.00),
    ("Merino Tee",         "Baseline", "apparel",     "black",   45.00),
    ("Trek 25L Pack",      "Summit",   "bags",        "black",  109.00),
    ("Trek 25L Pack",      "Summit",   "bags",        "red",    109.00),
    ("Commuter Sling",     "Summit",   "bags",        "grey",    59.00),
    ("Peak Cap",           "Velox",    "accessories", "black",   28.00),
    ("Peak Cap",           "Velox",    "accessories", "navy",    28.00),
    ("Wool Beanie",        "Northwind","accessories", "grey",    22.00),
    ("Trail Socks 3-Pack", "Summit",   "accessories", "white",   18.00),
]


def build_products():
    """Assign product_ids in catalog order so tests are reproducible."""
    return [
        {"product_id": 1000 + i,
         "product_name": name, "brand": brand, "category": cat,
         "color": color, "price": price}
        for i, (name, brand, cat, color, price) in enumerate(CATALOG)
    ]


# --- event stream ----------------------------------------------------------

START = datetime(2025, 5, 1, 9, 0, 0)
END   = datetime(2025, 8, 24, 18, 0, 0)  # ~ 4 months of activity


def iter_days(start: datetime, end: datetime):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def make_events(products):
    """Return a chronologically ordered list of event dicts.

    Rules kept deliberately simple:
      - insert:       qty_delta = starting stock, unit_price = launch price
      - restock:      qty_delta > 0, unit_price = NULL (restock isn't repricing)
      - sale:         qty_delta < 0 (a single unit), unit_price = current price
      - price_update: qty_delta = 0, unit_price = new price
    """
    events = []
    current_price = {}   # product_id -> current unit price
    stock = {}           # product_id -> current on-hand

    # 1) Insert every product on day 1 with a starting stock.
    for p in products:
        starting = random.randint(40, 120)
        current_price[p["product_id"]] = p["price"]
        stock[p["product_id"]] = starting
        events.append({
            "product": p,
            "action": "insert",
            "qty_delta": starting,
            "unit_price": p["price"],
            "notes": "initial catalog load",
            "ts": START + timedelta(minutes=random.randint(0, 30)),
        })

    # 2) Walk day-by-day and emit restocks, sales, and occasional repricing.
    for day in iter_days(START + timedelta(days=1), END):
        # A handful of products get restocked on any given weekday.
        if day.weekday() < 5 and random.random() < 0.55:
            for p in random.sample(products, k=random.randint(1, 3)):
                qty = random.randint(15, 60)
                stock[p["product_id"]] += qty
                events.append({
                    "product": p,
                    "action": "restock",
                    "qty_delta": qty,
                    "unit_price": None,
                    "notes": random.choice([
                        "PO fulfilled", "warehouse transfer",
                        "supplier shipment", "back-in-stock",
                    ]),
                    "ts": day.replace(hour=random.randint(8, 10),
                                      minute=random.randint(0, 59)),
                })

        # Occasional price update - promo or seasonal adjustment.
        if random.random() < 0.15:
            p = random.choice(products)
            old = current_price[p["product_id"]]
            direction = random.choice([-1, -1, +1])  # more markdowns than hikes
            new_price = round(max(5.0, old * (1 + direction * random.uniform(0.05, 0.20))), 2)
            current_price[p["product_id"]] = new_price
            events.append({
                "product": p,
                "action": "price_update",
                "qty_delta": 0,
                "unit_price": new_price,
                "notes": "promo markdown" if direction < 0 else "cost pass-through",
                "ts": day.replace(hour=random.randint(9, 11),
                                  minute=random.randint(0, 59)),
            })

        # Sales: weekends are quieter, footwear + apparel sell more.
        base = 22 if day.weekday() < 5 else 10
        n_sales = max(0, int(random.gauss(base, base * 0.3)))
        for _ in range(n_sales):
            weights = [
                3 if p["category"] in ("footwear", "apparel") else 1
                for p in products
            ]
            p = random.choices(products, weights=weights)[0]
            if stock[p["product_id"]] <= 0:
                continue   # skip - out of stock
            stock[p["product_id"]] -= 1
            events.append({
                "product": p,
                "action": "sale",
                "qty_delta": -1,
                "unit_price": current_price[p["product_id"]],
                "notes": None,
                "ts": day.replace(hour=random.randint(10, 20),
                                  minute=random.randint(0, 59)),
            })

    events.sort(key=lambda e: e["ts"])
    return events


# --- write -----------------------------------------------------------------

SCHEMA = """
CREATE TABLE events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL,
    product_name TEXT    NOT NULL,
    brand        TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    color        TEXT    NOT NULL,
    action       TEXT    NOT NULL CHECK (action IN ('insert','restock','sale','price_update')),
    qty_delta    INTEGER NOT NULL,
    unit_price   REAL,
    notes        TEXT,
    ts           TEXT    NOT NULL
);
CREATE INDEX idx_events_product ON events(product_id);
CREATE INDEX idx_events_action  ON events(action);
CREATE INDEX idx_events_ts      ON events(ts);
"""


def write_db(events):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.executemany(
        """INSERT INTO events
              (product_id, product_name, brand, category, color,
               action, qty_delta, unit_price, notes, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                e["product"]["product_id"],
                e["product"]["product_name"],
                e["product"]["brand"],
                e["product"]["category"],
                e["product"]["color"],
                e["action"],
                e["qty_delta"],
                e["unit_price"],
                e["notes"],
                e["ts"].strftime("%Y-%m-%d %H:%M:%S"),
            )
            for e in events
        ],
    )
    conn.commit()
    conn.close()


def main():
    products = build_products()
    events = make_events(products)
    write_db(events)
    print(f"Wrote {DB_PATH} - {len(events):,} events across {len(products)} products")
    print(f"Range: {events[0]['ts']} -> {events[-1]['ts']}")


if __name__ == "__main__":
    main()
