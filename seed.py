from decimal import Decimal
from sqlalchemy import select

from .auth import hash_password
from .config import ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD
from .database import Base, SessionLocal, engine, wait_for_db
from .models import PriceHistory, Product, User, Wallet

DEMO_PRODUCTS = [
    ("Growth Equity Fund", "Mutual Fund", "GEF", "100", "high", "Diversified equity fund targeting long-term capital growth."),
    ("Balanced Index Fund", "Index Fund", "BIF", "100", "moderate", "Tracks a broad market index with a balanced equity/debt mix."),
    ("Government Bond Fund", "Bond", "GBF", "100", "low", "Invests in government securities for stable, low-risk returns."),
]


def init_db() -> None:
    """Create tables and seed demo data. Safe to run repeatedly."""
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == ADMIN_EMAIL)):
            admin = User(name=ADMIN_NAME, email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role="admin")
            db.add(admin)
            db.flush()
            db.add(Wallet(user_id=admin.id, balance=Decimal("0")))
        if db.query(Product).count() == 0:
            for name, cat, sym, price, risk, desc in DEMO_PRODUCTS:
                p = Product(name=name, category=cat, symbol=sym, price=Decimal(price), risk=risk, description=desc)
                db.add(p)
                db.flush()
                db.add(PriceHistory(product_id=p.id, price=p.price))
        db.commit()


if __name__ == "__main__":
    init_db()
