"""Seed demo data. Coordinates are attributed to OpenStreetMap contributors (ODbL 1.0).

OSM locations:
- https://www.openstreetmap.org/node/13760763501
- https://www.openstreetmap.org/node/309888017
- https://www.openstreetmap.org/node/4377717036
- https://www.openstreetmap.org/node/12402616197
- https://www.openstreetmap.org/node/13429964095

Product prices are illustrative demo prices, not official branch menu prices.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import DATABASE_PATH, SessionLocal, create_tables
from app.models import Product, Shop, Subscription, User, UserRole

TEST_PHONE = "+905550000001"
TEST_PASSWORD = "Kahve2026!"
TEST_EMAIL = "demo@kahvecell.test"
TEST_SHOP_OWNER_PHONE = "+905550000002"

SEED_SHOPS = [
    {
        "name": "Cafe Down Engelsiz Cafe - Kızılay",
        "address": "İzmir 1 Caddesi, Kızılay Mahallesi, Çankaya, Ankara",
        "latitude": 39.9229865,
        "longitude": 32.8539956,
        "products": [
            ("Espresso", "Espresso", "95.00"),
            ("Cappuccino", "Sütlü Kahve", "150.00"),
            ("Caffe Latte", "Sütlü Kahve", "160.00"),
            ("Türk Kahvesi", "Türk Kahvesi", "105.00"),
            ("Americano", "Siyah Kahve", "130.00"),
        ],
    },
    {
        "name": "Coffee Lab - Tunalı Hilmi",
        "address": "82-B, Tunalı Hilmi Caddesi, Remzi Oğuz Arık, Çankaya, Ankara",
        "latitude": 39.9061676,
        "longitude": 32.8607376,
        "products": [
            ("Espresso", "Espresso", "110.00"),
            ("Cappuccino", "Sütlü Kahve", "175.00"),
            ("Caffe Latte", "Sütlü Kahve", "185.00"),
            ("Türk Kahvesi", "Türk Kahvesi", "125.00"),
            ("Americano", "Siyah Kahve", "150.00"),
        ],
    },
    {
        "name": "Coffee Lab - Bahçelievler 7. Cadde",
        "address": "Aşkabat Caddesi (7. Cadde), Yukarı Bahçelievler, Çankaya, Ankara",
        "latitude": 39.9194687,
        "longitude": 32.8273582,
        "products": [
            ("Espresso", "Espresso", "100.00"),
            ("Cappuccino", "Sütlü Kahve", "160.00"),
            ("Caffe Latte", "Sütlü Kahve", "170.00"),
            ("Türk Kahvesi", "Türk Kahvesi", "110.00"),
            ("Americano", "Siyah Kahve", "140.00"),
        ],
    },
    {
        "name": "Kahve Dünyası - İran Caddesi",
        "address": "İran Caddesi, Çankaya Mahallesi, Çankaya, Ankara",
        "latitude": 39.8988525,
        "longitude": 32.8626763,
        "products": [
            ("Espresso", "Espresso", "115.00"),
            ("Cappuccino", "Sütlü Kahve", "180.00"),
            ("Caffe Latte", "Sütlü Kahve", "190.00"),
            ("Türk Kahvesi", "Türk Kahvesi", "130.00"),
            ("Americano", "Siyah Kahve", "155.00"),
        ],
    },
    {
        "name": "Nunchi Coffee Co. - Çayyolu Nokta",
        "address": "Meksika Caddesi, Ümit Mahallesi, Çayyolu, Çankaya, Ankara",
        "latitude": 39.9002019,
        "longitude": 32.6923438,
        "products": [
            ("Espresso", "Espresso", "110.00"),
            ("Cappuccino", "Sütlü Kahve", "175.00"),
            ("Caffe Latte", "Sütlü Kahve", "185.00"),
            ("Türk Kahvesi", "Türk Kahvesi", "125.00"),
            ("Americano", "Siyah Kahve", "150.00"),
        ],
    },
]


def seed_data(session: Session) -> None:
    user = session.scalar(select(User).where(User.phone_number == TEST_PHONE))
    if user is None:
        user = User(
            phone_number=TEST_PHONE,
            full_name="Demo Kullanıcısı",
            email=TEST_EMAIL,
            role="CUSTOMER",
        )
        session.add(user)
    else:
        user.full_name = "Demo Kullanıcısı"
        user.email = TEST_EMAIL
        user.role = "CUSTOMER"

    user.password_hash = hash_password(TEST_PASSWORD)
    session.flush()

    subscription = session.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.plan_type == "STARTER",
        )
        .order_by(Subscription.id)
        .limit(1)
    )
    now = datetime.now(timezone.utc)
    if subscription is None:
        subscription = Subscription(
            user_id=user.id,
            plan_type="STARTER",
            remaining_credits=10,
            status="ACTIVE",
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
        session.add(subscription)
    else:
        subscription.remaining_credits = 10
        subscription.status = "ACTIVE"
        subscription.started_at = now
        subscription.expires_at = now + timedelta(days=30)

    shop_owner = session.scalar(
        select(User).where(User.phone_number == TEST_SHOP_OWNER_PHONE)
    )
    if shop_owner is None:
        shop_owner = User(
            phone_number=TEST_SHOP_OWNER_PHONE,
            full_name="Demo Dükkân Sahibi",
            email="shopowner@kahvecell.test",
            role=UserRole.SHOP_OWNER,
        )
        session.add(shop_owner)
        session.flush()
    else:
        shop_owner.full_name = "Demo Dükkân Sahibi"
        shop_owner.email = "shopowner@kahvecell.test"
        shop_owner.role = UserRole.SHOP_OWNER

    for shop_data in SEED_SHOPS:
        shop = session.scalar(select(Shop).where(Shop.name == shop_data["name"]))
        if shop is None:
            shop = Shop(
                name=shop_data["name"],
                address=shop_data["address"],
                owner_id=shop_owner.id,
            )
            session.add(shop)

        shop.address = shop_data["address"]
        if shop.owner_id is None:
            shop.owner_id = shop_owner.id
        shop.latitude = shop_data["latitude"]
        shop.longitude = shop_data["longitude"]
        shop.opening_hours = {
            "weekdays": "09:00-22:00",
            "weekends": "10:00-22:00",
        }
        session.flush()

        for product_name, category, price in shop_data["products"]:
            product = session.scalar(
                select(Product).where(
                    Product.shop_id == shop.id,
                    Product.name == product_name,
                )
            )
            if product is None:
                product = Product(
                    shop_id=shop.id,
                    name=product_name,
                    category=category,
                    price=Decimal(price),
                )
                session.add(product)
            else:
                product.category = category
                product.price = Decimal(price)
                product.is_available = True


def main() -> None:
    create_tables()

    with SessionLocal.begin() as session:
        seed_data(session)

    print(
        f"Seed tamamlandı: {len(SEED_SHOPS)} dükkân, "
        f"{sum(len(shop['products']) for shop in SEED_SHOPS)} ürün."
    )
    print(f"Test telefonu: {TEST_PHONE}")
    print(f"Test şifresi: {TEST_PASSWORD}")
    print(f"Test dükkân sahibi telefonu: {TEST_SHOP_OWNER_PHONE}")
    print(f"Veritabanı: {DATABASE_PATH}")
    print("Koordinat atfı: OpenStreetMap contributors (ODbL 1.0).")


if __name__ == "__main__":
    main()
