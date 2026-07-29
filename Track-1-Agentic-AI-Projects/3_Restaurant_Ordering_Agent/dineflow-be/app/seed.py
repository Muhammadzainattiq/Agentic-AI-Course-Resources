"""Seed the menu. Idempotent — run with `uv run python -m app.seed`.

Prices are in the unit configured by RESTAURANT_CURRENCY (PKR).
Re-running updates existing rows by name rather than duplicating them.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.db import postgres

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

# Placeholder photo for every dish, served from the frontend's /public.
# Replace per-item by updating menu_items.image_url — re-seeding will not
# clobber a URL that has already been customised (see the COALESCE below).
DEFAULT_IMAGE_URL = "/menu.jpeg"

# (name, category, description, price, tags, is_available)
MENU: list[tuple[str, str, str, float, list[str], bool]] = [
    # ── Starters ────────────────────────────────────────────────────────────
    ("Garlic Bread", "starters", "Wood-fired sourdough, roasted garlic butter, parsley.", 480, ["vegetarian"], True),
    ("Cheese Garlic Bread", "starters", "Garlic bread blanketed in melted mozzarella.", 650, ["vegetarian"], True),
    ("Chicken Wings", "starters", "Six wings tossed in house hot sauce, blue cheese dip.", 890, ["spicy"], True),
    ("Honey Chilli Wings", "starters", "Crisp wings glazed in honey, chilli and sesame.", 950, ["spicy"], True),
    ("Hummus Plate", "starters", "Chickpea hummus, olive oil, warm pita.", 620, ["vegan", "vegetarian"], True),
    ("Loaded Nachos", "starters", "Tortilla chips, cheese sauce, jalapeños, salsa.", 780, ["vegetarian", "spicy"], True),
    ("Chicken Spring Rolls", "starters", "Six rolls, sweet chilli dip.", 560, [], True),
    ("Mozzarella Sticks", "starters", "Golden fried, marinara on the side.", 720, ["vegetarian"], True),

    # ── Soups ───────────────────────────────────────────────────────────────
    ("Hot & Sour Soup", "soups", "Chicken, mushroom, white pepper, vinegar.", 450, ["spicy"], True),
    ("Chicken Corn Soup", "soups", "Sweetcorn, shredded chicken, egg drop.", 420, [], True),
    ("Cream of Mushroom", "soups", "Button mushrooms, cream, thyme.", 480, ["vegetarian"], True),
    ("Thai Coconut Soup", "soups", "Lemongrass, galangal, coconut milk, chilli.", 590, ["spicy", "gluten-free"], True),

    # ── Pizzas ──────────────────────────────────────────────────────────────
    ("Margherita Pizza", "pizzas", "San Marzano tomato, fior di latte, basil.", 1250, ["vegetarian"], True),
    ("Pepperoni Pizza", "pizzas", "Double pepperoni, mozzarella, chilli honey.", 1650, ["spicy"], True),
    ("Chicken Tikka Pizza", "pizzas", "Tikka chicken, onion, coriander, mint drizzle.", 1750, ["spicy"], True),
    ("Fajita Sizzler Pizza", "pizzas", "Peppers, onion, fajita chicken, jalapeño.", 1800, ["spicy"], True),
    ("Four Cheese Pizza", "pizzas", "Mozzarella, cheddar, parmesan, blue cheese.", 1900, ["vegetarian"], True),
    ("Veggie Supreme Pizza", "pizzas", "Olives, corn, capsicum, mushroom, onion.", 1450, ["vegetarian"], True),

    # ── Burgers ─────────────────────────────────────────────────────────────
    ("Classic Beef Burger", "burgers", "Aged beef patty, cheddar, pickles, brioche bun, fries.", 1150, [], True),
    ("Double Beef Burger", "burgers", "Two patties, double cheese, smoked mayo, fries.", 1550, [], True),
    ("Crispy Chicken Burger", "burgers", "Buttermilk-fried chicken, slaw, spicy mayo, fries.", 1050, ["spicy"], True),
    ("Grilled Chicken Burger", "burgers", "Chargrilled fillet, lettuce, tomato, garlic aioli.", 990, [], True),
    ("Zinger Stacker", "burgers", "Two crispy fillets, jalapeño cheese sauce, fries.", 1490, ["spicy"], True),
    ("Falafel Burger", "burgers", "Herbed falafel patty, tahini, pickled onion.", 890, ["vegan", "vegetarian"], True),

    # ── Sandwiches & Wraps ──────────────────────────────────────────────────
    ("Chicken Shawarma Wrap", "sandwiches", "Garlic sauce, pickles, fries in the wrap.", 750, [], True),
    ("Beef Shawarma Wrap", "sandwiches", "Slow-roasted beef, tahini, sumac onion.", 850, [], True),
    ("Falafel Wrap", "sandwiches", "Crisp falafel, tahini, pickled turnip, flatbread.", 680, ["vegan", "vegetarian"], True),
    ("Club Sandwich", "sandwiches", "Triple decker, chicken, egg, fries.", 950, [], True),
    ("Grilled Cheese Sandwich", "sandwiches", "Three cheeses on sourdough, tomato soup dip.", 720, ["vegetarian"], True),

    # ── BBQ & Grill ─────────────────────────────────────────────────────────
    ("Chicken Malai Boti", "bbq", "Eight pieces, cream-marinated, charcoal grilled.", 1350, ["gluten-free"], True),
    ("Seekh Kebab", "bbq", "Four skewers, minced beef, green chilli, coriander.", 1200, ["spicy", "gluten-free"], True),
    ("Chicken Tikka (Half)", "bbq", "Bone-in leg quarter, classic red masala.", 750, ["spicy", "gluten-free"], True),
    ("Beef Bihari Boti", "bbq", "Papaya-tenderised beef, raw spice paste.", 1550, ["spicy", "gluten-free"], True),
    ("Mixed Grill Platter", "bbq", "Malai boti, seekh, tikka, naan and chutney. Serves two.", 2650, ["spicy"], True),
    ("Grilled Fish Steak", "bbq", "Sole fillet, lemon butter, charred greens.", 1850, ["gluten-free"], False),

    # ── Karahi & Curries ────────────────────────────────────────────────────
    ("Butter Chicken", "curries", "Slow-cooked chicken in tomato-cream gravy.", 1450, ["spicy"], True),
    ("Chicken Karahi (Half)", "curries", "Wok-fired with tomato, ginger and green chilli.", 1600, ["spicy", "gluten-free"], True),
    ("Mutton Karahi (Half)", "curries", "Bone-in mutton, black pepper, slow simmered.", 2450, ["spicy", "gluten-free"], True),
    ("Daal Makhani", "curries", "Black lentils, butter, overnight simmer.", 850, ["vegetarian"], True),
    ("Palak Paneer", "curries", "Spinach, house paneer, garam masala.", 980, ["vegetarian", "gluten-free"], True),
    ("Chana Masala", "curries", "Chickpeas, onion-tomato masala, dried mango.", 780, ["vegan", "vegetarian"], True),

    # ── Rice & Biryani ──────────────────────────────────────────────────────
    ("Chicken Biryani", "rice", "Layered basmati, bone-in chicken, kewra, raita.", 890, ["spicy"], True),
    ("Beef Pulao", "rice", "Yakhni-cooked rice, tender beef shanks.", 950, ["gluten-free"], True),
    ("Mutton Biryani", "rice", "Slow-cooked mutton, saffron, fried onion.", 1350, ["spicy"], True),
    ("Egg Fried Rice", "rice", "Wok-tossed with spring onion and soy.", 620, ["vegetarian"], True),
    ("Vegetable Biryani", "rice", "Seasonal vegetables, whole spices, raita.", 750, ["vegetarian"], True),

    # ── Pasta ───────────────────────────────────────────────────────────────
    ("Alfredo Pasta", "pasta", "Fettuccine, cream, parmesan, grilled chicken.", 1250, [], True),
    ("Arrabbiata Pasta", "pasta", "Penne, tomato, garlic, dried chilli.", 1100, ["vegetarian", "spicy", "vegan"], True),
    ("Crunchy Chicken Pasta", "pasta", "Fried chicken strips over creamy pink sauce.", 1450, ["spicy"], True),
    ("Baked Mac & Cheese", "pasta", "Four cheeses, breadcrumb crust.", 1200, ["vegetarian"], True),

    # ── Sides ───────────────────────────────────────────────────────────────
    ("French Fries", "sides", "Skin-on, sea salt.", 320, ["vegan", "vegetarian"], True),
    ("Loaded Cheese Fries", "sides", "Cheese sauce, jalapeño, spring onion.", 520, ["vegetarian", "spicy"], True),
    ("Garlic Naan", "sides", "Tandoor-baked, garlic and coriander butter.", 180, ["vegetarian"], True),
    ("Plain Naan", "sides", "Fresh from the tandoor.", 120, ["vegan", "vegetarian"], True),
    ("Raita", "sides", "Whisked yoghurt, cucumber, roasted cumin.", 200, ["vegetarian", "gluten-free"], True),
    ("Garden Salad", "sides", "Cucumber, tomato, onion, lemon dressing.", 350, ["vegan", "vegetarian", "gluten-free"], True),
    ("Coleslaw", "sides", "Cabbage, carrot, creamy dressing.", 280, ["vegetarian", "gluten-free"], True),

    # ── Desserts ────────────────────────────────────────────────────────────
    ("Chocolate Brownie", "desserts", "Dark chocolate brownie, vanilla ice cream.", 650, ["vegetarian"], True),
    ("Molten Lava Cake", "desserts", "Warm centre, served with cream.", 720, ["vegetarian"], True),
    ("Baklava", "desserts", "Pistachio baklava, three pieces, honey syrup.", 580, ["vegetarian", "contains-nuts"], True),
    ("Gulab Jamun", "desserts", "Two pieces, warm cardamom syrup.", 400, ["vegetarian"], True),
    ("Kheer", "desserts", "Rice pudding, pistachio, rose water.", 450, ["vegetarian", "gluten-free", "contains-nuts"], True),
    ("Mango Sorbet", "desserts", "Alphonso mango sorbet, mint.", 500, ["vegan", "vegetarian", "gluten-free"], True),
    ("New York Cheesecake", "desserts", "Baked vanilla cheesecake, berry compote.", 780, ["vegetarian"], False),

    # ── Drinks ──────────────────────────────────────────────────────────────
    ("Fresh Lemonade", "drinks", "Lemon, mint, lightly sweetened.", 320, ["vegan", "gluten-free"], True),
    ("Masala Chai", "drinks", "Black tea, cardamom, ginger, milk.", 250, ["vegetarian"], True),
    ("Doodh Patti", "drinks", "Strong milk tea, slow boiled.", 280, ["vegetarian"], True),
    ("Cold Brew Coffee", "drinks", "18-hour cold brew, over ice.", 480, ["vegan", "gluten-free"], True),
    ("Mango Lassi", "drinks", "Yoghurt, mango pulp, cardamom.", 420, ["vegetarian", "gluten-free"], True),
    ("Sweet Lassi", "drinks", "Whisked yoghurt, sugar, ice.", 350, ["vegetarian", "gluten-free"], True),
    ("Fresh Lime Soda", "drinks", "Sweet or salted, your call.", 300, ["vegan", "gluten-free"], True),
    ("Sparkling Water", "drinks", "500ml bottle.", 220, ["vegan", "gluten-free"], True),
    ("Soft Drink", "drinks", "Regular bottle, chilled.", 150, ["vegan", "gluten-free"], True),
]


async def seed() -> None:
    settings = get_settings()
    await postgres.init_pool()
    try:
        for name, category, description, price, tags, is_available in MENU:
            await postgres.execute(
                """
                INSERT INTO menu_items
                    (name, category, description, price, tags, is_available, image_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (name) DO UPDATE
                SET category     = EXCLUDED.category,
                    description  = EXCLUDED.description,
                    price        = EXCLUDED.price,
                    tags         = EXCLUDED.tags,
                    is_available = EXCLUDED.is_available,
                    -- Keep a per-dish photo once someone has set one.
                    image_url    = COALESCE(menu_items.image_url, EXCLUDED.image_url)
                """,
                name,
                category,
                description,
                price,
                tags,
                is_available,
                DEFAULT_IMAGE_URL,
            )

        rows = await postgres.fetch(
            """
            SELECT category, count(*) AS n, min(price) AS lo, max(price) AS hi
            FROM menu_items WHERE is_available GROUP BY category ORDER BY category
            """
        )
        logger.info("Seeded %d menu items (%s):", len(MENU), settings.restaurant_currency)
        for r in rows:
            logger.info(
                "  %-12s %2d items  %.0f–%.0f", r["category"], r["n"], r["lo"], r["hi"]
            )
    finally:
        await postgres.close_pool()


if __name__ == "__main__":
    asyncio.run(seed())
