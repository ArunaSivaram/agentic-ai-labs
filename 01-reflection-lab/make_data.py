"""Generate a synthetic coffee-vending-machine sales dataset.

Writes coffee_sales.csv covering Jan 2024 - Mar 2025 so that a
Q1-2024 vs Q1-2025 comparison actually has data on both sides.
Deterministic: same seed -> same file, every time.
"""

import random
from datetime import date, timedelta

import pandas as pd

SEED = 7
random.seed(SEED)

MENU = {
    "Americano": 2.60,
    "Americano with Milk": 3.10,
    "Latte": 3.80,
    "Cappuccino": 3.60,
    "Cortado": 3.20,
    "Espresso": 2.20,
    "Hot Chocolate": 3.90,
    "Cocoa": 3.50,
}

# Relative popularity of each drink. Latte and Americano-with-Milk carry the shop.
POPULARITY = [0.12, 0.20, 0.24, 0.14, 0.08, 0.06, 0.09, 0.07]

CARDS = [f"ANON-{i:04d}" for i in range(1, 260)]


def daily_volume(day: date) -> int:
    """How many cups sold on this day."""
    # Year-over-year growth: 2025 runs ~35% busier than 2024.
    base = 42 if day.year == 2024 else 57
    # Weekends are quiet - this is an office-corridor machine.
    if day.weekday() >= 5:
        base = int(base * 0.45)
    # Winter months sell more hot drinks.
    if day.month in (1, 2):
        base = int(base * 1.10)
    return max(3, int(random.gauss(base, base * 0.18)))


def sale_time() -> str:
    """Morning rush, lunch bump, thin afternoon."""
    bucket = random.choices(["morning", "lunch", "afternoon"], [0.5, 0.28, 0.22])[0]
    hour = {"morning": random.randint(7, 10),
            "lunch": random.randint(11, 13),
            "afternoon": random.randint(14, 18)}[bucket]
    return f"{hour:02d}:{random.randint(0, 59):02d}"


rows = []
day = date(2024, 1, 1)
end = date(2025, 3, 31)

while day <= end:
    for _ in range(daily_volume(day)):
        drink = random.choices(list(MENU), weights=POPULARITY)[0]
        # Card is the dominant payment method, and grows more dominant in 2025.
        card_share = 0.82 if day.year == 2024 else 0.91
        cash_type = "card" if random.random() < card_share else "cash"
        rows.append({
            "date": day.isoformat(),
            "time": sale_time(),
            "cash_type": cash_type,
            "card": random.choice(CARDS) if cash_type == "card" else "",
            "price": MENU[drink],
            "coffee_name": drink,
        })
    day += timedelta(days=1)

df = pd.DataFrame(rows).sort_values(["date", "time"]).reset_index(drop=True)
df.to_csv("coffee_sales.csv", index=False)

print(f"Wrote coffee_sales.csv - {len(df):,} rows, {df['date'].min()} to {df['date'].max()}")
